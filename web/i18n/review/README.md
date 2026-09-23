# For troid's reviewers

Thank you for reviewing troid in your language. troid publishes a language only after its reviewer
signs off, so your sheet decides what readers see.

## Your sheet

- `{lang}.csv` — every string on the site. Columns: `key` (leave it), `english`, `draft` (a machine
  draft), `reviewer_edit` (your version, only where the draft is wrong), `note`.
- `{lang}-update.csv` — only the strings that are new or whose English changed after your sheet went
  out. If you already have `{lang}.csv`, fill this one in too and send both back.
- Rows whose note starts `CHECK FIRST:` are the questions the draft left open. `NEW` or
  `ENGLISH CHANGED` rows have no draft: write the translation in `reviewer_edit`.
- `web/i18n/STYLE.md` has the voice, the names that stay as they are (troid, firm names, tickers,
  UTC, TROID.md) and the form of address for your language.

The import refuses a sheet in which a figure, a link, a `{placeholder}` or an HTML tag differs from the
English, or which uses non-Latin digits or an exclamation mark. Those rules keep every number on every
page the same in every language.

## Sharing troid

The firms troid links to are paid affiliates, and their affiliate contracts set rules that the
Company must keep. When you share troid in your language:

- **Organic only.** Share it where you would share anything you use: your own posts, communities,
  messages.
- **No boosted or paid posts** and no ads of any kind that mention troid or its links.
- **No coupon or deal sites**, and no posting troid's affiliate links or codes on them.

If someone asks you whether they should buy a challenge, the answer is troid's: troid doesn't
recommend; it prices what you bring.
