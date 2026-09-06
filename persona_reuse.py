"""
SUTRADHAR - Persona-reuse signal
--------------------------------
A third, independent signal based on HARD identifiers a persona leaves in
its text: reused PGP keys, emails, crypto addresses, onion links and
handles (@username). Unlike stylometry (fuzzy), this is a hard match - if
two aliases share the same PGP key or wallet, that is strong evidence they
are the same operator, even if their writing looks different.

The extractor is fully automatic: it reads whatever text a persona carries
(including text pasted live in the console), so no manual tagging is needed.
"""

import re

# each pattern -> (label shown to a human, compiled regex)
PATTERNS = {
    "email":   re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "btc":     re.compile(r"\b(?:bc1[a-z0-9]{20,60}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "eth":     re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "pgp":     re.compile(r"\b0x[a-fA-F0-9]{8}(?:[a-fA-F0-9]{8})?\b"),   # 8 or 16 hex key id
    "onion":   re.compile(r"\b[a-z2-7]{16,56}\.onion\b"),
    "handle":  re.compile(r"(?<![\w@])@[A-Za-z0-9_]{4,32}\b"),
}

# how each identifier type reads in evidence
NICE = {"email": "email", "btc": "BTC wallet", "eth": "ETH wallet",
        "pgp": "PGP key", "onion": "onion service", "handle": "handle"}


def extract_identifiers(text):
    """Return a set of normalised 'type:value' identifiers found in text.
    ETH (40 hex) is matched before PGP so a 40-hex 0x... isn't mislabelled."""
    ids = set()
    if not text:
        return ids
    eth_hits = set(PATTERNS["eth"].findall(text))
    for kind, rx in PATTERNS.items():
        for m in rx.findall(text):
            val = m.lower()
            if kind == "pgp" and (val in {e.lower() for e in eth_hits}):
                continue  # it's actually an ETH address, skip as pgp
            ids.add(f"{kind}:{val}")
    return ids


def reuse_similarity(ids_a, ids_b):
    """Score + the shared identifiers between two personas.
    A single shared hard identifier is strong -> score 0.95."""
    shared = sorted(ids_a & ids_b)
    return (0.95 if shared else 0.0), shared


def human(identifier):
    """'pgp:0x9f3a21bc' -> 'PGP key 0x9f3a21bc' for display."""
    kind, _, val = identifier.partition(":")
    return f"{NICE.get(kind, kind)} {val}"


if __name__ == "__main__":
    a = "verify with my PGP 0x9F3A21BC, or reach @vendmirror"
    b = "signed, PGP key 0x9F3A21BC on file"
    ia, ib = extract_identifiers(a), extract_identifiers(b)
    score, shared = reuse_similarity(ia, ib)
    print("A ids:", ia)
    print("B ids:", ib)
    print("score:", score, "| shared:", [human(s) for s in shared])
