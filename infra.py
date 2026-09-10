"""
SUTRADHAR - Infrastructure correlation signal
------------------------------------------------
A dark-web (.onion) service hides its real host - but operators routinely
make MISCONFIGURATIONS that leak it. This module models the four
misconfiguration classes named in the problem statement:

  1. Exposed server-status pages   - debug/status endpoints (/server-status,
     /nginx_status, phpinfo) left reachable, revealing internal IPs/paths.
  2. SSL certificates tied to clearnet domains - the onion service reuses a
     TLS certificate also issued for a real, indexed clearnet domain.
  3. Default service banners - unmodified default banners (nginx/1.18.0,
     Apache default page) that make a server fingerprintable and often
     indicate copy-paste hosting shared with other operator infrastructure.
  4. Descriptor inconsistencies - the onion's hidden-service descriptor
     (introduction points, timestamps) overlaps with another descriptor,
     implying shared infrastructure.

Two outputs:
  - infra_trail(text)  -> per-persona: onion(s) found + every misconfig
    class detected + the leaked clearnet host.
  - infra_link(a, b)   -> do two personas share an onion / server cluster?

NOTE: real detection needs live onion probing + Shodan/Censys/OnionScan
(a production job carrying real legal/safety considerations for a student
prototype). This module ships a clearly-labelled MOCK reference ledger,
structured exactly along the four misconfiguration classes above, so the
capability is demonstrable end-to-end offline.
"""

import re

ONION_RE = re.compile(r"\b([a-z2-7]{16}|[a-z2-7]{56})\.onion\b")

# ---- MOCK infrastructure ledger (demo only; replace with Shodan/Censys/OnionScan) ----
MOCK_INFRA = {
    "abcdefghijklmnop.onion": {
        "cluster": "S1", "clearnet_ip": "185.220.101.47", "provider": "OVH SAS (FR)",
        "misconfigs": [
            {"class": "Exposed server-status page", "detail": "/server-status reachable, internal IP leaked"},
            {"class": "SSL certificate tied to clearnet domain", "detail": "cert SAN includes mirror-status.example.net"},
        ],
        "confidence": 0.9,
    },
    "qrstuvwxyzabcdef.onion": {
        # same physical box as above -> same operator
        "cluster": "S1", "clearnet_ip": "185.220.101.47", "provider": "OVH SAS (FR)",
        "misconfigs": [
            {"class": "Default service banner", "detail": "nginx/1.18.0 (Ubuntu) default banner, matches S1"},
            {"class": "Descriptor inconsistency", "detail": "shares introduction-point set with abcdefghijklmnop.onion"},
        ],
        "confidence": 0.88,
    },
    "mnbvcxzlkjhgfdsa.onion": {
        "cluster": "S2", "clearnet_ip": "45.132.192.13", "provider": "Hetzner (DE)",
        "misconfigs": [
            {"class": "Default service banner", "detail": "Apache/2.4.41 default \"It works!\" page exposed"},
        ],
        "confidence": 0.82,
    },
}


def extract_onions(text):
    return {m.group(0) for m in ONION_RE.finditer(text or "")}


def infra_trail(text):
    """Per-persona: each onion service found, every misconfiguration class
    detected on it, and the clearnet host it leaks to."""
    out = []
    for o in sorted(extract_onions(text)):
        info = MOCK_INFRA.get(o)
        out.append({
            "onion": o,
            "cluster": info["cluster"] if info else None,
            "clearnet_ip": info["clearnet_ip"] if info else None,
            "provider": info["provider"] if info else None,
            "misconfigs": info["misconfigs"] if info else [],
        })
    return out


def infra_link(text_a, text_b):
    """Score + reason if two personas' onion services share a server/cluster,
    citing the specific misconfiguration class that ties them together."""
    oa, ob = extract_onions(text_a), extract_onions(text_b)
    if not oa or not ob:
        return 0.0, None

    shared = oa & ob
    if shared:
        o = sorted(shared)[0]
        info = MOCK_INFRA.get(o)
        mc = (info["misconfigs"][0]["class"] if info and info["misconfigs"] else "shared onion service")
        return 0.95, {"kind": mc, "detail": o,
                      "clearnet_ip": info["clearnet_ip"] if info else None}

    ca = {(MOCK_INFRA.get(o) or {}).get("cluster") for o in oa} - {None}
    cb = {(MOCK_INFRA.get(o) or {}).get("cluster") for o in ob} - {None}
    shared_cluster = ca & cb
    if shared_cluster:
        cl = sorted(shared_cluster)[0]
        entry = next((MOCK_INFRA[o] for o in oa if (MOCK_INFRA.get(o) or {}).get("cluster") == cl), {})
        mc = entry.get("misconfigs", [{}])[0].get("class", "shared server")
        return 0.9, {"kind": mc, "detail": f"cluster {cl}", "clearnet_ip": entry.get("clearnet_ip")}

    return 0.0, None


if __name__ == "__main__":
    a = "mirror is up at abcdefghijklmnop.onion for now"
    b = "backup here qrstuvwxyzabcdef.onion same admin"
    print("trail A:", infra_trail(a))
    print("trail B:", infra_trail(b))
    print("link:", infra_link(a, b))
