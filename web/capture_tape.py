#!/usr/bin/env python3
"""What TradingView's real Ticker Tape sends when a symbol is tapped (the owner's iPhone: XRP tapped on troid.ai, BTC
selected). Every tape-tap test before this fed the desk a URL written by hand; the stub (backtest/tv_stub.py) draws no
links. This loads the live site with the real widget and records, for each of the tape's symbols:

- the links inside the widget's frame (text, href, target) before anything is tapped;
- every navigation a tap starts, in this tab or a new one, with its exact URL (placeholders, encoding, tracking);
- whether a new tab opened, whether it handed its address to troid's tab and closed (desk2.js), and what the desk then
  selected, and what it says by the Asset field.

It runs where TradingView can be reached: .github/workflows/tape-capture.yml, by hand. The container troid is built in
reaches neither troid.ai nor TradingView. Nothing is stored anywhere but the run's log and its artifact.

  python web/capture_tape.py --base https://troid.ai --out tape-capture.json
  python web/capture_tape.py --profiles chromium-desktop --symbols XRP,XAU,NVDA
"""
import argparse
import json
import sys
import time

PROFILES = {                      # engine, Playwright device (None: a desktop window)
    "chromium-desktop": ("chromium", None),
    "webkit-iphone13": ("webkit", "iPhone 13"),
    "chromium-pixel7": ("chromium", "Pixel 7"),
}
PAUSE = "*,*::before,*::after{animation-play-state:paused!important;animation-duration:0s!important;transition:none!important}"
DESK = """()=>{const a=document.getElementById('asset'),n=document.getElementById('assetnote'),c=document.getElementById('chipb'),m=document.getElementById('chipm'),
  r=document.getElementById('result');
  return a?{asset:a.value,opt:a.selectedOptions[0]?a.selectedOptions[0].textContent:null,note:n?n.innerText.slice(0,240):null,
    chip:c&&!c.hidden?c.innerText:null,chip_for:c&&!c.hidden?c.getAttribute('data-sym'):null,chipm:m&&!m.hidden?m.innerText:null,
    readout:r?r.innerText.slice(0,160):null,shared:!document.getElementById('shared').hidden,addr:location.href}:{addr:location.href}}"""


def widget_frame(pg, timeout=45):
    """The widget's iframe once its symbols are drawn, or None."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        el = pg.query_selector("#tv iframe")
        fr = el.content_frame() if el else None
        if fr:
            try:
                if fr.evaluate("document.body && document.body.innerText.length > 40"):
                    return fr
            except Exception:
                pass
        pg.wait_for_timeout(500)
    return None


def run_profile(p, name, base, symbols):
    engine, dev = PROFILES[name]
    b = getattr(p, engine).launch()
    kw = dict(p.devices[dev]) if dev else {"viewport": {"width": 1280, "height": 900}}
    out = {"profile": name, "links": None, "taps": []}
    try:
        ctx = b.new_context(**kw)
        navs, opened = [], []

        def on_req(r):                                  # every page load a tap starts, in any tab
            if r.resource_type == "document" and "tvwidgetsymbol" in r.url:
                navs.append(r.url)
        ctx.on("request", on_req)
        ctx.on("page", lambda q: opened.append(q))
        pg = ctx.new_page()
        pg.goto(base + "/", wait_until="load", timeout=60000)
        cfg = json.loads(pg.get_attribute("#tk", "data-tv"))
        out["largeChartUrl"] = cfg.get("largeChartUrl")
        fr = widget_frame(pg)
        if not fr:
            out["error"] = "the widget's frame never drew its symbols"
            return out
        out["frame_url"] = fr.url
        out["links"] = fr.evaluate("""()=>[...document.querySelectorAll('a')].map(a=>({text:a.innerText.replace(/\\s+/g,' ').trim().slice(0,60),
          href:a.getAttribute('href'),abs:a.href,target:a.target,rel:a.rel}))""")
        for s in cfg["symbols"]:
            sym, desc = s["proName"].split(":")[-1], s["description"]
            if symbols and not any(sym.startswith(x) or desc == x for x in symbols):
                continue
            rec = {"proName": s["proName"], "text": desc}
            for extra in ctx.pages[1:]:
                extra.close()
            navs.clear()
            pg.goto(base + "/", wait_until="load", timeout=60000)
            fr = widget_frame(pg)
            if not fr:
                rec["error"] = "no widget frame"
                out["taps"].append(rec)
                continue
            try:
                fr.add_style_tag(content=PAUSE)
            except Exception as e:
                rec["pause_error"] = str(e)[:120]
            navs.clear()
            opened.clear()
            # the tape repeats its items to loop: tap the copy that is on screen and on top at its centre (the first copy
            # can sit outside the frame, or under TradingView's logo link)
            all_ = fr.get_by_text(desc, exact=True)
            pick = None
            for i in range(all_.count()):
                c = all_.nth(i)
                hit = c.evaluate("""e=>{const r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2;
                  if(!r.width||x<0||y<0||x>innerWidth||y>innerHeight)return null;const t=document.elementFromPoint(x,y),a=e.closest('a');
                  return a&&t&&a.contains(t)?a.getAttribute('href'):null}""")
                if hit:
                    pick, rec["tapped_href"] = c, hit
                    break
            loc = pick or all_.first
            if not pick:
                rec["tap_note"] = "no copy of the symbol on screen and on top; tapped the first"
            try:
                rec["item_html"] = loc.evaluate("e=>{const x=e.closest('a,[role=link],[data-symbol],div');return (x||e).outerHTML.slice(0,400)}")
                if dev:
                    loc.tap(force=True, timeout=8000)
                else:
                    loc.click(force=True, timeout=8000)
            except Exception as e:
                rec["tap_error"] = str(e).splitlines()[0][:200]
            pg.wait_for_timeout(6000)
            rec["navigations"] = list(dict.fromkeys(navs))
            rec["new_tabs"] = [{"closed": q.is_closed(), "url": None if q.is_closed() else q.url} for q in opened]
            rec["pages"] = []
            for q in ctx.pages:
                try:
                    rec["pages"].append({"closed": q.is_closed(), **(q.evaluate(DESK) if not q.is_closed() else {})})
                except Exception as e:
                    rec["pages"].append({"error": str(e).splitlines()[0][:120]})
            out["taps"].append(rec)
            print(f"TAP {name} {desc}: navigations={rec.get('navigations')} new_tabs={len(rec['new_tabs'])} "
                  f"(closed {sum(1 for t in rec['new_tabs'] if t['closed'])}) desk={[(x.get('opt'), (x.get('note') or '')[:60]) for x in rec['pages']]}"
                  + f" chip={[(x.get('chip_for'), x.get('chip')) for x in rec['pages'] if x.get('asset')]}"
                  + f" readout={[(x.get('readout') or '')[:70] for x in rec['pages'] if x.get('asset')]}"
                  + f" tapped={rec.get('tapped_href') or rec.get('tap_note')} tabs={[t['url'] for t in rec['new_tabs']]}"
                  + (f" error={rec.get('tap_error')}" if rec.get("tap_error") else ""), flush=True)
    finally:
        b.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://troid.ai")
    ap.add_argument("--profiles", default=",".join(PROFILES))
    ap.add_argument("--symbols", default="", help="e.g. XRP,XAU,NVDA (the tape's own symbols, or their names)")
    ap.add_argument("--out", default="tape-capture.json")
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    res = {"base": a.base, "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "profiles": []}
    with sync_playwright() as p:
        for name in a.profiles.split(","):
            print(f"== {name}", flush=True)
            try:
                res["profiles"].append(run_profile(p, name, a.base.rstrip("/"), [x for x in a.symbols.split(",") if x]))
            except Exception as e:
                res["profiles"].append({"profile": name, "error": str(e).splitlines()[0][:300]})
    open(a.out, "w").write(json.dumps(res, indent=1, ensure_ascii=False))
    for pr in res["profiles"]:
        hrefs = list(dict.fromkeys((x["text"], x["href"], x["target"]) for x in (pr.get("links") or [])))
        print(f"LINKS {pr['profile']}: largeChartUrl={pr.get('largeChartUrl')} frame={str(pr.get('frame_url'))[:160]} "
              f"{len(pr.get('links') or [])} anchors, distinct {json.dumps(hrefs[:16], ensure_ascii=False)}" + (f" error={pr['error']}" if pr.get("error") else ""))
        for t in pr.get("taps", []):
            if t.get("item_html"):
                print(f"ITEM {pr['profile']} {t['text']}: {t['item_html'][:300]}")
    sys.exit(0)


if __name__ == "__main__":
    main()
