# troid brand

**troid** = trading droid. Lowercase always, including sentence-start.

## Voice

troid does not hype. Its defining trait is refusing to tell you what you want to hear:
*"your best backtest result is below the noise threshold for thirty configurations"*,
*"no, you can't afford that trade today"*, *"that hasn't been tested"*.

Flat, precise, slightly dry. A ship's computer, not a coach. Never excited, never
exclamatory, never emoji. Where a number exists, lead with the number.

The line, where troid introduces itself (share title and image, the X and Reddit banners, and the first line of the
home page, above its headline, in the mono and dim as the banners set it): *"The droid does the
prop-firm math. You decide the trade."* (the owner's words, 2026-09-26; it was "You make the trade."). It hides the name: "tr" in trade and "oid" in droid
take the dot's blue, the rest of those two words the wordmark's ink, the rest of the line the dim, wherever the line
appears (site_text.TAGLINE_MARKS: the home page, the share image, the banners). It says what the name means and where troid stops:
troid computes, a person places the order.

Every claim carries a tier — DERIVED, SOURCED, MODELLED, MEASURED — and a MEASURED
claim is never stated as fact.

### Third person

troid speaks of itself in the third person: "troid is independent", never "we are
independent"; "troid's ledger", never "our ledger". No first person — "we", "our", "us", "I",
and me, my, ours, we're and the like — anywhere on the site or in the assistant's prompt and
replies, except inside a firm's required verbatim sentence, text quoted from a third party,
or a user's example question, each quoted exactly as written.

- The reader is "you". A question put to troid names it: "How does troid make money?",
  not "How do you make money?".
- The assistant says "troid computes…", "troid doesn't cover that firm…". Never "I".
- Use "it" where the antecedent is unambiguous, so the name does not repeat in every clause.
- The affiliate relationship, in one sentence: "troid is an independent affiliate of the
  firms it compares."

### Product names

Lowercase, like the brand, and the same words every time they appear in prose.

| name | what it is |
|---|---|
| troid's desk | the calculator |
| troid's ledger | the shadow account |
| troid's compare | the three-firm page |
| troid's research | dashboard + tearsheet + methodology |
| ask troid | the assistant |

## Audience

troid speaks to swing and position traders — hours to days, the timeframes where a modest
edge survives the fee. Scalping and day trading appear only to show what they cost. The
Day Trader Challenge is out of scope and says so.

## Compensation, how troid talks about it

Disclosed always, never sold. The link is framed as reciprocity: if the tool earned its
place, using it is how the work stays free. Same price direct, and troid says so. No
percentages on the page — the requirement is disclosing the connection, not the rate.

Accuracy is not a conversion tactic. The moment a number is shaded to earn a click, the
brand is gone. Accuracy is the identity; the click follows from trust or not at all.

## Tokens

```
bg       #070b12   near-black navy, never pure black
surface  #0d1420   panels
surface2 #131c2b   inputs, insets
line     #1c2839   hairlines only, never heavy
ink      #e6edf5   off-white
dim      #7d8aa0   secondary
signal   #4da3ff   THE accent. state only, never decoration. The dot in the mark.
warn     #e0a33c   REDUCE
bad      #e05f4f   BLOCK
```

Light mode: bg `#f7f9fc`, surface `#fff`, surface2 `#eef2f7`, line `#dde4ee`, ink `#0b1220`,
dim `#5f6f86`, signal darkened to `#1f6fd1` for contrast.

These are the kit's colours (`brand/README.md`). The mark, the favicon, the OG image and
the site header are one object in shape and colour, or the brand is not one object.

## Type

- **Inter** — prose, headings. Tight tracking (-.02 to -.04em) at display sizes.
- **IBM Plex Mono** — every number, label, nav item, and the wordmark.

The mono/sans split is the identity. Numbers are always monospace and tabular. A number
set in a proportional face looks like marketing; set in mono it looks like an instrument.

## Rules

- 4px radius. No shadows. No emoji. No exclamation marks.
- One gradient only: the page background, `linear-gradient(180deg,#0e1a2e 0%,#0a1220 28%,
  var(--bg) 70%) fixed`, top of the viewport to 70% of it. Every panel, button and input
  on it is flat. Light mode has no gradient; the stops are navy.
- The signal colour marks state (OK, a key figure, a link). Never decoration.
- Hairline borders at 1px `--line`. Grids separated by 1px gaps over a line-coloured
  background, so panels read as an instrument cluster rather than cards.
- Numbers get more visual weight than words.

## Mark

Wordmark `troid` in Plex Mono 600, -.04em, with the o replaced by a signal dot carrying an
18% halo, above two floors: `tr●id`. The floors are the two loss ceilings, the daily limit
above the max loss; the dot stays above them, and that is the product. On the site the floors
are ink at 60%, so the letters keep their weight.

The dot is a status light. It ripples while troid's ledger is live (the last shadow run and
the last bar it processed are inside the windows `web/public/status.json` states: 13 hours
for the run, one skipped 4-hour run and a late next one; 17 hours for the bar) and holds still
when they are not, so a still dot says the live data has stopped. It links to troid's ledger.
The ripple is the site's one motion. It moves only transform and opacity (it grows to 2.8 times the dot, the halo's
old reach, fading in to 45% and out), so a phone's compositor draws it without re-laying the page. The build writes the
dot's state into every page from status.json (`site_build.status_now`), so it is right on first paint; `live.js`
confirms or corrects it, and any change of state fades over `--dur-slow` (480ms), never pops. Under
`prefers-reduced-motion` it stops and a thin solid ring in the signal colour, just outside the halo, shows live
instead; in forced colours the dot is drawn in LinkText with a ring for live.

The mark on its own is the dot above its two floors (`brand/mark-2ceilings-*`): the favicon,
the touch icon, the share image, the social avatars and the banners use it.

Source files live in brand/. The wordmark's dot is nudged 5% of a cell right of
geometric centre; do not "correct" it. The site header carries the same nudge in CSS
(`.dot` has a larger left margin than right). Web assets: favicon.ico,
apple-touch-icon.png, og-image.png in web/public/.

## Components

**Verdict.** A badge (OK, REDUCE, BLOCK; PENDING while a rule it needs is unrecorded) and a plain sentence beside it,
never a badge alone. The sentence is built from the result's own figures and adds none: "Fits. This trade risks $X,
within troid's cap of 35% of the $Y left before your daily loss limit." / "Cut to fit. Your X% would risk $A; troid sized
it down to $B, 35% of the room left." / "Can't be sized: the reason." The firm, product and room sit under both, in mono.
A "?" beside the badge says what the three verdicts mean.

**Price tape.** Under the header on every page: TradingView's free Ticker Tape widget, transparent on troid's background,
no logos, the page's theme and language, crypto then gold and oil then five stocks (firms.json `_ticker_universe`).
TradingView's attribution, "Track all markets on TradingView", sits under it in `--dim`. Its green and red are
TradingView's, accepted for this third-party strip only: everything troid draws itself keeps ▲/▼ in `--dim`, never green or
red, which read as buy and sell. A tapped symbol opens troid's desk, never TradingView's site. A pause/play button at the
label's end swaps the tape for troid's still row of the same symbols (WCAG 2.2.2), which is also what shows under reduced
motion and when the widget fails, fading in where the tape was. The still row prices crypto from `/api/ticker`
(Binance.US) in Plex Mono with the change in `--dim`, greys and says "delayed" past 60 s, and on the desk offers "use as
entry", a convenience that fills the entry field; the stop, the size and the trade stay the trader's. Gold, oil and the
stocks are names there: their quotes are TradingView's and troid doesn't copy them. One box of one height (44 px: the tape's one-line
layout at every width, the smallest TradingView draws) and one label cell, so the header never changes height.
`web/public/ticker.js`, `web/api/ticker.js`, `backtest/site_build.py` (`ticker`).

**Calendar strip.** One line under the tape's label, 32 px tall whatever it shows: the scheduled US releases of the next 7 days, each "CPI (Aug) · Tue 08:30 · 12:30 UTC" with the kind in `--ink` and the rest in `--dim`, separated by a `--line` │; on the desk each adds how long before or after the selected firm's nearest reset it lands. Names, times and sources only, never a forecast or a consensus. A tap opens a note (the popover below) saying what it is, the agency and read date, why troid lists it, the MEASURED finding stated as measured, with its sample, and that troid hasn't tested whether the releases are the cause, never "releases move prices". Empty week: "Next 7 days: no US releases scheduled." A schedule that fails or has gone stale: the line is hidden and its space kept, so nothing under it moves. When the events don't fit they move at about 40 px/s and hold while hovered, touched or open; keyboard focus, the tape's pause and reduced motion stop it. `web/public/calendar.js`, `backtest/fetch_calendar.py`, `backtest/site_build.py` (`calendar_strip`).

**The desk (redesigned 2026-09-25).** The logo becomes the account: the gauge is the mark's dot above two floors, drawn to scale, the dot at equity, the floors where the firm puts them, and a drop from the dot for the trade's loss at its stop; the dot keeps the signal blue for OK, turns `--warn` for REDUCE (the intended risk stays behind, faint) and `--bad` for BLOCK. Named state colours: `--ok`, `--reduce`, `--block`. Step cards fold to a one-line summary and say in words when their input stops the sizing. The breaker ladder gives each breaker a rung as far along as its adverse move; one far beyond the rest is stated, "→ 804.92%, off-scale", never drawn off the page. The fee bar splits the risk into the price move and the fees. Motion is transform and opacity only, from the motion tokens; nothing loops; reduced motion shows the end frame. Targets are 44 px (a step's summary, the entry chip). `web/public/desk2.js`, `web/templates/partials/_desk2.*`.

**Term and popover.** A term is its own trigger: every field label on the desk and every figure in its readout (the
verdict's badge, the binding limit and the room, each cell's label, each breaker, the losses left) carries a dotted
underline in its own ink, is reachable by Tab, and has a target of at least 24 px that stays off the input under it; no
"?" icons. "Tap any label for what it means." sits above the desk. The note reads, in order: what it is, in one plain
sentence; "also called", the names other platforms use, generic only and in English on every page (they're the words on
the firms' dashboards); an example with numbers (a field's is fixed and reproduced in `verify_claims.py`; a readout
figure's is "Now", this result's own numbers, which `i18n_equiv.py --design` checks are all in the result or the inputs);
the formula where there is one. A firm-specific example takes the firm, product and figure from firms.json with the date
troid read it. A tooltip shows after 300 ms of hover and at once on keyboard focus, and toggles on a tap; a note with
links (the desk's "why these 3?") opens on a click or tap only. Esc or a click elsewhere closes it; at most one is open.
Max 280 px, `--surface2` with a `--line` border, no shadow, `--z-popover`. Text in `web/i18n` under `glossary.*`, and a
screen reader hears a note through `aria-describedby` without opening it. `web/public/pop.js`, `backtest/regions.py`
(`glossary_html`, `term`).

## Implementation rule

Every page carries the identical `<style>` block from `web/public/index.html`, verbatim.
No page defines its own tokens. A new page starts by copying that block, then writes
only the selectors it needs beneath it. If the block changes, it changes on every page
in the same commit.

The header is the same `.bar` markup on every page: the `tr●id` wordmark (`site_build.mark`:
"tr" and "id" link home, the dot links to troid's ledger), the mono nav links. Nothing else
goes in it. The wordmark's letters are SVG paths drawn from `brand/PlexMono-SemiBold.ttf` by
`backtest/wordmark.py`, in the line box the text had (1.175em above the baseline, .425em below): a phone that has
not loaded Plex yet draws the same wordmark, so nothing moves when the font arrives. The dot and its floors stay CSS.

The wordmark is 32 px at every width (1.5× the 21 px it was; the owner, 2026-09-25, phones first and then desktop): the largest thing in the header, with every page's headline under it, 24 px on a phone to 30 px from about 680 px up (22 to 28 px on the faq and research). On a phone (640 px and under) the links fold into a dropdown behind a "data" button beside the wordmark (the owner, 2026-09-26; `site_build.nav`: each link a 44 px target, the current page in the signal blue, closed by a tap outside or Escape; without script they stay the one line that scrolls sideways) and the spacing tightens, so the desk's first field ends inside a 390 × 844 iPhone's first screen (664 px under Safari's bars). `backtest/phone_check.py` holds the wordmark over the headline, the one-line nav and the first field at every phone width.
