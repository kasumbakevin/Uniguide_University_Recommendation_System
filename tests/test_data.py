import pandas as pd
import pytest

from config import Config

REQUIRED_COLUMNS = [
    "University", "Course", "Qualification Level", "Essential Subjects",
    "Minimum Grades", "Principal Passes", "Cut-off Points", "Tuition Fees",
    "Academic Year", "Official Source",
]


@pytest.fixture()
def programmes():
    return pd.read_csv(Config.DATA_DIR + "/programmes.csv", na_filter=False)


@pytest.fixture()
def universities():
    return pd.read_csv(Config.DATA_DIR + "/universities.csv", na_filter=False)


def test_programmes_schema(programmes):
    for column in REQUIRED_COLUMNS:
        assert column in programmes.columns, "Missing column: {0}".format(column)


def test_programmes_not_empty(programmes):
    assert len(programmes) >= 20


def test_programme_universities_exist(programmes, universities):
    known = set(universities["name"])
    for university in programmes["University"]:
        assert university in known, "Unknown university: {0}".format(university)


def test_no_duplicate_programmes(programmes):
    pairs = list(zip(programmes["University"], programmes["Course"]))
    assert len(pairs) == len(set(pairs))


def test_cutoff_points_parseable(programmes):
    for raw in programmes["Cut-off Points"]:
        for part in str(raw).split(";"):
            part = part.strip()
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            assert key.strip().lower() in ("gov", "private")
            if value.strip().upper() != "NA":
                assert value.strip().isdigit(), "Non-numeric cut-off: {0}".format(raw)


def test_tuition_fees_parseable(programmes):
    for raw in programmes["Tuition Fees"]:
        for part in str(raw).split(";"):
            part = part.strip()
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            assert key.strip().lower() in ("gov", "private")
            if value.strip().upper() != "NA":
                assert value.strip().isdigit(), "Non-numeric fee: {0}".format(raw)


def test_essential_subjects_format(programmes):
    samples = programmes[programmes["Essential Subjects"].astype(bool)]
    for raw in samples["Essential Subjects"]:
        for subject in str(raw).split(";"):
            assert subject.strip(), "Empty subject token in: {0}".format(raw)


def test_principal_passes_in_range(programmes):
    for value in programmes["Principal Passes"]:
        assert 1 <= int(value) <= 3


def test_careers_file_exists():
    careers = pd.read_csv(Config.DATA_DIR + "/careers.csv", na_filter=False)
    assert len(careers) >= 10
    assert "programmes" in careers.columns


def test_university_logos_exist(universities):
    import os
    from config import Config

    assert "image" in universities.columns, "Missing column: image"
    for _, row in universities.iterrows():
        assert row["image"], "Missing logo for {0}".format(row["name"])
        logo = os.path.join(Config.STATIC_DIR, "images", row["image"])
        assert os.path.exists(logo), "Logo file missing for {0}: {1}".format(row["name"], row["image"])