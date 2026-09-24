# History rewrite, 24 September 2026

BrightFunded's signed affiliate agreement is confidential under its clause 6. Its terms were committed to this public
repository between 21 and 24 September 2026, and were moved out of the public files on 24 September (they now live
only with troid's operator, outside the repository). On 24 September the repository's history was rewritten so that
no commit carries them.

**What was removed, and only that.** Every file stays; only these strings and blocks were edited, in every commit
that held them:

- `firms.json` and `web/context/firms.json`, BrightFunded's entry only: the agreement's terms (the rate tiers and
  the rest of `affiliate_agreement`, except the signing date and the public referral code), `affiliate_payout` (the
  agreement's Schedule 2), `comparison_approval` (the support-chat record), the Oneflow number and the agreement's
  scope in `verified_from`, the arbitration clause in `governing_law`, and the clause references in
  `promotion_policy`, `_link_live_note` and the provenance source name, each replaced by the wording the file has
  today.
- `firms_evidence.json`: one quotation of the agreement's scope.
- `web/affiliate.json`: BrightFunded's rate tiers (the file itself is deleted in the commit that publishes this map).
- `web/test_assistant.js`: the support agent's name, in a list of strings the assistant's prompt must not contain.
- Two commit messages: a clause number each.

**What did not change.** No ledger, journal, result or rule data: `backtest/journal.csv`, `runs.csv`, `state.json`,
the results, every rule value in `firms.json` and every other firm's entry are byte-identical in every commit, and
no other file changed in any commit. Every commit keeps its author, committer, dates and parents, merges included.
Six commit messages quote other commits by ID; those IDs were updated to the new ones so the references still work.
The first 11 commits contain none of the removed text and keep their original IDs and signatures; the other
65 have new IDs and carry no signature (the originals were signed; a rewritten commit can't keep a
signature made over different content).

**How.** `git filter-repo` (a40bce548d2c) with a blob callback that edits the strings above and nothing else, limited
to the commits from the first that held them onward; earlier commits were left as they were. Before the push, a scan of all 861 blobs on both
branches found none of the removed strings, and a commit-by-commit comparison of the old and new trees found
differences only in the five files above.

GitHub can still serve cached views of the old commits by their old IDs until GitHub Support purges them. troid's
operator is asking for that through GitHub's "removing sensitive data" process.

## Every commit, old ID to new ID

In topological order, oldest first. Dates are the original commit dates.

| old | new | | date | subject |
|---|---|---|---|---|
| `2384dc856286b773fdcdf6083af9a7332d2483dc` | `2384dc856286b773fdcdf6083af9a7332d2483dc` | same | 2026-09-21 16:51 UTC | troid: desk, MCP, engines, ledger, accuracy ledger — basis corrected |
| `9b979f28ce2e94997074fefd5f7038601961d146` | `9b979f28ce2e94997074fefd5f7038601961d146` | same | 2026-09-21 17:04 UTC | shadow: daily forward test as a GitHub Actions cron |
| `429017555898daed08c0048578a14b3f2741519d` | `429017555898daed08c0048578a14b3f2741519d` | same | 2026-09-21 17:05 UTC | shadow: 2026-09-21 — 18 new, balance 101,299, running |
| `7d772b15d3f748c86c46df1c2585073f8d08b976` | `7d772b15d3f748c86c46df1c2585073f8d08b976` | same | 2026-09-21 17:10 UTC | shadow: freeze the history, extend it with live bars only |
| `b635e56cfbb64e478246c9a570b5d5ba3a080df2` | `b635e56cfbb64e478246c9a570b5d5ba3a080df2` | same | 2026-09-21 17:10 UTC | shadow: 2026-09-21 — 2 new, balance 101,753, running |
| `ce2cb462e58a89e24bb63fd55f0b85174674b972` | `ce2cb462e58a89e24bb63fd55f0b85174674b972` | same | 2026-09-21 17:29 UTC | data: one-shot workflow to fetch the multi-year history on a runner |
| `ca2da5f2a812d358d478186f7668ae10e2db53e1` | `ca2da5f2a812d358d478186f7668ae10e2db53e1` | same | 2026-09-21 17:31 UTC | data: BTCUSDT and ETHUSDT 4h from 2021-01-01 (binance.us) |
| `719e1abafced84ce5b3582e0dc396438feb8f84f` | `719e1abafced84ce5b3582e0dc396438feb8f84f` | same | 2026-09-21 17:40 UTC | shadow: re-backfill on binance.us, flag forward-filled bars, run the baseline walk-forward |
| `6d3efde5f0d8eae4ba4e7906e5b87a1f6dfb4f78` | `6d3efde5f0d8eae4ba4e7906e5b87a1f6dfb4f78` | same | 2026-09-21 17:47 UTC | strategy: name the in-sample-to-holdout shrinkage, 75% |
| `86fc78ed7948db62097508f7fde69b30d3dc2758` | `86fc78ed7948db62097508f7fde69b30d3dc2758` | same | 2026-09-21 17:48 UTC | journal: R to four decimals, so the public source agrees with the engine |
| `34e1fac1cebc77e46c2574046824f0c91a119c56` | `34e1fac1cebc77e46c2574046824f0c91a119c56` | same | 2026-09-21 19:14 UTC | faq: fixed daily limit, daily ledger, out-of-sample result |
| `187dc350797e0ca22acf937e477a723c78718553` | `a834deac247e9f55903c7f5a8c50e525aac3173f` | rewritten | 2026-09-21 22:28 UTC | snapshot from the other sandbox (2026-09-21 22:15 UTC) |
| `c563c810b5f671f326a838b113e1a3d3e988ee95` | `af2d8bb9885233ae45f56b01a48f9034038e0ab1` | rewritten | 2026-09-21 22:30 UTC | Merge the other sandbox's snapshot: compare page, firms.json, METHODOLOGY.md |
| `b5ebaed752e42decca6093969df35ec2c34becdd` | `940a656f5d6b3bdf85c948bfc6108ad06f49a3c5` | rewritten | 2026-09-22 01:32 UTC | brand: logo kit, favicon, OG image, header wordmark |
| `1c8b5687a2fc04111db6bfb183aed243de8717b5` | `0869922713eba4cdd2594d14faa2e8d6cf63d639` | rewritten | 2026-09-22 01:41 UTC | brand: blue palette, page gradient, OFL. |
| `41fe76bb069f3d0d846dae01eccca375547af504` | `08f7a576141714d711456575847abe9c9b938b91` | rewritten | 2026-09-22 02:05 UTC | site: social links. |
| `c3457b698e4b423596fb3847c1069ad0f2260518` | `c233def9b15cea7e35195805b9e0f3e106d2eacf` | rewritten | 2026-09-22 02:20 UTC | disclosure: generic text, firm-specific sentences generated from firms.json. |
| `68a75db2496f894e98b45ad0ad05ab9c27d34f1a` | `c9aed133dcab1f59bb8fc119e67bc83882a13dd7` | rewritten | 2026-09-22 02:22 UTC | compare: withhold gated codes from the page source; pending message states the rule |
| `7416ca4cb6956865fd915d1b81aa9b21807eb6ea` | `269c72100f8abaf45c0f70bdbfa4b492adece05e` | rewritten | 2026-09-22 02:25 UTC | firms: BrightFunded and CFT links live, CFT clause-10 sentence, agreements on record |
| `df7396d7d7e951386b4a09cb230b8a604abaa4ce` | `1c73e796c38570dbdba521160ad91b038ea9e698` | rewritten | 2026-09-22 03:55 UTC | firms: BrightFunded to 15 of 18; panel shows the verified count on linked firms |
| `f3579a6d1c89492ff292f84719390d1c173c68d0` | `ebd13dd8db553134fec7ac09e29026d3cd0463d5` | rewritten | 2026-09-22 03:57 UTC | ledger: six runs a day, heartbeat block, runs table |
| `6de485cd0c381ab20e6a96cae97b725e8b9c481a` | `8c2e05491705f695a2a78203a7091d59760e0461` | rewritten | 2026-09-22 03:58 UTC | shadow: 2026-09-22 — 0 new, balance 101,299, running |
| `843db2f6566c3af4086f0188b4976d479dccf270` | `e4fd09fafcdc4f4fd25c737ffed3650a67d267b3` | rewritten | 2026-09-22 04:06 UTC | calculator: firm selector, products from firms.json, three bases |
| `3d37d34e7d0b1d33056bc68876414665b4da8373` | `da083d0df0e0000f091b76fca269415f1d0e798f` | rewritten | 2026-09-22 04:13 UTC | ledger: one chart per closed trade; journal schema widened |
| `fbcbfbc4150e0a187c7a95acbff6a5158f225dad` | `4677f1e2bafb0d3c51d321c66f7b63774574abd9` | rewritten | 2026-09-22 04:17 UTC | tearsheet: quantstats over the journal, in the daily loop |
| `3c707fa8d27eca1f2972037ff47ce5bf5c0cec9d` | `7f26390f9de33b5b3ee2646b2a9a6f252d723320` | rewritten | 2026-09-22 04:17 UTC | handoff: engine gaps from the three-basis calculator port |
| `9d4e9ca22161bd36570574c487144f12ceff0558` | `81552e04bee8e48b28e863d21b73e858564cb7fd` | rewritten | 2026-09-22 04:22 UTC | shadow: 2026-09-22 — 0 new, balance 101,299, running |
| `c6359e053b59f993b573ee20ac4b821a9d554778` | `27683019916a8e043482972fbbdc77dccc767259` | rewritten | 2026-09-22 04:24 UTC | assistant: chat over the verified rules, behind a feature flag |
| `9321148243c7634f259bf1aec157e8355d8038bd` | `a0ea69d9c0a67ee8c795a1d4234a5abd41734b73` | rewritten | 2026-09-22 09:21 UTC | shadow: 2026-09-22 — 0 new, balance 101,299, running |
| `ccf6df599d0df45fc166f592a5f10c8f9cab87cf` | `bfbb3451685df90867964e0b06d5317717850207` | rewritten | 2026-09-22 17:02 UTC | shadow: 2026-09-22 — 0 new, balance 101,299, running |
| `37bcdab95dfbb3b82bd60167e2acbd2409ba1969` | `f9a75a482e56e91d3c6465e42253a007d8c76488` | rewritten | 2026-09-22 23:00 UTC | shadow: 2026-09-22 — 0 new, balance 101,299, running |
| `dca4d25e432111b73094047da04c77047a78d4a1` | `9ffc19c633dde45b7c293e5ff664490386a4c9d1` | rewritten | 2026-09-23 00:40 UTC | shadow: 2026-09-23 — 0 new, balance 101,299, running |
| `c7d96f2a83dfedb57abc4456ed32d927a7332b68` | `0c8fe89dd6d8d3615a85dece5df4a537fe294710` | rewritten | 2026-09-23 00:41 UTC | methodology: shadow deploys blocked on 22 Sep, fixed by the repo going public |
| `70333cce39aff5cc4e5a67affeb4756799d6b7a7` | `fdc64c657b6fec61fe0dff10d6f269b996e2987b` | rewritten | 2026-09-23 01:08 UTC | voice: troid in the third person; product names in the nav and on the pages |
| `2bb868858f280e66ce4f1373ec25fd91dae3c6f4` | `f5789714b335237bb2d4d4ca785a8bebf360835a` | rewritten | 2026-09-23 01:33 UTC | provenance: every computed number cites its rule, section and read date |
| `8c10c09df2e82948d0fd31b8af9b8e301d4b94c1` | `1e17d8aacff75ad3649db246f34636cc1cebdfe4` | rewritten | 2026-09-23 01:44 UTC | provenance: confirmation fixes — leverage cites by account class, immediate liquidation |
| `f82367e80d1200c5d18ec0ccc32c93213299f745` | `77f209494d0f4a241b450fba8204aa861abe6a39` | rewritten | 2026-09-23 01:48 UTC | disclosure: footer line on every page, 4.41 text beside the results, terms, README |
| `f7fce29b507d68ae22d4b662bdcfa91732a84d77` | `4b68ca5972ed3c8855f65226d061f17682fc4616` | rewritten | 2026-09-23 01:53 UTC | ask troid: customer service — support script, AI disclosure, abuse, refusals, sources |
| `0e4094ad44a393d260f04c3d232b9bdadadd22e5` | `09b958cee6cc499355cc91de8b99957c71ee3b0a` | rewritten | 2026-09-23 01:56 UTC | shadow: commit the pages that now carry generated footers |
| `09c505903a9cab15bb5e4e920a1e4fe7e375dcaf` | `0808587f2d6c547106b81ec857de3fa177221550` | rewritten | 2026-09-23 02:09 UTC | disclosure: verification fixes — honest criteria, corrections backlog, drift checks |
| `5696d182a6988a0137321877b0580374aedd930e` | `a07ce9a8786d8c1b749cb46f9cec1dae1153c8b0` | rewritten | 2026-09-23 02:25 UTC | ask troid / terms: review fixes — enforced warning, signed history, deadline, honest wording |
| `5deb6b3f5b945bc53b608f658cf1bd3af615abe4` | `a45d588125d662ea420699a6aaef749c98ee0da0` | rewritten | 2026-09-23 03:02 UTC | ask troid / terms: second review round — no end without a warning, no lockout, honest periods |
| `843d72a760e63498b516b9843a666e28d15780bc` | `93f099fe81e561b45e2d525877e2caf1a4e98b45` | rewritten | 2026-09-23 03:50 UTC | owner decisions: new disclosure, scam reply and footer; sources recorded; unsourced link held |
| `abc203b6439787931fbc0f5489a44859c04f3ff8` | `bfedbdb74e7b2f7a9787786d898464955c2b9518` | rewritten | 2026-09-23 04:14 UTC | Bitfunded price recorded, link back; price conflict logged; footer and scam reply final |
| `a724d505d8c064e76779830287cb7ae2c3020b66` | `98c955859cf0c997277bf5235e73160d45939257` | rewritten | 2026-09-23 05:47 UTC | i18n (work in progress, feature branch only): core, chat page, ask troid languages, availability data |
| `a8533d21c4410047ea0ad7a71246321700974697` | `fa9e2c5329ecf9378faa28b69dac99b5557ad05f` | rewritten | 2026-09-23 05:54 UTC | i18n (work in progress, feature branch only): page conversions in progress |
| `636e19d728cc54f873cdbb5984a9c778ddbb48dc` | `cb2837c0c3de041c252e243528044a71baa60b57` | rewritten | 2026-09-23 06:12 UTC | i18n (work in progress, feature branch only): dashboard, terms, ledger and tearsheet conversions |
| `147e555bfc4c69dc1366bc654d185df5c3e70b26` | `b170163c0850b3c6499082066eea08c2a988d01a` | rewritten | 2026-09-23 06:13 UTC | i18n (work in progress, feature branch only): shared fixes, en.json merged |
| `eecf6ab7bbd4c11c7538be2efe44102dc2e96ce8` | `db58417c5b9b993f4b92819a387263610f3b2f9a` | rewritten | 2026-09-23 04:51 UTC | shadow: 2026-09-23 — 0 new, balance 101,299, running |
| `0d78027206da572171aa3c7fc4a3b15b9f8b5410` | `ad9a2afeb27e1824f92e032c31c67fbbb783ebf6` | rewritten | 2026-09-23 06:13 UTC | merge main (shadow run 2026-09-23) |
| `3642d23a2cefb7494f8d8024464caa18842577cf` | `dfba9becc3e6d626d5a6f31736c33de2fac6b333` | rewritten | 2026-09-23 06:14 UTC | i18n (work in progress, feature branch only): English pages rendered from templates, scripts keyed |
| `1446b672c8414f49239cfebbeff583789dea1c25` | `33e4f4ffe142b57d8f8e64666164b380dd5a3707` | rewritten | 2026-09-23 08:01 UTC | i18n: nine language drafts, review sheets, and the reading aids for translated pages |
| `19dc70a5c0b9cf69b4b40920d5f75c921ba926d2` | `ccd66669cd391b9983c67eecf3cfa428cdefdfc9` | rewritten | 2026-09-23 13:15 UTC | Bitfunded sources of 23 Sep, the named LLC (feature branch; drafts follow) |
| `5226b263b79350b14c416ebfec6a7751d079bf58` | `0bb66e438fb7f4cf5c43dc7948d2de2ac88ef5e9` | rewritten | 2026-09-23 13:20 UTC | i18n drafts: the Bitfunded update's strings in nine languages, sheets re-exported |
| `5bf690c15db80e4c60553a7232e9648811d8458e` | `e7d0e5912f3c1486e96568c86f4c532f7b1f1023` | rewritten | 2026-09-23 17:27 UTC | ask troid: 30-day conversation record, session ID, deletion; wording on every surface |
| `4b67d03577e9a77a121ab322cc8747065fd2d003` | `efab8a9a82e5d993ed180ae8561e84f1ba76c1e8` | rewritten | 2026-09-23 13:42 UTC | shadow: 2026-09-23 — 0 new, balance 101,299, running |
| `612aa6b505b123a7646c1f63387355dfba9c8ba7` | `d78c247ed0ca2f0faa798ac6417e73acd5096322` | rewritten | 2026-09-23 17:27 UTC | merge main (shadow run 2026-09-23) |
| `85702e79a1b0ca1edc5b8781c19ddc2d84f460e8` | `35730ea563ebba4b153c170b4f890b82e346a664` | rewritten | 2026-09-23 17:33 UTC | troid.ai: canonical URLs, robots.txt, sitemap.xml; troid-one.vercel.app redirects |
| `4c6f46e76cdadede391489c9f18b6802e5069299` | `db7169d4eb93cd479714d81191c6666fdfecfe48` | rewritten | 2026-09-23 17:35 UTC | ask troid: live smoke test for switch-on (web/smoke_live.js) |
| `36afa1c90fb6811cdd1cbf9a5e7191a2112a218d` | `20a271fbe741e92785e1c48d0cdeebfea99a69c1` | rewritten | 2026-09-23 21:55 UTC | ask troid switched on at troid.ai; launch recorded; smoke test checks signing and deletion via the API |
| `ee1ad170b53fb2b070ccd58fc807603b9b6a50b2` | `808018cf6cf6ad75ed9a7966ecdc0398088f1915` | rewritten | 2026-09-23 19:42 UTC | shadow: 2026-09-23 — 0 new, balance 101,299, running |
| `4159e7261af3928a07ab58cc8e0dd4f5946d4508` | `cc4c3e584d7ef3c56d279554e71bf1e1929d34a8` | rewritten | 2026-09-23 21:55 UTC | merge main (shadow run 2026-09-23) |
| `af7f523fb9554d607ce39e0834a9ccd860190a6d` | `0faed581d23585915deaf6dc6a30ea23928e085a` | rewritten | 2026-09-23 22:16 UTC | ask troid: a session ID alone no longer yields its delete token; rules cited with their own read dates |
| `c41c7b67a162865f498e65580b92fd3104317091` | `d71d5bb4b51b64a5edf566f878a0d058fbf76e51` | rewritten | 2026-09-23 22:23 UTC | ask troid: the service writes each rule's source, the tier and troid's assumptions under a tool answer |
| `f5e4b45b25e9cc54de6317a486a33c64ddefa6a9` | `ef917d324cab885064bc72678658adf884eb674c` | rewritten | 2026-09-23 22:33 UTC | The status light: the wordmark's dot ripples while troid's ledger is live, links to it; two floors under the o |
| `1f67710ef025960f3fbc6226552921d76bed247b` | `788efe5a4516082039c8d5616f9c76339b6f193f` | rewritten | 2026-09-23 23:01 UTC | Status light: fixes from a four-lens review (accessibility, logic, brand, regressions) |
| `d88e2a8187253097c12aac7a48fd7af19b30adca` | `8b80abd9c2e8950467d0a59faf40fdd7812ed423` | rewritten | 2026-09-23 22:59 UTC | shadow: 2026-09-23 — 0 new, balance 101,299, running |
| `a74af006c6dfc8ca6ebec67b22d95e3450f5f5f5` | `538f3f930728adc16b582f275ef68ec61b864d3f` | rewritten | 2026-09-23 23:01 UTC | Merge remote-tracking branch 'origin/main' into claude/troid-repo-init-lnzzbt |
| `323d56f365030116da7a82d20227b5216b289137` | `c3578616676ad7ef59acf20e1e386b35f287f3ab` | rewritten | 2026-09-23 23:01 UTC | status.json: regenerated after merging the 22:59 UTC shadow run (it ran before gen_ledger wrote the file) |
| `d2eb125c1726884a8f5fa1b8094956138a324bc1` | `5ae3264339d7f75c5f2a96be1e00df58c23382f7` | rewritten | 2026-09-23 23:30 UTC | brand/: every asset redrawn with the two floors |
| `fcdc73df07383712980725fd11f3fe4ea608e008` | `129f9028c5ef3d6b7270123deeb3e7d66fcdced9` | rewritten | 2026-09-23 23:50 UTC | The line: "The droid does the prop-firm math. You make the trade." |
| `3e9e52ef0e0d4d4556d84ef43b4297d7bb140972` | `981a1cebd375507cdda88435d05e51f02fdfb26d` | rewritten | 2026-09-24 01:05 UTC | Operator is Kunjan Patel; the fourth purpose and the weekly question digest; BrightFunded's agreement out of public files; tiered hold on the landing page |
| `13c08bc6b749a59fd2c244f14356b04b4b7e1290` | `f71fb8f23343301611d9fe1791e6ffe982c86107` | rewritten | 2026-09-24 02:06 UTC | Live-site fixes (handoff 24 Sep §1): every figure tiered, 1-Step cites corrected, compare's claims generated |
| `8049a2087bf8bbdcf2ee9a2a836b1b3cf209e45a` | `df2c0febd1f53f1f3bb12d11922dda9e21231be4` | rewritten | 2026-09-24 02:07 UTC | brand/social: the owner's X and Reddit set; the banners replaced (handoff 24 Sep §4) |
| `1d4d3d81f1493f78e3d796be094c59c91bb99de5` | `71576ee92e71ef13a0bcf123b63c557ab1b4a039` | rewritten | 2026-09-24 02:15 UTC | Shareable desk links (handoff 24 Sep §3): every input in the fragment, restored with today's rules |
| `4f04c59b09b3a80695a3217e24da05b25425d3e4` | `b410c0c0e1aaaa49546436be4ad313532ce2d6a0` | rewritten | 2026-09-24 02:18 UTC | shadow: schedule paused for the history rewrite (handoff 24 Sep §2) |
