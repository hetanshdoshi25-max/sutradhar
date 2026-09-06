"""
SUTRADHAR - OPSEC exposure signal
---------------------------------
Where persona-reuse asks "do two aliases share an identifier?", OPSEC asks
"what has THIS alias accidentally leaked about itself?" - emails, phone
numbers, wallets, PGP keys, onion links, handles. Each leak is a thread an
investigator can pull; together they form an exposure profile with a risk
level. Operators with sloppy OPSEC are the ones who get caught.

Reuses the identifier extractor from persona_reuse and adds phone numbers.
"""

import re
from persona_reuse import PATTERNS as ID_PATTERNS, NICE

# phone: +country digits, a bare 10-digit, or xxx-xxx-xxxx style
PHONE_RE = re.compile(r"\+\d[\d\s-]{8,}\d|\b\d{3}[\s-]\d{3}[\s-]\d{4}\b|\b\d{10}\b")

# how dangerous each leak type is to the operator (0..1)
SEVERITY = {
    "email": 0.9, "phone": 0.9, "btc": 0.8, "eth": 0.8,
    "pgp": 0.55, "onion": 0.5, "handle": 0.35,
}


def exposure_profile(text):
    """Return the leaks found in one persona's text + an overall risk level."""
    items = []
    seen = set()

    def add(kind, value):
        key = (kind, value.lower())
        if key in seen:
            return
        seen.add(key)
        items.append({
            "type": kind,
            "label": NICE.get(kind, kind),
            "value": value,
            "severity": SEVERITY.get(kind, 0.4),
        })

    if text:
        for kind, rx in ID_PATTERNS.items():
            for m in rx.findall(text):
                add(kind, m)
        for m in PHONE_RE.findall(text):
            add("phone", m.strip())

    # overall risk: worst single leak dominates, more leaks add on top
    if items:
        worst = max(i["severity"] for i in items)
        score = min(1.0, worst + 0.05 * (len(items) - 1))
    else:
        score = 0.0

    level = ("Critical" if score >= 0.85 else "High" if score >= 0.6
             else "Medium" if score >= 0.35 else "Low" if score > 0 else "None")

    return {
        "items": sorted(items, key=lambda i: -i["severity"]),
        "score": round(score, 3),
        "level": level,
    }


if __name__ == "__main__":
    t = "grab it now!! hit me 9876543210 or vyprdeals@proton.me, pgp 0x1A2B3C4D"
    p = exposure_profile(t)
    print("risk:", p["level"], f"({p['score']})")
    for i in p["items"]:
        print(f"  [{i['label']}] {i['value']}  sev={i['severity']}")
