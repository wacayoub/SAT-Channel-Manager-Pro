#!/usr/bin/env python3
"""Enigma2-compatible smoke test for RC5 online TV GUI, without a receiver."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import service_sources_rc5_ui


class TestSession:
    def __init__(self):
        self.opened = []
    def open(self, *args):
        self.opened.append(args)


class FakeHome:
    def __init__(self):
        self.busy = False
        self._closed = False
        self.selected = {255}
        self.session = TestSession()
        self.menus = []
        self.actions = []
        self.messages = []
    def install_menu(self):
        self.actions.append("original-install")
    def run_action(self, action):
        self.actions.append(action)
    def open_chooser(self, title, rows, help_text, callback):
        self.menus.append((title, rows, help_text, callback))
    def current_position(self):
        return 255
    def status(self, msg):
        self.messages.append(msg)
    def _error(self, msg):
        self.messages.append("ERROR " + msg)


class DummyDeferred:
    def __init__(self, value):
        self.value = value
    def addCallbacks(self, good, bad):
        good(self.value)


class UISmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        service_sources_rc5_ui.attach_home(FakeHome)

    def test_green_menu_has_real_tv_catalogue_separate_from_scan(self):
        f = FakeHome()
        f.install_menu()
        self.assertEqual(len(f.menus), 1)
        titles = {name: key for name, key in f.menus[0][1]}
        self.assertTrue(any("CHAINES TV ONLINE" in name and key == "online_tv"
                            for name, key in titles.items()))
        self.assertTrue(any("scan tuner" in name and key == "scan_current"
                            for name, key in titles.items()))
        self.assertEqual(f.actions, [])

    def test_offline_navigation_does_not_download_tv(self):
        f = FakeHome()
        with patch.object(service_sources_rc5_ui.service_sources_rc5,
                          "source_status", side_effect=AssertionError("unexpected fetch")):
            f.install_menu()
            f.run_action("scan_current")
        self.assertEqual(f.actions, ["scan_current"])

    def test_explicit_online_preview_is_read_only(self):
        f = FakeHome()
        report = {"provider": "Morpheus883", "all_services": 2, "all_tv": 1,
                  "rows": [{"position": 255, "label": "25.5E", "online_tv": 1,
                            "local_tv": 0, "already_present": 0, "not_in_local": 1}],
                  "local_all": 0}
        fake_twisted = types.ModuleType("twisted")
        fake_internet = types.ModuleType("twisted.internet")
        fake_threads = types.ModuleType("twisted.internet.threads")
        def deferred(call, positions):
            self.assertIn(-70, positions)
            self.assertIn(255, positions)
            return DummyDeferred(call(positions=positions))
        fake_threads.deferToThread = deferred
        fake_screen = types.ModuleType("Screens")
        fake_message = types.ModuleType("Screens.MessageBox")
        class FakeMessageBox:
            TYPE_INFO = 0
        fake_message.MessageBox = FakeMessageBox
        modules = {"twisted": fake_twisted, "twisted.internet": fake_internet,
                   "twisted.internet.threads": fake_threads,
                   "Screens": fake_screen, "Screens.MessageBox": fake_message}
        with patch.dict(sys.modules, modules), patch.object(
                service_sources_rc5_ui.service_sources_rc5, "source_status",
                return_value=report):
            f.run_action("online_tv")
        self.assertFalse(f.busy)
        self.assertEqual(len(f.session.opened), 1)
        opened = f.session.opened[0]
        self.assertEqual(opened[0], FakeMessageBox)
        self.assertIn("1 TV en ligne", opened[1])
        self.assertEqual(f.actions, [])

    def test_attaching_twice_preserves_single_handler(self):
        previous = FakeHome.install_menu
        self.assertIs(service_sources_rc5_ui.attach_home(FakeHome).install_menu,
                      previous)


if __name__ == "__main__":
    unittest.main()
