#!/usr/bin/env python3
# SAT Channel Manager Pro RC5: strictly read-only source and receiver diagnostic.
# Never installs, scans, changes services, bouquets, satellite settings or tuners.
import argparse
import datetime
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = (
    ("OE-Alliance", "oe",
     "https://raw.githubusercontent.com/oe-alliance/oe-alliance-tuxbox-common/master/src/satellites.xml"),
    ("OpenPLi", "pli",
     "https://raw.githubusercontent.com/OpenPLi/tuxbox-xml/master/xml/satellites.xml"),
)
CACHE_DIR = "/etc/enigma2/SATChannelManager"
MAX_BYTES = 5 * 1024 * 1024


def catalogue_summary(data):
    if not isinstance(data, bytes) or not data or len(data) > MAX_BYTES:
        raise ValueError("XML missing/oversized")
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("DTD/entities disallowed")
    root = ET.fromstring(data)
    if root.tag != "satellites":
        raise ValueError("Not an Enigma2 transponder catalogue")
    sats = root.findall("sat")
    transponders = sum(len(s.findall("transponder")) for s in sats)
    services = len(root.findall(".//service")) + len(root.findall(".//channel"))
    if len(sats) < 25 or transponders < 100:
        raise ValueError("Catalogue incomplete")
    return len(sats), transponders, services


def cache_info(source):
    path = os.path.join(CACHE_DIR, "satellites-" + source + ".xml")
    if not os.path.isfile(path):
        return "not available"
    stat = os.stat(path)
    if stat.st_size > MAX_BYTES:
        return "file too large"
    try:
        with open(path, "rb") as file:
            numbers = catalogue_summary(file.read(MAX_BYTES + 1))
        stamp = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        return "OK (%d SAT / %d TP / %d services) last saved %s" % (*numbers, stamp)
    except (OSError, ValueError, ET.ParseError) as exc:
        return "invalid cache (%s)" % exc


def lamedb_info():
    path = "/etc/enigma2/lamedb"
    if not os.path.isfile(path):
        return "missing (receiver-only measurement)"
    if os.stat(path).st_size > 8 * 1024 * 1024:
        return "present but unusually large"
    try:
        with open(path, "r", errors="replace") as file:
            lines = file.read().splitlines()
        if not lines or not lines[0].startswith("eDVB services"):
            return "present, unrecognized format"
        section = False
        count = 0
        for line in lines:
            value = line.strip()
            if value == "services":
                section = True
                continue
            if section and value == "end":
                break
            if section and re.match(r"^[0-9a-fA-F]+(?::[0-9a-fA-F]+){4,}(?::|$)", value):
                count += 1
        return "%s bytes / approx. %d service entries (local receiver DB)" % (
            os.stat(path).st_size, count)
    except OSError as exc:
        return "unreadable: " + str(exc)


def genuine_tv_catalogue_online():
    """Independent Enigma2 motor lamedb: genuine TV service refs, no changes."""
    url = ("https://raw.githubusercontent.com/morpheus883/enigma2-settings/"
           "master/morph883_motor/lamedb")
    req = urllib.request.Request(url, headers={
        "User-Agent": "SATChannelManager-RC5-Audit/TV-ReadOnly"
    })
    with urllib.request.urlopen(req, timeout=15) as response:
        if not response.geturl().startswith(
                "https://raw.githubusercontent.com/morpheus883/enigma2-settings/"):
            raise ValueError("Unexpected TV catalogue redirect")
        data = response.read(3 * 1024 * 1024 + 1)
    if len(data) > 3 * 1024 * 1024:
        raise ValueError("TV catalogue exceeds size cap")
    lines = data.decode("utf-8", "replace").splitlines()
    if not lines or not lines[0].startswith("eDVB services /4/"):
        raise ValueError("Unexpected catalogue service database version")
    if "services" not in lines:
        raise ValueError("No Enigma2 service section")
    positions = {-70: 0, 130: 0, 192: 0, 255: 0, 260: 0}
    valid_tv = set()
    section = False
    for index, line in enumerate(lines):
        if line == "services":
            section = True
            continue
        if not section:
            continue
        if line == "end":
            break
        m = re.fullmatch(
            r"([0-9a-fA-F]{1,8}):([0-9a-fA-F]{8}):"
            r"([0-9a-fA-F]{1,4}):([0-9a-fA-F]{1,4}):(\d+):(\d+)",
            line.strip())
        if not m or index + 1 >= len(lines):
            continue
        sid, namespace, tsid, onid = (int(m.group(n), 16) for n in range(1, 5))
        stype = int(m.group(5))
        name = lines[index + 1].strip()
        if sid == 0 or stype not in (1, 4, 17, 19, 22, 25, 31, 134, 135) or not name or name == ".":
            continue
        pos = namespace >> 16
        if pos > 1800:
            pos -= 3600
        valid_tv.add((sid, namespace, tsid, onid, pos))
    if len(valid_tv) < 1000:
        raise ValueError("TV service index incomplete")
    for row in valid_tv:
        if row[4] in positions:
            positions[row[4]] += 1
    return len(valid_tv), positions


def main():
    parser = argparse.ArgumentParser(description="Read-only SAT RC5 source diagnostic")
    parser.add_argument("--online", action="store_true",
                        help="Also verify HTTPS reachability (up to 12s per source)")
    args = parser.parse_args()
    print("SAT Channel Manager Pro RC5 — source audit (READ ONLY)")
    for label, key, url in SOURCES:
        print("%s local cache: %s" % (label, cache_info(key)))
        if args.online:
            try:
                request = urllib.request.Request(url, headers={
                    "User-Agent": "SATChannelManager-RC5-Audit/1.0"
                })
                with urllib.request.urlopen(request, timeout=12) as response:
                    actual = response.geturl()
                    if not actual.startswith("https://raw.githubusercontent.com/"):
                        raise ValueError("Untrusted redirect blocked")
                    data = response.read(MAX_BYTES + 1)
                sats, tps, services = catalogue_summary(data)
                print("%s ONLINE: OK; SAT=%d TP=%d TV-services=%d" % (
                    label, sats, tps, services))
            except Exception as exc:
                print("%s ONLINE: FAILED (%s: %s)" % (
                    label, type(exc).__name__, str(exc)[:160]))
    print("Receiver lamedb:", lamedb_info())
    if args.online:
        print("---- Genuine online TV services (SEPARATE FROM OE/PLI XML) ----")
        try:
            total, rows = genuine_tv_catalogue_online()
            print("Morpheus883 ONLINE TV source: OK; %d actual TV service records" % total)
            for pos in (-70, 130, 192, 255, 260):
                label = "%.1f%s" % (abs(pos) / 10.0, "W" if pos < 0 else "E")
                print("  %s : %d TV catalogue entries" % (label, rows[pos]))
        except Exception as exc:
            print("Morpheus883 ONLINE TV: FAILED (%s: %s)" % (
                type(exc).__name__, str(exc)[:160]))
    print("CONCLUSION: OE-Alliance/OpenPLi XML contain frequencies, NOT TV")
    print("services. The optional Morpheus883 source holds real service records.")
    print("Service availability still requires DVB-S2 tuner reception/scan.")
    print("No file was written; no scan, bouquet or tuner settings changed.")


if __name__ == "__main__":
    main()
