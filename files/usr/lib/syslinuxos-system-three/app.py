#!/usr/bin/python3
"""SysLinuxOS-System-Three launcher and local network information."""

import argparse
import fcntl
import ipaddress
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import signal
import subprocess
import time
from urllib.request import Request, urlopen

PROC = Path('/proc')
TEMPLATE = Path('/etc/conky/syslinuxos-system-three.conf')
HELPER = '/usr/bin/syslinuxos-system-three'


def output(command):
    try:
        return subprocess.check_output(command, stderr=subprocess.DEVNULL, timeout=3, text=True)
    except (OSError, subprocess.SubprocessError):
        return ''


def resolution():
    text = output(['xrandr', '--current'])
    for pattern in [r' connected primary (\d+)x(\d+)\+', r' connected (\d+)x(\d+)\+',
                    r'^\s+(\d+)x(\d+)\s+.*\*']:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return int(match[1]), int(match[2])
    match = re.search(r'dimensions:\s+(\d+)x(\d+)', output(['xdpyinfo']))
    if match:
        return int(match[1]), int(match[2])
    return 1920, 1080


def layout(width, height, override=None):
    scale = min(width / 960, height / 1080)
    try:
        value = float(override)
        if math.isfinite(value) and value > 0:
            scale = value
    except (TypeError, ValueError):
        pass
    scale = max(0.2, min(scale, 3.0))
    return {'scale': scale, 'width': round(360 * scale), 'height': round(950 * scale),
            'gap_x': 0, 'gap_y': 0}


def safe_text(value):
    return ''.join(char for char in str(value) if char.isprintable() and char not in '$\\{}')[:160]


def atomic_write(path, text):
    temporary = path.with_name('.' + path.name + '.' + str(os.getpid()))
    try:
        temporary.write_text(text)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def find_logo(info, roots=None):
    if roots is None and info.get('ID', '').lower() == 'syslinuxos':
        branded = Path('/usr/share/syslinuxos-branding/data/usr/share/icons/desktop-base/256x256/emblems/emblem-debian-white.png')
        if branded.is_file():
            return branded
    roots = roots if roots is not None else [Path('/usr/share/pixmaps'), Path('/usr/share/icons')]
    identity = info.get('ID', '').lower()
    names = {'syslinuxos': ['syslinuxos-logo.png', 'syslinuxos-logo.svg'],
             'debian': ['debian-logo.png.debian', 'debian-logo.png', 'debian-logo.svg']}.get(identity, [])
    hint = info.get('LOGO', '')
    if re.fullmatch(r'[A-Za-z0-9_.-]+', hint):
        names += [hint + suffix for suffix in ['.svg', '.png', '.xpm']]
    if re.fullmatch(r'[a-z0-9_-]+', identity):
        names += [identity + '-logo.svg', identity + '-logo.png', 'distributor-logo-' + identity + '.svg']
    for name in dict.fromkeys(names):
        for root in roots:
            candidate = root / name
            if candidate.is_file():
                return candidate
            for candidate in root.rglob(name):
                if candidate.is_file():
                    return candidate
    return None


def prepare_logo(directory, info, scale):
    source = find_logo(info)
    if source is None:
        return ''
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf, GLib
    try:
        size = max(96, round(96 * scale))
        image = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(source), size, size, True)
        destination = directory / 'distro-logo.png'
        image.savev(str(destination), 'png', [], [])
        return str(destination)
    except GLib.Error:
        return ''


def public_info(route, refresh=True):
    path = runtime_dir() / 'public.json'
    try:
        cache = json.loads(path.read_text())
        if not isinstance(cache, dict) or cache.get('route') != route:
            cache = {}
    except (OSError, ValueError):
        cache = {}
    now = time.time()
    changed = False
    for key, fetch, ttl in [('public_ip', public_ip, 300), ('isp', isp_name, 3600)]:
        expiry = cache.get(key + '_expires', 0)
        if not isinstance(expiry, (int, float)) or not math.isfinite(expiry):
            expiry = 0
        if refresh and now >= expiry:
            value = fetch()
            cache[key] = value if value != 'N/A' else cache.get(key, 'N/A')
            cache[key + '_expires'] = now + (ttl if value != 'N/A' else 60)
            changed = True
    cache['route'] = route
    if changed:
        atomic_write(path, json.dumps(cache))
    return {key: safe_text(cache.get(key, 'N/A')) for key in ['public_ip', 'isp']}


def fetch_url(url):
    try:
        request = Request(url, headers={'User-Agent': 'SysLinuxOS-System-Three/0.1.0'})
        with urlopen(request, timeout=3) as response:
            return response.read(512).decode('utf-8', errors='replace').strip()
    except (OSError, ValueError):
        return ''


def public_ip():
    try:
        return str(ipaddress.IPv4Address(fetch_url('https://api.ipify.org').strip()))
    except ValueError:
        return 'N/A'


def isp_name():
    text = re.sub(r'^AS\d+\s+', '', fetch_url('https://ipinfo.io/org'))
    text = ''.join(char for char in text if char.isprintable() and char not in '$\\{}')
    return text[:32].strip() or 'N/A'


def owned_process(pid, config):
    try:
        process = PROC / str(pid)
        arguments = (process / 'cmdline').read_bytes().split(b'\0')
        return (process.stat().st_uid == os.getuid()
                and Path(os.fsdecode(arguments[0])).name == 'conky'
                and os.fsencode(config) in arguments)
    except (OSError, ValueError, IndexError):
        return False


def os_info():
    try:
        return platform.freedesktop_os_release()
    except OSError:
        return {'ID': 'linux', 'PRETTY_NAME': 'Linux'}


def network_info():
    interface = os.environ.get('CONKY_NET_INTERFACE', '')
    address = 'N/A'
    try:
        if not interface or interface == 'auto':
            routes = json.loads(output(['ip', '-j', 'route', 'get', '1.1.1.1']))
            route = routes[0] if routes else {}
            interface = route.get('dev', '')
            address = route.get('prefsrc', route.get('src', 'N/A'))
        if not isinstance(interface, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', interface) or interface == 'lo':
            return '', 'N/A'
        if address == 'N/A':
            data = json.loads(output(['ip', '-j', 'address', 'show', 'dev', interface]))
            address = next((entry['local'] for device in data for entry in device.get('addr_info', [])
                            if entry.get('family') == 'inet'), 'N/A')
        if address != 'N/A':
            address = str(ipaddress.IPv4Address(address))
        return interface, address
    except (ValueError, TypeError, IndexError, AttributeError, KeyError):
        return '', 'N/A'


def cpu_temperature():
    for device in Path('/sys/class/hwmon').glob('hwmon*'):
        try:
            if (device / 'name').read_text().strip() not in ['coretemp', 'k10temp', 'zenpower', 'cpu_thermal']:
                continue
            sensors = sorted(device.glob('temp*_input'))
            for sensor in sensors:
                label = sensor.with_name(sensor.name.replace('_input', '_label'))
                if label.exists() and label.read_text().strip() in ['Package id 0', 'Tctl', 'Tdie']:
                    sensors = [sensor]
                    break
            if sensors:
                value = float(sensors[0].read_text()) / 1000
                if math.isfinite(value) and -20 <= value <= 150:
                    return f'{value:.0f}°C'
        except (OSError, ValueError):
            pass
    return 'N/A'


def battery_percent(root=Path('/sys/class/power_supply')):
    for battery in sorted(root.glob('BAT*')):
        try:
            if (battery / 'present').exists() and (battery / 'present').read_text().strip() != '1':
                continue
            capacity = int((battery / 'capacity').read_text().strip())
            if 0 <= capacity <= 100:
                return str(capacity)
        except (OSError, ValueError):
            pass
    return 'N/A'


def cpu_threads():
    return os.cpu_count() or 1


def metrics(refresh=True):
    directory = runtime_dir()
    with (directory / 'metrics.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        info = os_info()
        identity = info.get('ID', 'linux').lower()
        brand = {'syslinuxos': 'SysLinuxOS', 'debian': 'Debian'}.get(identity, info.get('NAME', 'Linux'))
        interface, address = network_info()
        public = public_info(interface + ':' + address, refresh) if interface else {'public_ip': 'N/A', 'isp': 'N/A'}
        try:
            model = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                         if line.startswith(('model name', 'Hardware')))
        except (OSError, StopIteration):
            model = platform.machine()
        data = {'brand': brand, 'os_name': info.get('PRETTY_NAME', 'Linux'), 'cpu_model': model,
                'cpu_temp': cpu_temperature(), 'cpu_threads': cpu_threads(),
                'battery_percent': battery_percent(),
                'interface': interface, 'local_ip': address, **public}
        atomic_write(directory / 'metrics.tsv', ''.join(key + '\t' + safe_text(value) + '\n' for key, value in data.items()))


def render_config(width, height):
    replacements = {**layout(width, height, os.environ.get('CONKY_SYSTEM_THREE_SCALE')),
                    'helper': shlex.quote(HELPER), 'drawing': '/usr/lib/syslinuxos-system-three/drawing.lua'}
    text = TEMPLATE.read_text()
    for key, value in replacements.items():
        text = text.replace('@' + key.upper() + '@', str(value))
    return text


def runtime_dir():
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    base = Path(runtime) if runtime else Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    directory = base / 'syslinuxos-system-three'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise RuntimeError('The runtime directory must belong to the current user.')
    directory.chmod(0o700)
    return directory


def read_pid(path):
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return 0


def control(action):
    directory = runtime_dir()
    config = directory / 'conkyrc-system-three.conf'
    pidfile = directory / 'conky.pid'
    with (directory / 'control.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        pid = read_pid(pidfile)
        running = owned_process(pid, config)
        if action == 'status':
            print('SysLinuxOS-System-Three is running.' if running else 'SysLinuxOS-System-Three is stopped.')
            return 0 if running else 1
        if action == 'stop':
            if running:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                for _ in range(160):
                    if not owned_process(pid, config):
                        break
                    time.sleep(0.05)
                if owned_process(pid, config):
                    raise RuntimeError('SysLinuxOS-System-Three has not stopped yet; try again.')
            pidfile.unlink(missing_ok=True)
            print('SysLinuxOS-System-Three stopped.')
            return 0
        if running:
            print('SysLinuxOS-System-Three is already running.')
            return 0
        screen = resolution()
        settings = layout(*screen, os.environ.get('CONKY_SYSTEM_THREE_SCALE'))
        logo = prepare_logo(directory, os_info(), settings['scale'])
        metrics(refresh=False)
        config.write_text(render_config(*screen))
        environment = os.environ.copy()
        environment.update(CONKY_SYSTEM_THREE_LOGO=logo, CONKY_SYSTEM_THREE_DATA=str(directory / 'metrics.tsv'))
        with (directory / 'conky.log').open('w') as log:
            process = subprocess.Popen(['conky', '--config', str(config)], stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=environment)
        time.sleep(0.4)
        if process.poll() is not None:
            raise RuntimeError('Conky could not start. See ' + str(directory / 'conky.log'))
        pidfile.write_text(str(process.pid))
        print('SysLinuxOS-System-Three started.')
        return 0


def main():
    parser = argparse.ArgumentParser(description='Start or stop the SysLinuxOS-System-Three desktop monitor.')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'metrics', 'public-ip', 'isp'])
    arguments = parser.parse_args()
    try:
        if arguments.action == 'metrics':
            metrics()
            return 0
        if arguments.action in ['public-ip', 'isp']:
            print(public_ip() if arguments.action == 'public-ip' else isp_name())
            return 0
        return control(arguments.action)
    except (OSError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
