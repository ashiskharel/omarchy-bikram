import json
import unittest
from datetime import date
from pathlib import Path

import bikram

GAZETTE = [
    ((2083, 1, 1), date(2026, 4, 14)),
    ((2083, 1, 18), date(2026, 5, 1)),
    ((2083, 2, 15), date(2026, 5, 29)),
    ((2083, 5, 12), date(2026, 8, 28)),
    ((2083, 5, 13), date(2026, 8, 29)),
    ((2083, 5, 19), date(2026, 9, 4)),
    ((2083, 5, 29), date(2026, 9, 14)),
    ((2083, 6, 3), date(2026, 9, 19)),
    ((2083, 6, 9), date(2026, 9, 25)),
    ((2083, 6, 18), date(2026, 10, 4)),
    ((2083, 6, 19), date(2026, 10, 5)),
    ((2083, 6, 25), date(2026, 10, 11)),
    ((2083, 6, 31), date(2026, 10, 17)),
    ((2083, 7, 6), date(2026, 10, 23)),
    ((2083, 7, 22), date(2026, 11, 8)),
    ((2083, 7, 25), date(2026, 11, 11)),
    ((2083, 7, 26), date(2026, 11, 12)),
    ((2083, 7, 29), date(2026, 11, 15)),
    ((2083, 8, 17), date(2026, 12, 3)),
    ((2083, 9, 9), date(2026, 12, 24)),
    ((2083, 9, 10), date(2026, 12, 25)),
    ((2083, 9, 15), date(2026, 12, 30)),
    ((2083, 9, 27), date(2027, 1, 11)),
    ((2083, 10, 1), date(2027, 1, 15)),
    ((2083, 10, 16), date(2027, 1, 30)),
    ((2083, 10, 24), date(2027, 2, 7)),
    ((2083, 10, 28), date(2027, 2, 11)),
    ((2083, 11, 7), date(2027, 2, 19)),
    ((2083, 11, 22), date(2027, 3, 6)),
    ((2083, 11, 24), date(2027, 3, 8)),
    ((2083, 11, 25), date(2027, 3, 9)),
    ((2083, 12, 7), date(2027, 3, 21)),
    ((2083, 12, 8), date(2027, 3, 22)),
    ((2083, 12, 23), date(2027, 4, 6)),
]

LIBRARY = [
    ((1975, 1, 1), date(1918, 4, 13)),
    ((2013, 2, 8), date(1956, 5, 21)),
    ((2051, 10, 1), date(1995, 1, 15)),
    ((2076, 6, 27), date(2019, 10, 14)),
    ((2077, 4, 4), date(2020, 7, 19)),
    ((2081, 3, 31), date(2024, 7, 15)),
]


class ConversionTest(unittest.TestCase):
    def test_library_pins(self):
        for bs, ad in LIBRARY:
            self.assertEqual(bikram.bs_to_ad(*bs), ad)
            self.assertEqual(bikram.ad_to_bs(ad), bs)

    def test_gazette_pairs(self):
        for bs, ad in GAZETTE:
            self.assertEqual(bikram.bs_to_ad(*bs), ad, bs)
            self.assertEqual(bikram.ad_to_bs(ad), bs)

    def test_round_trip_span(self):
        cursor = date(2026, 4, 14)
        end = date(2027, 4, 13)
        while cursor <= end:
            year, month, day = bikram.ad_to_bs(cursor)
            self.assertEqual(bikram.bs_to_ad(year, month, day), cursor)
            cursor = date.fromordinal(cursor.toordinal() + 1)

    def test_today_label(self):
        payload = bikram.today_payload(date(2026, 10, 5), "both", "ne")
        self.assertEqual(payload["label"], "असोज १९ · 5 Oct")
        self.assertEqual(payload["bs"]["month"], 6)
        self.assertEqual(payload["next"]["name_en"], "Ghatasthapana")
        self.assertEqual(payload["next"]["in_days"], 6)

    def test_month_grid_starts_on_known_day(self):
        payload = bikram.month_payload(2083, 6, date(2026, 10, 5), "ne")
        self.assertEqual(payload["days"], 31)
        first = next(cell for cell in payload["cells"] if cell["day"] == 1)
        self.assertEqual(first["ad"], "2026-09-17")
        today = next(cell for cell in payload["cells"] if cell.get("today"))
        self.assertEqual(today["day"], 19)
        ghat = next(cell for cell in payload["cells"] if cell["day"] == 25)
        self.assertEqual(ghat["holidays"][0]["name_en"], "Ghatasthapana")

    def test_holiday_file_has_no_open_dates(self):
        raw = json.loads((Path(bikram.ROOT) / "holidays" / "2083.json").read_text())
        for item in raw["holidays"]:
            self.assertEqual(len(item["bs"]), 3)
            self.assertNotIn("to be", item["name_en"].lower())
            bikram.bs_to_ad(*item["bs"])

    def test_reject_missing_day(self):
        with self.assertRaises(bikram.DateError):
            bikram.bs_to_ad(2083, 8, 31)


if __name__ == "__main__":
    unittest.main()
