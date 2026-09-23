/* troid's reading aids for a page in another language (web/i18n, backtest/site_build.py). Loaded only where
   site_build turns them on: every translated page, and English once web/i18n/site.json says so.
   The page defines window.TROID = {code, loc, t, avail} before this file loads:
     loc    the language's Intl locale, always with Latin digits (languages.json "intl")
     t      the strings this file shows (common.country.*, common.avail.*, common.share*, common.time.*, share.line)
     avail  each firm's recorded country exclusions, from firms.json (never a statement that a firm is available)
   What it does:
     numbers   TROID.num / TROID.usd format with Intl in the page's locale; currency stays USD, never converted
     times     [data-utc] (an ISO instant) and [data-utc-hm] (a daily HH:MM or HH:MM–HH:MM in UTC) get the reader's local time
               before them, the UTC text staying beside it
     country   [data-country] becomes a country selector, preselected from the browser's language, never from
               location; [data-avail=<firm>] shows "not available in <country> per the firm's terms" in place of
               the firm's link ([data-avail-link]) when the firm's recorded terms exclude that country
     share     [data-share] shares the page with its share line (Web Share, else copies the link) */
(function () {
  "use strict";
  var C = window.TROID || {}, t = C.t || {}, loc = C.loc || undefined;
  function F(s, o) { return String(s || "").replace(/\{(\w+)\}/g, function (m, k) { return k in o ? o[k] : m; }); }
  function esc(x) { return String(x).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { return null; } }

  // ------------------------------------------------------------ numbers
  var NF = {}, RTL = document.documentElement.dir === "rtl";
  function nf(o) { var k = JSON.stringify(o || {}); return NF[k] || (NF[k] = new Intl.NumberFormat(loc, o)); }
  // On a right-to-left page an amount is isolated left to right (LRI … PDI), without the direction marks Intl adds,
  // so "100,000.00 US$" keeps its order inside Arabic text. Plain figures need nothing: 3.93% stays whole.
  function ltr(s) { return RTL ? "\u2066" + s.replace(/[\u200e\u200f\u061c]/g, "") + "\u2069" : s; }
  C.num = function (x, o) { return nf(o).format(x); };
  C.fixed = function (x, d) { return nf({ minimumFractionDigits: d, maximumFractionDigits: d, useGrouping: false }).format(x); };
  C.usd = function (x, d) {
    d = d == null ? 2 : d;
    return ltr(nf({ style: "currency", currency: "USD", minimumFractionDigits: d, maximumFractionDigits: d }).format(x));
  };

  // ------------------------------------------------------------ times
  var tz = "UTC";
  try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch (e) { /* keep UTC */ }
  function offsetMin(d) { return -d.getTimezoneOffset(); }
  function local(d, withDate) {
    var o = { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZoneName: "short" };
    if (withDate) { o.day = "numeric"; o.month = "short"; }
    return new Intl.DateTimeFormat(loc, o).format(d);
  }
  C.times = function (root) {
    (root || document).querySelectorAll("[data-utc],[data-utc-hm]").forEach(function (e) {
      if (e.getAttribute("data-tl")) return;
      var d, withDate = e.hasAttribute("data-utc");
      if (withDate) {
        var iso = e.getAttribute("data-utc").replace(" ", "T");
        d = new Date(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
      } else {                                               // a daily time, or a window: 16:00 or 16:00–16:10
        var m = /^(\d{1,2}):(\d{2})(?:[–-](\d{1,2}):(\d{2}))?$/.exec(e.getAttribute("data-utc-hm") || "");
        if (!m) return;
        d = new Date(); d.setUTCHours(+m[1], +m[2], 0, 0);
        if (m[3]) { var d2 = new Date(); d2.setUTCHours(+m[3], +m[4], 0, 0); }
      }
      if (isNaN(d) || offsetMin(d) === 0) return;          // the reader is on UTC: nothing to add
      e.setAttribute("data-tl", "1");
      var s = document.createElement("span"), cell = e.closest("td, .v");
      s.className = "tlocal" + (cell ? " tl-block" : ""); s.title = (t.time_local || "") + " (" + tz + ")";
      s.textContent = d2 ? new Intl.DateTimeFormat(loc, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(d)
                           + "–" + local(d2, false) : local(d, withDate);
      e.parentNode.insertBefore(s, e);                     // in a table cell or a big value: its own line above
      if (!cell) e.parentNode.insertBefore(document.createTextNode(" · "), e);
    });
  };

  // ------------------------------------------------------------ country
  var CODES = ("AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW " +
    "BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO " +
    "FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO " +
    "JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS " +
    "MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU " +
    "RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA " +
    "UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW").split(" ");
  var DN = null;
  try { DN = new Intl.DisplayNames([loc || "en"], { type: "region" }); } catch (e) { DN = null; }
  function cname(cc) { try { return (DN && DN.of(cc)) || cc; } catch (e) { return cc; } }
  function fromBrowser() {                                 // the browser's language, never the reader's location
    var tags = (navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ""]);
    for (var i = 0; i < tags.length; i++) {
      try { var r = new Intl.Locale(tags[i]).region; if (r && CODES.indexOf(r) >= 0) return r; } catch (e) { /* next */ }
    }
    try { var m = new Intl.Locale(tags[0]).maximize().region; if (m && CODES.indexOf(m) >= 0) return m; } catch (e) { /* none */ }
    return "";
  }
  var country = store("troid.country");
  if (country === null || (country && CODES.indexOf(country) < 0)) country = fromBrowser();

  function avail(root) {
    (root || document).querySelectorAll("[data-avail]").forEach(function (e) {
      var a = (C.avail || {})[e.getAttribute("data-avail")];
      e.querySelectorAll(".avail").forEach(function (x) { x.remove(); });
      e.querySelectorAll("[data-avail-link]").forEach(function (x) { x.hidden = false; });
      if (!a || !country) return;
      var name = esc(cname(country)), msg = "", no = false;
      if (!a.recorded) msg = t.avail_not_recorded;
      else if ((a.excluded || []).indexOf(country) >= 0) { msg = F(t.avail_excluded, { country: name }); no = true; }
      else {
        var p = Object.keys(a.platform || {}).filter(function (k) { return a.platform[k].indexOf(country) >= 0; });
        msg = p.length ? F(t.avail_platform, { platform: esc(p.join(", ")), country: name })
                       : (a.note ? esc(a.note) : F(t.avail_not_excluded, { country: name }));   // the firm's own note, if troid recorded one
      }
      if (no) e.querySelectorAll("[data-avail-link]").forEach(function (x) { x.hidden = true; });
      var s = document.createElement("div");
      s.className = "avail" + (no ? " no" : ""); s.innerHTML = msg;
      e.appendChild(s);
    });
  }
  C.avail_apply = avail;

  function selector(box) {
    var sel = document.createElement("select"), id = "country-" + Math.random().toString(36).slice(2, 8);
    sel.id = id;
    var opts = CODES.map(function (cc) { return [cc, cname(cc)]; });
    try { opts.sort(function (a, b) { return a[1].localeCompare(b[1], loc); }); } catch (e) { /* keep code order */ }
    var h = '<option value="">' + esc(t.country_unset || "—") + "</option>";
    opts.forEach(function (o) { h += '<option value="' + o[0] + '"' + (o[0] === country ? " selected" : "") + ">" + esc(o[1]) + "</option>"; });
    sel.innerHTML = h;
    sel.addEventListener("change", function () {
      country = sel.value; store("troid.country", country || "");
      document.querySelectorAll("[data-country] select").forEach(function (o) { if (o !== sel) o.value = country; });
      avail(document);
    });
    box.innerHTML = '<label for="' + id + '">' + esc(t.country_label || "") + "</label>";
    box.appendChild(sel);
    var n = document.createElement("span"); n.className = "cnote"; n.textContent = t.country_note || "";
    box.appendChild(n);
  }

  // ------------------------------------------------------------ share
  function share(b) {
    b.addEventListener("click", function () {
      var url = location.href.split("#")[0], text = t.share_line || "";
      if (navigator.share) { navigator.share({ title: document.title, text: text, url: url }).catch(function () {}); return; }
      if (navigator.clipboard) navigator.clipboard.writeText(text + " " + url).then(function () {
        var was = b.textContent; b.textContent = t.share_copied || was; setTimeout(function () { b.textContent = was; }, 1800);
      }).catch(function () {});
    });
  }

  function init() {
    document.querySelectorAll("[data-country]").forEach(selector);
    document.querySelectorAll("[data-share]").forEach(share);
    avail(document);
    C.times(document);
  }
  window.TROID = C;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
})();
