"""The challenge-proof audit as a check (2026-09-26, E1 and E2): run by verify_claims.py, and on its own
(python backtest/claim_check.py) it prints the audit's findings.

E1, every number on a public page has its tier and its source. A number in a page's text is covered when:
  - its section (the text between two headings) carries a tier label (SOURCED, DERIVED, MODELLED, MEASURED) and a source
    (a link, a read or publication date, a script or file troid publishes); or
  - its own paragraph cites a document with a read date ("read 2026-09-23"), or links to its entry on /sources; or
  - it is an input example (a glossary note's "Example …", "Also called …"), a formula (<code>), a date or time, a
    clause or section number; or
  - it is on the allow-list (claim_allow.json), with the reason it needs no source.
Also refused: "source not yet recorded" in a headline or a stat tile, and the words "independent", "largest",
"professional", "industry data", "studies show" without a citation beside them.

E2, one set of canonical figures (figures.json) that every page, TROID.md, the README and ask troid's context agree with:
each figure is read from its own source (firms.json, the walk-forward results, the frozen sample), and the pages are
checked for the contradictions the audit found (a 1-Step at $799, "no edge", a trade frequency or holdout that
isn't the measured one, a reset or fee that isn't the firm's).

The static pages are read as the build writes them; what their scripts draw (the desk's result, troid's compare cells)
is held to its sources elsewhere (the desk's provenance block, gen_compare's unsourced()).
"""
from __future__ import annotations

import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / "web" / "public"
PAGES = ["index", "faq", "dashboard", "chat", "compare", "ledger", "terms"]   # sources is the evidence itself
TEXTS = ["TROID.md", "README.md", "web/context/support.md", "web/context/TROID-CHARACTER.md", "METHODOLOGY.md"]

TIER = re.compile(r"\b(SOURCED|DERIVED|MODELLED|MEASURED)\b")
SOURCE = re.compile(r"\bread \d{4}-\d{2}-\d{2}|\bpublished\b|\bComputed from\b|\.py\b|\.md\b|\.json\b|\.csv\b|\bhref=|\bsha256\b", re.I)
READ = re.compile(r"\bread (on )?\d{4}-\d{2}-\d{2}|\(read \d{4}-\d{2}-\d{2}")
DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}(:\d{2})+( UTC)?\b|\bUTC[+−-]\d+\b|\b(19|20)\d{2}\b|\b\d{1,2} (January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\b")
REF = re.compile(r"\b(section|clause|s\.|RTP s\.|Terms|ToU|T&C|article)\s?\d+(\([a-z0-9]+\))*|\b\d+\([a-z]\)(\([a-z0-9]+\))*|\b\d+\.\d+ [ivx]+\b|\b[0-9]+\. (?=[A-Z])", re.I)
NUM = re.compile(r"[−+-]?\$?\d[\d,]*(?:\.\d+)?\s?(?:%|R\b|×)?")
WORDS = re.compile(r"\b(independent|largest|professional|industry data|studies show)\b", re.I)
BLOCK = {"p", "li", "td", "th", "h1", "h2", "h3", "h4", "blockquote", "dd", "dt", "figcaption", "summary", "caption", "label"}
HEAD = {"h1", "h2", "h3"}
SKIP = {"script", "style", "noscript", "svg", "template", "nav", "header", "footer", "select", "option"}


CONTAINER_TAGS = {"section", "article", "aside"}
CONTAINER_CLASSES = {"q", "panel", "stat", "hero", "disc", "discl", "hypo", "verdict"}


class _Blocks(HTMLParser):
    """A page as blocks of text in order, each with its tag, its classes, the raw HTML of its links, and the box it sits
    in: the innermost section, article or aside, or div of a CONTAINER_CLASSES class (a FAQ answer, a panel, a tile)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.cur, self.skip, self.code, self.cls = [], None, 0, 0, []
        self.boxes, self.nbox, self.open = [], 0, []

    def handle_starttag(self, t, a):
        a = dict(a)
        if t in SKIP or "data-skip-claims" in a:
            self.skip += 1
            return
        if t in CONTAINER_TAGS or t == "div":
            box = t in CONTAINER_TAGS or bool(set((a.get("class") or "").split()) & CONTAINER_CLASSES)
            if box:
                self.nbox += 1
            self.boxes.append(self.nbox if box else (self.boxes[-1] if self.boxes else 0))
        self.cls.append(a.get("class") or "")
        if t == "code":
            self.code += 1
        if t == "a" and self.cur is not None:
            self.cur["links"].append(a.get("href") or "")
        if t in BLOCK and not self.skip:
            self.cur = self._new(t)
            self.open.append(self.cur)
        elif t == "div" and not self.skip:
            self.cur = None                        # text directly in a div (a tile's figure) is a block of its own

    def _new(self, t):
        b = {"tag": t, "cls": " ".join(self.cls), "text": "", "code": "", "links": [], "box": self.boxes[-1] if self.boxes else 0}
        self.blocks.append(b)
        return b

    def handle_endtag(self, t):
        if t in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if t in BLOCK and self.open and self.open[-1]["tag"] == t:
            self.open.pop()
            self.cur = self.open[-1] if self.open else None
        elif t == "div":
            self.cur = self.open[-1] if self.open else None
        if (t in CONTAINER_TAGS or t == "div") and self.boxes:
            self.boxes.pop()
        if self.cls:
            self.cls.pop()
        if t == "code":
            self.code = max(0, self.code - 1)

    def handle_data(self, d):
        if self.skip:
            return
        if self.cur is None:
            if not d.strip():
                return
            self.cur = self._new("#text")
        self.cur["code" if self.code else "text"] += d


def numbers(text):
    """The figures in a text: dates, times, clause numbers and one- or two-digit list and count words set aside."""
    t = REF.sub(" ", DATE.sub(" ", text))
    out = []
    for m in NUM.finditer(t):
        s = m.group(0).strip()
        bare = s.strip("−+-$%R× ").replace(",", "")
        if not bare or (re.fullmatch(r"\d{1,2}", bare) and not re.search(r"[%$R×]", s)):
            continue
        out.append(s)
    return out


def allow_list():
    p = ROOT / "backtest" / "claim_allow.json"
    return json.loads(p.read_text())["allow"] if p.exists() else []


def e1_page(page, allow):
    """The numbers on a page with no tier and source, and the refused words and headlines."""
    html_text = (PUB / f"{page}.html").read_text()
    p = _Blocks()
    p.feed(html_text)
    # a block's segment is its box; blocks in no box are grouped by the heading above them
    segs, seg, byb = [], {"head": "(top)", "blocks": []}, {}
    for b in p.blocks:
        if b["box"]:
            if b["box"] not in byb:
                byb[b["box"]] = {"head": "", "blocks": []}
                segs.append(byb[b["box"]])
            sb = byb[b["box"]]
            if b["tag"] in HEAD and not sb["head"]:
                sb["head"] = re.sub(r"\s+", " ", b["text"]).strip()[:70]
            sb["blocks"].append(b)
        elif b["tag"] in HEAD:
            segs.append(seg)
            seg = {"head": re.sub(r"\s+", " ", b["text"]).strip()[:70], "blocks": [b]}
        else:
            seg["blocks"].append(b)
    segs.append(seg)
    for sg in segs:
        sg["head"] = sg["head"] or next((re.sub(r"\s+", " ", x["text"]).strip()[:70] for x in sg["blocks"] if x["text"].strip()), "")
    found = []
    mine = [a for a in allow if a["page"] in (page, "*")]
    for sg in segs:
        body = " ".join(x["text"] + " " + x["code"] + " " + " ".join("href=" + h for h in x["links"]) for x in sg["blocks"])
        tiered = bool(TIER.search(body) and SOURCE.search(body))
        for b in sg["blocks"]:
            text = re.sub(r"\s+", " ", b["text"]).strip()
            if not text:
                continue
            ok_block = (tiered or READ.search(text) or any("/sources#" in h for h in b["links"])
                        or re.match(r"(Example|Also called)\b", text) or TIER.search(text) and SOURCE.search(text + b["code"] + " ".join(b["links"])))
            for n in ([] if ok_block else numbers(text)):
                if any(a["text"] in text and (a.get("number") in (None, n)) for a in mine):
                    continue
                found.append(("E1 unsourced number", page, sg["head"], n, text[:160]))
            if (b["tag"] in HEAD or "stat" in b["cls"]) and "source not yet recorded" in text.lower():
                found.append(("E1 'source not yet recorded' in a headline or tile", page, sg["head"], "", text[:160]))
            for m in WORDS.finditer(text):
                after = text[m.start():m.start() + 220]
                cited = READ.search(after) or TIER.search(after) or b["links"]
                if not cited and not any(a["text"] in text and a.get("word") for a in mine):
                    found.append(("E1 claim word without a citation", page, sg["head"], m.group(0), text[:160]))
    return found


def _get(path):
    """A canonical figure's source value: 'firms.json:bitfunded.products.1step.fee_usd' or a results file."""
    f, _, keys = path.partition(":")
    x = json.loads((ROOT / f).read_text())
    for k in keys.split("."):
        x = x[k]
    return x


def canonical():
    """figures.json, each figure checked against its own source."""
    F = json.loads((ROOT / "figures.json").read_text())
    bad = []
    for k, v in F.items():
        if k.startswith("_") or "from" not in v:
            continue
        got = _get(v["from"])
        if isinstance(v["value"], str):
            if got != v["value"]:
                bad.append(("E2 canonical figure differs from its source", "figures.json", k, v["value"], f"{v['from']} = {got}"))
            continue
        if isinstance(got, str):
            got = re.sub(r"[^\d.]", "", got)
        if abs(float(got) - float(v["value"])) > v.get("tol", 1e-9):
            bad.append(("E2 canonical figure differs from its source", "figures.json", k, str(v["value"]), f"{v['from']} = {got}"))
    ho = F["holdout_r"]
    h = _get(ho["from_dir"])
    lo, hi = h["exp"] - 1.96 * h["sd"] / math.sqrt(h["n"]), h["exp"] + 1.96 * h["sd"] / math.sqrt(h["n"])
    if [round(lo, 3), round(hi, 3)] != ho["interval"]:
        bad.append(("E2 holdout interval differs from the walk-forward", "figures.json", "holdout_r", str(ho["interval"]), f"[{lo:.4f}, {hi:.4f}]"))
    return F, bad


def _plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))


def e2_texts(F):
    """The contradictions the audit found, looked for on every page, TROID.md, the README and ask troid's context."""
    docs = {f"{p}.html": _plain((PUB / f"{p}.html").read_text()) for p in PAGES + ["sources"]}
    docs.update({t: (ROOT / t).read_text() for t in TEXTS if (ROOT / t).exists()})
    # METHODOLOGY's corrections table quotes each error it corrects; its rows are the record, not claims
    docs["METHODOLOGY.md"] = re.sub(r"(?m)^\| \d{4}-\d{2}-\d{2} \|.*$", "", docs.get("METHODOLOGY.md", ""))
    fees = {f"{x:g}" for x in F["fee_pct"]["all"]}
    out = []
    for name, s in docs.items():
        for sent in re.split(r"(?<=[.!?])\s+|\n\n", s):
            t = re.sub(r"\s+", " ", sent)
            one = re.search(r"\$(\d{3})\b(?![,\d])[^.]{0,50}\b1-Step\b|\b1-Step\b[^.]{0,50}\$(\d{3})\b(?![,\d])", t)
            priced = one and re.search(r"\b(fee|fees|price|costs?|pay|buy|bought|purchase)\b", t, re.I)
            if priced and int(one.group(1) or one.group(2)) != F["price_1step"]["value"] and "2-Step" not in t:
                out.append(("E2 1-Step price", name, "", one.group(0), t[:160]))
            if re.search(r"(?<!measurable )\bno edge\b", t) and not re.search(r"\bedgeless\b|no edge is\b", t):
                out.append(("E2 'no edge' (the holdout shows no measurable edge)", name, "", "no edge", t[:160]))
            for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:trades?\s*)?(?:/mo\b|/month|a month|per month)", t):
                v = float(m.group(1))
                modelled = re.search(r"assum|MODELLED|income_math|simulat|ran at", t, re.I)
                if v != F["trades_per_month"]["value"] and not (v == 30 and modelled) and "$" not in t[max(0, m.start() - 12):m.start()]:
                    out.append(("E2 trade frequency", name, "", m.group(0), t[:160]))
            if re.search(r"holdout|out[- ]of[- ]sample|never saw|2021", t, re.I):
                for m in re.finditer(r"\+0\.\d{2,3}R", t):
                    if re.search(r"in[- ]sample|chosen on|best of", t[max(0, m.start() - 60):m.start()], re.I):
                        continue                             # the in-sample figure, named as such
                    if m.group(0) not in ("+" + format(F["holdout_r"]["value"], ".3f") + "R", "+0.03R", "+0.040R", "+0.10R", "+0.35R"):
                        out.append(("E2 holdout expectancy", name, "", m.group(0), t[:160]))
            for m in re.finditer(r"\b16:(\d\d) UTC", t):
                if m.group(1) not in ("00", "10", "20"):
                    out.append(("E2 reset time", name, "", m.group(0), t[:160]))
            for m in re.finditer(r"(0\.\d+)%(?:-| )per[- ]side", t):
                if f"{float(m.group(1)):g}" not in fees:
                    out.append(("E2 fee per side", name, "", m.group(0), t[:160]))
    return out


def run():
    allow = allow_list()
    found = []
    for pg in PAGES:
        found += e1_page(pg, allow)
    sys.path.insert(0, str(ROOT / "backtest"))
    from gen_compare import unsourced                     # compare: a filled cell has a recorded source (audit C)
    found += [("E1 compare cell filled but unsourced", "compare", n, x, "") for n, x in unsourced()]
    F, bad = canonical()
    return found + bad + e2_texts(F)


if __name__ == "__main__":
    res = run()
    by = {}
    for r in res:
        by.setdefault(r[0], []).append(r)
    for k, rs in by.items():
        print(f"\n{k}: {len(rs)}")
        for r in rs:
            print(f"  {r[1]} · {r[2][:50]} · {r[3]} · {r[4]}")
    print(f"\nRESULT: {len(res)} finding(s)")
    sys.exit(1 if res else 0)
