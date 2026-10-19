import os
import re

import pandas as pd
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash

from config import Config
from extensions import db
from models import (
    Career,
    Notification,
    Programme,
    Setting,
    StudentProfile,
    University,
    User,
    split_field,
)


def _read(filename):
    return pd.read_csv(os.path.join(Config.DATA_DIR, filename), na_filter=False)


def load_universities():
    frame = _read("universities.csv")
    by_name = {u.name: u for u in University.query.all()}
    for _, row in frame.iterrows():
        existing = by_name.get(row["name"])
        if existing is not None:
            if not existing.image and row["image"]:
                existing.image = row["image"]
            continue
        university = University(
            name=row["name"],
            institution_type=row["institution_type"],
            region=row["region"],
            district=row["district"],
            location=row["location"],
            established=int(row["established"]) if str(row["established"]).isdigit() else None,
            website=row["website"],
            application_link=row["application_link"],
            image=row["image"],
            active=str(row["active"]).upper() == "TRUE",
        )
        db.session.add(university)
        by_name[row["name"]] = university
    db.session.flush()


def _norm_name(value):
    return " ".join(str(value or "").lower().split())


def _parse_duration(value):
    text = str(value or "").strip()
    if not text:
        return None
    lower = text.lower()
    years = []
    months = 0
    for match in re.finditer(r"(\d+)\s*(?:[-\/]\s*(\d+))?\s*(years?|months?)", lower):
        count = int(match.group(1))
        second = int(match.group(2)) if match.group(2) else None
        if match.group(3).startswith("month"):
            months = max(months, count)
        else:
            years.append(second if second else count)
    if years:
        return max(years)
    if months:
        return max(1, (months + 11) // 12)
    if text.replace(",", "").isdigit():
        return int(text.replace(",", ""))
    return None


def _derive_level(name, hint=""):
    text = " ".join(str(hint or "").lower().split())
    if text:
        if any(key in text for key in ("postgrad", "master", "phd", "doctorate")):
            return "Postgraduate"
        if "diploma" in text:
            return "Diploma"
        if "certificate" in text:
            return "Certificate"
        if "bachelor" in text:
            return "Bachelor"
    name_text = " ".join(str(name or "").lower().split())
    if any(key in name_text for key in ("master", "postgrad", "doctor", "phd")):
        return "Postgraduate"
    if "diploma" in name_text:
        return "Diploma"
    if "certificate" in name_text:
        return "Certificate"
    return "Bachelor"


def _principal_hint(requirement):
    match = re.search(r"(\d+)\s*principal\s*pas", str(requirement or ""), re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extra_programme(university, course, source="", duration="", level="", minimum_grades="", tuition_private=None):
    passes = _principal_hint(minimum_grades) or 2
    fees = "Gov:NA;Private:NA"
    if tuition_private:
        fees = "Gov:NA;Private:{0}".format(int(tuition_private))
    return {
        "University": university,
        "Course": course,
        "Qualification Level": "UACE",
        "Essential Subjects": "",
        "Minimum Grades": minimum_grades,
        "Principal Passes": str(passes),
        "Cut-off Points": "Gov:NA;Private:NA",
        "Tuition Fees": fees,
        "Academic Year": "2026/27",
        "Official Source": source,
        "Sponsorship": "Private" if tuition_private else "",
        "Citizenship Applicability": "Ugandan & Foreign",
        "Required UCE": "",
        "Subject Weights": "",
        "Duration": duration,
        "District/Region": "",
        "Application Link": "",
        "Data-Year": "2026/27",
        "Level": level,
    }


def _extra_source_rows():
    """University catalogue CSVs (non-canonical schemas) normalised to canonical rows."""
    rows = []

    frame = _read("busitema_undergraduate_programmes.csv")
    for _, row in frame.iterrows():
        rows.append(_extra_programme("Busitema University", row["programme_name"], source=row["overview_url"]))

    frame = _read("gulu_university_undergraduate_programmes.csv")
    for _, row in frame.iterrows():
        rows.append(_extra_programme("Gulu University", row["Programme"],
                                     source=row["URL"], duration=row["Duration"]))

    frame = _read("kyambogo_undergraduate_programmes.csv")
    for _, row in frame.iterrows():
        rows.append(_extra_programme("Kyambogo University", row["Programme"],
                                     duration=row["Duration"],
                                     minimum_grades=row["Minimum Admission Requirements"]))

    frame = _read("must_undergraduate_programmes.csv")
    for _, row in frame.iterrows():
        rows.append(_extra_programme("Mbarara University of Science and Technology", row["Programme Name"],
                                     duration=row["Duration"], level=row["Level"]))

    frame = _read("nkumba_university_programs.csv")
    for _, row in frame.iterrows():
        if "postgraduate" in str(row["Level"]).lower():
            continue
        rows.append(_extra_programme("Nkumba University", row["Program"],
                                     source=row["URL"], duration=row["Duration"], level=row["Level"]))

    frame = _read("ucu_undergraduate_programs_tuition.csv")
    for _, row in frame.iterrows():
        fee = str(row["Tuition 2025 nationals (UGX) as listed"]).replace(",", "").strip()
        tuition = int(fee) if fee.isdigit() else None
        rows.append(_extra_programme("Uganda Christian University", row["Program"],
                                     duration=row["Duration (years)"], level=row["Level"],
                                     tuition_private=tuition))

    frame = _read("umu_bachelors_programmes.csv")
    for _, row in frame.iterrows():
        rows.append(_extra_programme("Uganda Martyrs University", row["Course"],
                                     duration=row["Duration"], source=row["Fee Structure Source"]))

    return rows


def load_programmes():
    universities = {u.name: u for u in University.query.all()}
    existing = {(p.university_id, _norm_name(p.name)): p for p in Programme.query.all()}

    def parse_money(value):
        parts = {}
        for chunk in split_field(value):
            if ":" not in chunk:
                continue
            key, _, val = chunk.partition(":")
            val = str(val).replace(",", "") or "0"
            parts[key.strip().lower()] = int(val) if val.isdigit() else None
        return parts.get("gov"), parts.get("private")

    frames = [_read("programmes.csv"), _read("programmes_mru.csv")]
    for frame in frames:
        for _, row in frame.iterrows():
            _import_programme_row(row, universities, parse_money, existing, backfill=True)

    for row in _extra_source_rows():
        _import_programme_row(row, universities, parse_money, existing)

    db.session.flush()


def _backfill_programme(programme, row, parse_money):
    duration = _parse_duration(row.get("Duration", ""))
    if duration and duration != programme.duration_years:
        programme.duration_years = duration
    if not programme.level or programme.level == "Bachelor":
        programme.level = _derive_level(row["Course"], row.get("Level", ""))
    if not programme.essential_subjects and row["Essential Subjects"]:
        programme.essential_subjects = row["Essential Subjects"]
    if not programme.minimum_grades and row["Minimum Grades"]:
        programme.minimum_grades = row["Minimum Grades"]
    if not programme.uce_requirement and row["Required UCE"]:
        programme.uce_requirement = row["Required UCE"]
    if not programme.official_source and row["Official Source"]:
        programme.official_source = row["Official Source"]
    if not programme.principal_passes or programme.principal_passes == 2:
        passes = int(row["Principal Passes"]) if str(row["Principal Passes"]).isdigit() else 2
        programme.principal_passes = passes
    international = _international_eligible(row.get("Citizenship Applicability", ""))
    if international and not programme.international_eligible:
        programme.international_eligible = True
    cuts = parse_money(row["Cut-off Points"])
    fees = parse_money(row["Tuition Fees"])
    if programme.cutoff_government is None:
        programme.cutoff_government = cuts[0]
    if programme.cutoff_private is None:
        programme.cutoff_private = cuts[1]
    if programme.tuition_government is None:
        programme.tuition_government = fees[0]
    if programme.tuition_private is None:
        programme.tuition_private = fees[1]


def _international_eligible(citizenship):
    return (not citizenship) or "Foreign" in citizenship


def _import_programme_row(row, universities, parse_money, existing, backfill=False):
    university = universities.get(row["University"])
    if university is None:
        return
    key = (university.id, _norm_name(row["Course"]))
    programme = existing.get(key)
    if programme is not None:
        if backfill:
            _backfill_programme(programme, row, parse_money)
        return
    cuts = parse_money(row["Cut-off Points"])
    fees = parse_money(row["Tuition Fees"])
    citizenship = row["Citizenship Applicability"]
    programme = Programme(
        university_id=university.id,
        name=row["Course"],
        level=_derive_level(row["Course"], row.get("Level", "")),
        qualification_level=row["Qualification Level"],
        duration_years=_parse_duration(row.get("Duration", "")) or 3,
        essential_subjects=row["Essential Subjects"],
        relevant_subjects="",
        minimum_grades=row["Minimum Grades"],
        principal_passes=int(row["Principal Passes"]) if str(row["Principal Passes"]).isdigit() else 2,
        uce_requirement=row["Required UCE"] or None,
        cutoff_government=cuts[0],
        cutoff_private=cuts[1],
        tuition_government=fees[0],
        tuition_private=fees[1],
        international_eligible=_international_eligible(citizenship),
        admission_year=row["Academic Year"],
        official_source=row["Official Source"],
        fees_verified=any(fees),
        active=True,
    )
    db.session.add(programme)
    existing[key] = programme


def load_careers():
    frame = _read("careers.csv")
    known = {c.name for c in Career.query.all()}
    for _, row in frame.iterrows():
        if row["name"] in known:
            continue
        career = Career(
            name=row["name"],
            description=row["description"],
            required_subjects=row["required_subjects"],
            skills=row["skills"],
            pathways=row["pathways"],
        )
        db.session.add(career)
        known.add(row["name"])
    db.session.flush()

    pairs = {}
    for _, row in frame.iterrows():
        career = Career.query.filter_by(name=row["name"]).first()
        if career is None:
            continue
        for token in split_field(row["programmes"]):
            token = token.strip().lower()
            for programme in Programme.query.all():
                if token in programme.name.lower():
                    pairs.setdefault(programme.id, set()).add(career.id)

    for programme_id, career_ids in pairs.items():
        programme = db.session.get(Programme, programme_id)
        for career_id in career_ids:
            if career_id not in [c.id for c in programme.careers]:
                programme.careers.append(db.session.get(Career, career_id))


def create_users():
    admin = User.query.filter_by(email="admin@uniguide.ug").first()
    if admin is None:
        admin = User(
            name="Administrator",
            username="admin",
            email="admin@uniguide.ug",
            password_hash=generate_password_hash("admin123"),
            role="admin",
        )
        db.session.add(admin)
    elif not admin.username:
        admin.username = "admin"

    student = User.query.filter_by(email="student@uniguide.ug").first()
    if student is None:
        student = User(
            name="Demo Student",
            username="student",
            email="student@uniguide.ug",
            password_hash=generate_password_hash("student123"),
            role="student",
        )
        db.session.add(student)
        db.session.flush()

    if student.profile is None:
        profile = StudentProfile(
            user_id=student.id,
            citizenship="ugandan",
            uace_subjects='{"Biology": "A", "Chemistry": "B", "Mathematics": "B", "Physics": "C"}',
            uace_subsidiary='{"General Paper": "A", "Sub-Mathematics": "B"}',
            uce_summary="Six credits including English and Mathematics.",
            preferred_field="Computing & IT",
            career_interests='["Software Developer", "Data Scientist"]',
            budget=6000000,
            preferred_region="Central",
            sponsorship_pref="private",
        )
        db.session.add(profile)


def migrate_schema():
    """Add any model columns missing from an existing database (lightweight migration)."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    for table in db.metadata.sorted_tables:
        if table.name not in tables:
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            column_type = column.type.compile(db.engine.dialect)
            db.session.execute(text(
                'ALTER TABLE "{0}" ADD COLUMN "{1}" {2}'.format(table.name, column.name, column_type)
            ))
    db.session.commit()


def seed_all(recreate=False):
    if recreate:
        db.drop_all()
    db.create_all()
    migrate_schema()

    load_universities()
    load_programmes()
    load_careers()
    create_users()
    Setting.ensure_defaults()
    db.session.commit()


def notify_programme_update(programme, message):
    for user in User.query.filter_by(role="student").all():
        db.session.add(Notification(
            user_id=user.id,
            message=message,
            link="/dashboard",
        ))
    db.session.commit()