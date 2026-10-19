"""Cleaning and standardisation.

Every function returns new objects; source frames are never mutated. Invalid
records are quarantined (kept for review) rather than silently dropped.
"""

import re

import pandas as pd

WHITESPACE_RE = re.compile(r"\s+")
MOJIBAKE_RE = re.compile("[\ufffd\u00c3\u00e2]+")


def clean_text(value):
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\u00a0", " ")
    text = MOJIBAKE_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def normalize_university(value):
    text = clean_text(value)
    text = re.sub(r"\bUniv\.?\b", "University", text)
    return text


def normalize_programme(value):
    text = clean_text(value)
    fixes = {
        "Bsc": "Bachelor of Science",
        "Bsc.": "Bachelor of Science",
        "Ba ": "Bachelor of Arts ",
    }
    for wrong, right in fixes.items():
        if text.startswith(wrong):
            text = right + text[len(wrong):]
    return text


def clean_text_column(series):
    return series.map(clean_text)


def parse_money(value):
    """Parse '1,300,000' / '1300000' / 'NA' to int or None."""
    text = clean_text(value).replace(",", "").replace(" ", "")
    if not text or text.upper() in ("NA", "N/A", "-", "NONE"):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return int(float(match.group(0)))
    except ValueError:
        return None


def parse_cutoff_pairs(value):
    """Parse 'Gov:26;Private:18' -> (government, private) ints or (None, None)."""
    gov = private = None
    for chunk in str(value or "").replace(";", ",").split(","):
        if ":" not in chunk:
            continue
        key, _, raw = chunk.partition(":")
        key = key.strip().lower()
        if key.startswith("gov"):
            gov = parse_money(raw)
        elif key.startswith("priv"):
            private = parse_money(raw)
    return gov, private


def parse_fee_pairs(value):
    """Parse 'Gov:1300000;Private:8500000' -> (government, private) ints."""
    return parse_cutoff_pairs(value)


DURATION_RE = re.compile(r"(\d+)\s*(?:[-/]\s*(\d+))?\s*(years?|yrs?|months?|semesters?)", re.I)


def parse_duration(value):
    text = clean_text(value).lower()
    if not text:
        return None
    if text.replace(",", "").isdigit():
        return int(text.replace(",", ""))
    years, months = [], 0
    for match in DURATION_RE.finditer(text):
        count = int(match.group(1))
        unit = match.group(3)
        if unit.startswith("month"):
            months = max(months, count)
        elif unit.startswith("semester"):
            months = max(months, count * 6)
        else:
            years.append(int(match.group(2)) if match.group(2) else count)
    if years:
        return max(years)
    if months:
        return max(1, (months + 11) // 12)
    return None


def derive_level(name, hint=""):
    text = " ".join([str(hint or ""), str(name or "")]).lower()
    if any(k in text for k in ("phd", "doctorate", "doctor of philosophy")):
        return "Doctorate"
    if any(k in text for k in ("master", "postgraduate", "pgd")):
        return "Postgraduate"
    if "diploma" in text:
        return "Diploma"
    if "certificate" in text:
        return "Certificate"
    return "Bachelor"


def standardise_columns(frame, mapping):
    """Rename columns via a {source: canonical} mapping.

    Returns (renamed_frame, report_rows). Unmapped columns are kept and also
    listed in the report.
    """
    report = []
    rename = {}
    for column in frame.columns:
        canonical = mapping.get(column)
        if canonical:
            rename[column] = canonical
            report.append({"original": column, "standardised": canonical, "action": "renamed"})
        else:
            report.append({"original": column, "standardised": column, "action": "kept"})
    renamed = frame.rename(columns=rename)
    if renamed.columns.duplicated().any():
        renamed = renamed.loc[:, ~renamed.columns.duplicated(keep="first")]
    return renamed, report


def missing_report(frame, source=""):
    rows = []
    total = len(frame) or 1
    for column in frame.columns:
        missing = int(frame[column].isna().sum() + (frame[column].astype(str) == "").sum())
        rows.append({
            "source": source,
            "column": column,
            "missing": missing,
            "missing_pct": round(missing / total * 100, 1),
        })
    return rows


def clean_tabular(frame, spec):
    """Clean one frame according to a spec.

    spec keys:
      source        - label for reports
      mapping       - {source_column: canonical_column}
      required      - canonical columns that must be present and non-empty
      text_columns  - canonical columns to text-clean
      numeric_columns - canonical columns to parse as numbers
      defaults      - {column: value} filled when missing
    Returns dict(clean, quarantine, column_report, missing_report, issues).
    """
    source = spec.get("source", "")
    renamed, column_report = standardise_columns(frame, spec.get("mapping", {}))
    renamed = renamed.copy()

    for column in spec.get("text_columns", ()):
        if column in renamed.columns:
            renamed[column] = renamed[column].map(clean_text)
    for column in spec.get("numeric_columns", ()):
        if column in renamed.columns:
            renamed[column] = renamed[column].map(parse_money)

    for column, value in spec.get("defaults", {}).items():
        if column in renamed.columns:
            renamed[column] = renamed[column].where(
                renamed[column].notna() & (renamed[column].astype(str) != ""), value
            )
        else:
            renamed[column] = value

    required = [c for c in spec.get("required", ()) if c in renamed.columns]
    issues = []
    missing_required = [c for c in spec.get("required", ()) if c not in renamed.columns]
    if missing_required:
        issues.append("Missing required column(s) after mapping: {0}".format(", ".join(missing_required)))

    if required:
        blank = renamed[required].isna() | renamed[required].apply(
            lambda column: column.astype(str).str.strip() == ""
        )
        invalid_mask = blank.any(axis=1)
    else:
        invalid_mask = pd.Series(False, index=renamed.index)

    clean = renamed[~invalid_mask].reset_index(drop=True)
    quarantine = renamed[invalid_mask].reset_index(drop=True)
    if len(quarantine):
        quarantine["_reason"] = "missing required field(s)"
        quarantine["_source"] = source

    return {
        "clean": clean,
        "quarantine": quarantine,
        "column_report": [dict(row, source=source) for row in column_report],
        "missing": missing_report(clean, source),
        "issues": issues,
    }
