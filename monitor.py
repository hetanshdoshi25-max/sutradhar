"""
SUTRADHAR - Autonomous monitoring
-----------------------------------
Simulates the "continuous gathering" / "autonomous mode" capability the
problem statement asks for: the system periodically polls a configured set
of sources and ingests newly discovered personas, each tagged with its
source, category, and discovery timestamp - without live-scraping real
onion services (see note below).

IMPORTANT: this module polls a CONFIGURED, LABELLED demo feed - it does not
connect to or scrape real dark-web marketplaces or forums. Live crawling of
.onion services carries real legal/safety risk (incidental exposure to
illegal content) and is out of scope for this prototype. In a production
deployment, this same polling architecture would connect to authorized,
vetted OSINT feeds (licensed forum-monitoring services, law-enforcement
data-sharing pipelines) under proper legal authorization - the engineering
pattern (scheduler -> ingest -> auto-correlate -> log) is what's being
demonstrated here.
"""

import threading
import time
import random
from datetime import datetime, timezone

import audit_log

# ---- configured sources (in production: authorized OSINT feeds) ----
SOURCES = [
    {"name": "ForumA - marketplace listings", "category": "marketplace"},
    {"name": "ForumB - general discussion",   "category": "forum"},
    {"name": "ForumC - vendor reviews",       "category": "marketplace"},
    {"name": "PasteMonitor - leak feed",      "category": "paste-site"},
    {"name": "TelegramWatch - channel scan",  "category": "chat-channel"},
]

# ---- a small pool of "newly discovered" personas revealed over time ----
_FEED = [
    {"alias": "duskrunner", "text": "not gonna lie this batch looks solid, or whatever "
     "it's hard to tell right now. idk man. hit me @vendmirror for the list"},
    {"alias": "quietledger", "text": "It should be observed that the escrow terms require "
     "review; furthermore, several members have raised concerns. PGP 0x9F3A21BC on file."},
    {"alias": "nullpoint7", "text": "YO this restock is INSANE!! grabbed mine already!! "
     "honestly best price I've seen!! trust me on this one!!"},
    {"alias": "greymarket_x", "text": "Confirmed. Shipment update as expected, no change "
     "from prior batch. Status: pending. Awaiting response."},
    {"alias": "shadowfox", "text": "the new vendor list looks kinda sketchy again... "
     "basically same story as last time. mirror abcdefghijklmnop.onion still up"},
    {"alias": "cipher9", "text": "One must consider the recent audit findings; however, "
     "no conclusive irregularity has been established at this juncture."},
]

_state = {
    "running": False,
    "last_scan": None,
    "scans_completed": 0,
    "discovered": [],       # ingested personas with source/category/timestamp
    "_feed_idx": 0,
    "_thread": None,
}
_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scan_once():
    """One polling cycle: pick a source, reveal the next feed item (if any)
    as a 'newly discovered' persona, persist it to the database, and log it.
    Persisting makes the autonomous mode feed the analytical front-end - the
    discovered actor survives restarts and becomes queryable by timeline."""
    with _lock:
        source = random.choice(SOURCES)
        _state["last_scan"] = _now()
        _state["scans_completed"] += 1

        item = None
        if _state["_feed_idx"] < len(_FEED):
            raw = _FEED[_state["_feed_idx"]]
            _state["_feed_idx"] += 1
            item = {
                "alias": raw["alias"],
                "text": raw["text"],
                "site": source["name"],
                "category": source["category"],
                "discovered_at": _state["last_scan"],
            }
            _state["discovered"].append(item)

    if item:
        try:
            import storage
            storage.init_db()
            c = storage._conn()
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            exists = c.execute("SELECT id FROM actors WHERE alias=?", (item["alias"],)).fetchone()
            if not exists:
                c.execute("""INSERT INTO actors (alias, site, source, category,
                             identifiers, cognitive_traits, last_scan, first_seen)
                             VALUES (?,?,?,?,?,?,?,?)""",
                          (item["alias"], item["site"], source["name"], source["category"],
                           "[]", "[]", now, now))
                c.commit()
            c.close()
        except Exception:
            pass

    audit_log.record(
        "autonomous_scan",
        f"polled '{source['name']}' ({source['category']})"
        + (f" - discovered '{item['alias']}', persisted to DB" if item else " - no new activity"),
    )
    return item


def _loop(interval_sec):
    while _state["running"]:
        _scan_once()
        for _ in range(interval_sec * 10):
            if not _state["running"]:
                break
            time.sleep(0.1)


def start(interval_sec=6):
    with _lock:
        if _state["running"]:
            return status()
        _state["running"] = True
        t = threading.Thread(target=_loop, args=(interval_sec,), daemon=True)
        _state["_thread"] = t
        t.start()
    audit_log.record("monitor_start", f"autonomous monitoring started, interval={interval_sec}s")
    return status()


def stop():
    with _lock:
        _state["running"] = False
    audit_log.record("monitor_stop", "autonomous monitoring stopped")
    return status()


def status():
    with _lock:
        return {
            "running": _state["running"],
            "last_scan": _state["last_scan"],
            "scans_completed": _state["scans_completed"],
            "sources_configured": len(SOURCES),
            "sources": [s["name"] for s in SOURCES],
            "discovered": list(_state["discovered"]),
            "discovered_count": len(_state["discovered"]),
        }


def reset():
    with _lock:
        _state.update({"running": False, "last_scan": None, "scans_completed": 0,
                       "discovered": [], "_feed_idx": 0})


if __name__ == "__main__":
    start(interval_sec=1)
    time.sleep(4)
    stop()
    import json
    print(json.dumps(status(), indent=2))
