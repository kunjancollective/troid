#!/usr/bin/env python3
"""troid's compare, written ahead of its script (launch handoff 2026-09-26, 5.1 item 4: search and AI crawlers read a
page's HTML, and the compare's rule columns were empty until the script ran).

  python web/test_compare_static.py

- The page as served, before any script: each firm's column carries its rules, its sizing at the default inputs and
  its foot, every value with its provenance line (Bitfunded's 1-Step: 4% · $4,000 daily, 6% · $6,000 max, the ceilings
  swapping at $98,000, 4 losses at 0.50% before max loss binds, 12 survivable from a fresh start).
- Static equals the script: in Chromium, every language rendered with drafts (site_build.py --preview), English also
  with the reading aids on (site.json english_features, launch day), each firm's rows and foot as the page carries them
  equal the rows and foot its render() writes at the default inputs, HTML for HTML.
- The number formats behind it: backtest/jsnum.py against Chromium, String(), toFixed and toLocaleString, and Intl in
  every language's locale (languages.json "num"), over a spread of figures, ties and negatives included.

Serves a preview from a temporary directory; every request off 127.0.0.1 is refused. Spends nothing, calls no one.
"""
import json
import random
import re
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backtest"))
import gen_compare  # noqa: E402
import i18n  # noqa: E402
import jsnum  # noqa: E402
import site_build  # noqa: E402
from i18n_equiv import serve  # noqa: E402

fails, n = [], 0


def ok(name, cond, info=""):
    global n
    n += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {str(info)[:700]}"))
    if not cond:
        fails.append(name)


def build(out):
    """Every language's compare with drafts (as site_build.py --preview renders it), English again with the reading
    aids on, and the site's assets beside them."""
    live = site_build.targets(preview=True)
    pages = {}
    for code in live:
        T = i18n.Strings(code, fallback=True)
        q = site_build.out_path(code, "compare", out)
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(gen_compare.render_compare(T, live))
        pages[code] = site_build.page_url(code, "compare")
    was = site_build.SITE.get("english_features")
    site_build.SITE["english_features"] = True
    try:
        q = Path(out) / "en-features" / "compare.html"
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(gen_compare.render_compare(i18n.Strings("en"), live))
        pages["en+features"] = "/en-features/compare"
    finally:
        site_build.SITE["english_features"] = was
    for f in site_build.PUB.iterdir():
        if f.is_file() and f.suffix != ".html" and not (Path(out) / f.name).exists():
            shutil.copy(f, Path(out) / f.name)
    return pages


COMPARE = """async () => {
  const doc = new DOMParser().parseFromString(await (await fetch(location.href)).text(), "text/html");
  const out = {};
  for (const k of ORDER) {
    const g = (d, id) => { const e = d.getElementById(id); return e ? e.innerHTML : null; };
    out[k] = {rows: [g(doc, "rows-" + k), g(document, "rows-" + k)], foot: [g(doc, "foot-" + k), g(document, "foot-" + k)]};
  }
  return out;
}"""


def first_diff(a, b):
    a, b = a or "", b or ""
    i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f"at {i}: static …{a[max(0, i - 80):i + 120]!r}… script …{b[max(0, i - 80):i + 120]!r}…"


def served_text(url):
    """The column text as a crawler reads it: the served HTML, tags dropped."""
    s = urllib.request.urlopen(url).read().decode()
    cols = {}
    for k in gen_compare.ORDER:
        m = re.search(rf'<div class="rows" id="rows-{k}">(.*?)</div><div class="colfoot" id="foot-{k}"[^>]*>(.*?)</div></div>',
                      s, re.S)
        cols[k] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", (m.group(1) + " " + m.group(2)) if m else "")).strip()
    return s, cols


PROBE = """(text) => {
  const xs = JSON.parse(text), L = LANGS, out = {str: xs.map(x => String(x)), en0: xs.map(x => "$" + x.toLocaleString(undefined, {maximumFractionDigits: 0}))};
  out.fixed = [0, 1, 2].map(d => xs.map(x => Math.abs(x) < 1e21 ? x.toFixed(d) : null));
  out.loc = {};
  for (const l of L) {
    const u = d => new Intl.NumberFormat(l.intl, {style: "currency", currency: "USD", minimumFractionDigits: d, maximumFractionDigits: d});
    const f = d => new Intl.NumberFormat(l.intl, {minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: false});
    out.loc[l.code] = {usd0: xs.map(x => u(0).format(x)), usd2: xs.map(x => u(2).format(x)), fx1: xs.map(x => f(1).format(x)),
                       fx2: xs.map(x => f(2).format(x)), num: xs.map(x => new Intl.NumberFormat(l.intl).format(x))};
  }
  return out;
}"""


def figures():
    random.seed(20260928)
    xs = [0.0, -0.0, 0.5, 1.005, 2.5, -2.5, 0.25, 999.5, 1000, 9999.5, 10000, 12345, 123456.789, 1234567, -1234, -0.4, 98000,
          96000, 2000, 4000, 6000, 500, 19.999999999999996, 1.6600000000000001, 0.19999999999999996, 4.6, 3.8, 1e-7, 1e-6,
          1.5e16, 2.0 ** 53, 0.1 + 0.2, 100000 * 0.005]
    xs += [random.uniform(-1e7, 1e7) for _ in range(150)] + [round(random.uniform(0, 1000), random.randint(0, 4)) for _ in range(150)]
    return xs


def check_numbers(pg):
    xs = figures()
    langs = [{"code": l["code"], "intl": l["intl"]} for l in i18n.LANGS]
    pg.evaluate("(L) => { window.LANGS = L; }", langs)
    o = pg.evaluate(PROBE, json.dumps(xs))       # as JSON text: Playwright's own bridge hands the page -0 for any zero
    bad = []
    en = jsnum.Intl(i18n.BY_CODE["en"])
    for i, x in enumerate(xs):
        if jsnum.js_str(x) != o["str"][i]:
            bad.append(("String", x, jsnum.js_str(x), o["str"][i]))
        if "$" + en.num(x, 0) != o["en0"][i]:
            bad.append(("toLocaleString", x, "$" + en.num(x, 0), o["en0"][i]))
        for d in range(3):
            if o["fixed"][d][i] is not None and jsnum.to_fixed(x, d) != o["fixed"][d][i]:
                bad.append((f"toFixed({d})", x, jsnum.to_fixed(x, d), o["fixed"][d][i]))
    ok(f"String(), toFixed and toLocaleString as Chromium writes them ({len(xs)} figures)", not bad, bad[:5])
    for l in i18n.LANGS:
        I, r, bad = jsnum.Intl(l), o["loc"][l["code"]], []

        def ltr(s):
            return "⁦" + "".join(c for c in s if c not in jsnum.MARKS) + "⁩" if I.rtl else s
        for i, x in enumerate(xs):
            for name, mine, theirs in (("usd 0", I.usd(x, 0), ltr(r["usd0"][i])), ("usd 2", I.usd(x, 2), ltr(r["usd2"][i])),
                                       ("fixed 1", I.fixed(x, 1), r["fx1"][i]), ("fixed 2", I.fixed(x, 2), r["fx2"][i]),
                                       ("num", I.num(x), r["num"][i])):
                if mine != theirs:
                    bad.append((name, x, mine, theirs))
        ok(f"{l['code']} ({l['intl']}): languages.json \"num\" writes numbers as Chromium's Intl does", not bad, bad[:4])


def main():
    out = tempfile.TemporaryDirectory()
    pages = build(out.name)
    srv, url = serve(out.name)

    # ---------------------------------------------------------------- the page before any script
    s, cols = served_text(url + "/compare")
    b = cols["bitfunded"]
    for want in ("4% · $4,000", "6% · $6,000", "$98,000", "$2,000 (2.0%)", "4 at 0.50%", "12 from a fresh start",
                 "$500 (0.50%)", "16:00–16:10", "Computed from Bitfunded 1-Step rules as published on",
                 "Rules change without notice. Verify with the firm before trading."):
        ok(f"served HTML, no script: Bitfunded's column reads {want!r}", want in b, b[:400])
    for k in gen_compare.ORDER:
        f = gen_compare.FIRMS[k]
        ok(f"served HTML, no script: {f['name']}'s column carries its rules, sizing and provenance",
           "pending" not in cols[k][:12] and "Computed from " + f["name"] in cols[k] and "$500 (0.50%)" in cols[k], cols[k][:300])
    for k, x in gen_compare.DEFAULTS.items():
        ok(f"the {k} input opens at the value the columns are written at ({jsnum.js_str(x)})",
           re.search(rf'<input id="{k}" type="number"[^>]*value="{re.escape(jsnum.js_str(x))}"', s) is not None)

    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx = br.new_context(locale="en-US", timezone_id="UTC")
        # no country chosen, so the availability note adds nothing to either copy of a foot
        ctx.add_init_script("try{localStorage.setItem('troid.country','')}catch(e){}")
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(url) and "/api/" not in r.request.url
                  else r.fulfill(status=404, body="") if r.request.url.startswith(url) else r.abort())
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))

        # ------------------------------------------------------------ static equals the script, every language
        for code, path in pages.items():
            errors.clear()
            pg.goto(url + path)
            pg.wait_for_function("() => document.getElementById('rows-' + ORDER[0]).children.length > 0")
            got = pg.evaluate(COMPARE)
            for k in gen_compare.ORDER:
                for part in ("rows", "foot"):
                    st, js = got[k][part]
                    ok(f"{code}: {k} {part} as served equal what render() writes at the default inputs",
                       st is not None and st == js and len(st) > (400 if part == "rows" else 20), first_diff(st, js))
            ok(f"{code}: no script error", not errors, errors[:2])

        # ------------------------------------------------------------ the number formats, against Chromium
        pg.goto(url + "/compare")
        check_numbers(pg)
        br.close()
    srv.shutdown()
    print(f"\n{n - len(fails)} of {n} checks passed" + (f"; FAILED: {fails}" if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
