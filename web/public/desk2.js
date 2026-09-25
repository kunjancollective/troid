/* troid's next desk: the preview at /desk-preview (partials/_desk2.html; design handoff 2026-09-24, section 4; ticker v2
   handoff, sections E and F; v3, section D). The desk's own script sizes the trade, exactly as on the live desk, and
   hands each result to DESK2.paint; everything here draws that result and never computes a figure of its own beyond
   placing it: positions on the gauge and ladder are the result's numbers to scale, and the explainer's lines are its
   numbers with their formulas. Words come from web/i18n (T2, desk2.js.*; T, the desk's own). Firm data comes from
   firms.json through DESK2DATA (regions.desk2_context): which firms list each asset, as what, on which page, read when,
   and each firm's hold limit with its source.
   - The Asset field changes two lines only: the firm's hold limit and whether it lists the asset. The size is the same.
   - The entry field's chip is the crypto asset's spot price from /api/ticker (Binance.US), asked every 15 s while the
     desk is on screen; a tap puts it in the entry. Gold, oil and stocks: their quotes are TradingView's, in its frame,
     so the field points to the tape instead. A tapped tape symbol (?tvwidgetsymbol=) opens this page with it selected.
   - A new entry from the chip or the tape that leaves the stop on the wrong side, or more than 25% away, clears the
     stop: the desk then says "Set your stop". troid never suggests one.
   - Motion is transform and opacity only, and reduced motion shows the end frame (the CSS). */
(function () {
  var D = window.DESK2DATA, S = window.T2, prices = {}, src = "Binance.US", cleared = false, tapeOnly = null, tapeSel = null, last = null;
  function $e(id) { return document.getElementById(id); }
  var gauge = $e("gauge"), tr = gauge.querySelector(".gtr"), asset = $e("asset");
  function q(s) { return tr.querySelector(s); }
  function link(s) { return '<a href="' + esc(s.url) + '" rel="noopener">' + esc(s.doc) + "</a>"; }
  function vertical() { return window.matchMedia && window.matchMedia("(min-width:1100px)").matches; }

  // labels along one axis: each as near its point as it can be without overlapping the one before, inside the track
  function spread(items, L, gap) {
    items.sort(function (a, b) { return a.c - b.c; });
    var end = -Infinity;
    items.forEach(function (it) { it.p = Math.max(it.c - it.s / 2, end + gap, 0); end = it.p + it.s; });
    var lim = L;
    for (var i = items.length - 1; i >= 0; i--) { items[i].p = Math.max(0, Math.min(items[i].p, lim - items[i].s)); lim = items[i].p - gap; }
  }

  function paintGauge(R) {
    gauge.className = "gauge s" + R.v;
    var line;
    if (R.v === "PENDING") { line = S.g_line_pending; }
    else {
      var V = vertical(), L = V ? tr.clientHeight : tr.clientWidth, fl = [R.dFloor, R.ddFloor].filter(function (x) { return x != null; });
      var drop = R.risk != null ? Math.max(R.risk, R.intended || 0) : 0;
      var lo = Math.min.apply(null, fl.concat([R.eq - drop, R.eq])), hi = Math.max(R.quota, R.eq), pad = (hi - lo) * 0.08 || R.quota * 0.01;
      lo -= pad; hi += pad;
      var at = function (v) { var k = (v - lo) / (hi - lo); return V ? (1 - k) * L : k * L; };
      var mv = function (e, p) { e.style.transform = V ? "translateY(" + p.toFixed(1) + "px)" : "translateX(" + p.toFixed(1) + "px)"; };
      var bindF = R.dB != null && (R.ddB == null || R.dB <= R.ddB) ? "d" : "m";
      [["d", R.dFloor], ["m", R.ddFloor]].forEach(function (x) {
        var e = q('.gfl[data-g="' + x[0] + '"]');
        e.style.opacity = x[1] == null ? 0 : 1; if (x[1] != null) mv(e, at(x[1]));
        e.classList.toggle("bind", x[0] === bindF);
      });
      mv(q(".gq"), at(R.quota)); mv(q(".gdot"), at(R.eq));
      var seg = function (e, amt) {
        var k = Math.max(0, amt) / (hi - lo), y = at(R.eq);
        e.style.transform = V ? "translateY(" + y.toFixed(1) + "px) scaleY(" + k.toFixed(4) + ")" : "translateX(" + (y - L).toFixed(1) + "px) scaleX(" + k.toFixed(4) + ")";
      };
      seg(q(".gseg"), R.risk || 0); seg(q(".gghost"), R.reduced ? R.intended : 0);
      q(".gseg").classList.toggle("over", R.risk != null && R.risk > R.eff);
      var bf = bindF === "d" ? R.dFloor : R.ddFloor, labs = { q: [S.g_quota, R.quota], e: [S.g_equity, R.eq], d: [S.g_daily, R.dFloor], m: [R.ddName, R.ddFloor], r: [S.g_room, R.eff] };
      var sides = V ? [["q", "r"], ["e", "d", "m"]] : [["d", "m"]];
      sides.forEach(function (ks) {
        var items = [];
        ks.forEach(function (k) {
          var e = q('.glab[data-g="' + k + '"]'), x = labs[k];
          if (x[1] == null || (k === "r" && !(R.eff > 0))) { e.style.opacity = 0; return; }
          e.style.opacity = 1;
          e.innerHTML = V ? esc(x[0]) + "<br><b>" + $(x[1]) + "</b>" : esc(x[0]);
          var c = k === "r" ? (at(R.eq) + at(bf)) / 2 : at(x[1]);
          items.push({ e: e, c: c, s: V ? e.offsetHeight : e.offsetWidth });
        });
        spread(items, L, V ? 4 : 8);
        items.forEach(function (it) { mv(it.e, it.p); });
      });
      line = R.v === "BLOCK" ? F(S.g_line_block, { reason: (R.blocks || []).join("; ").replace(/<[^>]+>/g, "") }) :
        F(R.v === "SET" ? S.g_line_set : R.v === "EMPTY" ? S.g_line_empty : S.g_line, { room: $(R.eff), bind: R.bind, risk: R.risk != null ? $(R.risk) : "" });
      var floors = [];
      if (R.dFloor != null) floors.push(S.g_daily + " " + $(R.dFloor));
      if (R.ddFloor != null) floors.push(R.ddName + " " + $(R.ddFloor));
      gauge.setAttribute("aria-label", F(S.g_aria, { eq: $(R.eq), floors: floors.join(", "), line: line }));
    }
    gauge.querySelector(".gline").textContent = line;
    if (R.v === "PENDING") gauge.setAttribute("aria-label", line);
  }

  // the readout's breakers as a ladder, and its risk as a split bar: put into the result the desk just wrote, marked
  // d2x (the preview's own, which test_desk_preview.py sets aside to compare the rest with the live desk's)
  function paintReadout(R) {
    var r = $e("result"), notes = r.querySelector(".notes"), read = r.querySelector(".read");
    if (!notes || !read || !R.ord) return;
    var firmMax = Math.max.apply(null, R.ord.filter(function (o) { return o[2] !== "liq" && isFinite(o[1]); }).map(function (o) { return o[1]; }));
    var max = firmMax * 1.1, lq = R.ord.filter(function (o) { return o[2] === "liq"; })[0];
    if (lq && isFinite(lq[1]) && lq[1] <= max * 1.5) max = Math.max(max, lq[1] * 1.05);
    var rows = R.ord.map(function (o, i) {
      var off = !isFinite(o[1]) || o[1] > max, bad = o[2] !== "stopd" && o[1] < R.sp, v = isFinite(o[1]) ? pc(o[1]) : "—";
      return '<div class="lr' + (i === 0 ? " first" : "") + (bad ? " bad" : "") + (off ? " off" : "") + '"><span class="ln">' + term(o[2], o[0]) +
        (bad ? ' <span class="lx">' + S.l_before + "</span>" : "") + "</span>" + (off ? '<span class="lb"></span><span class="lv">' + F(S.l_off, { pct: v }) + "</span>" :
        '<span class="lb"><i style="transform:scaleX(' + (o[1] / max).toFixed(4) + ')"></i></span><span class="lv">' + v + "</span>") + "</div>";
    });
    var lad = document.createElement("div");
    lad.className = "d2x lad";
    lad.innerHTML = '<div class="lh">' + term("breakers", T.breakers) + " · " + S.l_head + "</div>" + rows.join("");
    notes.parentNode.insertBefore(lad, notes);
    if (!R.feeKnown) return;
    var price = R.risk - R.fees, share = fx(R.fshare, 1) + "%", fb = document.createElement("div");
    fb.className = "d2x feebar";
    fb.innerHTML = '<div class="fbar" role="img" aria-label="' + esc(F(S.f_aria, { risk: $(R.risk), price: $(price), fees: $(R.fees), share: share })) + '"><i style="transform:scaleX(' +
      (R.fshare / 100).toFixed(4) + ')"></i></div><div class="fbl"><span>' + F(S.f_price, { x: $(price) }) + "</span><b>" + F(S.f_fees, { x: $(R.fees), share: share }) + "</b></div>";
    read.parentNode.insertBefore(fb, read.nextSibling);
  }

  // the two lines the Asset field changes: whether the selected firm lists it, and the firm's hold limit for it
  function paintAsset() {
    var a = D.assets[asset.value], fk = $e("firm").value, firm = esc(D.names[fk] || ""), L = a && a.listed[fk], H = D.hold[fk], out = [];
    if (tapeOnly) out.push(esc(F(S.tape_only, { sym: tapeOnly })));
    if (!a) { $e("assetnote").innerHTML = "<p>" + out.join("</p><p>") + "</p>"; return; }
    if (L) out.push(F(S.avail_listed, { firm: firm, asset: esc(a.name), as: esc(L.as), source: link(L), date: L.date }));
    else {
      var u = D.unnamed[fk], others = Object.keys(a.listed).map(function (k) { return esc(D.names[k]); });
      out.push(u ? F(S.avail_unnamed, { firm: firm, source: link(u), date: u.date }) : F(S.avail_not, { asset: esc(a.name), firm: firm }));
      if (others.length) out.push(F(S.avail_others, { firms: andj(others) }));
    }
    if (H && H.days) { if (L && L.tier) out.push(F(S.hold_days, { firm: firm, days: H.days[L.tier], asset: esc(a.name), tier: esc(L.tier_name), source: link(H.src), date: H.src.date })); }
    else if (H && H.src) out.push(F(S.hold_none_src, { firm: firm, source: link(H.src), date: H.src.date }));   // no cap, for any asset
    else if (H) out.push(F(S.hold_none, { firm: firm }));
    $e("assetnote").innerHTML = "<p>" + out.join("</p><p>") + "</p>";
  }

  function paintCards(R) {
    var f = FIRMS[$e("firm").value], p = f.products[$e("profile").value], a = D.assets[asset.value], stop = $e("stop").value.trim();
    $e("ss-account").textContent = F(S.sum_account, { firm: f.name, product: p.label, quota: $(n("quota")), eq: $(n("equity")) });
    var entry = $e("entry").value.trim();
    $e("ss-trade").textContent = F(!entry ? S.sum_trade_empty : stop ? S.sum_trade : S.sum_trade_nostop, { asset: a ? a.name : "", side: n("side") > 0 ? T.long : T.short,
      entry: n4(n("entry")), stop: n4(n("stop")), r: n("targetR") });
    $e("ss-risk").textContent = F(S.sum_risk, { rp: n("riskPct"), cp: n("capPct"), lev: n("lev"), mode: $e("mode").value === "isolated" ? T.isolated : T.cross });
    var stopBad = R.v === "SET" || (R.v === "BLOCK" && (R.blocks || []).some(function (b) { return b === T.b_long || b === T.b_short || b === T.b_zero; }));
    $e("st-trade").classList.toggle("err", stopBad);
    $e("st-account").classList.toggle("err", R.v === "BLOCK" && R.eff <= 0);
  }

  // the explainer: the result's own numbers, step by step, with the formula each came from
  function paintHow(R) {
    var st = [], p = R.p, code = function (s) { return "<code>" + s + "</code>"; };
    if (R.v !== "PENDING") {
      var fl = [];
      if (R.dFloor != null) fl.push(code(T.daily_floor + " = " + R.fd + " = " + $(R.dFloor)));
      if (R.ddFloor != null) fl.push(code(R.ddName + " = " + R.fdd + " = " + $(R.ddFloor)));
      st.push([S.x1_h, S.x1_p, fl.join("")]);
      var bf = R.bind === T.bind_daily ? R.dFloor : R.ddFloor;
      st.push([S.x2_h, S.x2_p, code(S.g_room + " = " + $(R.eq) + " − " + $(bf) + " = " + $(R.eff) + " · " + R.bind)]);
      var x = null, how = "";
      if (p.dd === "static" && p.basis === "initial" && R.dFloor != null) { x = R.quota * (1 - p.m / 100 + p.d / 100); how = $(R.quota) + " × (1 − " + p.m + "% + " + p.d + "%)"; }
      else if (p.dd === "static" && p.basis === "day_start" && R.ddFloor != null) { x = R.ddFloor / (1 - p.d / 100); how = $(R.ddFloor) + " ÷ (1 − " + p.d + "%)"; }
      st.push([S.x3_h, F(x == null ? S.x3_none : S.x3_p, { product: esc(R.f.name + " " + p.label) }), x == null ? "" : code(how + " = " + $(x))]);
    }
    if (R.v === "OK" || R.v === "REDUCE") {
      st.push([S.x4_h, S.x4_p, code(T.risk + " = min(" + $(R.eq) + " × " + R.rp + "%, " + $(R.eff) + " × " + R.cp + "%) = min(" + $(R.intended) + ", " + $(R.cap) + ") = " + $(R.risk))]);
      st.push([S.x5_h, S.x5_p, code(T.size + " = " + $(R.risk) + " ÷ (" + n4(R.dist) + " + " + n4(R.fu) + ") = " + n4(R.qty)) +
        (R.feeKnown ? code(T.fees + " = " + $(R.fees) + " ÷ " + $(R.risk) + " = " + fx(R.fshare, 1) + "%") : "")]);
      st.push([S.x6_h, S.x6_p, code(F(S.x6_code, { notional: $(R.notional), lev: R.levUsed, margin: $(R.margin), risk: $(R.risk) }))]);
    } else st.push(["", R.v === "BLOCK" ? S.x_wait_block : S.x_wait, ""]);
    $e("xs").innerHTML = st.map(function (s) { return "<li>" + (s[0] ? "<h3>" + s[0] + "</h3>" : "") + "<p>" + s[1] + "</p>" + s[2] + "</li>"; }).join("");
  }

  // the entry field's live price: crypto from /api/ticker; gold, oil and stocks: the tape above
  function paintChip() {
    var a = D.assets[asset.value], b = $e("chipb"), m = $e("chipm"), qt = prices[asset.value], sel = a && tapeSel === asset.value;
    b.hidden = !a || a.group !== "crypto" || !qt;
    m.hidden = !a || (a.group === "crypto" && !(sel && !qt));
    m.textContent = !a ? "" : a.group !== "crypto" ? (sel ? F(S.chip_no_fill, { asset: a.name }) : S.chip_manual) : F(S.chip_sel, { asset: a.name });
    if (b.hidden) return;
    var stale = Date.now() - qt.at > 60000, shown = tl(+qt.last, { maximumFractionDigits: 8 });
    b.classList.toggle("stale", stale);
    b.textContent = (sel ? F(S.chip_sel, { asset: a.name }) + " · " : "") + F(stale ? S.chip_delayed : S.chip_live, { price: shown });
    b.setAttribute("aria-label", F(S.chip_aria, { asset: a.name, price: shown, source: src }));
    b.setAttribute("data-last", qt.last);
  }
  function poll() {
    if (document.hidden || !window.fetch) return;
    fetch("/api/ticker").then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (j) {
      src = j.source || src;
      (j.items || []).forEach(function (it) { prices[it.sym] = { last: it.last, at: it.at || j.as_of }; });
      paintChip();
    }).catch(function () {});
  }

  // a new entry from the chip or the tape: a stop now on the wrong side, or more than 25% away, is cleared
  function use(v, sym) {
    if (sym && D.assets[sym] && asset.value !== sym) { asset.value = sym; tapeOnly = null; }
    var e = $e("entry"), s = $e("stop"), E = parseFloat(v), st = parseFloat(s.value);
    e.value = v;
    if (s.value.trim() !== "" && isFinite(st) && isFinite(E) && E > 0) {
      var wrong = n("side") > 0 ? st >= E : st <= E;
      if (wrong || Math.abs(E - st) / E > 0.25) { s.value = ""; cleared = true; }
    }
    tapeSel = null;
    e.dispatchEvent(new Event("input", { bubbles: true }));
    if (window.troidPop) window.troidPop.hide();
    flash(e);
  }
  // a field that changed without the reader typing in it lights up for a moment; focus stays where it was
  function flash(el) {
    var w = el.closest(".fi");
    if (!w) return;
    w.classList.add("on");
    clearTimeout(w._t); w._t = setTimeout(function () { w.classList.remove("on"); }, 1200);
  }
  function emptyReadout() { return '<p class="d2empty">' + S.empty + "</p>"; }

  function setVerdict(f, p, bind, eff) {
    return '<div class="verdict vSET"><span class="vtag">' + S.set_tag + '</span><p class="vsent">' + S.set_sent + (cleared ? " " + S.set_cleared : "") +
      '</p><span class="vtxt">' + F(T.v_txt, { firm: f.name, product: p.label, bind: term("binding", bind), room: term("room", $(eff)) }) + "</span></div>";
  }

  function paint(R) {
    last = R;
    paintGauge(R);
    if (R.v === "OK" || R.v === "REDUCE") paintReadout(R);
    paintAsset(); paintCards(R); paintHow(R); paintChip();
  }

  window.DESK2 = { paint: paint, set: setVerdict, use: use, empty: emptyReadout };

  // a tapped tape symbol: /?tvwidgetsymbol=BINANCEUS:ETHUSDT#desk (or OANDA:XAUUSD, NASDAQ:NVDA). TradingView may open it
  // in a new tab: when the tab that opened it is troid's, that tab takes the address and this one closes, so one tab
  // stays; with no opener (or another site's), this tab carries on
  var tv = (new URLSearchParams(location.search).get("tvwidgetsymbol") || "").toUpperCase();
  if (tv) {
    try {
      var op = window.opener && window.opener.top;
      if (op && op !== window && op.location.origin === location.origin) { op.location.href = location.href; window.close(); }
    } catch (e) { /* another site's window: stay here */ }
  }

  document.addEventListener("DOMContentLoaded", function () {
    $e("stop").addEventListener("input", function () { cleared = false; });
    var bare = tv.split(":").pop(), land = null;
    if (tv) {
      var hit = Object.keys(D.assets).filter(function (k) { var a = D.assets[k]; return k === bare || (a.tv && (a.tv === tv || a.tv.split(":").pop() === bare)); })[0];
      if (hit) { asset.value = hit; tapeSel = hit; land = asset; }
      else {
        tapeOnly = Object.keys(D.tape_only).filter(function (k) { return k === bare || D.tape_only[k] === tv || D.tape_only[k].split(":").pop() === bare; })[0] || null;
        if (tapeOnly) land = $e("assetnote");
      }
      // the tape's own parameters (and any TradingView adds after #desk) leave the address: a reload or a copied link
      // starts clean
      if (history.replaceState) history.replaceState(null, "", location.pathname + "#desk");
    }
    asset.addEventListener("change", function () { tapeOnly = null; tapeSel = null; render(); });
    $e("chipb").addEventListener("click", function () { use(this.getAttribute("data-last")); });
    // a phone opens on the trade: the account and the risk cards start folded, their summaries showing
    if (window.matchMedia && window.matchMedia("(max-width:640px)").matches) ["st-account", "st-risk"].forEach(function (id) { $e(id).open = false; });
    // the gauge follows the layout: its positions are px along the track, so a new width redraws it
    if (window.ResizeObserver) new ResizeObserver(function () { if (last) paintGauge(last); }).observe(tr);
    var on = true;
    if (window.IntersectionObserver) new IntersectionObserver(function (es) { on = es[0].isIntersecting; if (on) poll(); }).observe($e("desk"));
    setInterval(function () { if (on) poll(); else paintChip(); }, 15000);
    document.addEventListener("visibilitychange", function () { if (!document.hidden && on) poll(); });
    poll();
    render();
    if (land) {                                      // a tape tap: the asset in view, lit for a moment, the price by Entry
      var go = function () { land.scrollIntoView({ block: "center" }); if (land === asset) flash(asset); };
      if (document.readyState === "complete") setTimeout(go, 50); else window.addEventListener("load", function () { setTimeout(go, 50); });
    }
  });
})();
