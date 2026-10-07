#!/usr/bin/env python3
"""TypeSafe Jev as a gate on ask troid's replies: an offline trial, records only (the owner, 2026-10-07).

Sends troid's own saved eval replies (web/eval/runs/*: every reply with a person's read) and their cases' questions to
TypeSafe's System One endpoint with the questions in checks.json, and keeps Jev's answers in answers.jsonl. Visitor data
never goes: only eval runs are read. Nothing numeric is asked. Jev never grades the eval: the person's reads are its
verdict, and report() only measures Jev against them (labels.json sorts the reads by check, written before any call).

  TYPESAFE_API_KEY=… python3 web/eval/jev/jev_trial.py --runs web/eval/runs [--runs DIR …]   # ask, then report
  python3 web/eval/jev/jev_trial.py --runs web/eval/runs --report-only                         # report from answers.jsonl
  JEV_CHECKS=checks_v2.json python3 web/eval/jev/jev_trial.py …   # another set of questions, its answers in answers_v2.jsonl

The key is read from the environment and sent only in the Authorization header; it is never printed or written. The run
stops before a request that could take spend past checks.json's cap ($5), counted from the usage each answer reports.
"""
import argparse, json, os, ssl, sys, time, glob, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

HERE = os.path.dirname(os.path.abspath(__file__))
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
CHECKS_FILE = os.environ.get("JEV_CHECKS", "checks.json")
CHECKS = json.load(open(os.path.join(HERE, CHECKS_FILE)))
LABELS = json.load(open(os.path.join(HERE, "labels.json")))
ANSWERS = os.path.join(HERE, CHECKS_FILE.replace("checks", "answers").replace(".json", ".jsonl"))
PRICE = CHECKS["price_usd_per_mtok_input"] / 1e6
CAP = CHECKS["spend_cap_usd"]
REPLY_QS = {k: v for k, v in CHECKS["output_on_reply"].items() if not k.startswith("_")}
QR_QS = {k: v for k, v in CHECKS["output_on_question_and_reply"].items() if not k.startswith("_")}
ROUTE = CHECKS["input_routing"]["route"] if "input_routing" in CHECKS else None
ORDER = ["recommends_product", "first_person", "undated_rule", "forecast_or_signal", "names_price_source"]   # the owner's
CHECK_IDS = [c for c in ORDER if c in REPLY_QS or c in QR_QS]


def corpus(dirs):
    """Every saved reply with a person's read: {run, case, kind, q, reply, verdict, read}. A run file in two dirs counts once."""
    items, seen = [], set()
    for d in dirs:
        for f in sorted(glob.glob(os.path.join(d, "*.read.json"))):
            run = os.path.basename(f)[: -len(".read.json")]
            if run in seen:
                continue
            seen.add(run)
            read = json.load(open(f))
            res = json.load(open(f[: -len(".read.json")] + ".json"))
            for x in res["results"]:
                note = read.get(x["id"])
                if not isinstance(note, str) or not x.get("reply"):
                    continue
                items.append({"run": run, "case": x["id"], "kind": x["kind"], "q": x["q"], "reply": x["reply"],
                              "verdict": "error" if note.startswith("Error") else "pass", "read": note})
    return items


def ssl_context():
    for cafile in (os.environ.get("SSL_CERT_FILE"), "/root/.ccr/ca-bundle.crt"):
        if cafile and os.path.exists(cafile):
            return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


class Jev:
    def __init__(self, key):
        self.key, self.ctx, self.lock = key, ssl_context(), Lock()
        self.input_tokens = self.output_tokens = self.calls = 0
        self.stopped = False

    @property
    def usd(self):
        return self.input_tokens * PRICE

    def ask(self, state, questions):
        body = json.dumps({"state": state, "model": CHECKS["model"], "questions": questions}).encode()
        with self.lock:   # a conservative estimate (bytes / 3) must fit under the cap before the request goes
            if self.stopped or self.usd + (len(body) / 3) * PRICE > CAP:
                self.stopped = True
                return None
        for attempt in range(6):
            req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
                "Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120, context=self.ctx) as r:
                    j = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 529, 500, 502, 503) and attempt < 5:
                    time.sleep(min(30, 2 ** attempt) + float(e.headers.get("retry-after") or 0))
                    continue
                raise RuntimeError(f"HTTP {e.code}: {e.read()[:300].decode('utf-8', 'replace')}") from None
            except urllib.error.URLError:
                if attempt < 5:
                    time.sleep(2 ** attempt)
                    continue
                raise
        u = j.get("usage") or {}
        with self.lock:
            self.calls += 1
            self.input_tokens += u.get("input_tokens", 0)
            self.output_tokens += u.get("output_tokens", 0)
        return j


def done_keys():
    keys = set()
    if os.path.exists(ANSWERS):
        for line in open(ANSWERS):
            keys.add(json.loads(line)["key"])
    return keys


def ask_all(items, jev):
    have, out_lock = done_keys(), Lock()
    jobs = []
    for it in items:
        k = f"{it['run']}|{it['case']}"
        if REPLY_QS and k + "|reply" not in have:
            jobs.append((k + "|reply", it["reply"], REPLY_QS))
        if QR_QS and k + "|qr" not in have:
            jobs.append((k + "|qr", {"question": it["q"], "reply": it["reply"]}, QR_QS))
    qs = sorted({(it["case"], it["q"]) for it in items}) if ROUTE else []
    forward = dict(ROUTE or {})
    backward = dict(ROUTE, criteria=dict(reversed(list(ROUTE["criteria"].items())))) if ROUTE else {}
    for case, q in qs:
        for order, question in (("forward", forward), ("reversed", backward)):
            key = f"route|{case}|{order}"
            if key not in have:
                jobs.append((key, q, {"route": question}))

    def one(job):
        key, state, questions = job
        j = jev.ask(state, questions)
        if j is None:
            return
        rec = {"key": key, "model": j.get("model"), "answers": j.get("answers"), "usage": j.get("usage")}
        with out_lock, open(ANSWERS, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"{len(jobs)} requests to send ({len(have)} answered already)", file=sys.stderr)
    with ThreadPoolExecutor(8) as ex:
        for i, _ in enumerate(ex.map(one, jobs), 1):
            if i % 200 == 0:
                print(f"  {i}/{len(jobs)}  ${jev.usd:.4f}", file=sys.stderr)
    return len(jobs)


def load_answers():
    a = {}
    for line in open(ANSWERS):
        r = json.loads(line)
        a[r["key"]] = r
    return a


def report(items, sources):
    A = load_answers()
    pos = {c: {(p["run"], p["case"]) for p in LABELS["positives"][c]} for c in CHECK_IDS}
    usage_in = sum((r.get("usage") or {}).get("input_tokens", 0) for r in A.values())
    usage_out = sum((r.get("usage") or {}).get("output_tokens", 0) for r in A.values())
    models = sorted({r.get("model") for r in A.values() if r.get("model")})

    def noul(it, check):
        part = "reply" if check in REPLY_QS else "qr"
        r = A.get(f"{it['run']}|{it['case']}|{part}")
        return None if r is None else r["answers"][check]["noul"]

    L = []
    w = L.append
    n_pass = sum(it["verdict"] == "pass" for it in items)
    n_err = len(items) - n_pass
    missing = sum(any(noul(it, c) is None for c in CHECK_IDS) for it in items)
    w(f"Replies with a person's read: {len(items)} ({n_pass} passed, {n_err} with an error), from {len(sources)} sources; "
      f"{missing} without Jev's answers. Model: {', '.join(models)}.")
    w("")
    for check in CHECK_IDS:
        P = pos[check]
        w(f"### {check}")
        w("")
        w(f"Human-flagged errors of this kind: {len(P)}. Human-passed replies: {n_pass}.")
        w("")
        w("| threshold | caught | missed | false flags (of passed) | flags on other-error replies |")
        w("|---|---|---|---|---|")
        for t in CHECKS["thresholds"]:
            caught = missed = ff = other = 0
            for it in items:
                v = noul(it, check)
                if v is None:
                    continue
                flag = v >= t
                if (it["run"], it["case"]) in P:
                    caught += flag
                    missed += not flag
                elif it["verdict"] == "pass":
                    ff += flag
                else:
                    other += flag
            w(f"| {t} | {caught} | {missed} | {ff} | {other} |")
        w("")
        rows = sorted((noul(it, check), it["run"], it["case"]) for it in items if (it["run"], it["case"]) in P)
        if rows:
            w("Each human-flagged reply, Jev's value: " + "; ".join(f"{r} {c} {v:.2f}" for v, r, c in rows) + ".")
            w("")
        top = sorted(((noul(it, check), it["run"], it["case"]) for it in items
                      if it["verdict"] == "pass" and (noul(it, check) or 0) >= 0.35), reverse=True)
        if top:
            w(f"Passed replies at 0.35 or more ({len(top)}), highest first: " +
              "; ".join(f"{r} {c} {v:.2f}" for v, r, c in top[:25]) + ("; …" if len(top) > 25 else "") + ".")
            w("")

    if not ROUTE:
        w(f"Tokens: {usage_in:,} input, {usage_out:,} output (output is free), over {len(A)} requests. "
          f"Cost: ${usage_in * PRICE:.4f} at ${CHECKS['price_usd_per_mtok_input']} per million input tokens.")
        return "\n".join(L)
    # routing: one distinct question per case, asked in both option orders
    exp = CHECKS["expected_route"]
    kinds = {}
    for it in items:
        kinds[it["case"]] = it["kind"]
    routes = list(ROUTE["criteria"])
    w("### routing")
    w("")
    for order in ("forward", "reversed"):
        conf, right, total = {}, 0, 0
        per_case = []
        for case in sorted(kinds):
            r = A.get(f"route|{case}|{order}")
            if r is None:
                continue
            ans = r["answers"]["route"]
            ch = ans["choice"]
            conf.setdefault(kinds[case], {}).setdefault(ch, 0)
            conf[kinds[case]][ch] += 1
            ok = ch in exp[case]
            right += ok
            total += 1
            per_case.append((case, kinds[case], ch, ans.get("confidence"), ok))
        w(f"Options {order}: {right} of {total} cases routed to their expected route.")
        w("")
        w("| case kind | " + " | ".join(routes) + " | right |")
        w("|---|" + "---|" * (len(routes) + 1))
        for k in sorted(conf):
            n_ok = sum(1 for c, kk, ch, cf, ok in per_case if kk == k and ok)
            n = sum(conf[k].values())
            w(f"| {k} | " + " | ".join(str(conf[k].get(r, "")) for r in routes) + f" | {n_ok}/{n} |")
        w("")
        wrong = [f"{c} ({k}) → {ch} ({cf:.2f})" for c, k, ch, cf, ok in per_case if not ok]
        if wrong:
            w("Routed elsewhere: " + "; ".join(wrong) + ".")
            w("")
    flips = []
    for case in sorted(kinds):
        f_, b_ = A.get(f"route|{case}|forward"), A.get(f"route|{case}|reversed")
        if f_ and b_ and f_["answers"]["route"]["choice"] != b_["answers"]["route"]["choice"]:
            flips.append(f"{case}: {f_['answers']['route']['choice']} / {b_['answers']['route']['choice']}")
    w("Order changed the route on: " + ("; ".join(flips) if flips else "no case") + ".")
    w("")
    w(f"Tokens: {usage_in:,} input, {usage_out:,} output (output is free), over {len(A)} requests. "
      f"Cost: ${usage_in * PRICE:.4f} at ${CHECKS['price_usd_per_mtok_input']} per million input tokens.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", action="append", required=True, help="a directory of eval runs (repeatable)")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--out", default=os.path.join(HERE, CHECKS_FILE.replace("checks", "tables").replace(".json", ".md")))
    a = ap.parse_args()
    items = corpus(a.runs)
    if not a.report_only:
        key = os.environ.get("TYPESAFE_API_KEY")
        if not key:
            sys.exit("TYPESAFE_API_KEY is not set")
        jev = Jev(key)
        ask_all(items, jev)
        print(f"sent {jev.calls} requests: {jev.input_tokens:,} input tokens, {jev.output_tokens:,} output, "
              f"${jev.usd:.4f}" + ("  (STOPPED at the cap)" if jev.stopped else ""), file=sys.stderr)
    text = report(items, a.runs)
    open(a.out, "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
