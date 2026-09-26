"""
SUTRADHAR - Local AI Analyst (offline, rule-based reasoning)
---------------------------------------------------------------
An automated analyst layer that runs ENTIRELY OFFLINE - no external LLM
API, no outbound network call, nothing leaves the machine. This is a
deliberate design choice: an attribution platform for a national security
agency must keep case data air-gapped, so an internet-dependent AI (GPT /
Claude API) would violate the platform's own sovereignty guarantee.

Instead this module is a deterministic reasoning engine that reads a graph
result and produces:

  1. Auto-triage       - which findings/personas an analyst should look at
                         first, ranked by evidence strength + risk.
  2. Narrative summary - a plain-language explanation of each attribution,
                         generated from the actual signal evidence.
  3. Recommended next  - the concrete investigative action each finding
     action              points to (subpoena target, review flag, etc.).

It reads like an AI analyst's brief, but every sentence is traceable to a
specific signal value - which is exactly what a court-admissible tool
needs (explainable, not a black box).
"""


SIGNAL_PHRASES = {
    "cognitive":       "a matching behavioural-reasoning fingerprint (robust to AI-rephrasing)",
    "style_ratios":    "a near-identical writing style",
    "char_ngrams":     "matching character-level spelling and spacing habits",
    "function_words":  "the same unconscious use of common function words",
    "activity_pattern":"overlapping active-hour patterns",
    "persona_reuse":   "a reused hard identifier",
    "crypto_flow":     "a shared cryptocurrency wallet cluster",
    "infra":           "shared server infrastructure",
}


def _confidence_word(score):
    return ("very high" if score >= 0.9 else "high" if score >= 0.8
            else "moderate" if score >= 0.65 else "tentative")


def _next_action(ev, nodes, edge):
    """Derive the concrete investigative lead from the strongest hard signal."""
    if "crypto_detail" in ev and (ev["crypto_detail"] or {}).get("cashout"):
        vasp = ev["crypto_detail"]["cashout"].get("vasp", "the exchange")
        if ev["crypto_detail"]["cashout"].get("type") == "mixer":
            return f"Funds route through {vasp} (mixer) - flag for enhanced financial review."
        return f"Serve a KYC subpoena to {vasp} against the shared wallet cluster."
    if "infra_detail" in ev and (ev["infra_detail"] or {}).get("clearnet_ip"):
        return f"Request hosting records for clearnet host {ev['infra_detail']['clearnet_ip']}."
    if "shared_identifiers" in ev and ev["shared_identifiers"]:
        return f"Pivot on the shared identifier ({ev['shared_identifiers'][0]}) across clearnet platforms."
    return "Corroborate with an additional signal before escalation."


def summarize_edge(edge, nodes):
    """Plain-language narrative for one attribution link, built from evidence."""
    a, b = nodes[edge["source"]]["alias"], nodes[edge["target"]]["alias"]
    ev = edge["evidence"]
    score = edge["score"]

    present = [k for k in ("style_ratios", "cognitive", "activity_pattern", "persona_reuse",
                           "crypto_flow", "infra") if k in ev]
    reasons = [SIGNAL_PHRASES[k] for k in present if k in SIGNAL_PHRASES]

    if len(reasons) > 1:
        reason_text = ", ".join(reasons[:-1]) + f", and {reasons[-1]}"
    elif reasons:
        reason_text = reasons[0]
    else:
        reason_text = "converging evidence"

    conf = _confidence_word(score)
    narrative = (
        f"Aliases '{a}' and '{b}' are assessed, with {conf} confidence "
        f"({round(score*100)}%), to be operated by the same individual. "
        f"The assessment rests on {len(present)} independent signals: {reason_text}. "
        f"Because these signals are independent, their agreement is substantially "
        f"stronger than any single indicator alone."
    )
    return {
        "pair": [a, b],
        "confidence": round(score, 3),
        "confidence_word": conf,
        "signals_used": len(present),
        "narrative": narrative,
        "recommended_action": _next_action(ev, nodes, edge),
    }


def triage(graph):
    """Rank what an analyst should look at first: linked findings by
    strength, plus unlinked-but-high-risk personas (OPSEC / evasion)."""
    items = []

    for edge in graph.get("edges", []):
        a, b = graph["nodes"][edge["source"]]["alias"], graph["nodes"][edge["target"]]["alias"]
        items.append({
            "type": "attribution",
            "label": f"{a} = {b}",
            "priority": round(edge["score"], 3),
            "reason": f"{len([k for k in ('style_ratios','activity_pattern','persona_reuse','crypto_flow','infra') if k in edge['evidence']])} signals, {round(edge['score']*100)}% confidence",
        })

    for n in graph.get("nodes", []):
        exp = n.get("exposure", {})
        eva = n.get("evasion", {})
        if exp.get("level") in ("High", "Critical"):
            items.append({
                "type": "exposure",
                "label": f"{n['alias']} - {exp['level']} OPSEC exposure",
                "priority": exp.get("score", 0.6),
                "reason": "self-leaked contact details; high-value lead",
            })
        if eva.get("level") in ("High", "Professional"):
            items.append({
                "type": "evasion",
                "label": f"{n['alias']} - {eva['level']} evasion discipline",
                "priority": eva.get("score", 0.6),
                "reason": "anti-forensic behaviour; likely trained operator",
            })

    items.sort(key=lambda x: -x["priority"])
    return items


def analyst_brief(graph):
    """Full automated brief: triage queue + per-attribution narratives."""
    summaries = [summarize_edge(e, graph["nodes"]) for e in graph.get("edges", [])]
    queue = triage(graph)
    headline = (
        f"Automated analysis resolved {len(graph.get('nodes', []))} personas into "
        f"{len(graph.get('attributions', []))} suspected identities across "
        f"{len(graph.get('edges', []))} corroborated links. "
        f"{len([q for q in queue if q['type']!='attribution'])} personas flagged "
        f"for independent review."
    )
    return {"headline": headline, "triage_queue": queue, "attributions": summaries,
            "engine": "local rule-based analyst (offline, no external API)"}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from correlation import build_graph
    from sample_personas import PERSONAS
    g = build_graph(PERSONAS)
    brief = analyst_brief(g)
    print("HEADLINE:\n ", brief["headline"], "\n")
    print("TRIAGE QUEUE:")
    for q in brief["triage_queue"]:
        print(f"  [{q['priority']:.2f}] {q['label']} - {q['reason']}")
    print("\nATTRIBUTION NARRATIVES:")
    for s in brief["attributions"]:
        print(f"\n  {' = '.join(s['pair'])} ({round(s['confidence']*100)}%)")
        print("   ", s["narrative"])
        print("    ACTION:", s["recommended_action"])
