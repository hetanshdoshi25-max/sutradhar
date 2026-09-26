"""
SUTRADHAR - Temporal signal
---------------------------
A second, independent authorship signal based on WHEN a persona posts.

People are creatures of habit: they tend to be active in the same daily
window (their waking hours in their own timezone), no matter which username
they use. We turn each persona's posting hours into a 24-hour activity
histogram and compare two histograms. A high overlap is extra evidence that
two aliases are the same person - and the peak window hints at a timezone.

This signal is OPTIONAL: it only applies to personas that carry posting
times. Live-typed text (e.g. an audience volunteer) has none, so the system
falls back to stylometry alone for those.
"""

import numpy as np


def activity_vector(hours):
    """24-bin normalised histogram of posting hours (0-23)."""
    v = np.zeros(24)
    for h in hours:
        v[int(h) % 24] += 1
    total = v.sum()
    return v / total if total else v


def circadian_features(hours):
    """Higher-order rhythm descriptors beyond the raw histogram: how spread
    out, how peaked, and how nocturnal a persona's activity is. These are
    stable personal traits and add discriminative power to the raw overlap."""
    if not hours:
        return {"spread": 0.0, "peakedness": 0.0, "nocturnal": 0.0, "regularity": 0.0}
    v = activity_vector(hours)
    active_bins = sum(1 for x in v if x > 0)
    spread = active_bins / 24.0                       # how many hours-of-day used
    peakedness = float(v.max())                       # concentration in top hour
    nocturnal = float(sum(v[h] for h in list(range(0, 6)) + list(range(22, 24))))
    # regularity: inverse of hour-to-hour variability of the raw hours
    hrs = [int(h) % 24 for h in hours]
    mean_h = sum(hrs) / len(hrs)
    var = sum((h - mean_h) ** 2 for h in hrs) / len(hrs)
    regularity = 1.0 / (1.0 + var ** 0.5)
    return {"spread": round(spread, 3), "peakedness": round(peakedness, 3),
            "nocturnal": round(nocturnal, 3), "regularity": round(regularity, 3)}


def temporal_similarity(hours_a, hours_b):
    """Blend of (a) histogram overlap and (b) circadian-shape agreement -> 0..1."""
    a, b = activity_vector(hours_a), activity_vector(hours_b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    hist_sim = float(np.dot(a, b) / denom)
    # circadian-shape similarity
    fa, fb = circadian_features(hours_a), circadian_features(hours_b)
    keys = ["spread", "peakedness", "nocturnal", "regularity"]
    shape_dist = sum(abs(fa[k] - fb[k]) for k in keys) / len(keys)
    shape_sim = 1.0 - min(1.0, shape_dist)
    return round(0.75 * hist_sim + 0.25 * shape_sim, 4)


def peak_window(hours):
    """Best 5-hour active window, as a readable 'HH:00-HH:00' string.
    Handy as human-facing evidence ('both active 20:00-01:00')."""
    v = activity_vector(hours)
    if v.sum() == 0:
        return None
    best_start, best_sum = 0, -1.0
    for start in range(24):
        s = sum(v[(start + k) % 24] for k in range(5))
        if s > best_sum:
            best_sum, best_start = s, start
    end = (best_start + 5) % 24
    return f"{best_start:02d}:00-{end:02d}:00"


if __name__ == "__main__":
    # quick self-check
    evening_a = [20, 21, 22, 23, 20, 21, 22, 19, 23, 0]
    evening_b = [21, 22, 23, 20, 22, 21, 23, 0, 20, 22]
    daytime = [9, 10, 11, 12, 13, 14, 10, 11, 12, 15]
    print("same window :", round(temporal_similarity(evening_a, evening_b), 2),
          "| peaks", peak_window(evening_a), peak_window(evening_b))
    print("diff window :", round(temporal_similarity(evening_a, daytime), 2),
          "| peaks", peak_window(evening_a), peak_window(daytime))
