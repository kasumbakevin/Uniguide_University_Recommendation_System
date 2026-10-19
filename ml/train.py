"""Train programme category classifier and content-based recommender."""

import json
import os
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_recall_fscore_support)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.tree import DecisionTreeClassifier

from datapipeline import pipeline as dp_pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
MODELS_DIR = os.path.join(ROOT, "ml", "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def _latest_dir():
    d = dp_pipeline.latest_run_dir()
    if d:
        return d
    dirs = sorted([os.path.join(PROCESSED, n) for n in os.listdir(PROCESSED) if os.path.isdir(os.path.join(PROCESSED, n))])
    return dirs[-1] if dirs else None


def _load_csv(name):
    d = _latest_dir()
    if not d:
        raise FileNotFoundError("No processed data found. Run datapipeline.pipeline first.")
    path = os.path.join(d, name)
    return pd.read_csv(path)


def train_discipline_classifier(random_state=42):
    """Train multi-class classifier to predict NCHE Tier Discipline from programme text.

    Returns dict: best_model_name, metrics, model_path, metadata_path, classes.
    """
    df = _load_csv("uniguide_training_dataset.csv").dropna(subset=["discipline", "programme"]).copy()
    df["text"] = (df["programme"].astype(str) + " " + df["institution"].astype(str)).str.replace(r"\s+", " ", regex=True)
    df = df[df["discipline"].astype(str).str.strip() != ""]

    X = df[["text", "institution", "qualification_level", "institution_type"]].copy()
    X["institution"] = X["institution"].fillna("")
    X["qualification_level"] = X["qualification_level"].fillna("")
    X["institution_type"] = X["institution_type"].fillna("")
    y = df["discipline"].astype(str).str.strip()

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=random_state)
    X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.25, stratify=y_train, random_state=random_state)

    preprocessor = ColumnTransformer([
        ("tfidf", TfidfVectorizer(max_features=10000, ngram_range=(1, 2), stop_words="english"), "text"),
        ("inst", OneHotEncoder(handle_unknown="ignore"), ["institution"]),
        ("ql", OneHotEncoder(handle_unknown="ignore"), ["qualification_level"]),
        ("it", OneHotEncoder(handle_unknown="ignore"), ["institution_type"]),
    ])

    candidates = [
        ("logistic_regression", Pipeline([("pre", preprocessor), ("clf", LogisticRegression(max_iter=2000, random_state=random_state))])),
        ("decision_tree", Pipeline([("pre", preprocessor), ("clf", DecisionTreeClassifier(max_depth=40, random_state=random_state))])),
        ("random_forest", Pipeline([("pre", preprocessor), ("clf", RandomForestClassifier(n_estimators=200, max_depth=40, random_state=random_state, n_jobs=-1))])),
    ]

    best_name = None
    best_macro_f1 = -1
    results = {}
    for name, pipeline in candidates:
        pipeline.fit(X_train, y_train)
        y_pred_val = pipeline.predict(X_val)
        macro_f1 = f1_score(y_pred_val, y_val, average="macro")
        acc = accuracy_score(y_pred_val, y_val)
        results[name] = {"macro_f1": float(macro_f1), "accuracy": float(acc)}
        if macro_f1 > best_macro_f1:
            best_macro_f1 = macro_f1
            best_name = name

    best_pipe = next(p for n, p in candidates if n == best_name)
    best_pipe.fit(X_train, y_train)
    y_pred_test = best_pipe.predict(X_test)
    report = classification_report(y_test, y_pred_test, output_dict=True, zero_division=0)
    conf = confusion_matrix(y_test, y_pred_test)
    classes = list(best_pipe.classes_)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_path = os.path.join(MODELS_DIR, "programme_discipline_{0}.joblib".format(ts))
    meta_path = os.path.join(MODELS_DIR, "programme_discipline_{0}.meta.json".format(ts))
    joblib.dump(best_pipe, model_path)

    metadata = {
        "model_name": "programme_discipline_classifier",
        "file": "programme_discipline_{0}.joblib".format(ts),
        "algorithm": best_name,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "classes": classes,
        "num_classes": len(classes),
        "training_rows": int(len(X_train)),
        "validation_rows": int(len(X_val)),
        "test_rows": int(len(X_test)),
        "macro_f1": float(f1_score(y_pred_test, y_test, average="macro")),
        "accuracy": float(accuracy_score(y_pred_test, y_test)),
        "classification_report": report,
        "confusion_matrix": conf.tolist(),
        "features": ["text", "institution", "qualification_level", "institution_type"],
        "notes": "Multi-class classification trained on NCHE Tier Discipline labels. Content-based only; no admission outcome labels used.",
    }
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    return {
        "best_model_name": best_name,
        "results": results,
        "model_path": model_path,
        "metadata_path": meta_path,
        "classes": classes,
        "metrics": {"macro_f1": metadata["macro_f1"], "accuracy": metadata["accuracy"]},
        "report": report,
    }


def _build_corpus():
    corpus_rows = []
    try:
        df = _load_csv("uniguide_nche_register_clean.csv")
        for _, r in df.iterrows():
            txt = " ".join([str(r.get("programme", "")), str(r.get("institution", "")),
                            str(r.get("discipline", "")), str(r.get("qualification_level", ""))])
            corpus_rows.append({"text": re_clean(txt), "programme": r.get("programme"), "institution": r.get("institution")})
    except Exception:  # noqa: BLE001
        pass
    try:
        df = _load_csv("uniguide_programmes_clean.csv")
        for _, r in df.iterrows():
            txt = " ".join([str(r.get("programme", "")), str(r.get("university", "")), str(r.get("level", ""))])
            corpus_rows.append({"text": re_clean(txt), "programme": r.get("programme"), "institution": r.get("university")})
    except Exception:  # noqa: BLE001
        pass
    return pd.DataFrame(corpus_rows).drop_duplicates(subset=["text"]).reset_index(drop=True) if len(corpus_rows) else pd.DataFrame(columns=["text","programme","institution"])


def re_clean(s):
    import re
    s = str(s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def train_content_recommender(random_state=42):
    corpus = _build_corpus()
    vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1, 2), stop_words="english")
    X = vectorizer.fit_transform(corpus["text"]) if len(corpus) else vectorizer.fit_transform(["university programme"])
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_path = os.path.join(MODELS_DIR, "content_recommender_{0}.joblib".format(ts))
    meta_path = os.path.join(MODELS_DIR, "content_recommender_{0}.meta.json".format(ts))

    joblib.dump({"vectorizer": vectorizer, "matrix": X, "corpus": corpus.reset_index(drop=True)}, model_path)

    # Proxy evaluation: career -> programme relevance comes from careers.csv.
    # This is a WEAK, self-referential signal (the same file is not a held-out
    # ground truth), so results are reported with that caveat and must not be
    # read as evidence of admission quality.
    eval_results = {"precision_at_5": None, "recall_at_5": None, "ndcg_at_5": None,
                    "careers_evaluated": 0, "caveat": "proxy labels from careers.csv"}
    try:
        careers = _load_csv("uniguide_careers_clean.csv")
        from sklearn.metrics.pairwise import cosine_similarity

        queries, relevants = [], []
        corpus_names = corpus["programme"].astype(str).str.lower().tolist()
        for _, r in careers.iterrows():
            tokens = [t.strip().lower() for t in str(r.get("programmes", "")).replace(";", ",").split(",") if t.strip()]
            relevant = {i for i, name in enumerate(corpus_names) if any(tok in name for tok in tokens)}
            if not relevant:
                continue
            query = re_clean(" ".join([str(r.get("career", "")), str(r.get("required_subjects", "")),
                                       str(r.get("skills", "")), str(r.get("description", ""))]))
            queries.append(query)
            relevants.append(relevant)

        if queries:
            qv = vectorizer.transform(queries)
            sims = cosine_similarity(qv, X)
            precisions, recalls, ndcgs = [], [], []
            for i, relevant in enumerate(relevants):
                order = np.argsort(sims[i])[::-1][:5]
                hits = [1 if idx in relevant else 0 for idx in order]
                precisions.append(sum(hits) / 5.0)
                recalls.append(sum(hits) / float(len(relevant)))
                dcg = sum(h / np.log2(rank + 2) for rank, h in enumerate(hits))
                idcg = sum(1 / np.log2(rank + 2) for rank in range(min(len(relevant), 5)))
                ndcgs.append(dcg / idcg if idcg else 0.0)
            eval_results.update({
                "precision_at_5": round(float(np.mean(precisions)), 4),
                "recall_at_5": round(float(np.mean(recalls)), 4),
                "ndcg_at_5": round(float(np.mean(ndcgs)), 4),
                "careers_evaluated": len(queries),
            })
    except Exception:  # noqa: BLE001
        pass

    metadata = {
        "model_name": "content_based_recommender",
        "file": "content_recommender_{0}.joblib".format(ts),
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "corpus_rows": int(len(corpus)),
        "vectorizer_features": int(vectorizer.max_features or len(vectorizer.vocabulary_)),
        "metrics_proxy": eval_results,
        "notes": "TF-IDF cosine similarity over programme+institution text. Proxy metrics against career text queries (P@5/R@5 rough). No admission outcome labels used.",
    }
    with open(meta_path, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)

    return {"model_path": model_path, "metadata_path": meta_path, "metrics": eval_results, "corpus_rows": len(corpus)}


def train_all():
    return {
        "discipline_classifier": train_discipline_classifier(),
        "content_recommender": train_content_recommender(),
    }


if __name__ == "__main__":
    res = train_all()
    print(json.dumps({k: v.get("metrics") for k, v in res.items()}, indent=2))
