import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'files/usr/lib/syslinuxos-system-three/app.py'
spec = importlib.util.spec_from_file_location('app', SOURCE)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class LayoutTests(unittest.TestCase):
    def test_entire_panel_fits_all_supported_resolutions(self):
        for width, height in [(800,600),(1280,720),(1920,1080),(3840,2160)]:
            layout = app.layout(width,height)
            self.assertLessEqual(layout['width'],width)
            self.assertLessEqual(layout['height'],height-20)
        self.assertGreater(app.layout(3840,2160)['height'],app.layout(1920,1080)['height'])

    def test_bad_scale_keeps_automatic_layout(self):
        for value in ['nan','inf','0','-1','invalid']:
            self.assertEqual(app.layout(1920,1080,value),app.layout(1920,1080))


class LogoTests(unittest.TestCase):
    def test_syslinuxos_prefers_its_own_logo_over_debian_heritage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'syslinuxos-logo.png').touch()
            (root/'debian-logo.png').touch()
            result = app.find_logo({'ID':'SysLinuxOS','ID_LIKE':'debian'},[root])
            self.assertEqual(result,root/'syslinuxos-logo.png')

    def test_debian_does_not_pick_syslinuxos_branding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'syslinuxos-logo.png').touch()
            (root/'debian-logo.png').touch()
            (root/'debian-logo.png.debian').touch()
            self.assertEqual(app.find_logo({'ID':'debian'},[root]),root/'debian-logo.png.debian')

    def test_unknown_distribution_is_not_misidentified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root/'syslinuxos-logo.png').touch()
            self.assertIsNone(app.find_logo({'ID':'other'},[root]))


class PublicDataTests(unittest.TestCase):
    def test_cached_queries_respect_intervals_and_route_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(app,'runtime_dir',return_value=root):
                with patch.object(app,'public_ip',return_value='198.51.100.12') as ip:
                    with patch.object(app,'isp_name',return_value='Example ISP') as isp:
                        self.assertEqual(app.public_info('eth0')['public_ip'],'198.51.100.12')
                        app.public_info('eth0')
                        self.assertEqual(ip.call_count,1)
                        self.assertEqual(isp.call_count,1)
                        app.public_info('wlan0')
                        self.assertEqual(ip.call_count,2)

    def test_data_file_cannot_inject_extra_rows_or_lua(self):
        text = app.safe_text('ISP\nkey\t${exec false}')
        self.assertNotIn('\n',text)
        self.assertNotIn('\t',text)
        self.assertNotIn('${',text)


class BatteryTests(unittest.TestCase):
    def test_missing_and_valid_battery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(app.battery_percent(root), 'N/A')
            battery = root / 'BAT1'
            battery.mkdir()
            (battery / 'capacity').write_text('73')
            self.assertEqual(app.battery_percent(root), '73')
            (battery / 'present').write_text('0')
            self.assertEqual(app.battery_percent(root), 'N/A')


class ProcessTests(unittest.TestCase):
    def test_only_own_config_is_recognized(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);process=root/'123';process.mkdir()
            config=root/'conkyrc-system-three.conf'
            with patch.object(app,'PROC',root):
                (process/'cmdline').write_bytes(b'conky\0--config\0/conkyrc-system.conf\0')
                self.assertFalse(app.owned_process(123,config))
                (process/'cmdline').write_bytes(b'conky\0--config\0'+os.fsencode(config)+b'\0')
                self.assertTrue(app.owned_process(123,config))


class StopTests(unittest.TestCase):
    def test_stop_waits_for_a_threaded_lookup_to_finish(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            (directory/'conky.pid').write_text('123')
            with patch.object(app,'runtime_dir',return_value=directory):
                with patch.object(app,'owned_process',side_effect=[True]*35+[False,False]):
                    with patch.object(app.os,'kill') as kill:
                        with patch.object(app.time,'sleep'):
                            self.assertEqual(app.control('stop'),0)
                        kill.assert_called_once()


if __name__=='__main__':
    unittest.main()
