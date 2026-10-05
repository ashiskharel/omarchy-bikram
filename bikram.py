#!/usr/bin/env python3
"""Bikram Sambat dates for the Omarchy bar.

Month lengths come from the vendored Apache-2.0 table. Holidays are local
JSON. This program does not open a network connection.
"""

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ANCHOR_AD = date(1918, 4, 13)
FIRST_YEAR = 1975
LAST_YEAR = 2100

MONTHS_EN = (
    "Baisakh",
    "Jestha",
    "Ashadh",
    "Shrawan",
    "Bhadra",
    "Asoj",
    "Kartik",
    "Mangsir",
    "Poush",
    "Magh",
    "Falgun",
    "Chaitra",
)
MONTHS_NE = (
    "बैशाख",
    "जेठ",
    "असार",
    "साउन",
    "भदौ",
    "असोज",
    "कात्तिक",
    "मंसिर",
    "पुस",
    "माघ",
    "फागुन",
    "चैत",
)
WEEK_EN = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEK_NE = ("सोमबार", "मंगलबार", "बुधबार", "बिहिबार", "शुक्रबार", "शनिबार", "आइतबार")
WEEK_SHORT_EN = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
WEEK_SHORT_NE = ("सो", "मं", "बु", "बि", "शु", "श", "आ")
AD_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
AD_MONTHS_SHORT = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")
SCOPES = {
    "nationwide": "",
    "valley": "Kathmandu Valley",
    "women": "women",
    "educational": "schools",
    "hill": "hills",
    "terai": "Tarai",
    "kirat": "Kirat",
    "disability": "people with disabilities",
}


def digits(number, script):
    text = str(number)
    return text.translate(DIGITS) if script == "ne" else text


def load_months():
    table = {}
    path = ROOT / "vendor" / "calendar_bs.csv"
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            table[int(row["Year"])] = [
                int(row["Baisakh"]),
                int(row["Jestha"]),
                int(row["Ashar"]),
                int(row["Shrawan"]),
                int(row["Bhadra"]),
                int(row["Asoj"]),
                int(row["Kartik"]),
                int(row["Mangsir"]),
                int(row["Poush"]),
                int(row["Magh"]),
                int(row["Falgun"]),
                int(row["Chait"]),
            ]
    return table


MONTHS = load_months()


def load_holidays():
    found = []
    directory = ROOT / "holidays"
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text())
        for item in payload.get("holidays", []):
            year, month, day = item["bs"]
            found.append(
                {
                    "bs": [year, month, day],
                    "name_en": item["name_en"],
                    "name_ne": item.get("name_ne") or item["name_en"],
                    "scope": item.get("scope") or "nationwide",
                }
            )
    found.sort(key=lambda item: tuple(item["bs"]))
    return found


HOLIDAYS = load_holidays()


class DateError(ValueError):
    pass


def month_length(year, month):
    if year not in MONTHS or not 1 <= month <= 12:
        raise DateError(f"outside the Bikram Sambat table: {year}-{month}")
    return MONTHS[year][month - 1]


def bs_to_ad(year, month, day):
    length = month_length(year, month)
    if not 1 <= day <= length:
        raise DateError(f"no such Bikram Sambat day: {year}-{month}-{day}")
    elapsed = 0
    for cursor in range(FIRST_YEAR, year):
        elapsed += sum(MONTHS[cursor])
    elapsed += sum(MONTHS[year][: month - 1])
    elapsed += day - 1
    return ANCHOR_AD + timedelta(days=elapsed)


def ad_to_bs(ad):
    if ad < ANCHOR_AD:
        raise DateError("before Baisakh 1, 1975")
    remaining = (ad - ANCHOR_AD).days
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        year_days = sum(MONTHS[year])
        if remaining < year_days:
            for month, length in enumerate(MONTHS[year], start=1):
                if remaining < length:
                    return year, month, remaining + 1
                remaining -= length
        remaining -= year_days
    raise DateError("after the Bikram Sambat table")


def holidays_on(year, month, day):
    return [item for item in HOLIDAYS if item["bs"] == [year, month, day]]


def next_holiday(ad):
    for item in HOLIDAYS:
        year, month, day = item["bs"]
        try:
            when = bs_to_ad(year, month, day)
        except DateError:
            continue
        if when >= ad:
            return item, when
    return None, None


def holiday_public(item, script):
    name = item["name_ne"] if script == "ne" else item["name_en"]
    scope = SCOPES.get(item["scope"], item["scope"])
    return {
        "name": name,
        "name_en": item["name_en"],
        "name_ne": item["name_ne"],
        "scope": scope,
        "bs": item["bs"],
    }


def ad_public(ad):
    return {
        "iso": ad.isoformat(),
        "year": ad.year,
        "month": ad.month,
        "day": ad.day,
        "month_en": AD_MONTHS[ad.month - 1],
        "month_short": AD_MONTHS_SHORT[ad.month - 1],
        "weekday_en": WEEK_EN[ad.weekday()],
        "weekday_ne": WEEK_NE[ad.weekday()],
        "saturday": ad.weekday() == 5,
    }


def bs_public(year, month, day, script):
    return {
        "year": year,
        "month": month,
        "day": day,
        "month_en": MONTHS_EN[month - 1],
        "month_ne": MONTHS_NE[month - 1],
        "day_text": digits(day, script),
        "year_text": digits(year, script),
    }


def label_for(year, month, day, ad, era, script):
    bs = f"{MONTHS_NE[month - 1]} {digits(day, 'ne')}" if script == "ne" else f"{MONTHS_EN[month - 1]} {day}"
    gregorian = f"{ad.day} {AD_MONTHS_SHORT[ad.month - 1]}"
    if era == "ad":
        return gregorian
    if era == "bs":
        return bs
    return f"{bs} · {gregorian}"


def today_payload(ad, era, script):
    year, month, day = ad_to_bs(ad)
    upcoming, when = next_holiday(ad)
    nxt = None
    if upcoming:
        nxt = holiday_public(upcoming, script)
        nxt["ad"] = when.isoformat()
        nxt["in_days"] = (when - ad).days
    return {
        "label": label_for(year, month, day, ad, era, script),
        "mark": digits(day, script),
        "era": era,
        "script": script,
        "bs": bs_public(year, month, day, script),
        "ad": ad_public(ad),
        "holidays": [holiday_public(item, script) for item in holidays_on(year, month, day)],
        "next": nxt,
    }


def month_payload(year, month, today, script):
    length = month_length(year, month)
    first = bs_to_ad(year, month, 1)
    # Sunday is the first column. Python Monday is 0, so Sunday is 6.
    lead = (first.weekday() + 1) % 7
    cells = [{"day": 0} for _ in range(lead)]
    for day in range(1, length + 1):
        ad = bs_to_ad(year, month, day)
        cells.append(
            {
                "day": day,
                "text": digits(day, script),
                "ad": ad.isoformat(),
                "ad_short": f"{ad.day} {AD_MONTHS_SHORT[ad.month - 1]}",
                "weekday_en": WEEK_EN[ad.weekday()],
                "saturday": ad.weekday() == 5,
                "today": ad == today,
                "holidays": [holiday_public(item, script) for item in holidays_on(year, month, day)],
            }
        )
    headers = WEEK_SHORT_NE if script == "ne" else WEEK_SHORT_EN
    # Headers follow the grid: Sunday first.
    ordered = [headers[6], *headers[:6]]
    return {
        "year": year,
        "month": month,
        "month_en": MONTHS_EN[month - 1],
        "month_ne": MONTHS_NE[month - 1],
        "title": f"{MONTHS_NE[month - 1]} {digits(year, script)}"
        if script == "ne"
        else f"{MONTHS_EN[month - 1]} {year}",
        "days": length,
        "headers": ordered,
        "cells": cells,
    }


def emit(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


def fail(message):
    emit({"error": message})
    return 1


def parse_era(value):
    if value not in {"ad", "bs", "both"}:
        raise DateError("era must be ad, bs, or both")
    return value


def parse_script(value):
    if value not in {"ne", "en"}:
        raise DateError("script must be ne or en")
    return value


def command_today(args):
    ad = date.fromisoformat(args.date) if args.date else date.today()
    emit(today_payload(ad, parse_era(args.era), parse_script(args.script)))
    return 0


def command_month(args):
    today = date.fromisoformat(args.today) if args.today else date.today()
    year, month, _day = ad_to_bs(today)
    year = args.year or year
    month = args.month or month
    emit(month_payload(year, month, today, parse_script(args.script)))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Bikram Sambat dates")
    sub = parser.add_subparsers(dest="command", required=True)

    today = sub.add_parser("today")
    today.add_argument("--era", default="both")
    today.add_argument("--script", default="ne")
    today.add_argument("--date", help="Gregorian date, for tests")
    today.set_defaults(func=command_today)

    month = sub.add_parser("month")
    month.add_argument("--year", type=int)
    month.add_argument("--month", type=int)
    month.add_argument("--script", default="ne")
    month.add_argument("--today", help="Gregorian today, for tests")
    month.set_defaults(func=command_month)
    return parser


def main(argv):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (DateError, ValueError) as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
