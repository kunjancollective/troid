/* troid's calendar strip (site_build.calendar_strip; ticker v2 handoff, section D, kept by v3): the scheduled US releases
   of the next 7 days from /calendar.json, which backtest/fetch_calendar.py reads weekly from BLS, BEA and the Federal
   Reserve. Names, times and sources only: no forecasts. Each event shows the reader's local time with UTC beside it;
   on troid's desk it also says how long before or after the selected firm's daily reset it lands (firms.json
   reset_clock, in the desk's FIRMS), counting to the nearest reset. A tap opens a note (pop.js): what it is, why troid lists it (a MEASURED finding
   with its sample, and what it doesn't show), whether it lands in the bar that finding is about, and the agency's
   schedule with the date troid read it. A schedule that can't load, or whose newest read is over 14 days old, leaves
   the strip hidden with its space kept.
   When the events don't fit, the row moves at about 40 px/s: a copy of it follows it and a CSS transform moves both by
   exactly the distance from the first event to its copy, so the loop has no seam. It holds while hovered or touched,
   while its note is open and while the tab is hidden, and moves again 3 s after the last of those ends. Keyboard focus,
   the tape's pause (the tape's still row) and prefers-reduced-motion each make it a still row that swipes, so a focused
   event is never carried off the screen. */
(function () {
  var c = document.getElementById("cal");
  if (!c || !window.fetch) return;
  var row = c.querySelector(".calrow"), note = document.getElementById("cal-note"), tk = document.getElementById("tk");
  var S = JSON.parse(c.getAttribute("data-t")), lang = (document.documentElement.lang || "en") + "-u-nu-latn";
  var DAY = 864e5, list = [], shown = null, copies = "", key = "", pinned = false, unpin = null, why = {}, resume = null;
  var here = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  var reduce = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  function F(t, o) { return t.replace(/\{(\w+)\}/g, function (m, k) { return k in o ? o[k] : m; }); }
  function esc(x) { return String(x).replace(/[&<>"]/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]; }); }
  function fmt(o) { return new Intl.DateTimeFormat(lang, o); }
  var hm = { hour: "2-digit", minute: "2-digit", hourCycle: "h23" };
  var fLocal = fmt(Object.assign({ weekday: "short" }, hm)), fUtc = fmt(Object.assign({ timeZone: "UTC" }, hm));
  var fLong = fmt(Object.assign({ weekday: "short", month: "short", day: "numeric" }, hm));
  var fMon = fmt({ month: "short", timeZone: "UTC" }), fMonY = fmt({ month: "long", year: "numeric", timeZone: "UTC" });

  function offset(t, tz) {            // minutes a zone is ahead of UTC at instant t
    var p = {};
    new Intl.DateTimeFormat("en-US", { timeZone: tz, hourCycle: "h23", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit" }).formatToParts(t).forEach(function (x) { p[x.type] = +x.value; });
    return (Date.UTC(p.year, p.month - 1, p.day, p.hour % 24, p.minute, p.second) - t) / 6e4;
  }
  function resetOn(t, r) {            // the instant of the firm's reset on the day, in its own zone, that t falls on
    var o = offset(t, r.tz), d = new Date(t + o * 6e4), hh = +r.time.slice(0, 2), mm = +r.time.slice(3, 5);
    var guess = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), hh, mm);
    return guess - offset(guess - o * 6e4, r.tz) * 6e4;
  }
  function nearest(t, r) {            // the reset closest to t, the day before, the day of or the day after; a tie goes to the next
    return [resetOn(t, r), resetOn(t - DAY, r), resetOn(t + DAY, r)].reduce(function (a, b) {
      var da = Math.abs(a - t), db = Math.abs(b - t);
      return db < da || (db === da && b > a) ? b : a;
    });
  }
  function span(ms) {
    var m = Math.round(Math.abs(ms) / 6e4), h = Math.floor(m / 60);
    return !h ? F(S.m, { m: m }) : m % 60 ? F(S.hm, { h: h, m: m % 60 }) : F(S.h, { h: h });
  }
  function period(e, long) {
    if (!e.period) return "";
    var q = /^(\d{4})-Q(\d)$/.exec(e.period);
    if (q) return "Q" + q[2] + (long ? " " + q[1] : "") + (e.estimate ? ", " + (S.est[e.estimate] || e.estimate) : "");
    var t = Date.UTC(+e.period.slice(0, 4), +e.period.slice(5, 7) - 1, 15);
    return long ? fMonY.format(t) : fMon.format(t);
  }
  function when(t, f) {               // local time, then UTC; once when the reader's zone is UTC at that instant
    return f.format(t) + (offset(t, here) ? " · " + fUtc.format(t) : "") + " UTC";
  }
  function firm() {
    var s = document.getElementById("firm"), f = s && window.FIRMS && window.FIRMS[s.value];
    return f && f.reset ? f : null;
  }
  function line(e) {
    var t = Date.parse(e.utc), p = period(e, false), f = firm();
    var parts = ["<b>" + esc(S.kinds[e.kind] || e.kind) + "</b>" + (p ? " (" + esc(p) + ")" : ""), esc(when(t, fLocal))];
    if (f) { var r = nearest(t, f.reset); parts.push(esc(F(r > t ? S.before : S.after, { t: span(r - t), firm: f.name }))); }
    return parts.join(" · ");
  }
  function item(e, i, copy) {         // a copy is the moving row's second lap: it opens the same note, out of the Tab order
    var cl = copy ? " calclone" : "", hide = copy ? ' aria-hidden="true"' : "";
    return (i || copy ? '<span class="calsep' + cl + '" aria-hidden="true">│</span>' : "") +
      '<button type="button" class="cale' + cl + '"' + (copy ? ' tabindex="-1"' : "") + hide + ' data-pop="cal-note" aria-expanded="false"' +
      ' aria-controls="cal-note" data-i="' + list.indexOf(e) + '">' + line(e) + "</button>";
  }
  function paint() {
    var now = Date.now(), soon = list.filter(function (e) { var t = Date.parse(e.utc); return t > now && t <= now + 7 * DAY; });
    var html = soon.length ? soon.map(function (e, i) { return item(e, i, false); }).join("") : '<span class="calempty">' + esc(S.empty) + "</span>";
    if (html === shown) return;       // an unchanged minute leaves the row, and its motion, as they were
    var p = window.troidPop, o = p && p.owner();
    if (o && c.contains(o)) p.hide();
    shown = html;
    copies = soon.map(function (e, i) { return item(e, i, true); }).join("");
    row.innerHTML = html;
    key = "";
    motion();
  }
  function motion() {                 // move only what doesn't fit, only while nothing asks it to be still
    var still = reduce.matches || pinned || !!(tk && tk.classList.contains("still")) || !copies;
    var k = [still, c.clientWidth, shown].join("|");
    if (k === key) return;
    key = k;
    [].slice.call(row.querySelectorAll(".calclone")).forEach(function (x) { x.parentNode.removeChild(x); });
    c.classList.remove("mv");
    if (still || row.scrollWidth <= row.clientWidth + 1) return;
    row.insertAdjacentHTML("beforeend", copies);
    var first = row.querySelector(".cale"), twin = row.querySelector(".cale.calclone");
    var d = first.getBoundingClientRect().left - twin.getBoundingClientRect().left;   // negative left to right, positive right to left
    c.style.setProperty("--calx", d + "px");
    c.style.setProperty("--calt", (Math.abs(d) / 40).toFixed(1) + "s");
    c.classList.add("mv");
  }
  function hold(k, on) {              // one hold, several reasons; moving again 3 s after the last one ends
    if (on) why[k] = 1; else delete why[k];
    clearTimeout(resume);
    if (Object.keys(why).length) c.classList.add("hold");
    else resume = setTimeout(function () { c.classList.remove("hold"); }, 3000);
  }
  c.addEventListener("mouseenter", function () { hold("hover", true); });
  c.addEventListener("mouseleave", function () { hold("hover", false); });
  c.addEventListener("touchstart", function () { hold("touch", true); }, { passive: true });
  ["touchend", "touchcancel"].forEach(function (x) { c.addEventListener(x, function () { hold("touch", false); }, { passive: true }); });
  document.addEventListener("visibilitychange", function () { hold("tab", document.hidden); });
  c.addEventListener("focusin", function (ev) {
    clearTimeout(unpin);
    if (!pinned && ev.target.matches && ev.target.matches(":focus-visible")) { pinned = true; motion(); }
  });
  c.addEventListener("focusout", function (ev) {
    if (!pinned || (ev.relatedTarget && c.contains(ev.relatedTarget))) return;
    unpin = setTimeout(function () { pinned = false; motion(); }, 3000);
  });
  if (window.MutationObserver) {
    new MutationObserver(function () { var o = window.troidPop && window.troidPop.owner(); hold("note", !note.hidden && !!o && c.contains(o)); })
      .observe(note, { attributes: true, attributeFilter: ["hidden"] });
    if (tk) new MutationObserver(motion).observe(tk, { attributes: true, attributeFilter: ["class"] });
  }
  if (window.ResizeObserver) new ResizeObserver(function () { motion(); }).observe(c);
  else window.addEventListener("resize", motion);
  if (reduce.addEventListener) reduce.addEventListener("change", motion);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { key = ""; motion(); });
  var s = document.getElementById("firm");
  if (s) s.addEventListener("change", paint);

  // a tap opens the note (pop.js); this fills it first, in the capture phase
  document.addEventListener("click", function (ev) {
    var b = ev.target.closest && ev.target.closest("#cal .cale");
    if (!b) return;
    var e = list[+b.getAttribute("data-i")], t = Date.parse(e.utc), p = period(e, true), u = new Date(t);
    var mins = u.getUTCHours() * 60 + u.getUTCMinutes();
    note.querySelector(".cn1").textContent = F(S.what, { what: (S.longs[e.kind] || e.kind) + (p ? " (" + p + ")" : ""), source: e.source,
      when: when(t, fLong) });
    note.querySelector(".cn2").textContent = mins >= 720 && mins < 960 ? S.inside : S.outside;
    note.querySelector(".cn3").innerHTML = F(S.source, { url: esc(e.url), source: esc(e.source), date: esc(e.read) });
  }, true);

  fetch("/calendar.json").then(function (r) {
    if (!r.ok) throw new Error("calendar " + r.status);
    return r.json();
  }).then(function (j) {
    var read = Date.parse((j.read || "") + "T00:00:00Z");
    if (!j.events || !(Date.now() - read < 14 * DAY)) throw new Error("stale");
    list = j.events;
    paint();
    c.classList.remove("off");
    setInterval(paint, 6e4);          // events pass and the 7 days move on
  }).catch(function () { c.classList.add("off"); });
})();
