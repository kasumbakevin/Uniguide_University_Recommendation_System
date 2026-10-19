import pandas as pd

from datapipeline import clean, dedupe, merge, validate


def test_normalize_university_fix():
    assert clean.normalize_university("Makerere Univ") == "Makerere University"
    assert clean.normalize_university("Makerere University") == "Makerere University"


def test_parse_money():
    assert clean.parse_money("1,300,000") == 1300000
    assert clean.parse_money("5,000") == 5000
    assert clean.parse_money("NA") is None
    assert clean.parse_money("") is None


def test_parse_cutoff_pairs():
    assert clean.parse_cutoff_pairs("Gov:26;Private:18") == (26, 18)
    assert clean.parse_cutoff_pairs("Government:12") == (12, None)
    assert clean.parse_cutoff_pairs("") == (None, None)


def test_parse_duration():
    assert clean.parse_duration("3 years") == 3
    assert clean.parse_duration("4 Years") == 4
    assert clean.parse_duration("18 months") == 2
    assert clean.parse_duration("2") == 2


def test_clean_text_column():
    series = clean.clean_text_column(pd.Series([" AbC ", ""]))
    assert series.tolist() == ["AbC", ""]


def test_dedupe_returns_report():
    df = pd.DataFrame({"id": [1, 2, 1], "v": ["a", "b", "a"]})
    result = dedupe.dedupe(df, key_columns=["id"])
    assert set(result) == {"clean", "duplicates", "conflicts"}
    assert len(result["clean"]) == 2


def test_stack_sources_tags_origin():
    frames = [("a", pd.DataFrame({"name": ["X"], "val": [1]})),
              ("b", pd.DataFrame({"name": ["Y"], "val": [2]}))]
    combined, lineage = merge.stack_sources(frames, canonical_columns=["name", "val"])
    assert set(combined["source_file"]) == {"a", "b"}
    assert len(combined) == 2
    assert len(lineage) == 2


def test_validate_dataset_ready():
    df = pd.DataFrame({"name": ["A", "B"], "code": ["001", "002"], "year": ["2026/27", "2025/26"]})
    report = validate.validate_dataset(df, {
        "name": "test",
        "required": ["name", "code"],
        "key": ["code"],
        "year_column": "year",
        "valid_years": ["2025/26", "2026/27"],
        "min_rows": 1,
    })
    assert report["dataset"] == "test"
    assert report["readiness"] in ("ready", "ready_with_warnings")
    assert isinstance(report["findings"], list)
