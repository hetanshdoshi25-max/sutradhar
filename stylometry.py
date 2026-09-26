"""
SUTRADHAR - Stylometry engine
------------------------------
Turns a piece of writing into a numeric "fingerprint" and measures how
similar two fingerprints are. High similarity => likely the same author,
even across different usernames / sites.

We use THREE explainable feature groups so we can show a judge *why* two
personas matched, not just a black-box score:

  1. Character n-grams  -> spelling, spacing and punctuation habits
  2. Function words     -> unconscious use of common words (the, and, just...)
  3. Style ratios       -> punctuation rate, word/sentence length, caps, etc.

Final similarity = weighted blend of the three groups' cosine similarities.
"""

import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# A small, fixed list of very common English "function words". Their RATE of
# use is a strong authorship signal because writers use them unconsciously.
FUNCTION_WORDS = [
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "as", "at", "by", "from", "up", "about", "into", "over", "after",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "can", "could", "should", "may",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "them",
    "my", "your", "his", "its", "our", "their", "this", "that", "these",
    "those", "not", "no", "so", "just", "very", "really", "actually", "basically",
    "however", "though", "because", "while", "then", "than", "also", "too",
    "some", "any", "all", "more", "most", "such", "only", "even", "still",
    "here", "there", "when", "where", "what", "which", "who", "how", "why",
    "get", "got", "make", "like", "want", "need", "know", "think", "gonna",
    "yeah", "yep", "nah", "lol", "tbh", "ngl", "imo", "idk", "btw", "fr",
]


def style_ratios(text: str) -> np.ndarray:
    """Group 3: hand-crafted style ratios and lexical-richness measures.
    Each is normalised so text length doesn't dominate. Explainable, and
    collectively a strong authorship signal."""
    n_chars = max(len(text), 1)
    words = re.findall(r"[A-Za-z']+", text)
    n_words = max(len(words), 1)
    lower_words = [w.lower() for w in words]
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    n_sent = max(len(sentences), 1)
    word_lens = [len(w) for w in words]

    def rate(pattern):
        return len(re.findall(pattern, text)) / n_chars

    avg_word_len = sum(word_lens) / n_words
    avg_sent_len = n_words / n_sent
    # sentence-length variability (burstiness) — very personal
    sent_word_counts = [len(re.findall(r"[A-Za-z']+", s)) for s in sentences] or [0]
    mean_sc = sum(sent_word_counts) / len(sent_word_counts)
    sent_len_var = (sum((x - mean_sc) ** 2 for x in sent_word_counts) / len(sent_word_counts)) ** 0.5
    sent_len_cv = sent_len_var / mean_sc if mean_sc else 0

    # lexical richness
    vocab = set(lower_words)
    type_token = len(vocab) / n_words
    freq = {}
    for w in lower_words:
        freq[w] = freq.get(w, 0) + 1
    hapax = sum(1 for w, c in freq.items() if c == 1) / n_words   # once-only words
    dis = sum(1 for w, c in freq.items() if c == 2) / n_words     # twice-only words

    # word-length distribution buckets (share of short/medium/long words)
    short_w = sum(1 for l in word_lens if l <= 3) / n_words
    med_w = sum(1 for l in word_lens if 4 <= l <= 6) / n_words
    long_w = sum(1 for l in word_lens if l >= 7) / n_words

    uppercase_rate = sum(1 for c in text if c.isupper()) / n_chars
    digit_rate = sum(1 for c in text if c.isdigit()) / n_chars
    # repeated-punctuation habit (!!, ..., ??) — a strong personal tell
    emphatic = len(re.findall(r"([!?.])\1{1,}", text)) / n_sent

    return np.array([
        rate(r","),      # comma rate
        rate(r"\."),     # period rate
        rate(r"[!?]"),   # exclaim/question rate
        rate(r"[;:]"),   # semicolon/colon rate
        rate(r"'"),      # apostrophe rate
        rate(r"-"),      # dash/hyphen rate
        rate(r"\s"),     # whitespace rate (spacing habit)
        avg_word_len / 10.0,
        avg_sent_len / 30.0,
        sent_len_cv,             # sentence-length variability
        type_token,              # vocab richness
        hapax,                   # hapax legomena ratio
        dis,                     # dis legomena ratio
        short_w, med_w, long_w,  # word-length distribution
        uppercase_rate,
        digit_rate,
        emphatic,                # repeated-punctuation habit
    ], dtype=float)


class StylometryEngine:
    """Fit once on a set of documents, then compare any two of them.

    We fit the vectorisers across ALL documents together so every text is
    described in the same feature space (required for a fair comparison)."""

    def __init__(self, w_char=0.5, w_func=0.3, w_style=0.2):
        # weights for blending the three groups (must sum to 1)
        self.w_char, self.w_func, self.w_style = w_char, w_func, w_style

        # Group 1: character n-grams (2-3 chars). 'char_wb' keeps word
        # boundaries, capturing how someone starts/ends words and spaces.
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 4), min_df=1, lowercase=True, sublinear_tf=True
        )
        # Group 2: function-word rates, as a fixed vocabulary count vectoriser.
        self.func_vec = TfidfVectorizer(
            vocabulary=FUNCTION_WORDS, lowercase=True, token_pattern=r"[A-Za-z']+"
        )

    def fit(self, texts):
        self.texts = list(texts)
        self.char_m = self.char_vec.fit_transform(self.texts)   # sparse matrix
        self.func_m = self.func_vec.fit_transform(self.texts)
        # style ratios -> normalise each column to 0..1 range across docs
        raw = np.vstack([style_ratios(t) for t in self.texts])
        col_max = raw.max(axis=0)
        col_max[col_max == 0] = 1.0
        self.style_m = raw / col_max
        return self

    def group_scores(self, i, j):
        """Cosine similarity per feature group between doc i and doc j."""
        c = float(cosine_similarity(self.char_m[i], self.char_m[j])[0, 0])
        f = float(cosine_similarity(self.func_m[i], self.func_m[j])[0, 0])
        # style: cosine on the small dense vectors
        a, b = self.style_m[i], self.style_m[j]
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
        s = float(np.dot(a, b) / denom)
        return {"char_ngrams": c, "function_words": f, "style_ratios": s}

    def similarity(self, i, j):
        """Blended 0..1 similarity + the per-group breakdown (the evidence)."""
        g = self.group_scores(i, j)
        blended = (self.w_char * g["char_ngrams"]
                   + self.w_func * g["function_words"]
                   + self.w_style * g["style_ratios"])
        return blended, g
