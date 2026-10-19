"""Controlled dataset merging with a lineage report.

`stack_sources` concatenates compatible frames and records which source each
row came from. `join_datasets` performs a validated key join and reports
matched/unmatched counts and any row blow-up (accidental many-to-many joins).
"""

import pandas as pd

from datapipeline.clean import clean_text


def stack_sources(frames, canonical_columns, source_column="source_file"):
    """Concatenate frames into a canonical column set, tagging each row's source."""
    prepared = []
    lineage = []
    for label, frame in frames:
        frame = frame.copy()
        for column in canonical_columns:
            if column not in frame.columns:
                frame[column] = ""
        frame = frame[canonical_columns]
        frame[source_column] = label
        prepared.append(frame)
        lineage.append({"source": label, "input_rows": len(frame)})

    if not prepared:
        empty = pd.DataFrame(columns=list(canonical_columns) + [source_column])
        return empty, lineage

    combined = pd.concat(prepared, ignore_index=True)
    return combined, lineage


def _norm(series):
    return series.astype(str).map(clean_text).str.lower()


def join_datasets(left, right, left_on, right_on, how="left",
                  left_label="left", right_label="right", validate="many_to_one"):
    """Join two frames on normalised keys and return (result, report)."""
    left = left.copy()
    right = right.copy()
    left["_jkey"] = _norm(left[left_on])
    right["_jkey"] = _norm(right[right_on])

    matched = set(left["_jkey"]) & set(right["_jkey"])
    result = left.merge(right.drop(columns=[c for c in right_on if c in right.columns and c != "_jkey"]),
                        on="_jkey", how=how, suffixes=("", "_r"))
    result = result.drop(columns=["_jkey"])

    before = len(left)
    after = len(result)
    report = {
        "left_source": left_label,
        "right_source": right_label,
        "left_rows": before,
        "right_rows": len(right),
        "output_rows": after,
        "matched_keys": len(matched),
        "unmatched_left": int((~left["_jkey"].isin(matched)).sum()),
        "unmatched_right": int((~right["_jkey"].isin(matched)).sum()),
        "row_blowup": after > before,
        "many_to_many_risk": bool(after > before),
        "requested_validate": validate,
    }
    return result, report
