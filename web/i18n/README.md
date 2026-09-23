# troid in ten languages

Every UI string lives in `en.json`, keyed. Pages render from templates (`web/templates/`) and from the
generators (`backtest/gen_compare.py`, `gen_ledger.py`, `gen_tearsheet.py`, `regions.py`) through
`backtest/site_build.py`. English renders to `web/public/{page}.html`, exactly as before; a language renders
to `web/public/{lang}/{page}.html` only when `web/i18n/{lang}.json` says `"_status": "live"`.

## The rule

A language goes live only when its native-speaking reviewer has signed off — the same rule troid applies to
firm rules: reviewed, or not published. Drafts (`"_status": "draft"`) are never published, linked, listed in
hreflang or shown in the language switcher.

## Workflow

1. `python backtest/i18n_export.py` writes one review sheet per language: `review/{lang}.csv` with columns
   `key, english, draft, reviewer_edit, note`. Open it in Google Sheets; the reviewer fills `reviewer_edit`
   where the draft is wrong and leaves it empty where the draft is right.
2. `python backtest/i18n_import.py {lang} returned.csv --by INITIALS --on YYYY-MM-DD` applies the edits, checks
   every string against its English (same figures, placeholders, tags and links; troid lowercase in Latin
   script; no exclamation mark; product names in their fixed form), and writes `{lang}.json` with
   `_reviewed_by`, `_reviewed_on` and `_status: "live"`. A sheet that breaks the contract is refused.
3. The next build (`gen_compare.py`, run by the shadow loop, or `site_build.py`) publishes `/{lang}/`.

## What is never translated

The terms of use, the 17 CFR 4.41 text, each firm's required verbatim sentence, and every rule citation's
source name. On a translated page they appear in English, after a one-line summary in the reader's language
and `legal.governs` ("This translation is provided for convenience. The English version governs.").

## Conventions for strings

- Keys: `{page}.{section}.{name}`; strings a page's script needs: `{page}.js.{name}`; `{page}.meta.title`,
  `{page}.meta.description`. Shared: `product.*` (troid's product names, fixed once per language),
  `common.*`, `legal.*`, `hypo.*`, `prov.*`, `og.*`, `share.line`, `footer.text`.
- A value is the English exactly as the page showed it, inline HTML included. Keep a sentence (usually a whole
  paragraph) in one key, so a translator sees it whole.
- Placeholders: `{name}` for anything computed, filled by `t("key", name=...)` in templates or `F(T.key, {name:
  ...})` in scripts. Never build a sentence by concatenating fragments: word order differs between languages.
- Internal links in values: `href="{L}/compare"`, and `{H}` for the home page, so a translated page links
  inside its language. External links stay as they are.
- Not in `en.json`: firm data (names, labels, rule values, citation strings) from `firms.json`, the 4.41 text,
  required sentences, the terms body.

## Checks

- `python backtest/i18n_equiv.py` — the English pages against git HEAD: pixel-identical at 390 px and 1280 px,
  identical text, identical desk and compare output across a grid of inputs.
- `python backtest/i18n_pseudo.py` — renders every page in a pseudo-locale that marks each keyed string and
  reports visible English that is not keyed.
- `python backtest/i18n.py [lang ...]` — each language file against the contract.
- `verify_claims.py` re-checks every live language: translation may change words, never figures.
