"""ML training and prediction utilities.

Models:
  1. Programme-discipline classifier (multi-class) - trains on NCHE register data.
     Predicts `discipline` (Tier Discipline) from programme text and metadata.
  2. Content-based recommender - ranks programmes by cosine similarity to a profile
     or career text query. No admission-outcome prediction; used to re-rank after
     the rule-based eligibility filter.

Evaluation follows scikit-learn metrics; models are saved with joblib and a
sidecar metadata JSON. No fabricated labels are introduced.
"""
