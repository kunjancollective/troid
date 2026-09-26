"""Outside figures troid's pages use (sources.json, the challenge-proof audit, 2026-09-26): their tier lines, which
templates write as src("id"), and the public /sources page. A number from outside troid has a document and a read
date here, or it doesn't appear on a page. Firm rules are firms.json's, with their own provenance."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {k: v for k, v in json.loads((ROOT / "sources.json").read_text()).items() if not k.startswith("_")}


def tier(T, sid):
    """The tier line under a figure from source sid: SOURCED, who produced it and who reported it, when it was
    published and read, its caveat, and a link to its entry on /sources."""
    s = SOURCES[sid]
    return T(f"sources.tier.{sid}", published=s["published"], updated=s.get("updated") or "", read=s["read_on"])
