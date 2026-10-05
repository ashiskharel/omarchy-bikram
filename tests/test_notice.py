import tempfile
import unittest
from datetime import date
from pathlib import Path

import bikram

FIXTURE = (Path(__file__).parent / "notice_fixture.html").read_text(encoding="utf-8")
REVIEWED = {
    "pdf_name": "२०८३_सालको_सार्वजनिक_विदा_(67_11_18).pdf",
    "pdf_size": "8.22 MB",
    "upload": "e66443e81e8cc9c4fa5c099a1fb1bb87",
}


class FakeResponse:
    def __init__(self, headers, chunks):
        self.headers = headers
        self.chunks = list(chunks)
        self.reads = 0

    def read(self, _count):
        self.reads += 1
        if not self.chunks:
            return b""
        return self.chunks.pop(0)


class NoticeTest(unittest.TestCase):
    def test_parse_ministry_file_identity(self):
        self.assertEqual(bikram.parse_notice(FIXTURE), REVIEWED)

    def test_content_length_is_rejected_before_the_body(self):
        response = FakeResponse({"Content-Length": str(bikram.NOTICE_LIMIT + 1)}, [b"unused"])
        with self.assertRaises(bikram.NoticeError):
            bikram.read_bounded(response, bikram.NOTICE_LIMIT, deadline=10_000)
        self.assertEqual(response.reads, 0)

    def test_body_over_the_limit_is_not_returned(self):
        response = FakeResponse({}, [b"a" * (bikram.NOTICE_LIMIT + 1)])
        with self.assertRaises(bikram.NoticeError):
            bikram.read_bounded(response, bikram.NOTICE_LIMIT, deadline=10_000)

    def test_deadline_stops_a_slow_body(self):
        response = FakeResponse({}, [b"abcdef", b"ghijkl"])
        clock = {"now": 0}

        def now():
            clock["now"] += 6
            return clock["now"]

        with self.assertRaises(bikram.NoticeError):
            bikram.read_bounded(response, 100, deadline=10, now=now)
        self.assertEqual(response.reads, 1)

    def test_compressed_body_is_refused(self):
        response = FakeResponse({"Content-Encoding": "gzip"}, [b"x"])
        with self.assertRaises(bikram.NoticeError):
            bikram.read_bounded(response, 100, deadline=10_000)

    def test_redirect_must_stay_on_the_ministry_page(self):
        handler = bikram.NoticeRedirect()
        with self.assertRaises(bikram.NoticeError):
            handler.redirect_request(None, None, 302, "found", {}, "https://example.com/page")
        self.assertFalse(bikram.allowed_notice_url("http://moha.gov.np/page/government-and-public-holidays-in-2083"))
        self.assertTrue(bikram.allowed_notice_url("https://www.moha.gov.np/page/government-and-public-holidays-in-2083"))

    def test_fresh_check_does_not_read_the_page_again(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "notice.json"
            bikram.write_notice_cache(
                cache,
                {"checked_on": "2026-10-01", "year": 2083, "seen": REVIEWED},
            )

            def fetch(_url):
                raise AssertionError("network")

            payload = bikram.notice_payload(date(2026, 10, 5), directory, fetch)
        self.assertEqual(payload["line"], "")
        self.assertFalse(payload["changed"])

    def test_a_different_file_does_not_replace_the_reviewed_list(self):
        changed = FIXTURE.replace("e66443e81e8cc9c4fa5c099a1fb1bb87", "a" * 32)
        holiday = Path(bikram.ROOT) / "holidays" / "2083.json"
        before = holiday.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            payload = bikram.notice_payload(date(2026, 10, 5), directory, lambda _url: changed)
            self.assertTrue(payload["changed"])
            self.assertIn("still uses the reviewed 2083 list", payload["line"])
            cached = (Path(directory) / "notice.json").read_text(encoding="utf-8")
            self.assertNotIn("<table>", cached)
            self.assertLess(len(cached.encode("utf-8")), bikram.NOTICE_CACHE_LIMIT)
        self.assertEqual(holiday.read_bytes(), before)

    def test_a_failed_read_keeps_the_reviewed_list(self):
        def fetch(_url):
            raise bikram.NoticeError("the Home Ministry page could not be read")

        with tempfile.TemporaryDirectory() as directory:
            payload = bikram.notice_payload(date(2026, 10, 5), directory, fetch)
            self.assertFalse((Path(directory) / "notice.json").exists())
        self.assertIn("still uses the reviewed 2083 list", payload["line"])
        self.assertFalse(payload["changed"])


if __name__ == "__main__":
    unittest.main()
