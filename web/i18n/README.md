# troid in ten languages

Every UI string lives in `en.json`, keyed (600 keys). Pages render from templates (`web/templates/`) and from the
generators (`backtest/gen_compare.py`, `gen_ledger.py`, `gen_tearsheet.py`, `regions.py`) through
`backtest/site_build.py`. English renders to `web/public/{page}.html`, exactly as before; a language renders
to `web/public/{lang}/{page}.html` only when `web/i18n/{lang}.json` says `"_status": "live"`.

`languages.json` is the registry: code, the language's name in its own script, direction, the font loaded after
Inter, the og locale, and the Intl locale (always with Latin digits).

## The rule

A language goes live only when its native-speaking reviewer has signed off — the same rule troid applies to
firm rules: reviewed, or not published. Drafts (`"_status": "draft"`) are never published, linked, listed in
hreflang or shown in the language switcher. A language set back to draft is removed from `web/public` on the
next build.

## Where each language stands

The nine `{lang}.json` files are machine drafts (`"_drafted_by": "machine draft, unreviewed"`), every key and every
firm-data string translated, each passing the contract below. `_review_notes` holds the drafter's questions for
the reviewer, by key. `review/{lang}.csv` is the sheet to send.

## Workflow

1. `python backtest/i18n_export.py [lang ...]` writes one review sheet per language: `review/{lang}.csv`, columns
   `key, english, draft, reviewer_edit, note`, UTF-8 for Google Sheets. Product names come first (they are fixed
   once and used everywhere), then shared lines, then each page in page order, then text from firm data. Rows
   whose note starts `CHECK FIRST:` are the drafter's doubts; a row with an empty key is a general question.
   The reviewer fills `reviewer_edit` where the draft is wrong and leaves it empty where it is right. It also
   writes `review/{lang}-update.csv` with only the rows that are new or whose English changed since the draft, for
   a reviewer who already has the full sheet. `review/README.md` is the reviewer packet: how to fill the sheet,
   and the sharing rules the affiliate contracts set (organic only; no boosted or paid posts; no coupon or deal
   sites).
2. `python backtest/i18n_import.py {lang} returned.csv [returned-update.csv] --by INITIALS --on YYYY-MM-DD
   [--dry-run]` applies the edits (an update sheet's rows replace the full sheet's), checks every string against
   its English, and writes `{lang}.json` with `_reviewed_by`, `_reviewed_on` and `_status: "live"`. It is refused
   whole if an English cell changed since the export (add the update sheet, or export again), a key has no value,
   or any string breaks the contract.
3. `python backtest/gen_og.py {lang}` renders `web/public/og/{lang}.png` (the share image with the translated
   tagline; needs `(cd tools/og && npm install)` once).
4. `python backtest/i18n_check_pages.py {lang}` (every page in Chromium at 390 and 1280 px), then the build
   (`cd backtest && python gen_ledger.py && python gen_tearsheet.py && python gen_compare.py`) and
   `python backtest/verify_claims.py`, which re-checks the contract and that every page in the language shows the
   same figures as its English page. Commit; the shadow loop keeps the language's pages current from then on.
5. Launch day: `site.json` `"english_features": true` gives the English pages the country selector, local times
   and share line too. English gains hreflang and the language switcher as soon as a second language is live.

## The contract (`backtest/i18n.py` `check_pair`)

- The same figures as the English, in Latin digits. Separators may follow the language (`96,000` and `96 000` are
  one figure; `Sep 21 2026` is two). A month the English names may be written as its number (`2021 年 1 月 1 日`).
- The same `{placeholders}`, HTML tags and link targets.
- `troid` lowercase, in Latin script (the file name `TROID.md` stays as it is). No exclamation mark in any script.
- Each product name in the language's fixed form (`product.*`) wherever the English uses it.

## What is never translated

The terms of use, the 17 CFR 4.41 text, each firm's required verbatim sentence, and every rule citation's
source name. On a translated page they appear in English (`lang="en"`), after a one-line summary in the reader's
language and `legal.governs` ("This translation is provided for convenience. The English version governs.").
Firm names, product labels, tickers, UTC and the evidence tiers (DERIVED, SOURCED, MODELLED, MEASURED) stay as
they are. `STYLE.md` has the voice and the per-language register.

## What translated pages add (`web/public/i18n.js`, `i18n.css`)

- Numbers the page computes are formatted with Intl in the language's locale, Latin digits; amounts stay in USD
  (`98.000,00 US$` in Spanish), never converted. In Arabic an amount is isolated left to right; a formula takes
  the direction of its first letter, so `min(a, b)` reads left to right.
- Times: the reader's local time before the UTC time (the ledger's bars and runs, compare's daily reset). The
  chart captions keep UTC.
- Your country: a selector on troid's compare and above the firms panel, preselected from the browser's language,
  never from location, remembered in the browser only. Where a firm's recorded terms exclude that country the
  firm's link is replaced by "not available in {country} per the firm's terms"; a platform-only exclusion is
  noted; a firm whose list troid has not recorded says so. Data: `availability` in each firm's `firms.json` entry.
- Share: a button beside the language switcher, with `share.line` (Web Share, else the link is copied).
- Layout mirrors for Arabic through CSS logical properties in every page's own styles.

## Conventions for strings

- Keys: `{page}.{section}.{name}`; strings a page's script needs: `{page}.js.{name}`; `{page}.meta.title`,
  `{page}.meta.description`. Shared: `product.*` (troid's product names, fixed once per language),
  `common.*`, `legal.*`, `hypo.*`, `prov.*`, `og.*`, `share.line`, `footer.text`, `ask.*` (ask troid's fixed
  replies; the English must equal `EN` in `web/api/troid.js`).
- A value is the English exactly as the page showed it, inline HTML included. Keep a sentence (usually a whole
  paragraph) in one key, so a translator sees it whole.
- Placeholders: `{name}` for anything computed, filled by `t("key", name=...)` in templates or `F(T.key, {name:
  ...})` in scripts. Never build a sentence by concatenating fragments: word order differs between languages.
- Internal links in values: `href="{L}/compare"`, and `{H}` for the home page, so a translated page links
  inside its language. External links stay as they are.
- Text from firm data (`firms.json`: panel notes, rule values, product labels) is translated by content: the
  key is `data.<hash of the English>`, so when the English changes the page shows the new English until the
  translation is reviewed again.

## Checks

- `python backtest/i18n_equiv.py` — the English pages against git HEAD: pixel-identical at 390 px and 1280 px,
  identical text, identical desk and compare output across a grid of inputs.
- `python backtest/i18n_pseudo.py` — renders every page in a pseudo-locale that marks each keyed string and
  reports visible English that is not keyed.
- `python backtest/i18n.py [lang ...]` — each language file against the contract.
- `python backtest/i18n_check_pages.py [lang ...]` — every page of a language in Chromium (drafts included).
- `verify_claims.py` re-checks every live language: translation may change words, never figures.
