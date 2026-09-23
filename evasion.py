"""
SUTRADHAR - Evasion Confidence Meter (7th signal, meta-layer)
------------------------------------------------------------------
Every other signal asks "what did this persona leave behind?". This one
asks the inverse question: "how hard is this persona trying to leave
NOTHING behind?" - and treats professional-grade OPSEC discipline itself
as a signal, not an absence of one.

Three tells of deliberate anti-forensic behavior:

  1. Zero-identifier discipline - a persona with substantial text (enough
     words that an average user would likely slip at least one identifier)
     but literally zero emails/wallets/handles/PGP keys/onions found. Real
     casual actors leak *something* eventually; total silence at volume is
     itself unusual.

  2. Unnaturally uniform sentence structure - genuine human writing has
     "burstiness": sentence lengths vary a fair amount. Text edited to be
     deliberately neutral (or AI-smoothed to erase a personal style) tends
     to have abnormally LOW variance in sentence length - too consistent
     to be natural, unscripted writing.

  3. Scheduled-looking posting times - if hour-of-day data is available,
     posts clustered with near-zero spread (e.g. always the same hour)
     look automated/scheduled rather than a real person's organic,
     somewhat-irregular activity window.

None of these alone proves evasion - each is a soft tell. Combined into a
score, they flag "this actor is operating with unusual discipline" -
itself an investigative signal: professional/trained operators behave
differently from careless ones, and that distinction is worth surfacing.
"""

import re
import statistics as stats

from persona_reuse import extract_identifiers
from opsec import exposure_profile


def _sentence_lengths(text):
    sentences = [s.strip() for s in re.split(r"[.!?]+", text or "") if s.strip()]
    return [len(s.split()) for s in sentences]


def _uniformity_flag(text):
    lens = _sentence_lengths(text)
    if len(lens) < 3:
        return False, None
    mean = stats.mean(lens)
    if mean == 0:
        return False, None
    cv = stats.pstdev(lens) / mean  # coefficient of variation
    # real casual writing is bursty (cv typically > 0.35); low cv is suspicious
    return cv < 0.3, round(cv, 3)


def _timing_flag(hours):
    if not hours or len(hours) < 4:
        return False, None
    spread = stats.pstdev(hours)
    # near-zero spread across many posts looks scheduled, not organic
    return spread < 0.8, round(spread, 3)


def evasion_profile(text, hours=None):
    """Per-persona evasion assessment. Returns tells found + a 0..1 score
    + a human level (Low / Moderate / High / Professional)."""
    tells = []

    n_words = len((text or "").split())
    ids = extract_identifiers(text)
    if n_words >= 40 and len(ids) == 0:
        tells.append({
            "tell": "Zero-identifier discipline",
            "detail": f"{n_words} words of text with no leaked identifiers of any kind - "
                      f"unusual restraint versus typical persona baseline.",
        })

    uniform, cv = _uniformity_flag(text)
    if uniform:
        tells.append({
            "tell": "Unnaturally uniform sentence structure",
            "detail": f"Sentence-length variability (cv={cv}) is far below typical organic "
                      f"writing - consistent with deliberate neutralization or AI-smoothing.",
        })

    scheduled, spread = _timing_flag(hours)
    if scheduled:
        tells.append({
            "tell": "Scheduled-looking posting pattern",
            "detail": f"Posting hours cluster with almost no spread (std={spread}h) - "
                      f"more consistent with automation than organic behaviour.",
        })

    score = min(1.0, 0.4 * len(tells) + (0.15 if len(tells) >= 2 else 0))
    level = ("Professional" if score >= 0.75 else "High" if score >= 0.5
             else "Moderate" if score >= 0.25 else "Low")

    return {"tells": tells, "score": round(score, 3), "level": level}


if __name__ == "__main__":
    disciplined = (
        "The situation requires careful review. The evidence is not conclusive. "
        "Further analysis is needed. A decision will follow in due course. "
        "All parties should remain patient during this period. Updates will be provided."
    )
    casual = (
        "tbh idk what to make of this lol. the whole thing is kinda weird ngl, "
        "especially since nobody's said anything official yet!! anyway we'll see i guess"
    )
    for label, t in [("disciplined", disciplined), ("casual", casual)]:
        p = evasion_profile(t, hours=[14, 14, 14, 14, 14])
        print(f"{label}: level={p['level']} score={p['score']} tells={len(p['tells'])}")
        for tl in p["tells"]:
            print("   -", tl["tell"])
