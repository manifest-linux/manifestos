import datetime as dt
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
os.environ["MANIFESTOS_DATA_DIR"] = str(REPO / "data")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ["LANG"] = "C"
sys.path.insert(0, str(REPO / "packages" / "manifestos-apps" / "usr" / "lib" / "manifestos"))

import manifestos_common as mc

PLACEHOLDER = re.compile(r"\{[a-z]+\}")


class DataTests(unittest.TestCase):
    def test_members(self):
        data = json.loads((REPO / "data" / "members.json").read_text(encoding="utf-8"))
        ids = [m["id"] for m in data["members"]]
        self.assertEqual(len(ids), 6)
        self.assertEqual(len(set(ids)), 6)
        for m in data["members"]:
            self.assertRegex(m["color"], r"^#[0-9A-F]{6}$")
            dt.date.fromisoformat(m["birthday"])
        for album in data["albums"]:
            dt.date.fromisoformat(album["date"])

    def test_turkish_placeholders_match(self):
        catalog = json.loads((REPO / "data" / "i18n" / "tr.json").read_text(encoding="utf-8"))
        for source, target in catalog.items():
            self.assertEqual(sorted(PLACEHOLDER.findall(source)), sorted(PLACEHOLDER.findall(target)), source)


class DateTests(unittest.TestCase):
    def test_next_occurrence_wraps_to_next_year(self):
        self.assertEqual(mc.next_occurrence(1, 5, dt.date(2026, 10, 27)), dt.date(2027, 1, 5))
        self.assertEqual(mc.next_occurrence(10, 27, dt.date(2026, 10, 27)), dt.date(2026, 10, 27))

    def test_leap_day_falls_back_to_february_28(self):
        self.assertEqual(mc.next_occurrence(2, 29, dt.date(2027, 1, 1)), dt.date(2027, 2, 28))

    def test_age(self):
        self.assertEqual(mc.age_on(dt.date(2000, 8, 9), dt.date(2026, 8, 8)), 25)
        self.assertEqual(mc.age_on(dt.date(2000, 8, 9), dt.date(2026, 8, 9)), 26)

    def test_birthdays_on(self):
        self.assertEqual([m["id"] for m in mc.birthdays_on(dt.date(2027, 8, 9))], ["esin"])
        self.assertEqual(mc.birthdays_on(dt.date(2027, 1, 1)), [])


class UpcomingTests(unittest.TestCase):
    def tearDown(self):
        mc.save_user_events([])

    def test_sorted_and_past_events_hidden(self):
        mc.save_user_events([
            {"id": "a", "title": "Past show", "when": "2026-10-01T20:00"},
            {"id": "b", "title": "Tonight", "when": "2026-10-27T21:00"},
            {"id": "c", "title": "All day today", "when": "2026-10-27"},
        ])
        now = dt.datetime(2026, 10, 27, 12, 0)
        items = mc.upcoming(now)
        titles = [item["title"] for item in items]
        self.assertNotIn("Past show", titles)
        self.assertEqual(titles[:2], ["All day today", "Tonight"])
        self.assertEqual(items, sorted(items, key=lambda item: item["when"]))
        self.assertTrue(all(item["when"].date() >= now.date() for item in items))

    def test_countdown_text(self):
        now = dt.datetime(2026, 10, 27, 12, 0)
        self.assertEqual(mc.countdown({"all_day": True, "when": dt.datetime(2026, 10, 27)}, now), "Today!")
        self.assertEqual(mc.countdown({"all_day": True, "when": dt.datetime(2026, 10, 28)}, now), "Tomorrow")
        self.assertEqual(mc.countdown({"all_day": True, "when": dt.datetime(2026, 11, 6)}, now), "in 10 days")
        self.assertEqual(mc.countdown({"all_day": False, "when": dt.datetime(2026, 10, 28, 14, 30)}, now), "1d 2h 30m")
        self.assertEqual(mc.countdown({"all_day": False, "when": dt.datetime(2026, 10, 27, 13, 0, 5)}, now), "1h 0m 5s")

    def test_json_shape(self):
        payload = mc.upcoming_json(limit=3, now=dt.datetime(2026, 10, 27, 12, 0))
        self.assertEqual(len(payload["items"]), 3)
        self.assertIn("today", payload["labels"])
        json.dumps(payload)


class LogoTests(unittest.TestCase):
    def test_fastfetch_logo_uses_all_colors(self):
        art = mc.ring_fastfetch()
        for index in range(1, 8):
            self.assertIn(f"${index}", art)
        self.assertIn("manifest", art)


if __name__ == "__main__":
    unittest.main()
