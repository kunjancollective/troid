# troid brand

**troid** = trading droid. Lowercase always, including sentence-start.

## Voice

troid does not hype. Its defining trait is refusing to tell you what you want to hear:
*"your best backtest result is below the noise threshold for thirty configurations"*,
*"no, you can't afford that trade today"*, *"that hasn't been tested"*.

Flat, precise, slightly dry. A ship's computer, not a coach. Never excited, never
exclamatory, never emoji. Where a number exists, lead with the number.

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

The dot is a status light. It ripples while troid's ledger is live (the last shadow run is
inside the window `web/public/status.json` states: two missed 4-hour runs and an hour) and
holds still when it is not, so a still dot says the live data has stopped. It links to
troid's ledger. The ripple is the site's one motion; under `prefers-reduced-motion` it stops
and a second faint ring shows live instead.

The mark on its own is the dot above its two floors (`brand/mark-2ceilings-*`): the favicon,
the touch icon and the share image use it. The social avatars and banners in brand/ still
carry the one-floor mark and the plain wordmark until they are redrawn.

Source files live in brand/. The wordmark's dot is nudged 5% of a cell right of
geometric centre; do not "correct" it. The site header carries the same nudge in CSS
(`.dot` has a larger left margin than right). Web assets: favicon.ico,
apple-touch-icon.png, og-image.png in web/public/.

## Implementation rule

Every page carries the identical `<style>` block from `web/public/index.html`, verbatim.
No page defines its own tokens. A new page starts by copying that block, then writes
only the selectors it needs beneath it. If the block changes, it changes on every page
in the same commit.

The header is the same `.bar` markup on every page: the `tr●id` wordmark (`site_build.mark`:
"tr" and "id" link home, the dot links to troid's ledger), the mono nav links. Nothing else
goes in it.
