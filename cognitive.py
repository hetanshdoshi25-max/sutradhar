"""
SUTRADHAR - Cognitive Fingerprint (behavioural reasoning signature)
----------------------------------------------------------------------
The problem statement asks for "behavioural profiling ... to link rebranded
or migrated personas". This module implements exactly that, and targets the
single hardest evasion technique against every existing attribution tool:
an operator running their text through an AI rewriter.

Surface stylometry (word choice, punctuation) is defeated by AI rephrasing.
This signal instead fingerprints HOW a person REASONS, not which words they
pick - and reasoning structure is far more stable under paraphrase, because
a rewriter changes wording while preserving the author's underlying logic,
argument order, and decision framing.

Seven behavioural dimensions, each a rate normalized by length:

  1. hedging          - tentative language (maybe, probably, might, seems)
  2. certainty        - absolute language (always, never, definitely, clearly)
  3. causal_density   - explicit reasoning links (because, therefore, since)
  4. contrast         - argumentative pivots (but, however, although, yet)
  5. risk_frame       - loss/threat framing (risk, fail, avoid, careful)
  6. opportunity_frame- gain/upside framing (opportunity, benefit, could, gain)
  7. deductive_lean   - conclusion-before-evidence vs evidence-before-conclusion

Together they form a 7-D behavioural vector; two personas are compared by
cosine similarity in that space. It is offered as corroborating behavioural
evidence, and is explicitly labelled as more paraphrase-robust than surface
stylometry - not as infallible.
"""

import re
import math

HEDGE = ["maybe", "probably", "might", "perhaps", "seems", "i think", "i guess",
         "sort of", "kind of", "possibly", "not sure", "could be", "i feel"]
CERTAINTY = ["always", "never", "definitely", "certainly", "clearly", "obviously",
             "absolutely", "guaranteed", "without doubt", "for sure", "no question"]
CAUSAL = ["because", "therefore", "thus", "hence", "since", "so that", "as a result",
          "consequently", "due to", "leads to", "that's why", "which means"]
CONTRAST = ["but", "however", "although", "though", "yet", "whereas", "on the other hand",
            "even so", "nonetheless", "despite", "still"]
RISK = ["risk", "fail", "danger", "careful", "avoid", "worried", "threat", "loss",
        "scam", "sketchy", "caution", "problem", "trap", "burned"]
OPPORTUNITY = ["opportunity", "benefit", "gain", "profit", "potential", "upside",
               "worth", "advantage", "win", "great deal", "chance"]

CONCLUSION_MARKERS = ["therefore", "so ", "thus", "in conclusion", "overall", "hence",
                      "that's why", "which means", "the point is"]
EVIDENCE_MARKERS = ["because", "since", "given that", "the data", "evidence", "for example",
                    "for instance", "as shown", "considering"]

DIMENSIONS = ["hedging", "certainty", "causal_density", "contrast",
              "risk_frame", "opportunity_frame", "deductive_lean"]


def _count(text, terms):
    t = " " + text.lower() + " "
    return sum(t.count(" " + w) if " " not in w else t.count(w) for w in terms)


def _sentences(text):
    return [s for s in re.split(r"[.!?]+", text or "") if s.strip()]


def cognitive_vector(text):
    """Return the 7-D behavioural reasoning vector (rates per 100 words)."""
    words = max(1, len((text or "").split()))
    scale = 100.0 / words

    hedging = _count(text, HEDGE) * scale
    certainty = _count(text, CERTAINTY) * scale
    causal = _count(text, CAUSAL) * scale
    contrast = _count(text, CONTRAST) * scale
    risk = _count(text, RISK) * scale
    opp = _count(text, OPPORTUNITY) * scale

    # deductive lean: for each sentence, does a conclusion marker appear
    # before an evidence marker? deductive (conclusion-first) => +1.
    ded, total = 0, 0
    for s in _sentences(text):
        sl = s.lower()
        c_pos = min([sl.find(m) for m in CONCLUSION_MARKERS if m in sl] or [999])
        e_pos = min([sl.find(m) for m in EVIDENCE_MARKERS if m in sl] or [999])
        if c_pos == 999 and e_pos == 999:
            continue
        total += 1
        if c_pos < e_pos:
            ded += 1
    deductive_lean = (ded / total) if total else 0.5   # 0.5 = neutral/unknown

    return [round(hedging, 3), round(certainty, 3), round(causal, 3),
            round(contrast, 3), round(risk, 3), round(opp, 3), round(deductive_lean, 3)]


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def cognitive_similarity(text_a, text_b):
    """Behavioural-reasoning similarity between two texts (0..1)."""
    va, vb = cognitive_vector(text_a), cognitive_vector(text_b)
    return round(_cosine(va, vb), 3)


def cognitive_profile(text):
    """Human-readable behavioural profile of one persona, for display."""
    v = cognitive_vector(text)
    d = dict(zip(DIMENSIONS, v))
    traits = []
    if d["hedging"] > d["certainty"] + 0.5:
        traits.append("hedges heavily (tentative reasoner)")
    elif d["certainty"] > d["hedging"] + 0.5:
        traits.append("speaks in absolutes (assertive reasoner)")
    if d["causal_density"] > 2:
        traits.append("high causal-reasoning density")
    if d["risk_frame"] > d["opportunity_frame"] + 0.5:
        traits.append("risk-framed / loss-averse")
    elif d["opportunity_frame"] > d["risk_frame"] + 0.5:
        traits.append("opportunity-framed / gain-seeking")
    if d["deductive_lean"] > 0.6:
        traits.append("deductive (conclusion-first)")
    elif d["deductive_lean"] < 0.4:
        traits.append("inductive (evidence-first)")
    return {"vector": v, "dimensions": d,
            "traits": traits or ["neutral / insufficient signal"]}


if __name__ == "__main__":
    # two texts, same author's reasoning style, different surface wording
    a = ("tbh this seller looks kinda sketchy, probably a scam. i think we should "
         "be careful because the reviews are fake, so avoid it for now.")
    b = ("Honestly I'd be cautious with this vendor - it might be fraudulent. "
         "Since the feedback appears fabricated, I believe the prudent move is to steer clear.")
    c = ("YO this drop is FIRE, guaranteed profit!! definitely cop it now, huge "
         "opportunity, you will absolutely win big, no question!!")

    print("A vs B (same reasoning, B is 'AI-rephrased'):", cognitive_similarity(a, b))
    print("A vs C (different reasoner):                  ", cognitive_similarity(a, c))
    print("\nProfile A:", cognitive_profile(a)["traits"])
    print("Profile C:", cognitive_profile(c)["traits"])
