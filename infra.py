"""
SUTRADHAR - Infrastructure correlation signal
----------------------------------------------
A dark-web (.onion) service is meant to hide its real host - but the SERVER
behind it still has fingerprints: its TLS certificate, SSH host key, favicon
hash and HTTP headers. If the operator ever exposed the same server on the
clearnet (a misconfig, a staging box, a shared cert), those fingerprints
match and the onion service's real IP is revealed. This is a real technique
(famously used to locate Silk Road's server).

Two jobs from the onion links a persona leaves in its text:
  1. Infra attribution -> match an onion service's fingerprints to a clearnet
     host (real IP / hosting provider).
  2. Infra clustering  -> two personas whose onion services share a fingerprint
     are running on the same box -> same operator.

NOTE: real fingerprinting needs live onion crawling + Shodan/Censys (a
production job). This module ships a clearly-labelled MOCK fingerprint ledger
so the capability is demonstrable offline. Swap MOCK_INFRA for a real
Shodan/Censys/OnionScan pipeline in production.
"""

import re

ONION_RE = re.compile(r"\b([a-z2-7]{16}|[a-z2-7]{56})\.onion\b")

# ---- MOCK infrastructure ledger (demo only; replace with Shodan/Censys) ----
# onion host -> the clearnet fingerprints that leaked its real server
MOCK_INFRA = {
    "abcdefghijklmnop.onion": {
        "cluster": "S1",
        "clearnet_ip": "185.220.101.47",
        "provider": "OVH SAS (FR)",
        "match": "TLS cert SHA-256 + favicon hash",
        "confidence": 0.9,
    },
    "qrstuvwxyzabcdef.onion": {
        # same server box as above (shared SSH host key) -> same operator
        "cluster": "S1",
        "clearnet_ip": "185.220.101.47",
        "provider": "OVH SAS (FR)",
        "match": "shared SSH host key (RSA)",
        "confidence": 0.88,
    },
    "mnbvcxzlkjhgfdsa.onion": {
        "cluster": "S2",
        "clearnet_ip": "45.132.192.13",
        "provider": "Hetzner (DE)",
        "match": "favicon hash + Server header",
        "confidence": 0.82,
    },
}


def extract_onions(text):
    return {m.group(0) for m in ONION_RE.finditer(text or "")}


def infra_trail(text):
    """Per-persona: each onion service found + its leaked clearnet host."""
    out = []
    for o in sorted(extract_onions(text)):
        info = MOCK_INFRA.get(o)
        out.append({"onion": o,
                    "cluster": info["cluster"] if info else None,
                    "clearnet_ip": info["clearnet_ip"] if info else None,
                    "provider": info["provider"] if info else None,
                    "match": info["match"] if info else None})
    return out


def infra_link(text_a, text_b):
    """Score + reason if two personas' onion services share a server/cluster."""
    oa, ob = extract_onions(text_a), extract_onions(text_b)
    if not oa or not ob:
        return 0.0, None

    # same onion referenced by both
    shared = oa & ob
    if shared:
        o = sorted(shared)[0]
        info = MOCK_INFRA.get(o)
        return 0.95, {"kind": "shared onion service", "detail": o,
                      "clearnet_ip": info["clearnet_ip"] if info else None}

    # different onions, same server-cluster (shared fingerprint)
    ca = {(MOCK_INFRA.get(o) or {}).get("cluster") for o in oa} - {None}
    cb = {(MOCK_INFRA.get(o) or {}).get("cluster") for o in ob} - {None}
    shared_cluster = ca & cb
    if shared_cluster:
        cl = sorted(shared_cluster)[0]
        ip = next((MOCK_INFRA[o]["clearnet_ip"] for o in oa
                   if (MOCK_INFRA.get(o) or {}).get("cluster") == cl), None)
        return 0.9, {"kind": "shared server", "detail": f"cluster {cl}",
                     "clearnet_ip": ip}

    return 0.0, None


if __name__ == "__main__":
    a = "mirror is up at abcdefghijklmnop.onion for now"
    b = "backup here qrstuvwxyzabcdef.onion same admin"
    print("trail A:", infra_trail(a))
    print("link:", infra_link(a, b))
