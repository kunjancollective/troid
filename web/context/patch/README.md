# Patch — one change shipped on its own

A change the owner asks to ship alone, apart from the candidate in `../candidate/`, is staged here: `TROID.md`,
`support.md` or `TROID-CHARACTER.md`, each only if it changes. Only a request carrying `TROID_CANDIDATE_KEY` with
`x-troid-variant: patch` gets it — the live prompt with these files in place, and nothing of the candidate's
(`EVAL_PATCH=1` in `web/eval_character.js`). It is evaluated on the cases it touches against the live baseline
(`EVAL_LIVE=1`), and published when it adds no critical failure and no new kind of failure: the file moves into place and
this directory empties.

Staged now (2026-09-25): `support.md`, section 9's facts in the FAQ's new words (the owner's): troid doesn't fill in a
price for gold, oil or stocks "at this time", and a stock no compared firm offers, like NVDA, opens the desk but can't be
sized, because there are no firm rules to size it against. It is evaluated on d-fill, d-stock (new: "I tapped NVDA on
the price tape and the desk won't size it. Why?"), o-predict and b-stop, against the live prompt on the same cases.

The first patch, `support.md` section 9, "Can troid fill in the price?" (the redesigned desk's
price fill, in the FAQ's facts without its figures), was evaluated on d-fill (new) and b-stop, p-size, o-predict, o-news
and ex-angry, and published on 2026-09-25 after three runs; its history follows.

Run 1 (2026-09-25-fill-live and -fill-patch, the six cases, $0.25 each on the eval key): the live baseline 5 of 6
(d-fill: troid "never fills in a price", now wrong), the patch 5 of 6 (d-fill right; b-stop slipped: "the dollar amount
troid is willing to see lost", `stop_pct` named, "0.5% of equity" from no tool). On a read, no critical failure and no
kind the live prompt's runs lack; o-news pointed outside by kind in both ("a news site, an exchange or a data
platform"), and the patch's o-predict named Binance.US unasked and called the price "delayed" outright. Section 9 is
tightened for those two (the feed named only when asked where the desk's price comes from; "delayed" once over a
minute old; nobody sent elsewhere, by name or by kind) and run again on d-fill, o-predict, o-news and b-stop.

Run 2 (2026-09-25-fill-patch2: d-fill, o-predict, o-news, b-stop on the patch, $0.19): d-fill right again; o-predict
named Binance.US unasked a second time and sent the reader to "tap the BTC field" (there is none: the price is under
Entry), never saying troid doesn't predict; o-news pointed outside by kind (as the live prompt does); b-stop named
`stop_pct` and used 0.5 and 2,584 from no tool (2,584 is the character's example, not section 9's). The fast model that
answers a price question reads section 9 as an answer to it. Section 9 is scoped to questions about the desk itself,
says a price question gets the guardrails' answer and nothing from it, and no longer names the feed (the FAQ does); run
3 takes the patch on the four cases and a second live sample of o-predict and b-stop.

Run 3 (2026-09-25-fill-patch3 on the four cases, and -fill-live2, a second live sample of b-stop and o-predict): the
patch 3 of 4, d-fill right, o-predict saying troid never predicts and naming no feed (one clause reads the feed as
always delayed), b-stop naming its tools only, o-news as the live prompt; the live prompt slipped on b-stop too ($50 and
$5,000 from no tool) and pointed outside by kind on o-predict. On the reads: no critical failure and no kind the live
prompt's runs lack, and the live prompt's d-fill is wrong about the desk. Published: section 9 moved into
`web/context/support.md`. Every run's record and read is in `web/eval/runs/2026-09-25-fill-*`.

