# Data Engineering & Machine Learning Pipeline

This document describes the data pipeline and the machine-learning components added to
UniGuide Uganda, how to run them, and what their real measured results are.

## 1. Scope

The pipeline ingests the project's mixed source material (CSV, Excel and PDF), cleans and
validates it, produces a merged catalogue plus a training dataset, and trains two models:

1. **Programme-discipline classifier** — a supervised multi-class text classifier that predicts
   the NCHE *Tier Discipline* of a programme from its name and metadata.
2. **Content-based recommender** — TF-IDF cosine similarity over programme + institution text,
   used to surface similar programmes.

No admission-success model is trained, because the source data contains **no student outcome /
admission labels**. Inventing such labels would be fabrication, so this is documented as a
limitation rather than implemented.

## 2. Source data (read-only)

| Location | Content |
| --- | --- |
| `data/*.csv` | Seed catalogue: `universities.csv`, `programmes.csv`, `careers.csv`, cut-off and fee CSVs. |
| `data/Unicast datasets/` | 40 NCHE `tableExport*.csv` extracts (register + institutions) and 21 PDFs (cut-offs, fees, statutes). |
| `docs/data_inventory.*` | Machine-generated inventory of all 81 source files. |

Source files are **never modified**. All output is written to `data/processed/<run-id>/`.

Files explicitly **excluded** from the production pipeline:

- `Admission_Predict.csv` — a Kaggle GRE/TOEFL sample unrelated to Uganda; not used.
- Duplicate `gulu_university_undergraduate_programmes*.csv` copies — one is kept, the rest are
  recorded as duplicates.
- Three scanned, image-only PDFs — flagged `needs_review` (no OCR engine is available).

## 3. Architecture

```
datapipeline/
  ingest.py     safe upload validation, CSV/Excel/PDF loaders
  extract.py    PDF cut-off table/text extraction, institution & scheme detection
  clean.py      column standardisation, text/money/cut-off/duration parsing
  dedupe.py     row- and entity-level de-duplication with an audit trail
  merge.py      stacking + validated joins (blow-up detection)
  validate.py   quality checks and readiness scoring
  pipeline.py   orchestrator (run_pipeline)
ml/
  train.py      trains the classifier and recommender, writes model cards
  predict.py    loads the latest artifacts and serves predictions
  models/       joblib artifacts + *.meta.json model cards
scripts/
  data_inventory.py   read-only inventory scanner
```

Each stage writes its own CSV plus a `processing_log.json`, so a run is fully reproducible and
auditable. A `data/processed/latest.json` pointer records the newest run.

## 4. How to run

```powershell
# 1. Inventory the source files (read-only)
python -m scripts.data_inventory

# 2. Run the full pipeline
python -m datapipeline.pipeline

# 3. Train the models
python -m ml.train

# 4. Run the test suite
python -m pytest -q
```

The same operations are available in the admin UI at `/admin/data`, `/admin/models` and
`/admin/predict` (admin login required).

## 5. Measured results (run `20261017-084957`)

| Dataset | Rows in | Rows out | Notes |
| --- | --- | --- | --- |
| Universities | 11 | 11 | — |
| Programmes | 75 | 75 | — |
| Catalogues | 376 | 376 | 21 duplicate rows removed |
| Careers | 21 | 21 | — |
| NCHE register | 3753 | 3622 | 131 duplicate/blank rows removed |
| NCHE institutions | 178 | 153 | 25 duplicates removed |
| PDF cut-offs | — | 1361 | schemes: private 1262 / government 183 / national merit 74; years 2012/13–2026/27 |
| Extracted fees | — | 3 | low yield, source text OCR-garbled (see limitations) |
| Training dataset | — | 3622 | label = `discipline`, 12 classes |

### Model results

| Model | Algorithm | Metric | Value |
| --- | --- | --- | --- |
| Programme-discipline classifier | Logistic Regression | accuracy (held-out test) | **0.873** |
| | | macro-F1 (held-out test) | **0.709** |
| Content recommender | TF-IDF cosine | Precision@5 (proxy) | 0.114 |
| | | Recall@5 (proxy) | 0.056 |
| | | NDCG@5 (proxy) | 0.103 |

Classifier candidate selection compared Logistic Regression, Decision Tree and RandomForest on a
stratified validation split; the best macro-F1 was retrained and scored on a held-out 20% test
split. The recommender's proxy metrics use `careers.csv` career→programme links as a **weak,
self-referential** relevance signal — they are **not** held-out ground truth and must not be read
as evidence of admission quality.

## 6. Limitations and honest caveats

- **No admission-outcome labels.** The data supports programme *description* and classification,
  not prediction of who gets admitted. No such model is claimed.
- **Recommender evaluation is weak.** The only available relevance signal comes from the same
  careers file, so Precision/Recall/NDCG@5 are self-referential proxies.
- **Fee extraction is incomplete.** Only 3 fee rows were recovered; the fee PDFs contain
  OCR-corrupted numbers (e.g. `1 ,756,61 1`). Low-yield fee documents are flagged for manual
  review instead of emitting unreliable values.
- **Three scanned PDFs** (e.g. the 2024/25 postgraduate fee structure and the national-merit
  cut-off scans) cannot be parsed without an OCR engine and are flagged `needs_review`.
- **Cut-off values change yearly** and are only as accurate as the source PDFs; the app already
  warns users to confirm with admissions offices.

## 7. Integration points

- `models.py`: `DatasetUpload`, `DatasetRun`, `ModelVersion`, `PredictionLog`.
- `blueprints/admin.py`: `/admin/data`, `/admin/data/run`, `/admin/data/upload`,
  `/admin/data/download/...`, `/admin/models`, `/admin/models/train`,
  `/admin/models/<id>/approve`, `/admin/predict`.
- Templates: `templates/admin/data.html`, `models.html`, `predict.html`.
- Tests: `tests/test_pipeline.py`, `tests/test_ml.py`, `tests/test_admin_data.py`.
