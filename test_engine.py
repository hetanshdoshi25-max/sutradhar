"""Quick sanity test: does the engine score same-author pairs higher
than different-author pairs? Prints a similarity matrix + verdicts."""

from stylometry import StylometryEngine
from sample_personas import PERSONAS, GROUND_TRUTH

texts = [p["text"] for p in PERSONAS]
aliases = [p["alias"] for p in PERSONAS]

eng = StylometryEngine().fit(texts)
n = len(texts)

print("\nPairwise blended similarity (higher = more likely same author):\n")
header = "             " + "".join(f"{a[:9]:>11}" for a in aliases)
print(header)
for i in range(n):
    row = f"{aliases[i][:11]:<11} "
    for j in range(n):
        row += f"{eng.similarity(i, j)[0]:>11.2f}" if i != j else f"{'—':>11}"
    print(row)

print("\nStrongest links found (threshold 0.55):\n")
pairs = []
for i in range(n):
    for j in range(i + 1, n):
        score, groups = eng.similarity(i, j)
        pairs.append((score, i, j, groups))
pairs.sort(reverse=True)

for score, i, j, g in pairs:
    if score >= 0.55:
        same = "SAME AUTHOR" if GROUND_TRUTH[i] == GROUND_TRUTH[j] else "WRONG!"
        print(f"  {aliases[i]:<12} <-> {aliases[j]:<12}  {score:.2f}   [{same}]")
        print(f"      evidence  char-ngrams {g['char_ngrams']:.2f} | "
              f"function-words {g['function_words']:.2f} | "
              f"style {g['style_ratios']:.2f}")
