"""Automated data-quality validation and dataset readiness scoring."""

from datapipeline.clean import clean_text

VALID_GRADES = {"A", "B", "C", "D", "E", "F"}


def _non_null(frame, column):
    if column not in frame.columns:
        return None
    return int(frame[column].notna().sum() - (frame[column].astype(str).str.strip() == "").sum())


def validate_dataset(frame, spec):
    """Run quality checks and return a report dict.

    spec:
      name             - dataset label
      required         - columns that must be populated
      key              - column(s) that should be unique
      university_column, programme_column, year_column, source_column
      valid_years      - iterable of acceptable academic years
      label_column     - classification target that must not be empty
      min_rows         - expected minimum record count
    """
    name = spec.get("name", "dataset")
    findings = []
    total = len(frame)

    def add(check, status, detail, count=0):
        findings.append({"dataset": name, "check": check, "status": status, "count": count, "detail": detail})

    add("record_count", "pass" if total >= spec.get("min_rows", 1) else "warn",
        "{0} record(s)".format(total), total)

    for column in spec.get("required", ()):
        if column not in frame.columns:
            add("required_field", "fail", "column missing: {0}".format(column), total)
            continue
        present = _non_null(frame, column) or 0
        missing = total - present
        add("required_field:{0}".format(column), "pass" if missing == 0 else "warn",
            "{0} missing".format(missing), missing)

    for column in ([spec["key"]] if isinstance(spec.get("key"), str) else spec.get("key", []) or []):
        if column not in frame.columns:
            add("unique_key", "fail", "column missing: {0}".format(column))
            continue
        dupes = int(frame[column].astype(str).duplicated().sum())
        add("unique_key:{0}".format(column), "pass" if dupes == 0 else "warn",
            "{0} duplicate value(s)".format(dupes), dupes)

    year_column = spec.get("year_column")
    valid_years = spec.get("valid_years")
    if year_column and year_column in frame.columns and valid_years:
        valid = set(valid_years)
        bad = frame[~frame[year_column].map(clean_text).isin(valid)]
        add("academic_year", "pass" if bad.empty else "warn",
            "{0} record(s) outside {1}".format(len(bad), sorted(valid)), len(bad))

    source_column = spec.get("source_column")
    if source_column and source_column in frame.columns:
        missing_source = total - (_non_null(frame, source_column) or 0)
        add("source_reference", "pass" if missing_source == 0 else "warn",
            "{0} record(s) without a source".format(missing_source), missing_source)

    label_column = spec.get("label_column")
    if label_column and label_column in frame.columns:
        blank = total - (_non_null(frame, label_column) or 0)
        add("target_label", "pass" if blank == 0 else "fail",
            "{0} record(s) without a target label".format(blank), blank)

    grade_column = spec.get("grades_column")
    if grade_column and grade_column in frame.columns:
        import re

        bad_grades = 0
        for value in frame[grade_column].astype(str):
            for token in re.findall(r"[A-Fa-f](?![A-Za-z])", value):
                if token.upper() not in VALID_GRADES:
                    bad_grades += 1
        add("grade_range", "pass" if bad_grades == 0 else "warn",
            "{0} out-of-range grade token(s)".format(bad_grades), bad_grades)

    readiness = "ready"
    if any(f["status"] == "fail" for f in findings):
        readiness = "not_ready"
    elif any(f["status"] == "warn" for f in findings):
        readiness = "ready_with_warnings"

    return {"dataset": name, "rows": total, "readiness": readiness, "findings": findings}
