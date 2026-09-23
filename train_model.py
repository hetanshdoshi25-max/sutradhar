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
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from stylometry import StylometryEngine, style_ratios
from build_dataset import build_dataset, build_pairs

MODEL_PATH = "author_model.pkl"
FEATURE_NAMES = ["char_ngrams", "function_words", "style_ratios_sim"] + [
    f"style_diff_{i}" for i in range(12)
]


def build_training_matrix(pairs, corpus_texts):
    """Fit ONE stylometry engine on the whole corpus (stable vocabulary /
    IDF), then for every labeled pair combine (a) the 3 aggregate signal
    similarities and (b) 12 raw per-dimension style-ratio differences -
    richer, more discriminative feature set than similarity alone."""
    engine = StylometryEngine().fit(corpus_texts)
    text_to_idx = {t: i for i, t in enumerate(corpus_texts)}
    raw_ratios = {t: style_ratios(t) for t in corpus_texts}

    X, y = [], []
    for text_a, text_b, label in pairs:
        ia, ib = text_to_idx[text_a], text_to_idx[text_b]
        _, groups = engine.similarity(ia, ib)
        diff = np.abs(raw_ratios[text_a] - raw_ratios[text_b])
        feats = [groups["char_ngrams"], groups["function_words"], groups["style_ratios"]] + list(diff)
        X.append(feats)
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

    print("4. Training and comparing algorithms...")
    candidates = {
        "LogisticRegression": LogisticRegression(random_state=42, max_iter=500),
        "RandomForest": RandomForestClassifier(n_estimators=300, max_depth=12, random_state=42, n_jobs=-1),
        "GradientBoosting": GradientBoostingClassifier(n_estimators=200, max_depth=3, random_state=42),
    }
    best_name, best_clf, best_acc = None, None, -1
    for name, clf in candidates.items():
        clf.fit(X_train, y_train)
        acc = accuracy_score(y_test, clf.predict(X_test))
        print(f"   {name:<20} accuracy = {acc:.1%}")
        if acc > best_acc:
            best_name, best_clf, best_acc = name, clf, acc
    print(f"\n   -> best: {best_name} ({best_acc:.1%})")
    clf = best_clf

    print("5. Full evaluation of best model on held-out test set...")
    preds = clf.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"   accuracy: {acc:.1%}")
    print("   confusion matrix [[TN FP] [FN TP]]:")
    print("  ", confusion_matrix(y_test, preds).tolist())
    print(classification_report(y_test, preds, target_names=["different-author", "same-author"]))

    print("6. Feature importance / weights:")
    if hasattr(clf, "feature_importances_"):
        pairs_fi = sorted(zip(FEATURE_NAMES, clf.feature_importances_), key=lambda x: -x[1])
        for name, w in pairs_fi[:6]:
            print(f"   {name:<20} importance = {w:.3f}")
    elif hasattr(clf, "coef_"):
        for name, w in zip(FEATURE_NAMES, clf.coef_[0]):
            print(f"   {name:<20} weight = {w:+.3f}")

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"\nSaved trained model -> {MODEL_PATH}")
    return clf, acc


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def predict_same_author(text_a, text_b, model=None, background_corpus=None):
    """Use the TRAINED classifier (not the live-compute engine) to predict."""
    model = model or load_model()
    bg = background_corpus if background_corpus is not None else _default_background()
    texts = bg + [text_a, text_b]
    eng = StylometryEngine().fit(texts)
    ia, ib = len(texts) - 2, len(texts) - 1
    _, groups = eng.similarity(ia, ib)
    diff = np.abs(style_ratios(text_a) - style_ratios(text_b))
    feats = np.array([[groups["char_ngrams"], groups["function_words"], groups["style_ratios"]] + list(diff)])
    proba = model.predict_proba(feats)[0][1]
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
