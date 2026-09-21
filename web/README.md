# troid.ai — static site

Three pages, no build step, no framework, no dependencies.

| file | route | what |
|---|---|---|
| `public/index.html` | `/` | Landing + working risk calculator |
| `public/faq.html` | `/faq` | The honest FAQ (base rates, our conflict, disclaimer) |
| `public/dashboard.html` | `/dashboard` | Strategy review and audit findings |

`cleanUrls` in `vercel.json` serves `/faq` from `faq.html`.

## Deploy

```bash
cd web && vercel --prod
```
Then connect `troid.ai` to the project in the Vercel dashboard. Nameservers must finish
propagating first — the domain page shows "Pending" until they do.

## Accuracy

`public/index.html` carries a JavaScript port of `scripts/risk.py`. It is verified against
that script's reference cases and reproduces them to 4 decimal places, including the case
where equity sits below the crossover and the max-drawdown ceiling binds instead of the
daily. **If you change the arithmetic in one, change it in the other and re-check.**

Reference case 2 — quota 100000, equity 96000, day-start 96000, short, entry 77872,
0.3% stop:

```
binding      max drawdown        (not the daily, despite the daily budget being larger)
daily budget 3,840   dd budget   2,000
risk         480     qty         1.6221      notional  126,315.79
margin       25,263.16           fees        101.05  (21.05% of risk)
consumes     24%     losses left 4
```
