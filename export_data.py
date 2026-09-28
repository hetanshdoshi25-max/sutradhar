"""SUTRADHAR - CSV / JSON export of the analysis result set."""
import io
import csv
import json
from datetime import datetime, timezone


def build_json_export(graph, threshold, case_id=None):
    payload = {
        "case_id": case_id or datetime.now().strftime("%Y%m%d-%H%M%S"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "threshold": threshold,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "attributions": graph["attributions"],
        "trust_edges": graph.get("trust_edges", []),
        "trust_summary": graph.get("trust_summary", {}),
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def build_csv_export(graph):
    """One row per attributed pair (edge) with a flattened evidence summary,
    plus each node's evasion-discipline level - the 'result set' in a
    spreadsheet-friendly format."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["alias_a", "alias_b", "confidence_pct", "signals_matched",
               "shared_identifiers", "crypto_cashout", "infra_clearnet_ip",
               "peak_window_a", "peak_window_b", "evasion_a", "evasion_b"])
    for e in graph["edges"]:
        na, nb = graph["nodes"][e["source"]], graph["nodes"][e["target"]]
        ev = e["evidence"]
        signals = [k for k in ("char_ngrams", "function_words", "style_ratios", "cognitive",
                               "activity_pattern", "persona_reuse", "crypto_flow", "infra") if k in ev]
        shared = ", ".join(ev.get("shared_identifiers", []))
        cashout = (ev.get("crypto_detail") or {}).get("cashout", {}).get("vasp", "")
        clear_ip = (ev.get("infra_detail") or {}).get("clearnet_ip", "")
        pw = ev.get("peak_windows", ["", ""])
        w.writerow([na["alias"], nb["alias"], round(e["score"] * 100, 1), "|".join(signals),
                   shared, cashout, clear_ip, pw[0], pw[1],
                   na.get("evasion", {}).get("level", ""), nb.get("evasion", {}).get("level", "")])

    # --- per-actor profile block (PS: actor profiles, category, last scan, source) ---
    w.writerow([])
    w.writerow(["ACTOR PROFILES"])
    w.writerow(["alias", "category", "site", "source", "opsec_level",
               "evasion_level", "identifiers", "last_scan"])
    for n in graph["nodes"]:
        idents = "|".join(sorted({i for i in _node_idents(graph, n)}))
        w.writerow([n["alias"], n.get("category", ""), n.get("site", ""),
                   n.get("source", ""), n.get("exposure", {}).get("level", ""),
                   n.get("evasion", {}).get("level", ""), idents, n.get("last_scan", "")])
    return buf.getvalue().encode("utf-8")


def _node_idents(graph, node):
    """Collect identifier strings visible in a node's crypto/infra evidence."""
    out = set()
    for c in (node.get("crypto") or []):
        w = c.get("wallet") or c.get("address")
        if w:
            out.add(w)
    for inf in (node.get("infra") or []):
        if inf.get("onion"):
            out.add(inf["onion"])
    return out


if __name__ == "__main__":
    from correlation import build_graph
    from sample_personas import PERSONAS
    g = build_graph(PERSONAS)
    open("export_sample.json", "wb").write(build_json_export(g, 0.55))
    open("export_sample.csv", "wb").write(build_csv_export(g))
    print("wrote export_sample.json and export_sample.csv")
