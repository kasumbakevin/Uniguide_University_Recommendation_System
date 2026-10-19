import re

from courses import FIELD_KEYWORDS, keyword_matches_programme
from models import Programme, split_field

GRADE_POINTS = {"A": 6, "B": 5, "C": 4, "D": 3, "E": 2, "F": 1}
PASS_GRADES = {"A", "B", "C"}
FOREIGN_DEFAULT_TOTAL = {
    "CIE A-Level": 12,
    "IB Diploma": 24,
    "WAEC": 10,
    "KCSE": 28,
    "Other": 6,
}


def normalize_subject(name):
    cleaned = re.sub(r"[^a-z0-9]", "", (name or "").lower())
    aliases = {
        "maths": "mathematics",
        "ict": "computerstudies",
        "cs": "computerscience",
        "computer": "computerscience",
        "gp": "generalpaper",
        "subict": "computerstudies",
    }
    return aliases.get(cleaned, cleaned)


def parse_key_values(text):
    result = {}
    for part in (text or "").split(";"):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, _, value = part.partition(":")
        result[normalize_subject(key)] = value.strip().upper()
    return result


def tuition_for(programme, sponsorship):
    if sponsorship == "government":
        return programme.tuition_government or programme.tuition_private or None
    return programme.tuition_private or programme.tuition_government or None


def cutoff_for(programme, sponsorship):
    if sponsorship == "government":
        return programme.cutoff_government or programme.cutoff_private
    return programme.cutoff_private or programme.cutoff_government


def weighted_score(subjects, subsidiary, programme):
    essentials = [normalize_subject(s) for s in programme.essential_list()]
    relevant = [normalize_subject(r) for r in programme.relevant_list()]
    score = 0.0
    for raw_name, grade in subjects.items():
        points = GRADE_POINTS.get(grade.upper())
        if points is None:
            continue
        name = normalize_subject(raw_name)
        if name in essentials:
            score += points * 3
        elif name in relevant:
            score += points * 2
        else:
            score += points * 1
    for raw_name, grade in subsidiary.items():
        points = GRADE_POINTS.get(grade.upper())
        if points is None:
            continue
        name = normalize_subject(raw_name)
        if name in ("generalpaper", "submathematics", "computerstudies"):
            score += points * 0.5
    return round(score, 1)


def principal_pass_count(subjects):
    return sum(1 for g in subjects.values() if g.upper() in PASS_GRADES)


def analyse_ugandan(profile, programme):
    d = profile.data
    subjects = {normalize_subject(k): v.upper() for k, v in profile.subjects().items()}
    subsidiary = {normalize_subject(k): v.upper() for k, v in profile.subsidiary().items()}
    essentials = [normalize_subject(s) for s in programme.essential_list()]
    min_grades = parse_key_values(programme.minimum_grades)

    missing = [s for s in programme.essential_list() if normalize_subject(s) not in subjects]
    weak = [
        (s, min_grades[normalize_subject(s)], subjects[normalize_subject(s)])
        for s in programme.essential_list()
        if normalize_subject(s) in subjects
        and normalize_subject(s) in min_grades
        and GRADE_POINTS.get(subjects[normalize_subject(s)], 0)
        < GRADE_POINTS.get(min_grades[normalize_subject(s)], 0)
    ]

    passes = principal_pass_count(subjects)
    pass_ok = passes >= (programme.principal_passes or 0)
    score = weighted_score(subjects, subsidiary, programme)
    cutoff = cutoff_for(programme, d.get("sponsorship_pref", "private"))

    reasons = []
    if pass_ok:
        reasons.append("Meets required A-Level principal passes ({0}/{1}).".format(passes, programme.principal_passes or 0))
    else:
        reasons.append("Needs {0} principal pass(es); has {1}.".format(programme.principal_passes or 0, passes))
    if essentials and not missing:
        reasons.append("All essential subjects covered: {0}.".format(", ".join(programme.essential_list())))
    if weak:
        reasons.append("Low grade in essential subject(s): {0}.".format(
            ", ".join("{0} (needs {1}, has {2})".format(a, b, c) for a, b, c in weak)))
    if cutoff is not None:
        marker = "≥" if score >= cutoff else "<"
        reasons.append("Weighted score {0} {1} cut-off {2}.".format(score, marker, cutoff))

    if not pass_ok or missing or weak:
        status = "Not eligible"
    elif cutoff is not None and score < cutoff - 2:
        status = "Not eligible"
    elif cutoff is not None and score < cutoff:
        status = "Borderline"
    else:
        status = "Eligible"

    missing_requirements = []
    if missing:
        missing_requirements.append("Missing essential subject(s): {0}".format(", ".join(missing)))
    if not pass_ok:
        missing_requirements.append("Principal passes below the requirement.")
    if weak:
        missing_requirements.append("Improve essential subject grade(s).")
    if cutoff is not None and score < cutoff:
        missing_requirements.append("Score is below the {0} cut-off of {1}.".format(
            "government" if d.get("sponsorship_pref") == "government" else "private", cutoff))

    return {
        "status": status,
        "score": score,
        "cutoff": cutoff,
        "reasons": reasons,
        "missing": missing_requirements,
    }


def analyse_foreign(profile, programme):
    foreign = profile.foreign()
    qual = foreign.get("type", "CIE A-Level")
    try:
        total = float(foreign.get("total", 0) or 0)
    except (TypeError, ValueError):
        total = 0.0
    minimum = programme.foreign_min_total or FOREIGN_DEFAULT_TOTAL.get(qual, 6)

    reasons = []
    if programme.international_eligible:
        reasons.append("International applicants are accepted at {0}.".format(programme.university.name))
    reasons.append("Programme minimum for {0}: {1}.".format(qual, minimum))

    if not programme.international_eligible:
        status = "Not eligible"
    elif total >= minimum:
        status = "Eligible"
    elif total >= minimum - 2:
        status = "Borderline"
    else:
        status = "Not eligible"

    reasons.append("Your total ({0}) is {1} the minimum ({2}).".format(
        int(total), "at or above" if total >= minimum else "below", minimum))

    missing_requirements = []
    if status != "Eligible":
        missing_requirements.append("Confirm international eligibility with the university international office.")
        if total < minimum:
            missing_requirements.append("Score is below the {0} minimum of {1}.".format(qual, minimum))

    return {
        "status": status,
        "score": total,
        "cutoff": minimum,
        "reasons": reasons,
        "missing": missing_requirements,
    }


def suit_rating(status, programme, profile, score, cutoff):
    base = 35
    if status == "Eligible":
        base = 85
        if cutoff and score is not None and score >= cutoff * 1.15:
            base = 95
    elif status == "Borderline":
        base = 60

    adjustment = 0
    sponsorship = profile.data.get("sponsorship_pref", "private")
    tuition = tuition_for(programme, sponsorship)
    if profile.budget and tuition and tuition > profile.budget:
        adjustment -= 12
    region = profile.data.get("preferred_region", "")
    if region and programme.university.region and region.lower() not in programme.university.region.lower():
        adjustment -= 8

    return max(0, min(100, base + adjustment))


def analyse_one(profile, programme):
    d = profile.data
    if d.get("citizenship") == "foreign":
        analysis = analyse_foreign(profile, programme)
    else:
        analysis = analyse_ugandan(profile, programme)

    sponsorship = d.get("sponsorship_pref", "private")
    tuition = tuition_for(programme, sponsorship)
    return {
        "programme": programme,
        "university": programme.university,
        "status": analysis["status"],
        "score": analysis["score"],
        "cutoff": analysis["cutoff"],
        "reasons": analysis["reasons"],
        "missing": analysis["missing"],
        "tuition": tuition,
        "sponsorship": "Government" if sponsorship == "government" else "Private",
        "suitability": suit_rating(analysis["status"], programme, profile, analysis["score"], analysis["cutoff"]),
        "admission_year": programme.admission_year,
        "official_source": programme.official_source,
        "application_link": programme.university.application_link or programme.university.website,
    }


def recommend(profile, limit=50):
    field = profile.data.get("preferred_field", "")
    keywords = None
    if field:
        keywords = FIELD_KEYWORDS.get(field) or [field.lower()]

    results = []
    for programme in Programme.query.filter_by(active=True).all():
        if not keyword_matches_programme(programme, keywords):
            continue
        results.append(analyse_one(profile, programme))

    order = {"Eligible": 0, "Borderline": 1, "Not eligible": 2}
    results.sort(key=lambda r: (order.get(r["status"], 3), -r["suitability"], -(r["score"] or 0)))
    return results[:limit]


def summary_counts(results):
    return (
        sum(1 for r in results if r["status"] == "Eligible"),
        sum(1 for r in results if r["status"] == "Borderline"),
        sum(1 for r in results if r["status"] == "Not eligible"),
    )