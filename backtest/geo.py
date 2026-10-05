"""Where troid hides its affiliate links (geo.json; launch handoff 5.3, the owner's decision, 2026-10-03).

A firm's link is hidden in a country on any of geo.json's three lists: that firm's own terms (firm_terms, which must
match firms.json availability.excluded), the comprehensive embargoes and the local-law list (both for every firm). A
country troid didn't read in a firm's terms (availability.not_from_terms) and a platform-only exclusion
(availability.platform) never hide a link.

Every page carrying a link marks it data-geo="<firm>", with the message beside it marked data-geo-no="<firm>". finish()
(site_build.py) adds head() to any such page: a rule that hides both until web/public/geo.js has asked /api/where for
the visitor's country, the hidden-country lists, and geo.js. geo.js then shows each link, or its message, by adding
rules for that firm: the markup is never touched, so a column the compare's script redraws is covered as drawn. No
answer, an error or a timeout shows every message and no link (fail closed). Nothing else on a page reads the country:
the calculator is the same everywhere."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEO = json.loads((ROOT / "geo.json").read_text())
FIRMS = json.loads((ROOT / "firms.json").read_text())
LISTS = GEO["lists"]
TIMEOUT_MS = 3000          # how long geo.js waits for /api/where before it hides every link


def check():
    """geo.json holds together: firm_terms is firms.json's availability.excluded, firm by firm (never a not_from_terms
    or platform entry); every code is two capital letters and named; the law list's entries are its countries."""
    firms = {k: f for k, f in FIRMS.items() if not k.startswith("_") and isinstance(f, dict) and f.get("availability")}
    ft = LISTS["firm_terms"]["firms"]
    assert set(ft) == set(firms), f"geo.json firm_terms names {sorted(ft)}, firms.json records {sorted(firms)}"
    for k, f in firms.items():
        a = f["availability"]
        assert sorted(ft[k]) == sorted(a.get("excluded") or []), f"{k}: geo.json {ft[k]} != firms.json excluded {a.get('excluded')}"
        for cc in list(a.get("not_from_terms") or {}) + [c for v in (a.get("platform") or {}).values() for c in v]:
            assert cc not in ft[k] or cc in (a.get("excluded") or []), f"{k}: {cc} is not from the firm's terms"
    codes = set(LISTS["embargo"]["countries"]) | set(LISTS["law"]["countries"]) | {c for v in ft.values() for c in v}
    for cc in codes:
        assert len(cc) == 2 and cc.isupper() and cc in GEO["names"], f"geo.json: {cc!r} is not a named ISO code"
    assert set(LISTS["law"]["entries"]) == set(LISTS["law"]["countries"]), "geo.json: law entries != law countries"
    return True


def hidden(firm):
    """The countries where this firm's link is hidden, sorted."""
    ft = LISTS["firm_terms"]["firms"].get(firm, [])
    return sorted(set(ft) | set(LISTS["embargo"]["countries"]) | set(LISTS["law"]["countries"]))


def hidden_all():
    return {k: hidden(k) for k in LISTS["firm_terms"]["firms"]}


# Hidden until geo.js knows the country; [hidden] still wins (a firm the desk hasn't selected, the country selector)
STYLE = "<style>[data-geo],[data-geo-no]{display:none!important}[data-geo][hidden],[data-geo-no][hidden]{display:none!important}</style>"


def head():
    """What a page with an affiliate link carries in its head: the rule that hides links and messages until the check,
    the lists, and the script."""
    cfg = {"hide": hidden_all(), "timeout": TIMEOUT_MS}
    return (STYLE + "\n<script>window.TROID_GEO=" + json.dumps(cfg, separators=(",", ":")) + ";</script>\n"
            + '<script src="/geo.js" async></script>\n')


def wrap(T, firm, inner, msg_cls="geono", sep=""):
    """A firm's link (and what belongs beside it, its required wording) in its data-geo wrapper, then the message
    shown where it's hidden: "This firm's link isn't shown in your region.", linking the FAQ's answer."""
    return (f'<div data-geo="{firm}">{inner}</div>{sep}'
            f'<div class="{msg_cls}" data-geo-no="{firm}">{T("common.geo.hidden")}</div>')


check()
