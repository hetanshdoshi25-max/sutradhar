"""
Turns pairwise stylometry scores into a knowledge graph:
  - every persona becomes a NODE
  - every pair scoring above `threshold` becomes an EDGE (a suspected link)
  - connected personas are grouped into CLUSTERS (= one suspected real author)

Output is a plain dict, ready to hand to the web frontend as JSON.
"""

from stylometry import StylometryEngine
from temporal import temporal_similarity, peak_window
from persona_reuse import extract_identifiers, reuse_similarity, human
from opsec import exposure_profile
from crypto_flow import crypto_link, crypto_trail

# weight of each signal in the blended score (normalised over the ones present)
W_STYLE = 0.45     # writing style (stylometry)
W_TEMPORAL = 0.2   # activity pattern (temporal)
W_REUSE = 0.2      # shared hard identifiers (persona reuse)
W_CRYPTO = 0.15    # shared wallet / wallet cluster (crypto flow)
REUSE_FLOOR = 0.85 # a shared PGP key/wallet/handle is strong evidence on its own
CRYPTO_FLOOR = 0.8 # a shared wallet cluster is strong evidence too


def _clusters(n, edges):
    """Union-Find: group nodes that are connected by any chain of edges."""
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in edges:
        a, b = find(e["source"]), find(e["target"])
        if a != b:
            parent[a] = b
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def build_graph(personas, threshold=0.55):
    texts = [p["text"] for p in personas]
    eng = StylometryEngine().fit(texts)
    n = len(texts)

    nodes = [
        {"id": i, "alias": p["alias"], "site": p.get("site", ""),
         "exposure": exposure_profile(p.get("text", "")),
         "crypto": crypto_trail(p.get("text", ""))}
        for i, p in enumerate(personas)
    ]

    # pre-extract hard identifiers once per persona (from their text)
    ids = [extract_identifiers(p.get("text", "")) for p in personas]

    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            style_score, groups = eng.similarity(i, j)
            evidence = {k: round(v, 3) for k, v in groups.items()}

            # weighted components — a signal only counts when it applies
            comps = [(style_score, W_STYLE)]

            # temporal: only if BOTH personas carry posting hours
            hi, hj = personas[i].get("hours"), personas[j].get("hours")
            if hi and hj:
                t = temporal_similarity(hi, hj)
                comps.append((t, W_TEMPORAL))
                evidence["activity_pattern"] = round(t, 3)
                evidence["peak_windows"] = [peak_window(hi), peak_window(hj)]

            # persona reuse: only counts when a hard identifier is actually shared
            reuse_score, shared = reuse_similarity(ids[i], ids[j])
            if shared:
                comps.append((reuse_score, W_REUSE))
                evidence["persona_reuse"] = round(reuse_score, 3)
                evidence["shared_identifiers"] = [human(s) for s in shared]

            # crypto flow: shared wallet or same wallet-cluster
            c_score, c_why = crypto_link(personas[i].get("text", ""), personas[j].get("text", ""))
            if c_why:
                comps.append((c_score, W_CRYPTO))
                evidence["crypto_flow"] = round(c_score, 3)
                evidence["crypto_detail"] = c_why

            wsum = sum(w for _, w in comps)
            score = sum(s * w for s, w in comps) / wsum
            if shared:                       # hard identifier -> strong floor
                score = max(score, REUSE_FLOOR)
            if c_why:                        # shared wallet/cluster -> strong floor
                score = max(score, CRYPTO_FLOOR)

            if score >= threshold:
                edges.append({
                    "source": i,
                    "target": j,
                    "score": round(score, 3),
                    "evidence": evidence,
                })

    # tag each node with its cluster id so the UI can colour groups
    clusters = _clusters(n, edges)
    for cid, members in enumerate(clusters):
        for idx in members:
            nodes[idx]["cluster"] = cid

    # a human-readable attribution summary per multi-node cluster
    attributions = []
    for cid, members in enumerate(clusters):
        if len(members) > 1:
            aliases = [nodes[m]["alias"] for m in members]
            linkscores = [e["score"] for e in edges
                          if e["source"] in members and e["target"] in members]
            attributions.append({
                "cluster": cid,
                "aliases": aliases,
                "confidence": round(sum(linkscores) / len(linkscores), 3),
            })

    return {"nodes": nodes, "edges": edges, "attributions": attributions}


if __name__ == "__main__":
    import json
    from sample_personas import PERSONAS
    g = build_graph(PERSONAS)
    print(json.dumps(g, indent=2))
    print("\nATTRIBUTIONS:")
    for a in g["attributions"]:
        print(f"  {' = '.join(a['aliases'])}  ->  {a['confidence']*100:.0f}% confidence")
