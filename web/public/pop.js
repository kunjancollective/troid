/* troid's popovers (design handoff 2026-09-24, sections 2 and 6): a "?" beside a term explains it, in one or two
   plain sentences from web/i18n. Two kinds share this file, and at most one is open at a time.
   - [data-tip="id"]: a tooltip (role="tooltip", linked by aria-describedby, so a screen reader hears it without
     opening it). It shows after 300 ms of hover or at once on keyboard focus; a tap opens and closes it on a phone.
   - [data-pop="id"]: a note with links in it ("why these 3?"). It opens and closes on a click or tap, never on hover,
     and its button carries aria-expanded.
   Esc closes either and returns focus to its button; so does a click or tap anywhere else. The note is moved to the end
   of the page when it opens, so no box that clips its contents can cut it off, and placed under its button, inside
   the window. No framework; the page's CSS draws it (.pop, .qm): --surface2 and a --line border, no shadow. */
(function () {
  var open = null, openBtn = null, timer = null;
  function trigger(t) { return t && t.closest ? t.closest("[data-tip],[data-pop]") : null; }
  function place(btn, pop) {
    var W = document.documentElement.clientWidth, r = btn.getBoundingClientRect();
    pop.hidden = false;
    pop.style.maxWidth = Math.min(280, W - 32) + "px";
    var w = pop.offsetWidth, x = getComputedStyle(btn).direction === "rtl" ? r.right - w : r.left;
    x = Math.max(16, Math.min(x, W - 16 - w));
    pop.style.left = (x + window.scrollX) + "px";
    pop.style.top = (r.bottom + window.scrollY + 6) + "px";
  }
  function show(btn) {
    var pop = document.getElementById(btn.getAttribute("data-tip") || btn.getAttribute("data-pop"));
    if (!pop) return;
    if (open) hide();
    if (pop.parentNode !== document.body) document.body.appendChild(pop);
    place(btn, pop);
    open = pop; openBtn = btn;
    if (btn.hasAttribute("data-pop")) btn.setAttribute("aria-expanded", "true");
  }
  function hide() {
    clearTimeout(timer);
    if (!open) return;
    open.hidden = true;
    if (openBtn.hasAttribute("data-pop")) openBtn.setAttribute("aria-expanded", "false");
    open = openBtn = null;
  }
  document.addEventListener("click", function (e) {
    var b = trigger(e.target);
    if (b) { e.preventDefault(); if (openBtn === b) hide(); else show(b); return; }
    if (open && !open.contains(e.target)) hide();
  });
  document.addEventListener("mouseover", function (e) {
    var b = trigger(e.target);
    if (!b || !b.hasAttribute("data-tip") || openBtn === b) return;
    clearTimeout(timer);
    timer = setTimeout(function () { show(b); }, 300);
  });
  document.addEventListener("mouseout", function (e) {
    var b = trigger(e.target);
    if (!b || !b.hasAttribute("data-tip") || b.contains(e.relatedTarget)) return;
    clearTimeout(timer);
    if (openBtn === b) hide();
  });
  // keyboard focus only: a click or tap focuses the button too, and its click opens it
  document.addEventListener("focusin", function (e) {
    var b = trigger(e.target);
    if (b && b.hasAttribute("data-tip") && b.matches(":focus-visible")) show(b);
  });
  document.addEventListener("focusout", function (e) {
    var b = trigger(e.target);
    if (b && b.hasAttribute("data-tip") && openBtn === b) hide();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Escape" || !open) return;
    var b = openBtn;
    hide();
    b.focus();
  });
  // for a page's own button inside a note (ticker.js, "use as entry"), and for a page that is about to replace the
  // button a note belongs to (the desk's readout, re-rendered on every input)
  window.troidPop = { hide: hide, owner: function () { return openBtn; } };
  // a phone fires resize while scrolling (the address bar collapses): only a new width closes it; otherwise it moves
  var lastW = document.documentElement.clientWidth;
  window.addEventListener("resize", function () {
    var W = document.documentElement.clientWidth;
    if (W !== lastW) { lastW = W; hide(); } else if (open) place(openBtn, open);
  });
})();
