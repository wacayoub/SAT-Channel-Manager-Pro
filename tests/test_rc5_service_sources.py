#!/usr/bin/env python3
"""Real DVB TV service index regression tests — no receiver writes."""
import io
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from service_sources_rc5 import (parse_lamedb, normalize_position, source_status,
                                 text_report, download_service_catalog, TV_TYPES)

TEST_LAMEDB = b"""eDVB services /4/
transponders
0dca0000:0001:0001
s 11000000:27500000:0:2:3530:2:0
/
00820000:0002:0002
s 12000000:27500000:0:2:130:2:0
/
end
services
0011:0dca0000:0001:0001:1:0
Nilesat TV
p:Provider
0012:0dca0000:0001:0001:2:0
Radio Nilesat
p:Provider
0021:00820000:0002:0002:25:0
Hot Bird TV HD
p:Provider
0022:00820000:0002:0002:99:0
Data Hotbird
p:Provider
end
"""


class TVSourceTests(unittest.TestCase):
    def test_reads_real_service_refs_not_frequency_entries(self):
        data = parse_lamedb(TEST_LAMEDB)
        self.assertEqual(len(data), 3)
        self.assertEqual(sum(x[1] in TV_TYPES for x in data.values()), 2)

    def test_count_per_orbital_position(self):
        online = parse_lamedb(TEST_LAMEDB)
        local = parse_lamedb(TEST_LAMEDB.replace(b"0021:", b"0041:"))
        data = source_status((-70, 130, 260), online=online, local=local)
        self.assertEqual(data["rows"][0]["online_tv"], 1)
        self.assertEqual(data["rows"][0]["already_present"], 1)
        self.assertEqual(data["rows"][1]["online_tv"], 1)
        self.assertEqual(data["rows"][1]["already_present"], 0)
        self.assertEqual(data["rows"][1]["not_in_local"], 1)
        self.assertEqual(data["rows"][2]["online_tv"], 0)
        self.assertEqual(data["all_tv"], 2)
        self.assertIn("TV en ligne", text_report(data))

    def test_positions_and_west_wrapping(self):
        self.assertEqual(normalize_position("00820000"), 130)
        self.assertEqual(normalize_position("0dca0000"), -70)
        self.assertEqual(normalize_position("01680000"), 360)
        self.assertIsNone(normalize_position("f0000000"))

    def test_bad_source_cannot_fake_a_positive_count(self):
        for broken in (b"<satellites><sat /></satellites>", b"", b"random"):
            with self.assertRaises(ValueError):
                parse_lamedb(broken)

    def test_malformed_or_empty_service_section(self):
        with self.assertRaises(ValueError):
            parse_lamedb(b"eDVB services /4/\ntransponders\nend\n")

    def test_unauthorized_urls_disallowed(self):
        with self.assertRaises(ValueError):
            download_service_catalog("http://example.com/lamedb")


if __name__ == "__main__":
    unittest.main(verbosity=2)
