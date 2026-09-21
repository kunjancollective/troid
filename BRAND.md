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

## Audience

troid speaks to swing and position traders — hours to days, the timeframes where a modest
edge survives the fee. Scalping and day trading appear only to show what they cost. The
Day Trader Challenge is out of scope and says so.

## Compensation, how we talk about it

Disclosed always, never sold. The link is framed as reciprocity: if the tool earned its
place, using it is how the work stays free. Same price direct, and we say so. No
percentages on the page — the requirement is disclosing the connection, not the rate.

Accuracy is not a conversion tactic. The moment a number is shaded to earn a click, the
brand is gone. Accuracy is the identity; the click follows from trust or not at all.

## Tokens

```
bg       #08090a   near-black, never pure
surface  #0f1113   panels
surface2 #151719   inputs, insets
line     #1e2124   hairlines only, never heavy
ink      #e8e9ea   off-white
dim      #7a7f85   secondary
signal   #4dd8ac   THE accent. state only, never decoration
warn     #e0a33c   REDUCE
bad      #e05f4f   BLOCK
```

Light mode inverts with signal darkened to `#158b68` for contrast.

## Type

- **Inter** — prose, headings. Tight tracking (-.02 to -.04em) at display sizes.
- **IBM Plex Mono** — every number, label, nav item, and the wordmark.

The mono/sans split is the identity. Numbers are always monospace and tabular. A number
set in a proportional face looks like marketing; set in mono it looks like an instrument.

## Rules

- 4px radius. No shadows. No gradients. No emoji. No exclamation marks.
- The signal colour marks state (OK, a key figure, a link). Never decoration.
- Hairline borders at 1px `--line`. Grids separated by 1px gaps over a line-coloured
  background, so panels read as an instrument cluster rather than cards.
- Numbers get more visual weight than words.

## Mark

Wordmark `troid` in Plex Mono 600, -.04em, preceded by a 7px signal dot with an 18%
halo. The dot is a status light: the droid is on.

## Implementation rule

Every page carries the identical `<style>` block from `web/public/index.html`, verbatim.
No page defines its own tokens. A new page starts by copying that block, then writes
only the selectors it needs beneath it. If the block changes, it changes on every page
in the same commit.

The header is the same `.bar` markup on every page: status dot, wordmark linking home,
three mono nav links. Nothing else goes in it.
