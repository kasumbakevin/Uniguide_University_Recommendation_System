"""Load trained models and produce predictions / rankings."""

import json
import os
from glob import glob

import joblib
import numpy as np

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")


def _latest_joblib(prefix):
    files = sorted(glob(os.path.join(MODELS_DIR, prefix + "_*.joblib")))
    return files[-1] if files else None


def _meta_for(joblib_path):
    meta = os.path.splitext(joblib_path)[0] + ".meta.json"
    if os.path.exists(meta):
        with open(meta, encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def list_models():
    models = []
    for path in sorted(glob(os.path.join(MODELS_DIR, "*.joblib"))):
        meta = _meta_for(path)
        models.append({
            "name": meta.get("model_name", os.path.basename(path)),
            "file": os.path.basename(path),
            "algorithm": meta.get("algorithm", "content-based"),
            "trained_at": meta.get("trained_at", ""),
            "metrics": {k: meta.get(k) for k in ("accuracy", "macro_f1", "precision_at_5", "recall_at_5", "ndcg_at_5") if meta.get(k) is not None},
            "notes": meta.get("notes", ""),
        })
    return models


def load_discipline_classifier():
    path = _latest_joblib("programme_discipline")
    if not path:
        return None, {}
    return joblib.load(path), {**_meta_for(path), "path": path}


def predict_discipline(programme, institution="", qualification_level="", institution_type=""):
    model, meta = load_discipline_classifier()
    if model is None:
        return {"error": "No discipline classifier has been trained yet."}
    import pandas as pd

    row = pd.DataFrame([{
        "text": "{0} {1}".format(programme, institution).strip(),
        "institution": institution or "",
        "qualification_level": qualification_level or "",
        "institution_type": institution_type or "",
    }])
    label = model.predict(row)[0]
    result = {"predicted_discipline": label, "model": meta.get("algorithm", ""),
              "trained_at": meta.get("trained_at", "")}
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(row)[0]
        classes = list(model.classes_)
        ranked = sorted(zip(classes, proba), key=lambda x: -x[1])[:5]
        result["top_probabilities"] = [{"discipline": c, "probability": round(float(p), 4)} for c, p in ranked]
    return result


def load_content_recommender():
    path = _latest_joblib("content_recommender")
    if not path:
        return None, {}
    return joblib.load(path), {**_meta_for(path), "path": path}


def recommend_similar(text, top_k=10):
    bundle, meta = load_content_recommender()
    if bundle is None:
        return {"error": "No content recommender has been trained yet."}
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = bundle["vectorizer"]
    matrix = bundle["matrix"]
    corpus = bundle["corpus"]
    query = vectorizer.transform([text])
    sims = cosine_similarity(query, matrix)[0]
    order = np.argsort(sims)[::-1][:top_k]
    items = []
    for idx in order:
        row = corpus.iloc[idx]
        items.append({
            "programme": row.get("programme", ""),
            "institution": row.get("institution", ""),
            "score": round(float(sims[idx]), 4),
        })
    return {"items": items, "model": "content_based_recommender", "trained_at": meta.get("trained_at", "")}
