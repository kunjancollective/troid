/* troid's status light: the dot in the tr●id wordmark (site_build.mark). It ripples while troid's ledger is live,
   meaning status.json (written by backtest/gen_ledger.py on every shadow run) shows a run inside the window it
   states, and holds still otherwise, including when status.json can't be read. The dot links to troid's ledger. */
(function () {
  var d = document.querySelector(".mark .dot");
  if (!d || !window.fetch) return;
  fetch("/status.json", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (s) {
    var t = Date.parse(s.last_run_utc), age = (Date.now() - t) / 60000;
    var live = isFinite(age) && age > -30 && age <= +s.stale_after_minutes;
    d.classList.toggle("live", live);
    var msg = d.getAttribute(live ? "data-live" : "data-still");
    if (msg && isFinite(t)) {
      msg = msg.replace("{time}", new Date(t).toISOString().slice(0, 16).replace("T", " "));
      d.title = msg;
      d.setAttribute("aria-label", msg);
    }
  }).catch(function () {});
})();
