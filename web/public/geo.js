/* Where troid's affiliate links show (geo.json, backtest/geo.py; launch handoff 5.3, the owner's decision, 2026-10-03).
   The page's head hides every [data-geo=<firm>] link and its [data-geo-no=<firm>] message, and gives
   window.TROID_GEO = {hide: {firm: [ISO codes]}, timeout}. This asks /api/where for the visitor's country, then adds a
   rule per firm: its link where the country isn't on that firm's list, its message ("isn't shown in your region")
   where it is. No country, an error or no answer within the timeout: every message, no link (fail closed). The markup
   is never touched, so a column the compare redraws is covered as drawn. Nothing else reads the country: the
   calculator is the same everywhere. A VPN defeats this; it is a good-faith measure (/faq#regions). */
(function () {
  "use strict";
  var G = window.TROID_GEO || {}, hide = G.hide || {}, done = false;
  function apply(cc) {
    if (done) return;
    done = true;
    var css = "";
    Object.keys(hide).forEach(function (k) {
      var show = !!cc && hide[k].indexOf(cc) < 0;
      css += "[data-" + (show ? "geo" : "geo-no") + '="' + k + '"]{display:block!important}';
    });
    var s = document.createElement("style");
    s.id = "geo-rules";
    s.textContent = css;
    document.head.appendChild(s);
    document.documentElement.setAttribute("data-geo-state", cc ? "known" : "closed");
  }
  var t = setTimeout(function () { apply(""); }, G.timeout || 3000);
  try {
    fetch("/api/where", { cache: "no-store", credentials: "omit" }).then(function (r) {
      if (!r.ok) throw new Error("where " + r.status);
      return r.json();
    }).then(function (j) {
      clearTimeout(t);
      apply(j && typeof j.country === "string" && /^[A-Z]{2}$/.test(j.country) ? j.country : "");
    }).catch(function () { clearTimeout(t); apply(""); });
  } catch (e) { clearTimeout(t); apply(""); }
})();
