/* troid's price strip (site_build.ticker; design handoff 2026-09-24, section 3): BTC, ETH, SOL, XRP and BNB, the last
   spot price and the 24-hour change, from /api/ticker, which reads the exchange server-side, so the browser talks only
   to troid.ai. For reference, never a signal: the change is an arrow and a number in the page's dim ink, no green or
   red. Refreshed every 15 s while the page is visible. A price over 60 s old greys the strip and says "delayed"; its
   age is the CDN's Age header plus the gap between the exchange's time and the server's, never the visitor's clock. A
   failed fetch hides the strip, keeping its space, so nothing on the page moves; it is not an error.
   On troid's desk a symbol is a button: it opens a note with "use as entry", which puts the price, as the exchange
   quoted it, in the desk's entry field. That is a convenience; the stop, the size and the trade stay the trader's. */
(function () {
  var s = document.getElementById("tk");
  if (!s || !window.fetch) return;
  var lang = (document.documentElement.lang || "en") + "-u-nu-latn", age0 = 0, recv = 0, source = s.getAttribute("data-source");
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
  load();
  setInterval(function () { if (!document.hidden) load(); }, 15000);
  setInterval(stale, 5000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) load(); });

  // the desk: a symbol opens the note (web/public/pop.js); this fills it first, in the capture phase
  var note = document.getElementById("tk-use"), entry = document.getElementById("entry");
  if (!note || !entry) return;
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("#tk [data-sym]");
    if (!b || !b.getAttribute("data-last")) return;
    note.querySelector(".tkn").textContent = F(s.getAttribute("data-note"), { sym: b.getAttribute("data-sym"), price: b.getAttribute("data-price"), source: source });
    note.querySelector("button").setAttribute("data-last", b.getAttribute("data-last"));
  }, true);
  note.querySelector("button").addEventListener("click", function () {
    entry.value = this.getAttribute("data-last");
    entry.dispatchEvent(new Event("input"));
    if (window.troidPop) window.troidPop.hide();
    entry.focus();
  });
})();
