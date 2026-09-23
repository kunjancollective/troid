#!/usr/bin/env python3
"""Find English that is not in web/i18n/en.json: render every page in a pseudo-locale that marks each keyed
string ⟦like this⟧, drive the desk and compare through their states, and report any visible text that is
neither marked nor data (firm names and rule values from firms.json, rule-source names, the 4.41 text, the
firms' required sentences, the terms body — which stay in English by design).

  python i18n_pseudo.py                  # every page with a template or a generator renderer
  python i18n_pseudo.py --pages index,compare
"""
import argparse
import html
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i18n  # noqa: E402
import site_build  # noqa: E402
import site_text  # noqa: E402
from i18n_equiv import serve, desk_states, compare_states  # noqa: E402

ROOT = HERE.parent
PUB = ROOT / "web" / "public"


def data_strings():
    """Text that comes from data, not from en.json: every string in firms.json, the legal verbatim texts."""
    out = set()

    def walk(x):
        if isinstance(x, str):
            out.add(x)
        elif isinstance(x, dict):
            for k, v in x.items():
                if not k.startswith("_"):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    F = json.loads((ROOT / "firms.json").read_text())
    for k, v in F.items():
        if not k.startswith("_"):
            walk(v)
    out.update([site_text.HYPO, *site_text.required_sentences()])
    return sorted((s for s in out if len(s) >= 2), key=len, reverse=True)


def render_pseudo(out, pages):
    T = i18n.Strings("en", pseudo=True)
    ctx = site_build.extra_context(T)
    for page in pages:
        text = site_build.render_page(page, T, ["en"], ctx=ctx if page in site_build.STATIC else None)
        if text is None:
            print(f"skip {page}: no template or renderer yet")
            continue
        (out / ("index.html" if page == "index" else f"{page}.html")).write_text(text)


SCAN = """() => {
  const out = [];
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const p = n.parentElement;
    if (!p || ['SCRIPT','STYLE','NOSCRIPT'].includes(p.tagName)) continue;
    const t = n.textContent; if (t.trim()) out.push(t);
  }
  for (const e of document.querySelectorAll('[placeholder],[title],[aria-label],option,meta[name=description]'))
    for (const a of ['placeholder','title','aria-label','content']) if (e.getAttribute(a)) out.push(e.getAttribute(a));
  out.push(document.title);
  return out;
}"""


def leftovers(texts, data, page):
    bad = []
    for t in texts:
        s = re.sub(r"⟦[^⟧]*⟧", " ", t, flags=re.S)
        for d in data:
            if d in s:
                s = s.replace(d, " ")
        s = html.unescape(s)
        s = re.sub(r"\btroid\b|\btr\b|\bid\b|https?://\S+|[\w.-]+\.(md|json|py|csv)\b", " ", s)
        words = re.findall(r"[A-Za-z]{2,}", s)
        if words and page == "terms" and len(t) > 60:
            continue                                  # the terms body is English by design
        if words:
            bad.append((" ".join(words)[:80], t.strip()[:120]))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default=",".join(site_build.PAGES))
    a = ap.parse_args()
    pages = a.pages.split(",")
    data = data_strings()
    from playwright.sync_api import sync_playwright
    problems = 0
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for f in PUB.iterdir():
            if f.is_file() and f.suffix != ".html":
                shutil.copy(f, out / f.name)
        render_pseudo(out, pages)
        srv, url = serve(out)
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for page in pages:
                f = out / ("index.html" if page == "index" else f"{page}.html")
                if not f.exists():
                    continue
                ctx = b.new_context(viewport={"width": 1280, "height": 900})
                ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith("http://127.0.0.1") else r.continue_())
                pg = ctx.new_page()
                pg.goto(url + ("/" if page == "index" else f"/{page}"), wait_until="load")
                pg.wait_for_timeout(200)
                texts = pg.evaluate(SCAN)
                if page == "index":
                    for st in desk_states(pg):
                        texts.append(re.sub(r"<[^>]+>", " ", st[3]))
                if page == "compare":
                    for st in compare_states(pg):
                        texts.append(re.sub(r"<[^>]+>", " ", st[4]))
                bad = leftovers(texts, data, page)
                seen = set()
                for w, t in bad:
                    if (w, t) in seen:
                        continue
                    seen.add((w, t))
                    print(f"{page}: unkeyed «{w}» in: {t}")
                problems += len(seen)
                print(f"{page}: {len(seen)} unkeyed text run(s)")
                ctx.close()
            b.close()
        srv.shutdown()
    print(f"RESULT: {problems} unkeyed text run(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
