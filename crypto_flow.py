"""
SUTRADHAR - Crypto-flow signal
------------------------------
Two jobs, both from the wallet addresses a persona leaves in its text:

  1. Wallet clustering  -> two aliases whose wallets belong to the same
     entity (co-spent / same cluster) are linked, even if the addresses
     themselves differ. Attribution survives a fresh address.
  2. Cash-out attribution -> follow a wallet's cluster to where it finally
     off-ramps: a KYC exchange (a subpoena away from a name) or a mixer
     (obscured, a red flag in itself).

NOTE: real on-chain tracing needs live blockchain data (a production job).
This module ships a small, clearly-labelled MOCK chain-analysis ledger so
the capability can be demonstrated end-to-end offline. Swap MOCK_LEDGER for
a real chain-analysis API (Chainalysis / GraphSense) in production.
"""

import re

WALLET_RE = {
    "btc": re.compile(r"\b(?:bc1[a-z0-9]{20,60}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "eth": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
}

# ---- MOCK chain-analysis ledger (demo only; replace with a real API) ----
# address -> which entity-cluster it belongs to + where that cluster cashes out
MOCK_LEDGER = {
    # cluster C1 - two different addresses, same operator, off-ramps at Binance
    "bc1qs4f0x9k2m3n8p7q6r5t4v3w2x1y0z9a8b7c6d":
        {"cluster": "C1", "cashout": {"vasp": "Binance", "type": "KYC exchange",
                                       "risk": "Traceable (KYC subpoena)"}},
    "bc1qn1ghtcr4wl3r7h8j9k0l1m2n3o4p5q6r7s8t":
        {"cluster": "C1", "cashout": {"vasp": "Binance", "type": "KYC exchange",
                                       "risk": "Traceable (KYC subpoena)"}},
    # cipher9 - cashes out at Coinbase
    "bc1qc1ph3r9k8j7h6g5f4d3s2a1z0x9c8v7b6n5m4":
        {"cluster": "C2", "cashout": {"vasp": "Coinbase", "type": "KYC exchange",
                                       "risk": "Traceable (KYC subpoena)"}},
    # vypr - runs funds through a CoinJoin mixer, cash-out obscured
    "bc1qvypr0m1x3r5cash0ut9obscured8mixer7wasab":
        {"cluster": "C3", "cashout": {"vasp": "Wasabi CoinJoin", "type": "mixer",
                                       "risk": "Obscured (mixer) - flag for review"}},
}


def extract_wallets(text):
    ids = set()
    if text:
        for rx in WALLET_RE.values():
            for m in rx.findall(text):
                ids.add(m)
    return ids


def _lookup(addr):
    return MOCK_LEDGER.get(addr)


def crypto_trail(text):
    """Per-persona: each wallet found + where our ledger says it cashes out."""
    out = []
    for w in sorted(extract_wallets(text)):
        info = _lookup(w)
        entry = {"address": w, "cluster": None, "cashout": None}
        if info:
            entry["cluster"] = info["cluster"]
            entry["cashout"] = info["cashout"]
        out.append(entry)
    return out


def crypto_link(text_a, text_b):
    """Score + reason if two personas' wallets share an address or a cluster."""
    wa, wb = extract_wallets(text_a), extract_wallets(text_b)
    if not wa or not wb:
        return 0.0, None

    # exact same address is the strongest
    shared_addr = wa & wb
    if shared_addr:
        addr = sorted(shared_addr)[0]
        info = _lookup(addr)
        return 0.95, {"kind": "shared wallet", "detail": addr,
                      "cashout": info["cashout"] if info else None}

    # different addresses, same entity-cluster (co-spent)
    ca = {(_lookup(w) or {}).get("cluster") for w in wa} - {None}
    cb = {(_lookup(w) or {}).get("cluster") for w in wb} - {None}
    shared_cluster = ca & cb
    if shared_cluster:
        cl = sorted(shared_cluster)[0]
        cash = next((_lookup(w)["cashout"] for w in wa
                     if (_lookup(w) or {}).get("cluster") == cl), None)
        return 0.9, {"kind": "wallet cluster", "detail": cl, "cashout": cash}

    return 0.0, None


if __name__ == "__main__":
    a = "payment sent to bc1qs4f0x9k2m3n8p7q6r5t4v3w2x1y0z9a8b7c6d"
    b = "use bc1qn1ghtcr4wl3r7h8j9k0l1m2n3o4p5q6r7s8t for the deposit"
    print("trail A:", crypto_trail(a))
    score, why = crypto_link(a, b)
    print("link:", score, why)
