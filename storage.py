"""
SUTRADHAR - Persistent storage (SQLite)
------------------------------------------
The problem statement asks for "collection, STORAGE, contextualization and
QUERYING" of actor intelligence, with fields for identifiers, persona
linkages, attribution confidence, category, last-scan date and source.

This module persists every analysis to a local SQLite database (no external
server, ships with Python, works air-gapped and on Railway). It stores one
row per discovered actor and one row per attributed link, and exposes a
timeline query so an analyst can ask "which actors were seen between date X
and date Y" - the analytical-front-end requirement.

SQLite is chosen deliberately: zero-dependency, file-based, survives
restarts, and is trivially swappable for PostgreSQL/Neo4j in a production
deployment without changing the query interface.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "sutradhar.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = _conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS actors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alias TEXT, site TEXT, source TEXT, category TEXT,
        opsec_level TEXT, evasion_level TEXT,
        identifiers TEXT, cognitive_traits TEXT,
        last_scan TEXT, first_seen TEXT
    );
    CREATE TABLE IF NOT EXISTS links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alias_a TEXT, alias_b TEXT, confidence REAL,
        signals TEXT, kind TEXT, recorded TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_actor_scan ON actors(last_scan);
    CREATE INDEX IF NOT EXISTS idx_actor_cat  ON actors(category);
    """)
    c.commit(); c.close()


def save_graph(graph, personas):
    """Persist an analysis: upsert actors, insert attribution + trust links."""
    init_db()
    c = _conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    saved_actors = 0

    for n in graph.get("nodes", []):
        alias = n["alias"]
        row = c.execute("SELECT id, first_seen FROM actors WHERE alias=? AND site=?",
                        (alias, n.get("site", ""))).fetchone()
        idents = json.dumps(sorted(
            list({k for k in _idents_for(personas, alias)})))
        traits = json.dumps(n.get("cognitive", {}).get("traits", []))
        if row:
            c.execute("""UPDATE actors SET source=?, category=?, opsec_level=?,
                         evasion_level=?, identifiers=?, cognitive_traits=?, last_scan=?
                         WHERE id=?""",
                      (n.get("source", ""), n.get("category", ""),
                       n.get("exposure", {}).get("level", ""),
                       n.get("evasion", {}).get("level", ""),
                       idents, traits, n.get("last_scan", now), row["id"]))
        else:
            c.execute("""INSERT INTO actors (alias, site, source, category, opsec_level,
                         evasion_level, identifiers, cognitive_traits, last_scan, first_seen)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (alias, n.get("site", ""), n.get("source", ""), n.get("category", ""),
                       n.get("exposure", {}).get("level", ""),
                       n.get("evasion", {}).get("level", ""),
                       idents, traits, n.get("last_scan", now), now))
        saved_actors += 1

    for a in graph.get("attributions", []):
        al = a["aliases"]
        c.execute("""INSERT INTO links (alias_a, alias_b, confidence, signals, kind, recorded)
                     VALUES (?,?,?,?,?,?)""",
                  (al[0], al[1] if len(al) > 1 else "", a.get("confidence", 0),
                   json.dumps(a.get("signals", [])), "attribution", now))
    for t in graph.get("trust_edges", []):
        na = graph["nodes"][t["source"]]["alias"]
        nb = graph["nodes"][t["target"]]["alias"]
        c.execute("""INSERT INTO links (alias_a, alias_b, confidence, signals, kind, recorded)
                     VALUES (?,?,?,?,?,?)""",
                  (na, nb, 0, json.dumps([t["type"]]), "trust:" + t["type"], now))

    c.commit(); c.close()
    return {"actors_saved": saved_actors,
            "attribution_links": len(graph.get("attributions", [])),
            "trust_links": len(graph.get("trust_edges", []))}


def _idents_for(personas, alias):
    from persona_reuse import extract_identifiers
    for p in personas:
        if p.get("alias") == alias:
            return extract_identifiers(p.get("text", ""))
    return set()


def query_actors(category=None, since=None, until=None, limit=200):
    """Timeline / category query - the analytical front-end backend."""
    init_db()
    c = _conn()
    q = "SELECT * FROM actors WHERE 1=1"
    args = []
    if category:
        q += " AND category=?"; args.append(category)
    if since:
        q += " AND last_scan >= ?"; args.append(since)
    if until:
        q += " AND last_scan <= ?"; args.append(until)
    q += " ORDER BY last_scan DESC LIMIT ?"; args.append(limit)
    rows = [dict(r) for r in c.execute(q, args).fetchall()]
    c.close()
    for r in rows:
        r["identifiers"] = json.loads(r.get("identifiers") or "[]")
        r["cognitive_traits"] = json.loads(r.get("cognitive_traits") or "[]")
    return rows


def db_stats():
    init_db()
    c = _conn()
    a = c.execute("SELECT COUNT(*) n FROM actors").fetchone()["n"]
    l = c.execute("SELECT COUNT(*) n FROM links").fetchone()["n"]
    cats = [dict(r) for r in c.execute(
        "SELECT category, COUNT(*) n FROM actors GROUP BY category").fetchall()]
    c.close()
    return {"total_actors": a, "total_links": l, "by_category": cats}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from correlation import build_graph
    from sample_personas import PERSONAS
    g = build_graph(PERSONAS)
    print("save:", save_graph(g, PERSONAS))
    print("stats:", db_stats())
    print("query (all):", len(query_actors()), "actors")
    print("query Financial:", [a["alias"] for a in query_actors(category="Financial / crypto")])
