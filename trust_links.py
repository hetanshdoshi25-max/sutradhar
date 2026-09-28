"""
SUTRADHAR - Trust-link graph
--------------------------------
The problem statement asks to map actors into a relationship graph of
"handles, PGP keys, wallets AND trust links". The first three are hard
identifiers (persona_reuse). Trust links are the SOFT social edges of a
dark-web marketplace: who vouches for whom, who co-mentions whom, who
endorses a vendor. These edges matter because a rebranded actor rebuilds
the SAME trust relationships - vouching for the same associates, endorsed
by the same buyers - even when their identifiers change.

This module scans each persona's text for references to OTHER known
aliases in the case set, and classifies the reference:
  - vouch / endorse  (positive trust)  e.g. "vouch for", "trusted", "legit"
  - warn / scam-flag (negative trust)  e.g. "scammer", "avoid", "exit"
  - co-mention       (neutral link)    a bare mention of another handle

The result is a set of directed trust edges that sit alongside the
identifier and similarity edges in the knowledge graph.
"""

import re

VOUCH = ["vouch", "vouched", "trusted", "legit", "reliable", "endorse",
         "recommend", "solid vendor", "good vendor", "stand by", "co-sign"]
WARN = ["scammer", "scam", "avoid", "exit scam", "ripped", "fraud", "burned",
        "don't trust", "do not trust", "fake", "selective scam"]


def _handle_variants(alias):
    """Match an alias whether written bare, @-prefixed, or quoted."""
    a = re.escape(alias)
    return re.compile(r"(?<![\w@])@?%s\b" % a, re.IGNORECASE)


def trust_links(personas):
    """Return directed trust edges between personas in the case set.
    Each edge: {source, target, type, sentiment, evidence}."""
    edges = []
    aliases = [(i, p["alias"]) for i, p in enumerate(personas) if p.get("alias")]

    for i, p in enumerate(personas):
        text = p.get("text", "") or ""
        low = text.lower()
        for j, alias in aliases:
            if j == i:
                continue
            rx = _handle_variants(alias)
            m = rx.search(text)
            if not m:
                continue
            # find the sentence/window around the mention to judge sentiment
            start = max(0, m.start() - 60)
            end = min(len(text), m.end() + 60)
            window = low[start:end]

            sentiment, ttype = "neutral", "co-mention"
            if any(w in window for w in WARN):
                sentiment, ttype = "negative", "scam-flag"
            elif any(w in window for w in VOUCH):
                sentiment, ttype = "positive", "vouch"

            edges.append({
                "source": i, "target": j,
                "type": ttype, "sentiment": sentiment,
                "evidence": text[start:end].strip(),
            })
    return edges


def trust_summary(edges, nodes):
    """Human-readable per-actor trust standing for display."""
    incoming = {}
    for e in edges:
        t = e["target"]
        incoming.setdefault(t, {"vouch": 0, "scam-flag": 0, "co-mention": 0})
        incoming[t][e["type"]] = incoming[t].get(e["type"], 0) + 1
    out = {}
    for nid, counts in incoming.items():
        alias = nodes[nid]["alias"] if nid < len(nodes) else str(nid)
        standing = ("Trusted" if counts["vouch"] > counts["scam-flag"]
                    else "Flagged" if counts["scam-flag"] > 0 else "Neutral")
        out[alias] = {"standing": standing, **counts}
    return out


if __name__ == "__main__":
    demo = [
        {"alias": "shadowfox", "text": "i vouch for nightcrawler, solid vendor, been trading months"},
        {"alias": "nightcrawler", "text": "thanks, cipher9 is also legit and trusted"},
        {"alias": "cipher9", "text": "stay away from vypr, total scammer, exit scammed me"},
        {"alias": "vypr", "text": "deals here, best prices"},
    ]
    edges = trust_links(demo)
    for e in edges:
        print(f"{demo[e['source']]['alias']} --{e['type']}({e['sentiment']})--> {demo[e['target']]['alias']}")
    print()
    import json
    print(json.dumps(trust_summary(edges, demo), indent=2))
