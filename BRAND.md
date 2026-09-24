# troid brand

**troid** = trading droid. Lowercase always, including sentence-start.

## Voice

troid does not hype. Its defining trait is refusing to tell you what you want to hear:
*"your best backtest result is below the noise threshold for thirty configurations"*,
*"no, you can't afford that trade today"*, *"that hasn't been tested"*.

Flat, precise, slightly dry. A ship's computer, not a coach. Never excited, never
exclamatory, never emoji. Where a number exists, lead with the number.

The line, where troid introduces itself (share title and image): *"The droid does the
prop-firm math. You make the trade."* It says what the name means and where troid stops:
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

**Price strip.** Under the header on every page: BTC, ETH, SOL, XRP, BNB, the last spot price in Plex Mono and the
24-hour change as ▲/▼ with a number in `--dim`, never green or red, which read as buy and sell. A label names the source
and says firm prices come from their own feeds. Over 60 s old it greys and says "delayed"; when it fails it is hidden
with its space kept, never an error. One row on a wide screen, a row that scrolls with snap on a phone, no motion. On
the desk a symbol offers "use as entry", a convenience that fills the entry field; the stop, the size and the trade stay
the trader's. `web/api/ticker.js`, `web/public/ticker.js`.

**Term and popover.** A "?" (16 px, a 44 px touch target) beside a term opens one or two plain sentences, then the formula
where there is one, in troid's voice. A tooltip shows after 300 ms of hover and at once on keyboard focus, and toggles on
a tap; a note with links (the desk's "why these 3?") opens on a click or tap only. Esc or a click elsewhere closes it;
at most one is open. Max 280 px, `--surface2` with a `--line` border, no shadow, `--z-popover`. Its text is in
`web/i18n` (firm names from firms.json), and a screen reader hears a tooltip through `aria-describedby` without opening
it. `web/public/pop.js`.

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
