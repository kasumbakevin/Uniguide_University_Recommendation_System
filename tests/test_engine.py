from models import StudentProfile, University
from recommender import (
    analyse_foreign,
    analyse_one,
    analyse_ugandan,
    principal_pass_count,
    recommend,
    weighted_score,
)


def make_programme(**overrides):
    defaults = dict(
        id=1,
        name="Bachelor of Medicine and Bachelor of Surgery",
        essential_subjects="Biology;Chemistry",
        relevant_subjects="Physics;Mathematics",
        minimum_grades="Biology:C;Chemistry:C;Physics:D",
        principal_passes=2,
        cutoff_government=26,
        cutoff_private=18,
        tuition_private=8500000,
        tuition_government=1300000,
        international_eligible=True,
        foreign_min_total=12,
        admission_year="2026/27",
        official_source="https://www.mak.ac.ug/study-mak/cut-points",
    )
    defaults.update(overrides)
    from models import Programme

    return Programme(**defaults)


def make_university():
    return University(
        id=1,
        name="Makerere University",
        region="Central",
        district="Kampala",
        location="Kampala",
        application_link="https://apply.mak.ac.ug",
    )


def make_profile(**overrides):
    defaults = dict(
        citizenship="ugandan",
        uace_subjects='{"Biology": "A", "Chemistry": "B", "Mathematics": "B", "Physics": "C"}',
        uace_subsidiary='{"General Paper": "A", "Sub-Mathematics": "B"}',
        uce_summary="Six credits including English and Mathematics.",
        preferred_field="Medicine & Health",
        budget=6000000,
        preferred_region="Central",
        sponsorship_pref="private",
    )
    defaults.update(overrides)
    return StudentProfile(**defaults)


def test_normalize_subject_aliases():
    from recommender import normalize_subject

    assert normalize_subject("Mathematics") == normalize_subject("maths")
    assert normalize_subject("Computer Science") == normalize_subject("CS")
    assert normalize_subject("General Paper") == normalize_subject("GP")


def test_weighted_score():
    programme = make_programme()
    profile = make_profile()
    score = weighted_score(profile.subjects(), profile.subsidiary(), programme)
    expected = 6 * 3 + 5 * 3 + 5 * 2 + 4 * 2 + 6 * 0.5 + 5 * 0.5
    assert score == expected


def test_principal_pass_count():
    assert principal_pass_count({"Biology": "A", "Chemistry": "C", "Mathematics": "D"}) == 2


def test_ugandan_eligible():
    programme = make_programme()
    programme.university = make_university()
    result = analyse_ugandan(make_profile(), programme)
    assert result["status"] == "Eligible"
    assert result["score"] > result["cutoff"]
    assert result["missing"] == []


def test_ugandan_missing_essential():
    programme = make_programme()
    programme.university = make_university()
    profile = make_profile(uace_subjects='{"Biology": "A", "Mathematics": "B"}')
    result = analyse_ugandan(profile, programme)
    assert result["status"] == "Not eligible"
    assert "Chemistry" in result["missing"][0]


def test_ugandan_borderline():
    programme = make_programme(cutoff_private=57)
    programme.university = make_university()
    result = analyse_ugandan(make_profile(), programme)
    assert result["status"] == "Borderline"


def test_foreign_eligible():
    programme = make_programme()
    programme.university = make_university()
    profile = make_profile(
        citizenship="foreign",
        foreign_qual='{"type": "CIE A-Level", "total": "15", "subjects": "Maths, Physics, Chem"}',
    )
    result = analyse_foreign(profile, programme)
    assert result["status"] == "Eligible"


def test_foreign_below_minimum():
    programme = make_programme()
    programme.university = make_university()
    profile = make_profile(
        citizenship="foreign",
        foreign_qual='{"type": "CIE A-Level", "total": "6", "subjects": ""}',
    )
    result = analyse_foreign(profile, programme)
    assert result["status"] == "Not eligible"


def test_analyse_one_returns_required_keys():
    programme = make_programme()
    programme.university = make_university()
    result = analyse_one(make_profile(), programme)
    for key in [
        "programme", "university", "status", "score", "cutoff", "reasons",
        "missing", "tuition", "sponsorship", "suitability", "admission_year",
        "official_source", "application_link",
    ]:
        assert key in result


def test_recommend_from_seeded_db(app):
    with app.app_context():
        profile = make_profile()
        results = recommend(profile, limit=10)
        assert isinstance(results, list)
        for item in results:
            assert item["status"] in ("Eligible", "Borderline", "Not eligible")
            assert 0 <= item["suitability"] <= 100


def test_recommend_field_filter(app):
    with app.app_context():
        computing = make_profile(preferred_field="Computing & IT")
        computing_results = recommend(computing)
        law = make_profile(preferred_field="Law & Governance")
        law_results = recommend(law)
        computing_names = [r["programme"].name for r in computing_results]
        law_names = [r["programme"].name for r in law_results]
        assert any("Software" in n for n in computing_names)
        assert any("Laws" in n for n in law_names)