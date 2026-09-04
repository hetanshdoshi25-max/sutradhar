"""
Turns pairwise stylometry scores into a knowledge graph:
  - every persona becomes a NODE
  - every pair scoring above `threshold` becomes an EDGE (a suspected link)
  - connected personas are grouped into CLUSTERS (= one suspected real author)

Output is a plain dict, ready to hand to the web frontend as JSON.
"""

from stylometry import StylometryEngine
from temporal import temporal_similarity, peak_window

# how much each top-level signal counts toward the final score
W_STYLE = 0.7      # writing style (stylometry)
W_TEMPORAL = 0.3   # activity pattern (temporal), when available


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
        {"id": i, "alias": p["alias"], "site": p.get("site", "")}
        for i, p in enumerate(personas)
    ]

    edges = []
    for i in range(n):
        for j in range(i + 1, n):
            style_score, groups = eng.similarity(i, j)

            # temporal signal only if BOTH personas carry posting hours
            hi, hj = personas[i].get("hours"), personas[j].get("hours")
            evidence = {k: round(v, 3) for k, v in groups.items()}
            if hi and hj:
                t = temporal_similarity(hi, hj)
                score = W_STYLE * style_score + W_TEMPORAL * t
                evidence["activity_pattern"] = round(t, 3)
                evidence["peak_windows"] = [peak_window(hi), peak_window(hj)]
            else:
                score = style_score  # fall back to stylometry alone

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
