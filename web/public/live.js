/* troid's status light: the dot in the tr●id wordmark (site_build.mark). It ripples while troid's ledger is live,
   meaning status.json (written by backtest/gen_ledger.py on every shadow run) shows the last run and the last bar
   it processed inside the windows it states, and holds still otherwise. When status.json can't be read the dot
   holds still and says so. Checked on load, every five minutes while the page is visible, and when it becomes
   visible again. The dot links to troid's ledger. */
(function () {
  var d = document.querySelector(".mark .dot");
  if (!d || !window.fetch) return;
  function label(msg, when) {
    if (!msg) return;
    if (when != null) msg = msg.replace("{time}", new Date(when).toISOString().slice(0, 16).replace("T", " "));
    d.title = msg;
    d.setAttribute("aria-label", msg);
  }
  function unknown() { d.classList.remove("live"); label(d.getAttribute("data-unknown")); }
  function check() {
    fetch("/status.json", { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("status " + r.status);
      return r.json();
    }).then(function (s) {
      var run = Date.parse(s.last_run_utc), bar = Date.parse(s.as_of_bar_utc) + (+s.bar_minutes || 0) * 60000;
      if (!isFinite(run) || !isFinite(bar)) return unknown();
      var now = Date.now(), runAge = (now - run) / 60000, barAge = (now - bar) / 60000;
      var live = runAge > -30 && runAge <= +s.stale_after_minutes && barAge <= +(s.bar_stale_after_minutes || s.stale_after_minutes);
      d.classList.toggle("live", live);
      label(d.getAttribute(live ? "data-live" : "data-still"), live ? run : Math.min(run, bar));
    }).catch(unknown);
  }
  check();
  setInterval(function () { if (!document.hidden) check(); }, 300000);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) check(); });
})();
