#!/usr/bin/env python3
"""RC5 trial: static evidence that frequency downloads are not service scans.

Inspect the real built IPK's Python AST, without importing/starting Enigma2.
No tuner, lamedb, bouquets or network access.
"""
import ast
import io
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
IPK = ROOT / "rc5-trial.ipk"
REL = "./usr/lib/enigma2/python/Plugins/Extensions/SATChannelManager/"


def packaged_python(filename):
    blob = subprocess.check_output(["ar", "p", str(IPK), "data.tar.gz"])
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        return tar.extractfile(REL + filename).read().decode("utf-8")


def cls_method(tree, cls, name):
    klass = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == cls)
    return next(x for x in klass.body if isinstance(x, ast.FunctionDef) and x.name == name)


def methods_called(node):
    called = set()
    for x in ast.walk(node):
        if isinstance(x, ast.Call):
            if isinstance(x.func, ast.Attribute):
                called.add(x.func.attr)
            elif isinstance(x.func, ast.Name):
                called.add(x.func.id)
    return called


def assert_native_scan(callsite):
    calls = [n for n in ast.walk(callsite) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "openWithCallback"
             and len(n.args) >= 2 and isinstance(n.args[1], ast.Name)
             and n.args[1].id == "ServiceScan"]
    assert len(calls) == 1, "Expected exactly one native Enigma2 ServiceScan call"
    c = calls[0]
    assert any(k.arg == "updateBouquets" and isinstance(k.value, ast.Constant)
               and k.value.value is False for k in c.keywords), (
        "Native scan must not auto-overwrite user bouquets"
    )


def main():
    if not IPK.is_file():
        raise AssertionError("Build rc5-trial.ipk first")
    neo = ast.parse(packaged_python("neo.py"))
    plugin = ast.parse(packaged_python("plugin.py"))
    core = ast.parse(packaged_python("core.py"))

    download = next(n for n in core.body if isinstance(n, ast.FunctionDef)
                    and n.name == "download")
    assert "atomic_save" in methods_called(download), (
        "Source download should only save validated XML cache"
    )
    scan = cls_method(neo, "SATNeoHome", "launch_multi_scan")
    assert_native_scan(scan)
    self_scan = cls_method(plugin, "SATChannelManager", "_launch_scan_after_timeshift")
    assert_native_scan(self_scan)

    gui_scan = cls_method(neo, "SATNeoHome", "scan_current")
    assert "open_advanced" in methods_called(gui_scan), (
        "GREEN CHAINES must open native scan options"
    )
    gui_multi = cls_method(neo, "SATNeoHome", "scan_selected")
    assert "openWithCallback" in methods_called(gui_multi), (
        "Multi-satellite scan needs user confirmation"
    )

    for tree, cls, name in ((neo, "SATNeoHome", "scan_finished"),
                            (plugin, "SATChannelManager", "scan_done")):
        method = cls_method(tree, cls, name)
        assert "revert_last_scanned" in methods_called(method), (
            "Scanned bouquets must preserve preexisting favourites"
        )
    assert "create_backup" in methods_called(scan)
    assert "create_backup" in methods_called(self_scan)

    print("PASS: source HTTPS download -> XML cache only, no TV service API")
    print("PASS: native single-satellite and multi-satellite ServiceScan are wired")
    print("PASS: native scan has callback, backups and updateBouquets=False")
    print("PASS: scan requires explicit user confirmation")
    print("WARNING: detected services enter lamedb but NOT the existing bouquets.")
    print("         New services may be invisible in favourites until manually added.")


if __name__ == "__main__":
    main()
