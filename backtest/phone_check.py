#!/usr/bin/env python3
"""Nothing on troid's pages runs off a phone's right edge (design handoff 2026-09-24, 1a).

iOS Safari's text size (the aA menu) zooms the page: at 130% a 390 px phone lays out 300 CSS px. So each page is
loaded at the CSS widths a 375 px and a 390 px iPhone give at 100%, 115% and 130%, and on the desk every firm and
product with its result and its working open. A page fails when it scrolls sideways or when an element's right edge
passes the viewport's, unless that element sits inside a box that scrolls on its own (the working's table). Form
controls are sized as WebKit sizes them (WEBKIT_CONTROLS). The header's price tape is present, laid out as TradingView's
script lays it out (tv_stub.py).

The phone header (the owner's Android check, 2026-09-25) is held too: on every page at every width the nav is one line
(since 2026-09-26 a "data" button beside the wordmark, the owner's dropdown; the check opens it on every page and holds
the open panel to the same edges) and the wordmark is larger than the page's headline; and at 390 px, in the owner's words, "the desk's first field
visible without scrolling past more than one screenful": the desk starts inside the first screen, FIRST_SCREEN px (the
height a 390 x 844 iPhone shows under Safari's bars), and Entry, the first field a visitor fills in, is on screen after
at most one screenful of scrolling. (Until the redesign the check was the firm field inside the first screen; the
redesigned desk puts the gauge above its cards, and the owner kept that layout and this wording, 2026-09-25.)

  python phone_check.py                     # every page, web/public as it is
  python phone_check.py --pages index
  python phone_check.py --rev HEAD          # the pages as a revision left them
"""
import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_equiv import PUB, serve  # noqa: E402
from tv_stub import route_tv  # noqa: E402

PAGES = ["index", "compare", "faq", "dashboard", "chat", "terms", "ledger", "tearsheet", "sources"]
# (device width, text size): the CSS width Safari lays out
WIDTHS = sorted({round(w / z) for w in (375, 390) for z in (1.0, 1.15, 1.3)})

FIRST_SCREEN = 664

HEADER = """() => {
  const q = s => document.querySelector(s), px = e => parseFloat(getComputedStyle(e).fontSize);
  const nav = q('nav'), mark = q('.mark'), h1 = q('h1'), desk = q('#desk'), entry = q('#entry');
  return { navH: nav ? Math.round(nav.getBoundingClientRect().height) : 0, navLine: nav ? parseFloat(getComputedStyle(nav).lineHeight) || 20 : 0,
           mark: mark ? px(mark) : 0, h1: h1 ? px(h1) : 0, desk: desk ? Math.round(desk.getBoundingClientRect().top + scrollY) : null,
           entry: entry ? Math.round(entry.getBoundingClientRect().bottom + scrollY) : null };
}"""

OVER = """() => {
  const W = document.documentElement.clientWidth, out = [];
  const scrolls = (e) => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return true; } return false; };
  for (const e of document.body.querySelectorAll('*')) {
    const r = e.getBoundingClientRect();
    if (!r.width || r.right <= W + 0.5 || scrolls(e)) continue;
    const s = getComputedStyle(e); if (s.position === 'fixed' || s.visibility === 'hidden' || s.display === 'none') continue;
    const id = e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).join('.') : '');
    out.push(id + ' ' + Math.round(r.right - W) + 'px: ' + (e.textContent || '').trim().slice(0, 50));
  }
  const sw = document.documentElement.scrollWidth;
  return { sideways: sw > W ? sw - W : 0, over: out };
}"""


# WebKit, unlike Chromium, lets a select (and an input) keep its natural width as a grid or flex item's minimum: a select
# is as wide as its longest option. Chromium can't show that, so it is imitated: every grid or flex item still at
# min-width:auto that holds a form control gets its content's width as its minimum. An item the page lets shrink
# (min-width:0) is left alone, as WebKit leaves it.
WEBKIT_CONTROLS = """() => {
  for (const e of document.querySelectorAll('select,input')) {
    for (let p = e; p && p.parentElement && p !== document.body; p = p.parentElement) {
      const d = getComputedStyle(p.parentElement).display;
      if (/(grid|flex)/.test(d) && getComputedStyle(p).minWidth === 'auto') p.style.minWidth = 'max-content';
    }
  }
}"""


def desk_views(pg, url):
    """Every firm and product on the desk, as a visitor leaves it: the default inputs, then the working open; and a
    tapped tape stock no firm lists, in the Asset field as its temporary option (the longest, GOOGL's)."""
    for f in pg.eval_on_selector_all("#firm option", "e=>e.map(x=>x.value)"):
        pg.select_option("#firm", f)
        for p in pg.eval_on_selector_all("#profile option", "e=>e.map(x=>x.value)"):
            pg.select_option("#profile", p)
            yield f"{f}/{p}"
            pg.evaluate("()=>{const d=document.querySelector('#result details.work');if(d)d.open=true}")
            yield f"{f}/{p} working"
    # a glossary note open on the rightmost field label and on the readout's rightmost figure (glossary v2)
    for scope in ("#desk .grid", "#result"):
        tid = pg.evaluate("""s=>{let b=null,r=-1;for(const e of document.querySelectorAll(s+' .term')){const x=e.getBoundingClientRect();
          if(x.width&&x.right>r){r=x.right;b=e}}return b&&b.dataset.tip}""", scope)
        if tid:
            pg.evaluate("()=>window.troidPop&&window.troidPop.hide()")
            pg.click(f'{scope} .term[data-tip="{tid}"]')
            pg.wait_for_timeout(50)
            yield f"note {tid} open"
    pg.goto(url + "/?tvwidgetsymbol=NASDAQ%3AGOOGL#desk", wait_until="load")
    pg.wait_for_timeout(300)
    pg.evaluate("()=>document.querySelectorAll('details.step').forEach(d=>d.open=true)")
    yield "tape tap on GOOGL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--root", default=str(PUB))
    ap.add_argument("--rev", help="check a git revision's web/public instead")
    a = ap.parse_args()
    if a.rev:
        import tempfile
        from i18n_equiv import baseline
        a.root = tempfile.mkdtemp()
        baseline(a.rev, Path(a.root))
    from playwright.sync_api import sync_playwright
    srv, url = serve(Path(a.root))
    fails = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        for name in a.pages.split(","):
            for w in WIDTHS:
                ctx = b.new_context(viewport={"width": w, "height": 800}, device_scale_factor=2, is_mobile=True, has_touch=True)
                ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith("http://127.0.0.1") else r.continue_())
                route_tv(ctx)                   # the price tape present, as TradingView's script lays it out
                pg = ctx.new_page()
                pg.goto(url + ("/" if name == "index" else f"/{name}"), wait_until="load")
                pg.wait_for_timeout(400)
                h = pg.evaluate(HEADER)
                hdr = []
                if h["navH"] > 40:
                    hdr.append(f"the nav is {h['navH']} px tall, more than one line")
                if h["mark"] and h["h1"] and not h["mark"] > h["h1"]:        # the tearsheet (quantstats) has no troid header
                    hdr.append(f"the headline ({h['h1']:g} px) is not smaller than the wordmark ({h['mark']:g} px)")
                if name == "index" and w == 390 and not (h["desk"] and h["desk"] < FIRST_SCREEN):
                    hdr.append(f"the desk starts at {h['desk']} px, past the first screen ({FIRST_SCREEN} px)")
                if name == "index" and w == 390 and not (h["entry"] and h["entry"] <= 2 * FIRST_SCREEN):
                    hdr.append(f"Entry ends at {h['entry']} px, more than one screenful of scrolling ({2 * FIRST_SCREEN} px)")
                fails += [f"{name} {w}px header: {x}" for x in hdr]
                if name == "index":                    # the desk's step cards open, so every field is laid out
                    pg.evaluate("()=>document.querySelectorAll('details.step').forEach(d=>d.open=true)")
                views = desk_views(pg, url) if name == "index" else iter(["page"])
                bad = 0
                def menu_open():            # the phone menu (site_build.nav): opened, its panel inside the screen
                    if not pg.is_visible(".menu"):
                        return
                    pg.evaluate("()=>{scrollTo(0,0);document.querySelectorAll('.pop').forEach(p=>p.hidden=true)}")
                    pg.click(".menu")
                    pg.wait_for_timeout(80)
                    if not pg.evaluate("()=>document.getElementById('menu-nav').getBoundingClientRect().height>0"):
                        fails.append(f"{name} {w}px: the menu button does not open the links")
                    yield "menu open"
                    pg.click(".menu")
                for v in itertools.chain(views, menu_open()):
                    pg.evaluate(WEBKIT_CONTROLS)
                    r = pg.evaluate(OVER)
                    if r["sideways"] or r["over"]:
                        bad += 1
                        if bad <= 3:
                            fails.append(f"{name} {w}px {v}: scrolls {r['sideways']}px sideways; " + " | ".join(r["over"][:4]))
                print(("ok  " if not (bad or hdr) else "FAIL") + f" {name} {w}px" + (f" ({bad} views)" if bad else "")
                      + (f" (header: {'; '.join(hdr)})" if hdr else "") + (f" · desk starts at {h['desk']} px, Entry ends at {h['entry']} px" if name == "index" else ""))
                ctx.close()
        b.close()
    srv.shutdown()
    for f in fails:
        print("FAIL", f)
    print(f"RESULT: {len(fails)} problem(s) (overflow or header) at {', '.join(map(str, WIDTHS))} CSS px")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
