/* The two lines under troid's desk (calculator audit, 2026-09-29). The first says when an independent model last
   re-derived the desk's arithmetic and what it found: /audit.json, written by the weekly audit (audit/run.py), with a
   link to that week's report. It stays hidden when the file can't be read or doesn't hold together (checks = passed +
   failed, the report named for its week); an old audit shows its date as it is. The second says when troid read the
   rules the desk sizes with: the build writes it from firms.json with ISO dates, and this only puts them in the page's
   language. Dates are Intl's, in the page's locale (en-GB for English: "4 Oct 2026"). Kept out of desk2.js, whose
   size is budgeted. */
(function () {
  var a = document.getElementById("audit"), r = document.getElementById("rulesread");
  if (!a && !r) return;
  function day(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || "");
    if (!m) return null;
    var d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    return d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3] ? d : null;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; });
  }
  function fmt(el) {
    try {
      return new Intl.DateTimeFormat(el.getAttribute("data-intl") || "en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
    } catch (e) { return null; }
  }
  if (r) {
    var f = fmt(r), d0 = day(r.getAttribute("data-from")), d1 = day(r.getAttribute("data-to")), t = r.getAttribute("data-t");
    if (f && d0 && d1 && d0 <= d1 && t) {
      try { r.textContent = t.replace("{range}", f.formatRange ? f.formatRange(d0, d1) : f.format(d0) + " – " + f.format(d1)); } catch (e) {}
    }
  }
  if (!a || !window.fetch) return;
  fetch("/audit.json", { cache: "no-store" }).then(function (x) {
    if (!x.ok) throw new Error("audit " + x.status);
    return x.json();
  }).then(function (j) {
    var n = function (v) { return typeof v === "number" && v >= 0 && Math.floor(v) === v; };
    var f = fmt(a), when = j && day(j.date);
    if (!f || !when || !/^\d{4}-W\d{2}$/.test(j.week) || !/^[0-9a-f]{40}$/.test(j.commit) || !n(j.checks) || !n(j.passed)
        || !n(j.failed) || j.checks < 1 || j.checks !== j.passed + j.failed || j.report !== "audit/reports/" + j.week + ".md") return;
    var tpl = a.getAttribute(j.failed ? "data-fail" : "data-pass"), repo = a.getAttribute("data-repo");
    if (!tpl || !repo) return;
    var num = new Intl.NumberFormat(a.getAttribute("data-intl") || "en-GB");
    a.innerHTML = tpl.replace("{date}", esc(f.format(when))).replace("{n}", esc(num.format(j.failed || j.passed)))
      .replace("{href}", esc(repo + j.report));
    a.hidden = false;
  }).catch(function () { a.hidden = true; });
})();
