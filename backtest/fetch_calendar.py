#!/usr/bin/env python3
"""The scheduled US releases troid's calendar strip shows (ticker v2 handoff, section D; kept by v3, section E), read from
the agencies' own published schedules into web/public/calendar.json. Weekly, by .github/workflows/calendar.yml.

  python fetch_calendar.py                 # fetch, merge, write web/public/calendar.json
  python fetch_calendar.py --check FILE    # parse a saved file only (tests)

Sources, all US government, public domain, no consensus forecasts (those are proprietary):
- BLS, one schedule page per release (reference month, date, Eastern time): CPI, PPI, the Employment Situation, JOLTS.
  bls.gov refuses scripted requests that don't identify themselves, so the request names troid and a contact address.
- BEA's release schedule as iCalendar (UTC, the period in the title): GDP estimates and Personal Income and Outlays (PCE).
- The Federal Reserve's calendar data (the JSON its calendar page reads): FOMC statements and minutes, 2:00 p.m. Eastern.

Every event carries its source's page and the date troid read it. A source that fails keeps the events it gave last time,
with their old read date, so one refused request never empties the strip; the page hides an event list whose newest read
is over 14 days old. Eastern times become UTC with the IANA zone, so the DST switch is the zone's, never a guess.
"""
from __future__ import annotations
import datetime as dt
import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "calendar.json"
ET = ZoneInfo("America/New_York")
UA = "troid-calendar/1.0 (+https://troid.ai; hello@troid.ai)"
AHEAD = 60                                   # days of events kept past the read

BLS = {"cpi": "https://www.bls.gov/schedule/news_release/cpi.htm",
       "ppi": "https://www.bls.gov/schedule/news_release/ppi.htm",
       "jobs": "https://www.bls.gov/schedule/news_release/empsit.htm",
       "jolts": "https://www.bls.gov/schedule/news_release/jolts.htm"}
BEA = "https://www.bea.gov/news/schedule/ics/online-calendar-subscription.ics"   # /news/schedule/ics redirects here over http://
BEA_PAGE = "https://www.bea.gov/news/schedule"
FED = "https://www.federalreserve.gov/json/calendar.json"
FED_PAGE = "https://www.federalreserve.gov/newsevents/calendar.htm"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/calendar,application/json,*/*"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8-sig", errors="replace")


def _cells(page):
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", page):
        yield [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
               for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", row)]


def et_to_utc(day, hhmm):
    return dt.datetime.combine(day, hhmm, tzinfo=ET).astimezone(dt.timezone.utc)


def parse_bls(page, kind, url):
    """A BLS release schedule: rows of 'Reference Month | Release Date | Release Time', e.g.
    'September 2026 | Oct. 14, 2026 | 08:30 AM' (Eastern)."""
    out = []
    for c in _cells(page):
        if len(c) < 3:
            continue
        m = re.fullmatch(r"([A-Z][a-z]{2,8})\.? (\d{1,2}), (\d{4})", c[1])
        t = re.fullmatch(r"(\d{1,2}):(\d{2}) ([AP])M", c[2])
        ref = re.fullmatch(r"([A-Z][a-z]+) (\d{4})", c[0])
        if not (m and t and ref):
            continue
        day = dt.datetime.strptime(f"{m.group(1)[:3]} {m.group(2)} {m.group(3)}", "%b %d %Y").date()
        h = int(t.group(1)) % 12 + (12 if t.group(3) == "P" else 0)
        when = et_to_utc(day, dt.time(h, int(t.group(2))))
        out.append({"kind": kind, "period": dt.datetime.strptime(c[0], "%B %Y").strftime("%Y-%m"),
                    "utc": when.strftime("%Y-%m-%dT%H:%MZ"), "source": "BLS", "url": url})
    return out


def _ics_events(text):
    text = text.replace("\r\n ", "").replace("\r\n\t", "").replace("\r", "")
    for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", text, re.S):
        f = {}
        for line in block.strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                f[k.split(";")[0]] = v.replace("\\,", ",").replace("\\;", ";").strip()
        yield f


def parse_bea(text):
    """BEA's schedule as iCalendar: 'GDP (Advance Estimate), 3rd Quarter 2026' (the later estimates name more
    releases before the quarter: 'GDP (Third Estimate), GDP by Industry, and Corporate Profits (Revised), 2nd Quarter
    2026'; the fourth quarter is '4th Quarter and Year 2026') and 'Personal Income and Outlays, August 2026', at UTC
    times (DTSTART ...Z)."""
    out = []
    for f in _ics_events(text):
        s, d = f.get("SUMMARY", ""), f.get("DTSTART", "")
        m = re.fullmatch(r"(\d{8})T(\d{4})\d{2}Z", d)
        if not m:
            continue
        when = dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M")
        g = re.match(r"GDP \((Advance|Second|Third) Estimate\).*, (\d)(?:st|nd|rd|th) Quarter(?: and Year)? (\d{4})$", s)
        p = re.match(r"Personal Income and Outlays, ([A-Z][a-z]+)(?: and [A-Z][a-z]+)? (\d{4})$", s)
        if g:
            out.append({"kind": "gdp", "estimate": g.group(1).lower(), "period": f"{g.group(3)}-Q{g.group(2)}",
                        "utc": when.strftime("%Y-%m-%dT%H:%MZ"), "source": "BEA", "url": BEA_PAGE})
        elif p:
            out.append({"kind": "pce", "period": dt.datetime.strptime(f"{p.group(1)} {p.group(2)}", "%B %Y").strftime("%Y-%m"),
                        "utc": when.strftime("%Y-%m-%dT%H:%MZ"), "source": "BEA", "url": BEA_PAGE})
    return out


def parse_fed(text):
    """The Fed's calendar data: {'events': [{'title': 'FOMC Meeting' | 'FOMC Minutes', 'type': 'FOMC', 'month': '2026-10',
    'days': '27-28', 'time': '2:00 p.m.'}, ...]}. A meeting's entry is its last day, when the statement is released; a
    meeting that ends in the next month ('31-1') ends in that month."""
    out = []
    for e in json.loads(text).get("events", []):
        title = e.get("title", "")
        if e.get("type") != "FOMC" or title not in ("FOMC Meeting", "FOMC Minutes"):
            continue
        t = re.fullmatch(r"(\d{1,2}):(\d{2}) ([ap])\.m\.", (e.get("time") or "").strip())
        days = re.findall(r"\d+", e.get("days") or "")
        if not (t and days and re.fullmatch(r"\d{4}-\d{2}", e.get("month", ""))):
            continue
        y, mo = map(int, e["month"].split("-"))
        if int(days[-1]) < int(days[0]):
            y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
        h = int(t.group(1)) % 12 + (12 if t.group(3) == "p" else 0)
        when = et_to_utc(dt.date(y, mo, int(days[-1])), dt.time(h, int(t.group(2))))
        out.append({"kind": "fomc" if title == "FOMC Meeting" else "minutes", "utc": when.strftime("%Y-%m-%dT%H:%MZ"),
                    "source": "Federal Reserve", "url": FED_PAGE})
    return out


def main(now=None, out=OUT):
    now = now or dt.datetime.now(dt.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    old = json.loads(out.read_text()) if out.exists() else {"events": []}
    events, reads, failed = [], {}, []
    jobs = [(f"bls:{k}", (lambda k=k, u=u: parse_bls(get(u), k, u))) for k, u in BLS.items()]
    jobs += [("bea", lambda: parse_bea(get(BEA))), ("fed", lambda: parse_fed(get(FED)))]
    for name, job in jobs:
        try:
            got = job()
            if not got:
                raise ValueError("no events parsed")
            for e in got:
                e["read"] = today
            events += got
            reads[name] = today
        except Exception as ex:                 # keep what this source gave last time, with its old read date
            failed.append(f"{name}: {ex}")
            src = {"bls": "BLS", "bea": "BEA", "fed": "Federal Reserve"}[name.split(":")[0]]
            kind = name.split(":")[1] if ":" in name else None
            kept = [e for e in old.get("events", []) if e["source"] == src and (kind is None or e["kind"] == kind)]
            events += kept
            reads[name] = max((e["read"] for e in kept), default=None)
    lo, hi = (now - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%MZ"), (now + dt.timedelta(days=AHEAD)).strftime("%Y-%m-%dT%H:%MZ")
    events = sorted({(e["utc"], e["kind"]): e for e in events if lo <= e["utc"] <= hi}.values(), key=lambda e: (e["utc"], e["kind"]))
    doc = {"_note": "Scheduled US releases for troid's calendar strip, from the agencies' own schedules "
                    "(backtest/fetch_calendar.py, weekly). Times in UTC. No forecasts.",
           "read": today, "reads": reads, "events": events}
    for f in failed:
        print("kept last read:", f, file=sys.stderr)
    if len(failed) == len(jobs):
        sys.exit("every source failed; calendar.json left as it was")
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    print(f"calendar.json: {len(events)} events to {hi[:10]}; {len(failed)} source(s) kept from the last read")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        t = Path(sys.argv[2]).read_text()
        print(json.dumps(parse_fed(t) if t.lstrip().startswith("{") else parse_bea(t) if "BEGIN:VCALENDAR" in t
                         else parse_bls(t, "cpi", "file"), indent=1))
    else:
        main()
