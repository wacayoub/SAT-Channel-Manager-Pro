# -*- coding: utf-8 -*-
"""RC5.1: genuine online Enigma2 TV SERVICE index, read-only.

Do not merge third-party settings into the user's lamedb, bouquets or tuner.
Morpheus883's independent catalogue is downloaded only on explicit user action;
GitHub remains the original host and attribution/licensing is unchanged.
"""
import re
import os
import urllib.request

CATALOG_URL = (
    "https://raw.githubusercontent.com/morpheus883/enigma2-settings/"
    "master/morph883_motor/lamedb"
)
CATALOG_NAME = "Morpheus883 Enigma2 motor"
MAX_CATALOG_BYTES = 3 * 1024 * 1024
MAX_LOCAL_BYTES = 8 * 1024 * 1024
TV_TYPES = frozenset((1, 4, 17, 19, 22, 25, 31, 134, 135))
RADIO_TYPES = frozenset((2, 10))
SERVICE_REF = re.compile(
    r"^([0-9a-fA-F]{1,8}):([0-9a-fA-F]{8}):"
    r"([0-9a-fA-F]{1,4}):([0-9a-fA-F]{1,4}):(\d+):(\d+)$"
)
FRQ_REF = re.compile(
    r"^([0-9a-fA-F]{8}):([0-9a-fA-F]{1,4}):([0-9a-fA-F]{1,4})$"
)
# Service references use 0..3599 tenths of degrees in top 16 namespace bits.
DEFAULT_POSITIONS = (-70, 130, 192, 260)


def normalize_position(namespace):
    pos = (int(namespace, 16) >> 16) & 0xFFFF
    if not (0 <= pos < 3600):
        return None
    return pos - 3600 if pos > 1800 else pos


def orbital_label(pos):
    return "%.1f%s" % (abs(pos) / 10.0, "W" if pos < 0 else "E")


def parse_lamedb(data):
    """Read v4/v5 real service records; keep only DVB satellite + valid refs.

    Returns a dict keyed by (sid, namespace, tsid, onid), with type, name and
    orbit. No writing and no fabrication of service IDs.
    """
    if len(data) > MAX_LOCAL_BYTES:
        raise ValueError("Channel database exceeds read cap")
    text = data.decode("utf-8", "replace")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("eDVB services /"):
        raise ValueError("Not a valid Enigma2 lamedb")
    version = lines[0].split("/")
    if len(version) < 3 or version[1] not in ("4", "5"):
        raise ValueError("Unsupported lamedb version")
    version = int(version[1])
    services = {}
    section = False
    saw_section = False
    current = None
    for line in lines[1:]:
        token = line.strip()
        if not section:
            if token == "services":
                section = True
                saw_section = True
            continue
        if token == "end":
            break
        if version == 5 and token.startswith("s:"):
            # v5 encodes service info in service lines, with extra fields.
            # Do not misinterpret as the v4 alternating name/flags layout.
            parts = token.split(",")
            key_parts = parts[0].split(":")
            if len(key_parts) < 7:
                current = None
                continue
            sid, namespace, tsid, onid, stype, _flags = key_parts[1:7]
            match = SERVICE_REF.match(":".join((sid, namespace, tsid, onid, stype, _flags)))
            name = parts[1].strip() if len(parts) > 1 else ""
            if match and name:
                _add(services, match, name)
            current = None
            continue
        match = SERVICE_REF.match(token) if version == 4 else None
        if match:
            current = match
            continue
        if current:
            # First line after a v4 service reference is the service name.
            if token and not token.startswith(("p:", "c:", "C:", "f:")):
                _add(services, current, token)
            current = None
    if not saw_section:
        raise ValueError("Service section missing")
    return services


def _add(services, match, name):
    sid = int(match.group(1), 16)
    namespace = int(match.group(2), 16)
    tsid = int(match.group(3), 16)
    onid = int(match.group(4), 16)
    stype = int(match.group(5))
    pos = normalize_position(match.group(2))
    if pos is None or stype not in TV_TYPES | RADIO_TYPES:
        return
    # Avoid placeholders, empty names and zero-SID pseudo-services.
    if not sid or not name or name == ".":
        return
    key = sid, namespace, tsid, onid
    if key not in services:
        services[key] = (pos, stype, name[:160])


def download_service_catalog(url=CATALOG_URL, opener=None):
    """Bounded HTTPS download, no automatic caching/writes."""
    if url != CATALOG_URL:
        raise ValueError("Unapproved TV service catalogue URL")
    open_url = opener or urllib.request.urlopen
    request = urllib.request.Request(
        url, headers={"User-Agent": "SATChannelManager-Pro-RC5-ServiceAudit"})
    with open_url(request, timeout=15) as response:
        final = response.geturl()
        if not final.startswith(
                "https://raw.githubusercontent.com/morpheus883/enigma2-settings/"):
            raise ValueError("Unexpected catalogue redirect")
        raw = response.read(MAX_CATALOG_BYTES + 1)
    if len(raw) > MAX_CATALOG_BYTES:
        raise ValueError("Online TV service catalogue too large")
    services = parse_lamedb(raw)
    if len(services) < 1000:
        raise ValueError("Online catalogue incomplete: %d records" % len(services))
    return services


def read_local_services(path="/etc/enigma2/lamedb"):
    if not os.path.isfile(path) or os.path.islink(path):
        return {}
    if os.stat(path).st_size > MAX_LOCAL_BYTES:
        raise ValueError("Local lamedb exceeds size cap")
    with open(path, "rb") as stream:
        return parse_lamedb(stream.read(MAX_LOCAL_BYTES + 1))


def source_status(positions=None, online=None, local=None):
    """Evaluate real online TV services against exact local DVB references."""
    wanted = tuple(DEFAULT_POSITIONS if positions is None else positions)
    online = download_service_catalog() if online is None else online
    local = read_local_services() if local is None else local
    rows = []
    for pos in wanted:
        remote = {key: row for key, row in online.items()
                  if row[0] == pos and row[1] in TV_TYPES}
        existing = {key for key, row in local.items()
                    if row[0] == pos and row[1] in TV_TYPES}
        fresh = sum(1 for key in remote if key not in existing)
        rows.append({
            "position": pos, "label": orbital_label(pos),
            "online_tv": len(remote),
            "already_present": len(remote) - fresh,
            "not_in_local": fresh,
            "local_tv": len(existing),
        })
    return {
        "provider": CATALOG_NAME,
        "all_services": len(online),
        "all_tv": sum(row[1] in TV_TYPES for row in online.values()),
        "rows": rows,
        "local_all": len(local),
    }


def text_report(report):
    lines = [
        "CHAINES TV EN LIGNE : %s" % report["provider"],
        "%d services (TV+radio) / %d TV dans le catalogue" %
        (report["all_services"], report["all_tv"]),
        "Source externe independante : ne prouve pas la reception du signal.",
        "",
    ]
    for row in report["rows"]:
        lines.append(
            "%s : %d TV en ligne, %d deja presentes, %d non repertoriees localement" %
            (row["label"], row["online_tv"], row["already_present"],
             row["not_in_local"]))
    lines.extend((
        "",
        "ATTENTION : 'non repertoriees' ne signifie pas 'recevables'.",
        "Aucune chaine, bouquet, lamedb, tuner ou frequence n'a ete modifie.",
        "Pour les recevoir, une recherche DVB-S/S2 reelle reste necessaire.",
    ))
    return "\n".join(lines)
