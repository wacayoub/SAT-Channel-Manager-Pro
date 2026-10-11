#!/usr/bin/env python3
"""Build an UNPUBLISHED SAT Channel Manager RC5 trial package.

Based on SHA-pinned RC4.1, with Easy Mode + Neo UI pre-applied and checked.
Only writes rc5-trial.ipk in this checkout; no tuner, lamedb, bouquets, opkg,
receiver, main branch, or online update changes.
"""
import gzip
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "packages/enigma2-plugin-extensions-satchannelmanager_0.4.1-rc4.1_all.ipk"
OUT = ROOT / "rc5-trial.ipk"
HASH = "4eed0b5c1c61cf2e763b431a57ef5b2977d845164a345bef439991242595762a"
VERSION = "0.5.0-rc5-trial"
EXT = Path("usr/lib/enigma2/python/Plugins/Extensions/SATChannelManager")


def unpack(ipk, group, dest):
    compressed = subprocess.check_output(["ar", "p", str(ipk), group + ".tar.gz"])
    with tarfile.open(fileobj=io.BytesIO(compressed), mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            item = PurePosixPath(member.name)
            if item.is_absolute() or ".." in item.parts or not (member.isdir() or member.isfile()):
                raise AssertionError("Unsafe or unexpected archive member: " + member.name)
        archive.extractall(dest, members=members, filter="data")


def pack(src, dest):
    # Reproducible tar content; all installation files are root owned.
    with open(dest, "wb") as output:
        with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
                for p in sorted(src.rglob("*")):
                    if "__pycache__" in p.parts or p.suffix in (".pyc", ".pyo"):
                        continue
                    relative = p.relative_to(src).as_posix()
                    info = tar.gettarinfo(str(p), arcname="./" + relative)
                    info.uid, info.gid, info.uname, info.gname, info.mtime = 0, 0, "", "", 0
                    if p.is_file():
                        with open(p, "rb") as handle:
                            tar.addfile(info, handle)
                    elif p.is_dir():
                        tar.addfile(info)
                    else:
                        raise AssertionError("Unexpected packaging entry: " + str(p))


def main():
    if hashlib.sha256(BASE.read_bytes()).hexdigest() != HASH:
        raise AssertionError("Published RC4.1 baseline SHA-256 drift; build refused")
    with tempfile.TemporaryDirectory(prefix="satcm-rc5-build-") as temp:
        tmp = Path(temp)
        data, control = tmp / "data", tmp / "control"
        data.mkdir()
        control.mkdir()
        unpack(BASE, "data", data)
        unpack(BASE, "control", control)
        ext = data / EXT
        if not ext.is_dir():
            raise AssertionError("SATChannelManager plugin missing from baseline")
        # Execute real audited patch scripts against ONLY the unpacked files.
        for script in ("easy-mode-rc4.1.py", "neo-icons-easy-rc4.1.py"):
            p = subprocess.run([sys.executable, str(ROOT / script), str(ext)],
                               check=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, timeout=30)
            print(script, p.stdout.decode("utf-8", "replace").strip())
        # The patches intentionally produce backups for on-receiver use, but
        # they must not ship stale/duplicate Python modules inside an IPK.
        for p in ext.rglob("*"):
            if p.is_file() and ".bak-before-" in p.name:
                p.unlink()
        core = ext / "core.py"
        original = core.read_text("utf-8")
        old = "VERSION = '0.4.1-rc4.1-easy'"
        if original.count(old) != 1:
            raise AssertionError("Unrecognized Easy Mode version marker")
        core.write_text(original.replace(old, "VERSION = '" + VERSION + "'"))
        for py in ext.rglob("*.py"):
            compile(py.read_bytes(), str(py), "exec")
        for icon in ("install", "bouquets", "options"):
            if not (ext / "icons" / (icon + ".png")).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                raise AssertionError("Neo PNG invalid: " + icon)
        forbidden = ("lamedb", "lamedb5", "satellites.xml",
                     "bouquets.tv", "bouquets.radio", "settings")
        actual = {p.name for p in data.rglob("*") if p.is_file()}
        if actual.intersection(forbidden):
            raise AssertionError("RC5 may not bundle existing receiver config")
        conf = control / "control"
        txt = conf.read_text("utf-8")
        oldver = "Version: 0.4.1-rc4.1"
        if txt.count(oldver) != 1:
            raise AssertionError("Unexpected original control version")
        txt = txt.replace(oldver, "Version: " + VERSION)
        conf.write_text(txt)
        (ext / "RC5-TRIAL-HOLD.txt").write_text(
            "RC5 trial: bundled audited Easy Mode + Neo Icons from RC4.1.\n"
            "No direct TV service import from LyngSat, FlySat or KingOfSat.\n"
            "SAT/tuner scans remain receiver-dependent; test hardware before release.\n"
            "This build is not published to online update.\n"
        )
        pack(data, tmp / "data.tar.gz")
        pack(control, tmp / "control.tar.gz")
        (tmp / "debian-binary").write_bytes(b"2.0\n")
        candidate = tmp / "rc5-trial.ipk"
        subprocess.run(["ar", "qc", str(candidate),
                        "debian-binary", "control.tar.gz", "data.tar.gz"],
                       cwd=str(tmp), check=True, stdout=subprocess.PIPE)
        if not candidate.read_bytes().startswith(b"!<arch>\n"):
            raise AssertionError("Invalid trial IPK")
        shutil.copyfile(candidate, OUT)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print("SAT_RC5_TRIAL_BUILT version=", VERSION, "size=", OUT.stat().st_size)
    print("SHA256", digest)
    print("HOLD: no installation, no online update, hardware validation required")


if __name__ == "__main__":
    main()
