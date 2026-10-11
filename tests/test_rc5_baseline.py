#!/usr/bin/env python3
"""RC5 trial gate: exercise RC4.1 install patches on extracted Enigma2 files.

Runs entirely in an isolated temporary directory. Never writes real Enigma2
settings, real /etc/enigma2/lamedb, bouquets or tuner configuration.
"""
import hashlib
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "packages/enigma2-plugin-extensions-satchannelmanager_0.4.1-rc4.1_all.ipk"
PINNED = "4eed0b5c1c61cf2e763b431a57ef5b2977d845164a345bef439991242595762a"
REL = "usr/lib/enigma2/python/Plugins/Extensions/SATChannelManager"


def ar_data(path, member):
    return subprocess.check_output(["ar", "p", str(path), member])


def safe_unpack(ipk, path):
    compressed = ar_data(ipk, "data.tar.gz")
    with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as tar:
        members = tar.getmembers()
        for item in members:
            p = pathlib.PurePosixPath(item.name)
            if p.is_absolute() or ".." in p.parts or item.issym() or item.islnk():
                raise AssertionError("Unsafe package member: " + item.name)
            if not (item.isdir() or item.isfile()):
                raise AssertionError("Unexpected package member: " + item.name)
        tar.extractall(path, members=members, filter="data")
    folder = path / REL
    if not folder.is_dir():
        raise AssertionError("SATChannelManager directory absent from IPK")
    return folder


class TrialCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        actual = hashlib.sha256(PACKAGE.read_bytes()).hexdigest()
        if actual != PINNED:
            raise AssertionError("RC4.1 package SHA256 changed: " + actual)
        cls.context = tempfile.TemporaryDirectory(prefix="sat-rc5-sim-")
        cls.root = pathlib.Path(cls.context.name)
        cls.ext = safe_unpack(PACKAGE, cls.root)
        cls.original = {p.name: p.read_bytes() for p in cls.ext.glob("*.py")}

    @classmethod
    def tearDownClass(cls):
        cls.context.cleanup()

    def test_package_control_version(self):
        control = ar_data(PACKAGE, "control.tar.gz")
        with tarfile.open(fileobj=io.BytesIO(control), mode="r:gz") as tar:
            data = tar.extractfile("./control").read().decode()
        self.assertIn("Version: 0.4.1-rc4.1", data)

    def test_baseline_python_compiles(self):
        for name, source in self.original.items():
            with self.subTest(name=name):
                compile(source, name, "exec")

    def test_easy_then_neo_patch_is_idempotent(self):
        for script in ("easy-mode-rc4.1.py", "neo-icons-easy-rc4.1.py"):
            subprocess.run([sys.executable, str(ROOT / script), str(self.ext)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=30)
        first = {p.name: p.read_bytes() for p in self.ext.glob("*.py")}
        for script in ("easy-mode-rc4.1.py", "neo-icons-easy-rc4.1.py"):
            subprocess.run([sys.executable, str(ROOT / script), str(self.ext)],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=30)
        second = {p.name: p.read_bytes() for p in self.ext.glob("*.py")}
        self.assertEqual(first, second)
        for name, source in second.items():
            with self.subTest(name=name):
                compile(source, name, "exec")

    def test_rc4_patches_do_not_delete_originals(self):
        self.assertTrue((self.ext / "plugin.py").exists())
        self.assertTrue((self.ext / "neo.py").exists())
        self.assertTrue((self.ext / "core.py").exists())
        self.assertTrue((self.ext / "ui_skin.py").exists())

    def test_no_scan_or_bouquet_data_writes_during_simulation(self):
        names = {str(x.relative_to(self.root)) for x in self.root.rglob("*") if x.is_file()}
        self.assertFalse(any(x.endswith(("lamedb", "lamedb5", "satellites.xml",
                                         "bouquets.tv", "bouquets.radio")) for x in names))

    def test_ui_has_clear_tp_vs_service_separation(self):
        # Static UI compatibility contract, no Enigma2 Screens implementation.
        text = (self.ext / "neo.py").read_text()
        for token in ("FREQUENCES", "CHAINES TV", "smart_installation('preset')",
                      "scan_current", "MES BOUQUETS"):
            self.assertIn(token, text)

    def test_neo_icons_are_real_png(self):
        for name in ("install", "bouquets", "options"):
            p = self.ext / "icons" / (name + ".png")
            self.assertTrue(p.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(p.stat().st_size, 100)

    def test_unknown_patch_baseline_fails_closed(self):
        # Copy a patched layout and intentionally break the easy-mode marker.
        with tempfile.TemporaryDirectory(prefix="sat-rc5-invalid-") as d:
            target = pathlib.Path(d)
            for f in ("core.py", "neo.py", "plugin.py", "ui_skin.py"):
                shutil.copy2(self.ext / f, target / f)
            content = (target / "core.py").read_text()
            (target / "core.py").write_text(content.replace(
                "0.4.1-rc4.1-easy", "unexpected_revision"))
            before = {p.name: p.read_bytes() for p in target.glob("*.py")}
            p = subprocess.run(
                [sys.executable, str(ROOT / "neo-icons-easy-rc4.1.py"), str(target)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
            )
            self.assertNotEqual(p.returncode, 0)
            after = {p.name: p.read_bytes() for p in target.glob("*.py")}
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
