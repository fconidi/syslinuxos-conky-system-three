# SysLinuxOS-System-Three

A transparent desktop monitor for SysLinuxOS and Debian, inspired by
[MX-CoreBlue](https://github.com/MX-Linux/mx-conky-data/tree/master/themes/MX-CoreBlue).

The monitor combines the installed distribution's logo, a digital clock,
concentric clock rings, battery and CPU gauges, and compact sections for
network, storage, memory and top processes. Headings are white, with cyan
indicators and pale values. The background is fully transparent.
The CPU gauge shows overall usage across all logical processors and the
number of threads detected on the current machine.

## Install

With the SysLinuxOS APT repository configured:

```sh
sudo apt update
sudo apt install syslinuxos-conky-system-three
```

Or install the downloaded package with APT:

```sh
sudo apt install ./syslinuxos-conky-system-three_0.1.2_all.deb
```

The shared `syslinuxos-conky-menu` dependency supplies the Conky submenu and
launcher icon. It must also be available when installing a downloaded package.

## Use

Open **System Tools > Conky > Start Conky-System-Three** or
**Stop Conky-System-Three**. The same menu labels are shown in every locale.

```sh
syslinuxos-conky-system-three start
syslinuxos-conky-system-three stop
syslinuxos-conky-system-three status
```

The panel is centered at the right edge. It is intended as an alternative to
Conky System or Conky Window. The existing themes keep their own controls.

All text, icons, meters, spacing and dimensions scale together to the active
monitor's resolution. Restart after changing the resolution. An optional
manual scale is available:

```sh
CONKY_SYSTEM_THREE_SCALE=1.2 syslinuxos-conky-system-three start
```

The distribution is identified through `/etc/os-release`. SysLinuxOS uses its
own logo; Debian uses the Debian logo. Other distributions can provide the
standard `LOGO` icon entry. Logo artwork is loaded from the operating system.
A generic Linux mark is used when no matching logo is installed.

Memory shows RAM and swap usage separately. The network
section follows the default route and displays local and external IPv4
addresses, transfer rates, totals and ISP. Select a fixed interface with
`CONKY_NET_INTERFACE=enp3s0`. Route changes are detected within ten seconds.

The external IPv4 address is obtained from ipify every five minutes and the
ISP from IPinfo every hour. Requests use HTTPS and three-second timeouts.
Network lookups run in a background thread and use a private cache, keeping
the clock and meters responsive. Unavailable values are shown as `N/A`.

The editable template is `/etc/conky/syslinuxos-conky-system-three.conf`; dpkg preserves
edits across upgrades. A compositing window manager provides full alpha
transparency.

## Build

```sh
bash build-deb.sh
```

The package is produced in `dist/`.

## License

Copyright 2026 Franco Conidi. GPL-3.0-or-later; see [LICENSE](LICENSE).

## Renamed from syslinuxos-system-three

Since 0.2.0 the package is called `syslinuxos-conky-system-three`, like the other SysLinuxOS Conky themes. The old name is kept as an empty transitional package, so `apt upgrade` migrates existing installs. The command is now `syslinuxos-conky-system-three` and the template `/etc/conky/syslinuxos-conky-system-three.conf`; an edited template is carried over.
