/* troid's price tape (site_build.ticker; ticker v3 handoff, section B). Two things share one box of one height under
   the header, so the header never changes height and nothing on the page moves:
   - TradingView's Ticker Tape widget, loaded after the page with the page's theme and language. It scrolls on its own.
     Its quotes live in TradingView's frame; troid can't read them and doesn't try. A tapped symbol opens troid's desk
     (largeChartUrl), never TradingView's site.
   - troid's still row: the same symbols without motion. It shows under prefers-reduced-motion, when the visitor presses
     pause (WCAG 2.2.2: the tape moves for more than five seconds, so it can be stopped), and when the widget fails to
     load, fading in where the tape was. Its crypto prices come from /api/ticker, which reads Binance.US server-side:
     the last spot price and the 24-hour change, an arrow and a number in the dim ink, refreshed every 15 s while the row
     shows and the page is visible. A price over 60 s old greys the row and says "delayed"; its age is the CDN's Age
     header plus the gap between the exchange's time and the server's, never the visitor's clock. Gold, oil and the
     stocks are names there, since their quotes are TradingView's.
   On troid's desk a crypto symbol in the still row is a button: it opens a note with "use as entry", which puts the
   price, as the exchange quoted it, in the desk's entry field. A convenience: the stop, the size and the trade stay the
   trader's. */
(function () {
  var s = document.getElementById("tk");
  if (!s) return;
  var box = document.getElementById("tv"), btn = s.querySelector(".tkp"), cfg = JSON.parse(s.getAttribute("data-tv"));
  var SRC = "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js", PLACE = '<div class="tradingview-widget-container__widget"></div>';
  var mq = function (q) { return window.matchMedia ? window.matchMedia(q) : { matches: false }; };
  var lang = (document.documentElement.lang || "en") + "-u-nu-latn", age0 = 0, recv = 0, source = s.getAttribute("data-source");
  var failed = false, wait = null, poll = null;

  function theme() {
    return document.documentElement.getAttribute("data-theme") !== "dark" && mq("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  function fail() {
    if (failed) return;
    failed = true;
    clearTimeout(wait);
    box.innerHTML = PLACE;
    s.classList.add("fail");
    still(true);
  }
  function tape() {                 // TradingView's script reads its settings from its own text and puts its frame in place
    clearTimeout(wait);
    box.innerHTML = PLACE;
    var sc = document.createElement("script");
    sc.src = SRC;
    sc.async = true;
    sc.text = JSON.stringify(Object.assign({}, cfg, { colorTheme: theme() }));
    sc.onerror = fail;
    box.appendChild(sc);
    wait = setTimeout(function () { if (!box.querySelector("iframe")) fail(); }, 10000);
  }
  function still(on) {
    s.classList.toggle("still", on);
    btn.setAttribute("aria-label", btn.getAttribute(on ? "data-play" : "data-pause"));
    clearInterval(poll);
    if (on) { load(); poll = setInterval(function () { if (!document.hidden) load(); }, 15000); }
  }
  btn.addEventListener("click", function () {
    if (failed) return;
    if (s.classList.contains("still")) { tape(); still(false); }
    else { clearTimeout(wait); box.innerHTML = PLACE; still(true); }         // the frame goes, so nothing moves or loads
  });
  var scheme = mq("(prefers-color-scheme: light)");
  if (scheme.addEventListener) scheme.addEventListener("change", function () { if (!failed && !s.classList.contains("still")) tape(); });

  // the still row's crypto prices
  function fmt(v, d) { return new Intl.NumberFormat(lang, { minimumFractionDigits: d, maximumFractionDigits: d }).format(v); }
  function dp(v) { return v >= 1000 ? 0 : v >= 10 ? 2 : 4; }
  function F(t, o) { return t.replace(/\{(\w+)\}/g, function (m, k) { return k in o ? o[k] : m; }); }
  function stale() { if (recv) s.classList.toggle("stale", age0 + (performance.now() - recv) / 1000 > 60); }
  function paint(j) {
    j.items.forEach(function (x) {
      var el = s.querySelector('[data-sym="' + x.sym + '"]');
      if (!el) return;
      var v = +x.last, price = fmt(v, dp(v)), up = x.chg_pct == null || x.chg_pct >= 0;
      var chg = x.chg_pct == null ? "" : (up ? "▲ " : "▼ ") + fmt(Math.abs(x.chg_pct), 2) + "%";
      el.querySelector(".p").textContent = price;
      el.querySelector(".c").textContent = chg;
      el.setAttribute("data-last", x.last);
      el.setAttribute("data-price", price);
      el.setAttribute("aria-label", x.chg_pct == null ? x.sym + " " + price
        : F(s.getAttribute(up ? "data-up" : "data-down"), { sym: x.sym, price: price, chg: fmt(Math.abs(x.chg_pct), 2) }));
    });
  }
  function load() {
    if (!window.fetch) return;
    fetch("/api/ticker").then(function (r) {
      if (!r.ok) throw new Error("ticker " + r.status);
      age0 = +(r.headers.get("age") || 0);
      return r.json();
    }).then(function (j) {
      if (!j || !j.items || !j.items.length) throw new Error("no prices");
      age0 += Math.max(0, ((+j.served || 0) - (+j.as_of || 0)) / 1000);
      recv = performance.now();
      paint(j);
      s.classList.remove("off");
      stale();
    }).catch(function () { s.classList.add("off"); });
  }
  setInterval(stale, 5000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden && s.classList.contains("still")) load(); });

  if (mq("(prefers-reduced-motion: reduce)").matches) still(true);
  else if (document.readyState === "complete") tape();
  else window.addEventListener("load", tape);                 // after the page's own content

  // the desk: a symbol opens the note (web/public/pop.js); this fills it first, in the capture phase
  var note = document.getElementById("tk-use"), entry = document.getElementById("entry");
  if (!note || !entry) return;
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("#tk [data-sym]");
    if (!b || !b.getAttribute("data-last")) return;
    note.querySelector(".tkn").textContent = F(s.getAttribute("data-note"), { sym: b.getAttribute("data-sym"), price: b.getAttribute("data-price"), source: source });
    note.querySelector("button").setAttribute("data-last", b.getAttribute("data-last"));
    note.querySelector("button").setAttribute("data-sym", b.getAttribute("data-sym"));
  }, true);
  note.querySelector("button").addEventListener("click", function () {
    // the desk (desk2.js) also selects the asset and clears a stop the new entry leaves behind; focus stays put (a phone
    // zooms into a focused field), the field lights up instead
    if (window.DESK2) { window.DESK2.use(this.getAttribute("data-last"), this.getAttribute("data-sym")); return; }
    entry.value = this.getAttribute("data-last");
    entry.dispatchEvent(new Event("input"));
    if (window.troidPop) window.troidPop.hide();
    entry.focus();
  });
})();
