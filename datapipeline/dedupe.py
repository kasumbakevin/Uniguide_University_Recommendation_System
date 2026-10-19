"""Duplicate detection with an auditable trail.

Two levels:
  * exact duplicate rows (all columns identical) - safe to drop, always logged;
  * entity duplicates on a business key - identical payloads are merged, while
    records whose key matches but whose values conflict are preserved and
    flagged for human review (never silently deleted).
"""

import pandas as pd

from datapipeline.clean import clean_text


def _key(value):
    return clean_text(value).lower()


def business_key(frame, key_columns):
    return frame[key_columns].astype(str).agg(" | ".join, axis=1).map(_key)


def dedupe(frame, key_columns, source="", value_columns=None, sort_columns=None):
    frame = frame.reset_index(drop=True).copy()
    records = []
    value_columns = [c for c in (value_columns or frame.columns) if c in frame.columns]

    if sort_columns:
        present = [c for c in sort_columns if c in frame.columns]
        if present:
            frame = frame.sort_values(present, kind="stable").reset_index(drop=True)

    exact_mask = frame.duplicated(keep="first")
    for index in frame.index[exact_mask]:
        records.append({
            "source": source,
            "level": "row",
            "key": "",
            "action": "removed",
            "reason": "exact duplicate row",
            "kept_row": int(frame[~exact_mask].index[0]) if (~exact_mask).any() else -1,
            "dropped_row": int(index),
        })
    frame = frame[~exact_mask].reset_index(drop=True)

    if not key_columns:
        return {"clean": frame, "duplicates": records, "conflicts": pd.DataFrame()}

    frame["_bkey"] = business_key(frame, key_columns)
    groups = frame.groupby("_bkey", sort=False)
    keep_indices = []
    conflict_rows = []
    for bkey, group in groups:
        if len(group) == 1:
            keep_indices.append(group.index[0])
            continue
        payload = group[value_columns].astype(str).agg(" | ".join, axis=1)
        if payload.nunique() == 1:
            keep_indices.append(group.index[0])
            for index in group.index[1:]:
                records.append({
                    "source": source,
                    "level": "entity",
                    "key": bkey,
                    "action": "merged",
                    "reason": "identical payload for the same key",
                    "kept_row": int(group.index[0]),
                    "dropped_row": int(index),
                })
        else:
            keep_indices.extend(list(group.index))
            conflict_rows.append(group)
            records.append({
                "source": source,
                "level": "entity",
                "key": bkey,
                "action": "review",
                "reason": "same key, conflicting values - both records retained",
                "kept_row": int(group.index[0]),
                "dropped_row": -1,
            })

    clean = frame.loc[sorted(keep_indices)].drop(columns=["_bkey"]).reset_index(drop=True)
    conflicts = pd.concat(conflict_rows).drop(columns=["_bkey"]) if conflict_rows else pd.DataFrame()
    return {"clean": clean, "duplicates": records, "conflicts": conflicts}
