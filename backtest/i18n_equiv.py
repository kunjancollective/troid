#!/usr/bin/env python3
"""Prove the English site is unchanged by the move to templates (HANDOFF-global-launch: "English site unchanged").

Compares web/public against a git revision (default HEAD) of the same files:
  1. every page at 390 px and 1280 px: full-page screenshots, pixel for pixel, and the visible text;
  2. troid's desk: the result panel's HTML across a grid of firms, products and inputs;
  3. troid's compare: the three columns' HTML across a grid of sizing inputs.
External requests (fonts, the chart library) are blocked in both, so the comparison is deterministic.

  python i18n_equiv.py                 # against HEAD
  python i18n_equiv.py --rev abc203b   # against another revision
  python i18n_equiv.py --pages index,compare
"""
import argparse
import http.server
import io
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "web" / "public"
PAGES = ["index", "compare", "faq", "dashboard", "chat", "terms", "ledger", "tearsheet"]
WIDTHS = (390, 1280)


def baseline(rev, dest):
    names = subprocess.run(["git", "ls-tree", "--name-only", rev, "web/public/"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.split()
    for n in names:
        p = Path(n)
        if p.suffix in (".html", ".png", ".ico", ".md", ".css"):
            data = subprocess.run(["git", "show", f"{rev}:{n}"], cwd=ROOT, capture_output=True, check=True).stdout
            (dest / p.name).write_bytes(data)


def serve(directory):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(directory), **k)

        def log_message(self, *a):
            pass

        def do_GET(self):
            path = self.path.split("?")[0]
            if path != "/" and "." not in path.rsplit("/", 1)[-1]:
                self.path = path + ".html"                      # cleanUrls, as Vercel serves them
            return super().do_GET()
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


DESK_GRID = []
for q, eq, ds, side, entry, stop, lev, mode in [
        (100000, 100000, 100000, "1", 77872, 74814, 5, "cross"),
        (100000, 96000, 96000, "-1", 77872, 78105.616, 5, "cross"),
        (100000, 106000, 106000, "1", 77872, 74814, 150, "isolated"),
        (30000, 30000, 30000, "1", 77872, 74814, 150, "cross"),
        (10000, 10000, 10000, "1", 100, 101, 5, "cross"),
        (100000, 93000, 94000, "1", 77872, 77600, 20, "isolated")]:
    DESK_GRID.append(dict(quota=q, equity=eq, daystart=ds, side=side, entry=entry, stop=stop, lev=lev, mode=mode))


def desk_states(page):
    out = []
    firms = page.eval_on_selector_all("#firm option", "e=>e.map(x=>x.value)")
    for f in firms:
        page.select_option("#firm", f)
        for p in page.eval_on_selector_all("#profile option", "e=>e.map(x=>x.value)"):
            page.select_option("#profile", p)
            for g in DESK_GRID:
                page.evaluate("""g=>{for(const k of ['quota','equity','daystart','entry','stop','lev']){const e=document.getElementById(k);e.value=g[k];}
                  document.getElementById('side').value=g.side;document.getElementById('mode').value=g.mode;
                  document.getElementById('quota').dispatchEvent(new Event('input'));}""", g)
                out.append((f, p, str(g), page.inner_html("#result")))
            page.evaluate("()=>{const d=document.querySelector('#result details.work');if(d){d.open=true;}"
                          "document.getElementById('quota').dispatchEvent(new Event('input'))}")
            out.append((f, p, "working open", page.inner_html("#result")))
    return out


def compare_states(page):
    out = []
    for q, r, s, lev in [(100000, 0.5, 1.66, 5), (10000, 1, 0.3, 150), (30000, 2, 4, 20), (50000, 0.25, 1, 100)]:
        page.evaluate("""a=>{const [q,r,s,l]=a;document.getElementById('quota').value=q;document.getElementById('risk').value=r;
          document.getElementById('stop').value=s;document.getElementById('lev').value=l;
          document.getElementById('quota').dispatchEvent(new Event('input'));}""", [q, r, s, lev])
        out.append((q, r, s, lev, page.inner_html(".cols")))
    return out


def render_english(out):
    """The English pages as the templates and generators render them now, into out (never web/public, so
    parallel work cannot race on it). A page with nothing to render yet is copied from web/public."""
    import shutil
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import i18n
    import site_build
    T = i18n.Strings("en")
    ctx = site_build.extra_context(T)
    for f in PUB.iterdir():
        if f.is_file():
            shutil.copy(f, out / f.name)
    for page in PAGES:
        text = site_build.render_page(page, T, ["en"], ctx=ctx if page in site_build.STATIC else None)
        if text is not None:
            (out / ("index.html" if page == "index" else f"{page}.html")).write_text(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--shots", default="", help="directory to keep differing screenshots in")
    a = ap.parse_args()
    pages = a.pages.split(",")
    from playwright.sync_api import sync_playwright
    from PIL import Image, ImageChops
    fails = []
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as tmp2:
        base, new = Path(tmp), Path(tmp2)
        baseline(a.rev, base)
        render_english(new)
        s_old, u_old = serve(base)
        s_new, u_new = serve(new)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for page_name in pages:
                path = "/" if page_name == "index" else f"/{page_name}"
                for w in WIDTHS:
                    shots, texts, errs = [], [], []
                    for u in (u_old, u_new):
                        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1)
                        ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith("http://127.0.0.1") else r.continue_())
                        pg = ctx.new_page()
                        pe = []
                        pg.on("pageerror", lambda e, pe=pe: pe.append(str(e)))
                        pg.goto(u + path, wait_until="load")
                        pg.wait_for_timeout(250)
                        shots.append(Image.open(io.BytesIO(pg.screenshot(full_page=True))).convert("RGB"))
                        texts.append(pg.inner_text("body"))
                        errs.append(pe)
                        if w == WIDTHS[-1] and page_name == "index":
                            st = desk_states(pg)
                            if u == u_old:
                                desk_old = st
                            else:
                                bad = [x[:3] for x, y in zip(desk_old, st) if x != y]
                                if len(desk_old) != len(st) or bad:
                                    fails.append(f"desk: {len(bad)} of {len(st)} states differ, first {bad[:3]}")
                                else:
                                    print(f"ok   desk: {len(st)} result states identical")
                        if w == WIDTHS[-1] and page_name == "compare":
                            st = compare_states(pg)
                            if u == u_old:
                                cmp_old = st
                            else:
                                bad = [x[:4] for x, y in zip(cmp_old, st) if x != y]
                                if bad:
                                    fails.append(f"compare: {len(bad)} sizing states differ: {bad}")
                                else:
                                    print(f"ok   compare: {len(st)} sizing states identical")
                        ctx.close()
                    if errs[0] != errs[1]:
                        fails.append(f"{page_name} {w}px: page errors differ: {errs[0]} vs {errs[1]}")
                    if texts[0] != texts[1]:
                        fails.append(f"{page_name} {w}px: visible text differs")
                    if shots[0].size != shots[1].size or ImageChops.difference(shots[0], shots[1]).getbbox():
                        bbox = None if shots[0].size != shots[1].size else ImageChops.difference(shots[0], shots[1]).getbbox()
                        fails.append(f"{page_name} {w}px: pixels differ (size {shots[0].size} vs {shots[1].size}, box {bbox})")
                        if a.shots:
                            Path(a.shots).mkdir(parents=True, exist_ok=True)
                            shots[0].save(Path(a.shots) / f"{page_name}_{w}_old.png"); shots[1].save(Path(a.shots) / f"{page_name}_{w}_new.png")
                    else:
                        print(f"ok   {page_name} {w}px: pixel-identical, text identical")
            b.close()
        s_old.shutdown(); s_new.shutdown()
    for f in fails:
        print("FAIL", f)
    print(f"RESULT: {len(fails)} difference(s) against {a.rev}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
