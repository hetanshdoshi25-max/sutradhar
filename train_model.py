"""
SUTRADHAR - Trained ML classifier (authorship verification)
-------------------------------------------------------------
Supervised counterpart to the unsupervised stylometry engine. Where
stylometry.py computes a live similarity score with no training step, THIS
module trains an actual classifier on a labeled dataset and saves the
learned model to disk - i.e. it answers "what algorithm, what dataset,
what training" directly.

Pipeline:
  1. Load the labeled pairs (text_a, text_b, same_author) from build_dataset.py
  2. For each pair, engineer a feature vector describing HOW SIMILAR the two
     texts are (char n-gram overlap, function-word overlap, style-ratio
     distance, etc.) - reusing stylometry.py's feature groups.
  3. Split into train/test sets.
  4. Train a Logistic Regression classifier: same author (1) or not (0).
  5. Evaluate accuracy on the held-out test set.
  6. Save the trained model + vectorizers to disk (model.pkl) so it can be
     loaded and reused without retraining - this IS the "trained model".

Algorithm: Logistic Regression (scikit-learn) - chosen because its learned
coefficients are directly interpretable (which features matter, and by how
much), which matters for forensic/courtroom explainability.
"""

import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from stylometry import StylometryEngine
from build_dataset import build_dataset, build_pairs

MODEL_PATH = "author_model.pkl"


def pair_features(engine, text_a, text_b):
    """Read off the ALREADY-FITTED engine's 3 group similarities for texts
    at positions ia, ib - THIS is the feature vector the classifier learns
    from. (Caller must fit `engine` on the full corpus first - fitting a
    TF-IDF vectorizer on just 2 documents gives unstable, noisy IDF weights.)
    """
    raise NotImplementedError  # replaced by build_training_matrix below


def build_training_matrix(pairs, corpus_texts):
    """Fit ONE stylometry engine on the whole corpus (stable vocabulary /
    IDF), then for every labeled pair look up their precomputed vectors and
    compute similarity - this is the standard, stable way to do it."""
    engine = StylometryEngine().fit(corpus_texts)
    text_to_idx = {t: i for i, t in enumerate(corpus_texts)}

    X, y = [], []
    for text_a, text_b, label in pairs:
        ia, ib = text_to_idx[text_a], text_to_idx[text_b]
        _, groups = engine.similarity(ia, ib)
        X.append([groups["char_ngrams"], groups["function_words"], groups["style_ratios"]])
        y.append(label)
    return np.array(X), np.array(y), engine


def train():
    print("1. Building labeled dataset...")
    corpus = build_dataset(samples_per_author=100)
    pairs = build_pairs(corpus)
    corpus_texts = [c["text"] for c in corpus]
    print(f"   {len(pairs)} labeled pairs ({sum(p[2] for p in pairs)} same-author, "
          f"{len(pairs)-sum(p[2] for p in pairs)} different-author)")

    print("2. Engineering features (char n-grams, function words, style ratios)...")
    X, y, _ = build_training_matrix(pairs, corpus_texts)

    print("3. Splitting train/test (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"   train: {len(X_train)} pairs | test: {len(X_test)} pairs")

    print("4. Training Logistic Regression classifier...")
    clf = LogisticRegression(random_state=42)
    clf.fit(X_train, y_train)

    print("5. Evaluating on held-out test set...")
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"   accuracy: {acc:.1%}")
    print("   confusion matrix [[TN FP] [FN TP]]:")
    print("  ", confusion_matrix(y_test, preds).tolist())
    print(classification_report(y_test, preds, target_names=["different-author", "same-author"]))

    print("6. Learned feature weights (coefficients):")
    for name, w in zip(["char_ngrams", "function_words", "style_ratios"], clf.coef_[0]):
        print(f"   {name:<16} weight = {w:+.3f}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"\nSaved trained model -> {MODEL_PATH}")
    return clf, acc


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_same_author(text_a, text_b, model=None, background_corpus=None):
    """Use the TRAINED classifier (not the live-compute engine) to predict.
    We fit a fresh stylometry engine on [background_corpus + the 2 new
    texts] so the vectorizer has a stable vocabulary to score against,
    exactly like at training time."""
    model = model or load_model()
    bg = background_corpus if background_corpus is not None else _default_background()
    texts = bg + [text_a, text_b]
    eng = StylometryEngine().fit(texts)
    ia, ib = len(texts) - 2, len(texts) - 1
    _, groups = eng.similarity(ia, ib)
    feats = np.array([[groups["char_ngrams"], groups["function_words"], groups["style_ratios"]]])
    proba = model.predict_proba(feats)[0][1]   # P(same author)
    return bool(model.predict(feats)[0]), round(float(proba), 3)


def _default_background():
    """A small fixed background corpus (reused so predictions are stable
    across calls) - ships with the trained model."""
    corpus = build_dataset(samples_per_author=4)
    return [c["text"] for c in corpus]


if __name__ == "__main__":
    clf, acc = train()

    print("\n--- sanity check on new, unseen text (same format as training) ---")
    from build_dataset import make_sample
    import random
    rng = random.Random(99)
    a = make_sample("A_casual", rng)
    b = make_sample("A_casual", rng)
    c = make_sample("B_formal", rng)
    same_ab, p_ab = predict_same_author(a, b, clf)
    same_ac, p_ac = predict_same_author(a, c, clf)
    print(f"  A: {a}")
    print(f"  B: {b}")
    print(f"  C: {c}")
    print(f"\n  A vs B (both A_casual style) -> same_author={same_ab}, P={p_ab}")
    print(f"  A vs C (casual vs formal)     -> same_author={same_ac}, P={p_ac}")
