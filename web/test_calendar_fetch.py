#!/usr/bin/env python3
"""backtest/fetch_calendar.py against saved-shape samples of each agency's schedule: no network, nothing written outside a
temporary folder.

  python web/test_calendar_fetch.py

- BLS schedule rows: the reference month, and the Eastern release time in UTC on both sides of the DST switch.
- BEA's iCalendar: every GDP estimate's title shape (the later ones name more releases before the quarter, the fourth
  quarter adds "and Year"), Personal Income and Outlays, folded lines, escaped commas; other releases ignored.
- The Fed's calendar data (with its byte-order mark): the statement on a meeting's last day, one that ends in the next
  month, the minutes; everything that isn't FOMC ignored.
- The weekly merge: a source that fails keeps the events it gave last time, with their old read date; every source
  failing leaves the file as it was; the window is yesterday to 60 days ahead; one event per time and kind.
"""
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backtest"))
import fetch_calendar as FC  # noqa: E402

fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:400]}"))
    if not cond:
        fails.append(name)


BLS_PAGE = """<table class="release-list"><thead><tr><th>Reference Month</th><th>Release Date</th><th>Release Time</th></tr></thead>
<tbody><tr><td>August 2026</td><td>Sep. 11, 2026</td><td>08:30 AM</td></tr>
<tr><td>September 2026</td><td>Oct. 14, 2026</td><td>08:30 AM</td></tr>
<tr><td>October 2026</td><td>Nov. 10, 2026</td><td>08:30 AM</td></tr>
<tr><td>May 2026</td><td>June 10, 2026</td><td>08:30 AM</td></tr>
<tr><td>August 2026</td><td>Sept. 29, 2026</td><td>10:00 AM</td></tr>
<tr><td colspan="3">Note: dates are subject to change</td></tr></tbody></table>"""

BEA_ICS = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0",
    "BEGIN:VEVENT", "DTSTART:20261029T123000Z", "SUMMARY:GDP (Advance Estimate)\\, 3rd Quarter 2026", "END:VEVENT",
    "BEGIN:VEVENT", "DTSTART:20261125T133000Z", "SUMMARY:GDP (Second Estimate)\\, Corporate Profits (Preliminary)\\, 3rd", "  Quarter 2026", "END:VEVENT",
    "BEGIN:VEVENT", "DTSTART:20260924T123000Z", "SUMMARY:GDP (Third Estimate)\\, GDP by Industry\\, and Corporate Profits (Revised)\\, 2nd Quarter 2026", "END:VEVENT",
    "BEGIN:VEVENT", "DTSTART:20270128T133000Z", "SUMMARY:GDP (Advance Estimate)\\, 4th Quarter and Year 2026", "END:VEVENT",
    "BEGIN:VEVENT", "DTSTART;VALUE=DATE-TIME:20260930T123000Z", "SUMMARY:Personal Income and Outlays\\, August 2026", "END:VEVENT",
    "BEGIN:VEVENT", "DTSTART:20261006T123000Z", "SUMMARY:U.S. International Trade in Goods and Services\\, August 2026", "END:VEVENT",
    "BEGIN:VEVENT", "DTSTART:20261015", "SUMMARY:GDP (Advance Estimate)\\, 3rd Quarter 2026", "END:VEVENT",
    "END:VCALENDAR", ""])

FED_JSON = "﻿" + json.dumps({"events": [
    {"title": "FOMC Meeting", "type": "FOMC", "month": "2026-10", "days": "27-28", "time": "2:00 p.m."},
    {"title": "FOMC Minutes", "type": "FOMC", "month": "2026-11", "days": "18", "time": "2:00 p.m."},
    {"title": "FOMC Meeting", "type": "FOMC", "month": "2027-01", "days": "31-1", "time": "2:00 p.m."},
    {"title": "FOMC Meeting", "type": "FOMC", "month": "2026-12", "days": "8-9", "time": "2:00 p.m."},
    {"title": "Speech - Governor", "type": "Speeches", "month": "2026-10", "days": "2", "time": "9:15 a.m."},
    {"title": "FOMC Press Conference", "type": "FOMC", "month": "2026-10", "days": "28", "time": "2:30 p.m."}]})


def main():
    u = "https://www.bls.gov/schedule/news_release/cpi.htm"
    got = [(e["period"], e["utc"]) for e in FC.parse_bls(BLS_PAGE, "cpi", u)]
    ok("BLS: every row, its reference month, Eastern time in UTC (EDT +4, EST +5)", got == [
        ("2026-08", "2026-09-11T12:30Z"), ("2026-09", "2026-10-14T12:30Z"), ("2026-10", "2026-11-10T13:30Z"),
        ("2026-05", "2026-06-10T12:30Z"), ("2026-08", "2026-09-29T14:00Z")], got)
    e = FC.parse_bls(BLS_PAGE, "cpi", u)[0]
    ok("BLS: each event names its source and page", e["source"] == "BLS" and e["url"] == u and e["kind"] == "cpi", e)

    got = [(e["kind"], e.get("estimate"), e["period"], e["utc"]) for e in FC.parse_bea(BEA_ICS)]
    ok("BEA: every GDP estimate's title shape, PCE, folded lines and escaped commas; other releases ignored", got == [
        ("gdp", "advance", "2026-Q3", "2026-10-29T12:30Z"), ("gdp", "second", "2026-Q3", "2026-11-25T13:30Z"),
        ("gdp", "third", "2026-Q2", "2026-09-24T12:30Z"), ("gdp", "advance", "2026-Q4", "2027-01-28T13:30Z"),
        ("pce", None, "2026-08", "2026-09-30T12:30Z")], got)
    ok("BEA: each event links BEA's schedule page", all(e["source"] == "BEA" and e["url"] == FC.BEA_PAGE for e in FC.parse_bea(BEA_ICS)))

    got = [(e["kind"], e["utc"]) for e in FC.parse_fed(FED_JSON.lstrip("﻿"))]
    ok("Fed: the statement on the meeting's last day, one ending in the next month, the minutes; nothing else", got == [
        ("fomc", "2026-10-28T18:00Z"), ("minutes", "2026-11-18T19:00Z"), ("fomc", "2027-02-01T19:00Z"),
        ("fomc", "2026-12-09T19:00Z")], got)

    # the weekly merge, with the network replaced by the samples above
    now = dt.datetime(2026, 9, 25, 6, 17, tzinfo=dt.timezone.utc)
    pages = {**{v: BLS_PAGE for v in FC.BLS.values()}, FC.BEA: BEA_ICS, FC.FED: FED_JSON.lstrip("﻿")}
    real_get = FC.get
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "calendar.json"
        try:
            FC.get = lambda url: pages[url]
            FC.main(now=now, out=out)
            j = json.loads(out.read_text())
            utc = [e["utc"] for e in j["events"]]
            ok("merge: from yesterday to 60 days ahead, in time order", utc == sorted(utc) and min(utc) >= "2026-09-24T06:17Z"
               and max(utc) <= "2026-11-24T06:17Z" and "2026-09-11T12:30Z" not in utc and "2026-11-25T13:30Z" not in utc, utc)
            ok("merge: one event per time and kind", len({(e["utc"], e["kind"]) for e in j["events"]}) == len(j["events"]))
            ok("merge: every event carries its page and today's read", all(e["url"].startswith("https://") and e["read"] == "2026-09-25"
                                                                          for e in j["events"]) and j["read"] == "2026-09-25")

            def refuse(url):
                if url == FC.FED:
                    raise OSError("403")
                return pages[url]
            FC.get = refuse
            FC.main(now=now + dt.timedelta(days=7), out=out)
            k = json.loads(out.read_text())
            fed = [e for e in k["events"] if e["source"] == "Federal Reserve"]
            ok("a refusing source keeps last week's events, with their old read date", fed and all(e["read"] == "2026-09-25" for e in fed)
               and k["reads"]["fed"] == "2026-09-25" and k["reads"]["bea"] == "2026-10-02" and k["read"] == "2026-10-02", k["reads"])

            def down(url):
                raise OSError("down")
            FC.get = down
            before = out.read_text()
            try:
                FC.main(now=now + dt.timedelta(days=14), out=out)
                ok("every source failing exits", False)
            except SystemExit as ex:
                ok("every source failing leaves the file as it was, and says so", out.read_text() == before and "every source failed" in str(ex))
        finally:
            FC.get = real_get

    live = json.loads((FC.OUT).read_text())
    ok("the published calendar.json: every event names a known kind, an agency page and a read date", all(
        e["kind"] in ("cpi", "ppi", "jobs", "jolts", "gdp", "pce", "fomc", "minutes") and e["source"] in ("BLS", "BEA", "Federal Reserve")
        and e["url"].startswith(("https://www.bls.gov/", "https://www.bea.gov/", "https://www.federalreserve.gov/")) and len(e["read"]) == 10
        for e in live["events"]), live["events"][:2])
    print(f"\n{n - len(fails)}/{n} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
