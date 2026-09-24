/* troid's desk: a result as a link. Every desk input rides in the URL fragment (/#f=bitfunded&p=1step&q=100000…).
   Browsers never send the part after # to a server, so a shared result reaches no server and no log; troid sets no
   cookies and runs no analytics. Opening a link restores the inputs and the desk recomputes with the rules troid has
   today, and says so. A value the desk can't read (an unknown firm or challenge, a malformed number, a fragment
   longer than MAX) is ignored and that input keeps its default; nothing fails. A link carries l=<language> only from
   a page in a language that is live.

   encode() and decode() are pure (tested in web/test_desk_links.py); init() wires them to the desk in index.html. */
(function (root) {
  "use strict";
  var MAX = 400;                                   // the longest fragment read; a full desk link is about 150 characters
  var NUM = /^-?\d{1,12}(\.\d{1,10})?$/;
  var NAME = /^[A-Za-z0-9_-]{1,40}$/;              // how an unknown firm or challenge key is echoed back, if at all
  // fragment key, the desk input's id, the kind of value
  var FIELDS = [["q", "quota", "num"], ["e", "equity", "num"], ["ds", "daystart", "num"], ["hi", "hirollover", "num"],
                ["hwm", "hwm", "num"], ["sd", "side", "side"], ["en", "entry", "num"], ["st", "stop", "num"],
                ["r", "targetR", "num"], ["rp", "riskPct", "num"], ["cp", "capPct", "num"], ["lv", "lev", "num"],
                ["m", "mode", "mode"]];
  var SIDE = { "long": "1", "short": "-1" }, SIDE_KEY = { "1": "long", "-1": "short" };
  var MODE = { "cross": 1, "isolated": 1 };
  var enc = encodeURIComponent;

  // s: {f, p, l, and each input id: its value as a string}. Empty inputs are left out.
  function encode(s) {
    var out = ["f=" + enc(s.f), "p=" + enc(s.p)];
    FIELDS.forEach(function (x) {
      var v = s[x[1]];
      if (v === undefined || v === null || v === "") return;
      out.push(x[0] + "=" + enc(x[2] === "side" ? SIDE_KEY[v] : v));
    });
    if (s.l) out.push("l=" + enc(s.l));
    return out.join("&");
  }

  // hash: location.hash. firms: the desk's FIRMS. live: the published language codes.
  // Returns null when the fragment is not a desk link (empty, or a plain anchor such as #firms), otherwise
  // {firm, product, lang, values: {input id: string}, unknownFirm, unknownProduct, bad, tooLong}.
  function decode(hash, firms, live) {
    var h = String(hash || "").replace(/^#/, "");
    if (h.indexOf("=") < 0) return null;
    var d = { firm: null, product: null, lang: null, values: {}, unknownFirm: null, unknownProduct: null, bad: 0, tooLong: false };
    if (h.length > MAX) { d.tooLong = true; return d; }
    var got = Object.create(null);                                        // no prototype: a key named __proto__ is just a key
    h.split("&").forEach(function (kv) {
      var i = kv.indexOf("="), k, v;
      if (i < 1) return;
      k = kv.slice(0, i);
      try { v = decodeURIComponent(kv.slice(i + 1).replace(/\+/g, " ")); } catch (e) { got[k] = got[k] || { bad: true }; return; }
      if (v === "") return;                                                 // an empty value is no value
      if (!(k in got)) got[k] = { v: v };                                   // the first of a repeated key counts
    });
    var byKey = Object.create(null);
    FIELDS.forEach(function (x) { byKey[x[0]] = x; });
    Object.keys(got).forEach(function (k) {
      var g = got[k], v = g.v;
      if (k === "f" || k === "p" || k === "l") return;
      var x = byKey[k];
      if (!x) return;                                                       // a key this desk doesn't know: ignored
      if (g.bad) { d.bad++; return; }
      if (x[2] === "num") { if (NUM.test(v) && isFinite(parseFloat(v))) d.values[x[1]] = v; else d.bad++; }
      else if (x[2] === "side") { if (SIDE.hasOwnProperty(v)) d.values[x[1]] = SIDE[v]; else d.bad++; }
      else if (x[2] === "mode") { if (MODE.hasOwnProperty(v)) d.values[x[1]] = v; else d.bad++; }
    });
    var f = got.f, p = got.p, l = got.l;
    if (f) {
      if (!f.bad && Object.prototype.hasOwnProperty.call(firms, f.v)) d.firm = f.v;
      else d.unknownFirm = !f.bad && NAME.test(f.v) ? f.v : "";
    }
    // a challenge belongs to its firm: looked up in the firm the link names, or the desk's default when it names none
    var home = d.firm || (f ? null : Object.keys(firms)[0]);
    if (p && home) {
      if (!p.bad && Object.prototype.hasOwnProperty.call(firms[home].products, p.v)) d.product = p.v;
      else d.unknownProduct = !p.bad && NAME.test(p.v) ? p.v : "";
    }
    if (l && !l.bad && (live || []).indexOf(l.v) >= 0) d.lang = l.v;       // a language that isn't live: ignored
    return d;
  }

  function init(o) {
    var el = function (id) { return document.getElementById(id); };
    var T = o.T, esc = o.esc, F = o.F, live = o.live || [], lang = o.lang;
    var box = el("shared"), result = el("result");

    function state() {
      var s = { f: el("firm").value, p: el("profile").value };
      FIELDS.forEach(function (x) { var i = el(x[1]); if (i) s[x[1]] = i.value.trim(); });
      if (lang !== "en" && live.indexOf(lang) >= 0) s.l = lang;
      return s;
    }
    function link() { return location.origin + location.pathname + "#" + encode(state()); }

    // under the verdict: copy, or show the link to copy by hand where the clipboard is unavailable
    result.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest("[data-copy-link]");
      if (!b) return;
      var url = link(), msg = b.parentNode.querySelector(".linkmsg");
      function manual() {
        msg.innerHTML = T.share_manual + ' <input class="linkurl" readonly value="' + esc(url) + '">';
        var i = msg.querySelector("input"); i.focus(); i.select();
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () { msg.textContent = T.share_copied; }, manual);
      } else manual();
    });

    var d = decode(location.hash, o.firms, live);
    if (!d) return;
    if (d.lang && d.lang !== lang) {                                         // the sharer's language, when it is live
      location.replace((d.lang === "en" ? "/" : "/" + d.lang) + location.hash);
      return;
    }
    var lines = [];
    if (d.tooLong) lines.push(T.shared_long);
    else {
      if (d.firm) { el("firm").value = d.firm; o.fillProfiles(); }
      if (d.product) el("profile").value = d.product;
      Object.keys(d.values).forEach(function (id) { var i = el(id); if (i) i.value = d.values[id]; });
      o.toggleInputs(); o.render();
      var firm = o.firms[el("firm").value];
      lines.push(T.shared);
      if (d.unknownFirm !== null) lines.push(F(T.shared_firm, { firm: esc(d.unknownFirm || "?"), shown: esc(firm.name) }));
      else if (d.unknownProduct !== null) lines.push(F(T.shared_product, { firm: esc(firm.name), product: esc(d.unknownProduct || "?"),
                                                                             shown: esc(firm.products[el("profile").value].label) }));
      if (d.bad) lines.push(F(T.shared_bad, { n: d.bad }));
    }
    box.innerHTML = lines.map(function (x) { return "<div>" + x + "</div>"; }).join("");
    box.hidden = false;
    // the first edit makes the numbers the reader's own: the notice goes, and so does the fragment in the address bar
    function edited() {
      box.hidden = true;
      if (history.replaceState) history.replaceState(null, "", location.pathname + location.search);
      ["input", "change"].forEach(function (t) { el("desk").removeEventListener(t, edited); });
    }
    ["input", "change"].forEach(function (t) { el("desk").addEventListener(t, edited); });
  }

  var api = { encode: encode, decode: decode, init: init, MAX: MAX, FIELDS: FIELDS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DESKLINK = api;
})(this);
