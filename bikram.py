#!/usr/bin/python3
"""Bikram Sambat dates for the Omarchy bar.

Month lengths come from the vendored Apache-2.0 table. Holidays are local
JSON. The month grid does not use the network. Once a month, the notice
command reads one Home Ministry page and compares the posted file's name,
size, and upload id with the reviewed list. It does not download that file
and it does not replace the list.
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
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
NOTICE_LIMIT = 256 * 1024
NOTICE_DEADLINE = 15
NOTICE_CHUNK = 8192
NOTICE_INTERVAL_DAYS = 30
NOTICE_CACHE_LIMIT = 4096
NOTICE_HOSTS = frozenset({"moha.gov.np", "www.moha.gov.np"})
NOTICE_FIELDS = ("pdf_name", "pdf_size", "upload")


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


class NoticeError(Exception):
    pass


def notice_page(year):
    return f"https://moha.gov.np/page/government-and-public-holidays-in-{year}"


def allowed_notice_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.username or parts.password:
        return False
    if parts.hostname not in NOTICE_HOSTS:
        return False
    prefix = "/page/government-and-public-holidays-in-"
    return parts.path.startswith(prefix) and parts.path[len(prefix):].isdigit()


class NoticeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.max_redirections = 2

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_notice_url(newurl):
            raise NoticeError("redirect left the Home Ministry holiday page")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def read_bounded(response, limit, deadline, now=time.monotonic):
    """Read at most `limit` bytes. A longer body is rejected before use."""
    declared = response.headers.get("Content-Length")
    if declared is not None:
        try:
            size = int(declared)
        except (TypeError, ValueError) as exc:
            raise NoticeError("Content-Length was not a number") from exc
        if size < 0 or size > limit:
            raise NoticeError(f"response declared {size} bytes; limit is {limit}")
    encoding = (response.headers.get("Content-Encoding") or "").strip().lower()
    if encoding not in ("", "identity"):
        raise NoticeError("compressed notice pages are not read")
    body = bytearray()
    while len(body) <= limit:
        if now() > deadline:
            raise NoticeError("the Home Ministry page took too long")
        chunk = response.read(min(NOTICE_CHUNK, limit + 1 - len(body)))
        if not chunk:
            break
        body.extend(chunk)
    if len(body) > limit:
        raise NoticeError(f"response exceeded {limit} bytes")
    return bytes(body)


def fetch_notice_page(url):
    if not allowed_notice_url(url):
        raise NoticeError("the notice address is not a Home Ministry holiday page")
    deadline = time.monotonic() + NOTICE_DEADLINE
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "omarchy-bikram/1.1",
            "Accept-Encoding": "identity",
        },
    )
    opener = urllib.request.build_opener(NoticeRedirect())
    try:
        with opener.open(request, timeout=NOTICE_DEADLINE) as response:
            if not allowed_notice_url(response.geturl()):
                raise NoticeError("redirect left the Home Ministry holiday page")
            body = read_bounded(response, NOTICE_LIMIT, deadline)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise NoticeError("not-posted") from exc
        raise NoticeError("the Home Ministry page could not be read") from exc
    except urllib.error.URLError as exc:
        raise NoticeError("the Home Ministry page could not be read") from exc
    except TimeoutError as exc:
        raise NoticeError("the Home Ministry page took too long") from exc
    return body.decode("utf-8", "replace")


def parse_notice(html):
    name = re.search(r">\s*([^<>\n]*?\.pdf)\s*<", html)
    upload = re.search(r"/upload/([0-9a-f]{32})/files/", html)
    if not name or not upload:
        raise NoticeError("the Home Ministry page has no holiday file")
    window = html[name.start():name.start() + 800]
    size = re.search(r"(\d+(?:\.\d+)?\s*[KMG]B)", window)
    if not size:
        raise NoticeError("the Home Ministry page has no file size")
    return {
        "pdf_name": " ".join(name.group(1).split()),
        "pdf_size": " ".join(size.group(1).split()),
        "upload": upload.group(1),
    }


def same_notice(seen, reviewed):
    if not seen or not reviewed:
        return False
    return all(seen.get(field) == reviewed.get(field) for field in NOTICE_FIELDS)


def load_reviewed(year):
    path = ROOT / "holidays" / f"{year}.json"
    if not path.is_file():
        return None
    reviewed = json.loads(path.read_text()).get("reviewed")
    if not isinstance(reviewed, dict):
        return None
    if not all(isinstance(reviewed.get(field), str) and reviewed[field] for field in NOTICE_FIELDS):
        return None
    return {field: reviewed[field] for field in NOTICE_FIELDS}


def cache_fresh(cache, today):
    if cache.get("seen") is None:
        return False
    try:
        checked = date.fromisoformat(str(cache.get("checked_on")))
    except ValueError:
        return False
    return 0 <= (today - checked).days < NOTICE_INTERVAL_DAYS


def read_notice_cache(path):
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_notice_cache(path, payload):
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if len(text.encode("utf-8")) > NOTICE_CACHE_LIMIT:
        raise NoticeError("notice cache would be too large")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(text)
    temporary.replace(path)


def notice_line(year, seen, reviewed, problem):
    if problem == "not-posted" and reviewed is None:
        return f"The Home Ministry has not posted the {year} holiday page. This calendar has no reviewed list for that year."
    if problem:
        if reviewed is None:
            return f"The Home Ministry page could not be read. This calendar has no reviewed list for {year}."
        return f"The Home Ministry page could not be read. This calendar still uses the reviewed {year} list."
    if reviewed is None and seen:
        return f"The Home Ministry has posted {seen['pdf_name']}. This calendar has no reviewed list for {year}."
    if seen and reviewed and not same_notice(seen, reviewed):
        return f"The Home Ministry holiday file changed. This calendar still uses the reviewed {year} list."
    return ""


def notice_payload(today, cache_dir, fetch=fetch_notice_page):
    year, _month, _day = ad_to_bs(today)
    reviewed = load_reviewed(year)
    path = Path(cache_dir) / "notice.json"
    cache = read_notice_cache(path)
    problem = ""
    if cache.get("year") == year and cache_fresh(cache, today):
        seen = cache.get("seen")
    else:
        try:
            seen = parse_notice(fetch(notice_page(year)))
        except NoticeError as exc:
            seen = None
            problem = str(exc)
        else:
            write_notice_cache(
                path,
                {"checked_on": today.isoformat(), "year": year, "seen": seen},
            )
    return {
        "ok": problem == "",
        "changed": bool(seen and reviewed and not same_notice(seen, reviewed)),
        "line": notice_line(year, seen, reviewed, problem),
        "year": year,
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


def command_notice(args):
    today = date.fromisoformat(args.today) if args.today else date.today()
    cache_dir = Path(args.cache) if args.cache else Path.home() / ".cache" / "omarchy-bikram"

    def fetch(_url):
        return Path(args.html).read_text(encoding="utf-8")

    emit(notice_payload(today, cache_dir, fetch if args.html else fetch_notice_page))
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

    notice = sub.add_parser("notice")
    notice.add_argument("--today", help="Gregorian today, for tests")
    notice.add_argument("--cache", help="Directory for the notice fingerprint")
    notice.add_argument("--html", help="Read this page instead of the ministry site")
    notice.set_defaults(func=command_notice)
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
