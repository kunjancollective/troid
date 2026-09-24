"""A stand-in for TradingView's Ticker Tape embed script, for the browser checks (web/test_ticker_page.py,
phone_check.py), which never call TradingView. It does what the real script does to the page, as read from
s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js on 2026-09-24: reads its settings from its own text,
replaces the container's .tradingview-widget-container__widget with an iframe 44 px high (72 px when displayMode is
adaptive and the container is 767 px wide or less; 2 px more when not transparent), sets the container to that height
and removes itself. It records the settings it got in window.__tv, so a check can read them.

  from tv_stub import route_tv
  route_tv(ctx, "ok")      # ok | fail (the request is refused) | hang (never answered)
"""
URL = "**/external-embedding/embed-widget-ticker-tape.js"

STUB_JS = r"""(function () {
  var sc = document.currentScript, cfg = JSON.parse(sc.text || sc.textContent), box = sc.parentNode;
  window.__tv = { cfg: cfg, loads: ((window.__tv || {}).loads || 0) + 1 };
  var w = box.getBoundingClientRect().width, h = (cfg.displayMode === "adaptive" ? w <= 767 : cfg.displayMode === "compact") ? 72 : 44;
  if (!cfg.isTransparent) h += 2;
  var f = document.createElement("iframe");
  f.title = "ticker tape (stub)";
  f.style.cssText = "width:100%;height:" + h + "px;border:0;display:block";
  f.srcdoc = "<body style='margin:0;font:12px monospace;color:#888;white-space:nowrap'>" +
    cfg.symbols.map(function (s) { return s.description || s.proName; }).join(" · ") + "</body>";
  var ph = box.querySelector(".tradingview-widget-container__widget");
  if (ph) box.replaceChild(f, ph); else box.appendChild(f);
  box.style.height = h + "px";
  sc.remove();
})();"""


def route_tv(ctx, mode="ok"):
    """Answer the widget script for every page in ctx: the stub, a refusal, or nothing at all."""
    def handler(r):
        if mode == "fail":
            return r.abort()
        if mode == "hang":
            return None
        return r.fulfill(status=200, body=STUB_JS, content_type="application/javascript")
    ctx.route(URL, handler)
