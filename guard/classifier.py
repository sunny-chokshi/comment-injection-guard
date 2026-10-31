"""Small learned detector: TF-IDF (character and word n-grams) plus logistic regression.

Trained only on data/train.jsonl, which data/build_dataset.py writes from
public sources and from templates in this repo. The threshold is picked on
data/val.jsonl to hold clean false positives at or under TARGET_FPR.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .rules import normalize

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.environ.get("GUARD_MODEL_PATH", ROOT / "models" / "clf.joblib"))
TARGET_FPR = 0.01
MIN_WORDS = 3  # shorter comments are left to the regex rules


def _load(path: Path) -> tuple[list[str], np.ndarray]:
    rows = [json.loads(l) for l in path.open() if l.strip()]
    return [normalize(r["text"]) for r in rows], np.array([r["label"] for r in rows])


def build() -> Pipeline:
    feats = FeatureUnion([
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)),
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
    ])
    return Pipeline([("f", feats), ("lr", LogisticRegression(C=4.0, class_weight="balanced", max_iter=2000))])


def pick_threshold(scores: np.ndarray, labels: np.ndarray, target_fpr: float = TARGET_FPR) -> float:
    neg = np.sort(scores[labels == 0])
    if len(neg) == 0:
        return 0.5
    # Smallest threshold whose clean false positive rate is <= target.
    k = int(np.floor(target_fpr * len(neg)))
    cut = neg[-(k + 1)] if k + 1 <= len(neg) else neg[0]
    return float(min(max(cut + 1e-6, 0.05), 0.99))


def _masked(model, texts: list[str]) -> np.ndarray:
    """Probabilities with short comments zeroed, matching Detector.scores."""
    p = model.predict_proba(texts)[:, 1]
    p[np.array([len(t.split()) < MIN_WORDS for t in texts])] = 0.0
    return p


def train(data_dir: Path = ROOT / "data", out: Path = MODEL_PATH) -> dict:
    Xtr, ytr = _load(data_dir / "train.jsonl")
    Xva, yva = _load(data_dir / "val.jsonl")
    model = build().fit(Xtr, ytr)
    dev = data_dir / "derived" / "primevul_dev_comments.jsonl"
    fixed = data_dir / "threshold.json"
    if dev.exists():
        # Add out-of-domain C comments (PrimeVul dev projects) to the threshold pick, then record it
        # so builds without PrimeVul (CI, Docker) reproduce the same operating point.
        Xd, yd = _load(dev)
        thr = pick_threshold(_masked(model, Xva + Xd), np.concatenate([yva, yd]))
        fixed.write_text(json.dumps({"threshold": thr, "picked_on": "val + primevul_dev", "target_fpr": TARGET_FPR}))
    elif fixed.exists():
        thr = json.loads(fixed.read_text())["threshold"]
    else:
        thr = pick_threshold(_masked(model, Xva), yva)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "threshold": thr}, out)
    return {"threshold": thr, "n_train": len(ytr), "n_val": len(yva)}


class Detector:
    def __init__(self, path: Path = MODEL_PATH):
        blob = joblib.load(path)
        self.model, self.threshold = blob["model"], blob["threshold"]

    def scores(self, texts: list[str]) -> list[float]:
        if not texts:
            return []
        norm = [normalize(t) for t in texts]
        p = self.model.predict_proba(norm)[:, 1]
        return [float(s) if len(t.split()) >= MIN_WORDS else 0.0 for s, t in zip(p, norm)]


if __name__ == "__main__":
    print(train())
