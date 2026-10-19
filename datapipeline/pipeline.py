"""Pipeline orchestrator.

Runs every stage and writes versioned outputs to `data/processed/<run-id>/`.
Original files in `data/` are only ever read.
"""

import json
import os
import shutil
from datetime import datetime

import pandas as pd

from datapipeline import clean as clean_mod
from datapipeline import dedupe as dedupe_mod
from datapipeline import extract as extract_mod
from datapipeline import merge as merge_mod
from datapipeline import validate as validate_mod
from datapipeline.ingest import load_csv, safe_filename

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
UNICAST_DIR = os.path.join(DATA_DIR, "Unicast datasets")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
CLEANED_DIR = os.path.join(DATA_DIR, "cleaned")

CURRENT_YEARS = {"2024/25", "2025/26", "2026/27"}

PROGRAMME_COLUMNS = [
    "university", "programme", "qualification_level", "level", "duration_years",
    "essential_subjects", "minimum_grades", "principal_passes",
    "cutoff_government", "cutoff_private", "tuition_government", "tuition_private",
    "academic_year", "official_source", "application_link", "district_region",
    "sponsorship", "citizenship_applicability", "source_file",
]

CATALOGUE_COLUMNS = [
    "university", "programme", "programme_code", "level", "duration_years",
    "study_time", "faculty", "admission_requirements", "url",
    "tuition_national_ugx", "source_file",
]

CANONICAL_PROGRAMME_MAP = {
    "University": "university",
    "Course": "programme",
    "Qualification Level": "qualification_level",
    "Essential Subjects": "essential_subjects",
    "Minimum Grades": "minimum_grades",
    "Principal Passes": "principal_passes",
    "Cut-off Points": "cutoff_pairs",
    "Tuition Fees": "tuition_pairs",
    "Academic Year": "academic_year",
    "Official Source": "official_source",
    "Sponsorship": "sponsorship",
    "Citizenship Applicability": "citizenship_applicability",
    "Required UCE": "uce_requirement",
    "Subject Weights": "subject_weights",
    "Duration": "duration_years",
    "District/Region": "district_region",
    "Application Link": "application_link",
    "Data-Year": "data_year",
}

NCHE_REGISTER_MAP = {
    "No.": "no",
    "Institution": "institution",
    "Programme": "programme",
    "Type": "institution_type",
    "Level": "qualification_level",
    "Tier Discipline": "discipline",
    "Last Accreditation": "last_accreditation",
    "Due for Review": "due_for_review",
    "Review Year": "review_year",
    "District": "district",
}

NCHE_INSTITUTION_MAP = {
    "Name": "institution",
    "Institution Category": "category",
    "Accreditation Status": "accreditation_status",
    "District": "district",
    "Campuses": "campuses",
    "Programmes": "programme_count",
}

CATALOGUE_SPECS = [
    ("busitema_undergraduate_programmes.csv", "Busitema University", {
        "programme_name": "programme", "programme_code": "programme_code",
        "overview_url": "url", "description_excerpt": "description",
    }),
    ("gulu_university_undergraduate_programmes.csv", "Gulu University", {
        "Programme": "programme", "Code": "programme_code", "Duration": "duration_years",
        "Study time": "study_time", "URL": "url", "University": "university",
    }),
    ("kyambogo_undergraduate_programmes.csv", "Kyambogo University", {
        "Programme": "programme", "Prog Code (Day)": "programme_code",
        "Minimum Admission Requirements": "admission_requirements",
        "Duration": "duration_years", "School/Faculty": "faculty",
    }),
    ("must_undergraduate_programmes.csv", "Mbarara University of Science and Technology", {
        "Programme Name": "programme", "Code": "programme_code", "Duration": "duration_years",
        "Study Time": "study_time", "Level": "level",
    }),
    ("nkumba_university_programs.csv", "Nkumba University", {
        "Program": "programme", "Level": "level", "Duration": "duration_years", "URL": "url",
    }),
    ("ucu_undergraduate_programs_tuition.csv", "Uganda Christian University", {
        "Program": "programme", "Level": "level", "Duration (years)": "duration_years",
        "Tuition 2025 nationals (UGX) as listed": "tuition_national_ugx",
        "School/Faculty": "faculty", "Note": "notes",
    }),
    ("umu_bachelors_programmes.csv", "Uganda Martyrs University", {
        "Course": "programme", "Duration": "duration_years", "Fee Structure Source": "url",
    }),
]


def _load(name, base=DATA_DIR):
    return load_csv(os.path.join(base, name), na_filter=False)


def _write(frame, out_dir, filename):
    path = os.path.join(out_dir, filename)
    frame.to_csv(path, index=False)
    return path


def _classify_university(value):
    text = clean_mod.clean_text(value).lower()
    if not text:
        return ""
    return {
        "makerere university business school": "Makerere University Business School",
        "mubs": "Makerere University Business School",
        "makerere": "Makerere University",
        "kyambogo": "Kyambogo University",
        "gulu": "Gulu University",
        "busitema": "Busitema University",
        "mbarara": "Mbarara University of Science and Technology",
    }.get(text, clean_mod.clean_text(value))


def _clean_universities(out_dir, log):
    frame = _load("universities.csv")
    spec = {
        "source": "universities.csv",
        "mapping": {"name": "university"},
        "required": ["university"],
        "text_columns": ["university", "region", "district", "location", "website", "application_link"],
        "numeric_columns": ["established"],
    }
    result = clean_mod.clean_tabular(frame, spec)
    clean = result["clean"]
    clean["university"] = clean["university"].map(clean_mod.normalize_university)
    clean = clean.drop_duplicates(subset=["university"]).reset_index(drop=True)
    _write(clean, out_dir, "uniguide_universities_clean.csv")
    log["universities"] = {"rows_in": len(frame), "rows_out": len(clean)}
    return result, clean


def _clean_programmes(out_dir, log):
    frames = []
    column_report, missing, quarantine = [], [], []
    for name in ("programmes.csv", "programmes_mru.csv"):
        frame = _load(name)
        spec = {
            "source": name,
            "mapping": CANONICAL_PROGRAMME_MAP,
            "required": ["university", "programme"],
            "text_columns": ["university", "programme", "qualification_level", "academic_year",
                             "essential_subjects", "minimum_grades", "official_source",
                             "sponsorship", "citizenship_applicability", "district_region",
                             "application_link"],
            "numeric_columns": ["principal_passes", "duration_years"],
        }
        result = clean_mod.clean_tabular(frame, spec)
        clean = result["clean"]
        clean["university"] = clean["university"].map(clean_mod.normalize_university)
        clean["programme"] = clean["programme"].map(clean_mod.normalize_programme)
        clean["level"] = [clean_mod.derive_level(p) for p in clean["programme"]]

        gov_cut, priv_cut = zip(*clean["cutoff_pairs"].map(clean_mod.parse_cutoff_pairs)) if "cutoff_pairs" in clean else ([], [])
        clean["cutoff_government"] = list(gov_cut)
        clean["cutoff_private"] = list(priv_cut)
        gov_fee, priv_fee = zip(*clean["tuition_pairs"].map(clean_mod.parse_fee_pairs)) if "tuition_pairs" in clean else ([], [])
        clean["tuition_government"] = list(gov_fee)
        clean["tuition_private"] = list(priv_fee)
        clean["fees_verified"] = [bool(a or b) for a, b in zip(clean["tuition_government"], clean["tuition_private"])]
        clean["source_file"] = name
        for column in PROGRAMME_COLUMNS:
            if column not in clean.columns:
                clean[column] = ""
        frames.append(clean[PROGRAMME_COLUMNS])
        column_report.extend(result["column_report"])
        missing.extend(result["missing"])
        if len(result["quarantine"]):
            quarantine.append(result["quarantine"])

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=PROGRAMME_COLUMNS)
    dedup = dedupe_mod.dedupe(
        combined, ["university", "programme"],
        source="programmes",
        value_columns=["duration_years", "cutoff_government", "cutoff_private",
                       "tuition_government", "tuition_private", "academic_year"],
    )
    _write(dedup["clean"], out_dir, "uniguide_programmes_clean.csv")
    log["programmes"] = {"rows_in": len(combined), "rows_out": len(dedup["clean"]),
                         "duplicates": len(dedup["duplicates"])}
    return dedup, column_report, missing, quarantine


def _clean_catalogues(out_dir, log):
    prepared, column_report, quarantine = [], [], []
    for filename, university, mapping in CATALOGUE_SPECS:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            continue
        frame = _load(filename)
        spec = {
            "source": filename,
            "mapping": mapping,
            "required": ["programme"],
            "text_columns": ["programme", "programme_code", "study_time", "faculty",
                             "admission_requirements", "url", "level"],
            "numeric_columns": ["duration_years", "tuition_national_ugx"],
            "defaults": {"university": university},
        }
        result = clean_mod.clean_tabular(frame, spec)
        clean = result["clean"]
        clean["programme"] = clean["programme"].map(clean_mod.normalize_programme)
        clean["university"] = clean["university"].map(clean_mod.normalize_university)
        if "level" in clean.columns:
            clean["level"] = [
                clean_mod.derive_level(p, l) for p, l in zip(clean["programme"], clean["level"])
            ]
        else:
            clean["level"] = [clean_mod.derive_level(p) for p in clean["programme"]]
        clean["source_file"] = filename
        for column in CATALOGUE_COLUMNS:
            if column not in clean.columns:
                clean[column] = ""
        prepared.append(clean[CATALOGUE_COLUMNS])
        column_report.extend(result["column_report"])
        if len(result["quarantine"]):
            quarantine.append(result["quarantine"])

    combined = pd.concat(prepared, ignore_index=True) if prepared else pd.DataFrame(columns=CATALOGUE_COLUMNS)
    dedup = dedupe_mod.dedupe(
        combined, ["university", "programme", "level"],
        source="catalogues", value_columns=["programme_code", "duration_years", "url"],
    )
    _write(dedup["clean"], out_dir, "uniguide_catalogues_clean.csv")
    log["catalogues"] = {"rows_in": len(combined), "rows_out": len(dedup["clean"]),
                         "duplicates": len(dedup["duplicates"])}
    return dedup, column_report, quarantine


def _clean_careers(out_dir, log):
    frame = _load("careers.csv")
    spec = {
        "source": "careers.csv",
        "mapping": {"name": "career"},
        "required": ["career"],
        "text_columns": ["career", "description", "required_subjects", "skills", "pathways", "programmes"],
    }
    result = clean_mod.clean_tabular(frame, spec)
    clean = result["clean"].drop_duplicates(subset=["career"]).reset_index(drop=True)
    _write(clean, out_dir, "uniguide_careers_clean.csv")
    log["careers"] = {"rows_in": len(frame), "rows_out": len(clean)}
    return result, clean


def _clean_nche(out_dir, log):
    register_frames, institution_frames = [], []
    for filename in sorted(os.listdir(UNICAST_DIR)):
        if not filename.lower().startswith("tableexport") or not filename.lower().endswith(".csv"):
            continue
        frame = _load(filename, base=UNICAST_DIR)
        lowered = [str(c).lower() for c in frame.columns]
        if "institution category" in lowered:
            spec = {"source": filename, "mapping": NCHE_INSTITUTION_MAP,
                    "required": ["institution"],
                    "text_columns": ["institution", "category", "accreditation_status", "district"]}
            result = clean_mod.clean_tabular(frame, spec)
            institution_frames.append(result["clean"])
        else:
            spec = {"source": filename, "mapping": NCHE_REGISTER_MAP,
                    "required": ["institution", "programme"],
                    "text_columns": ["institution", "programme", "institution_type",
                                     "qualification_level", "discipline", "district"],
                    "numeric_columns": ["review_year"]}
            result = clean_mod.clean_tabular(frame, spec)
            register_frames.append(result["clean"])

    register = pd.concat(register_frames, ignore_index=True) if register_frames else pd.DataFrame()
    if not register.empty:
        register = register.map(lambda v: clean_mod.clean_text(v) if isinstance(v, str) else v)
        register["institution"] = register["institution"].map(clean_mod.normalize_university)
        register["programme"] = register["programme"].map(clean_mod.normalize_programme)
        register = register.drop_duplicates(subset=["institution", "programme", "qualification_level", "discipline"])
        register = register.sort_values(["institution", "programme"]).reset_index(drop=True)
    _write(register, out_dir, "uniguide_nche_register_clean.csv")

    institutions = pd.concat(institution_frames, ignore_index=True) if institution_frames else pd.DataFrame()
    if not institutions.empty:
        institutions["institution"] = institutions["institution"].map(clean_mod.normalize_university)
        institutions = institutions.drop_duplicates(subset=["institution"]).reset_index(drop=True)
    _write(institutions, out_dir, "uniguide_nche_institutions_clean.csv")

    log["nche_register"] = {"rows_in": sum(len(f) for f in register_frames), "rows_out": len(register)}
    log["nche_institutions"] = {"rows_in": sum(len(f) for f in institution_frames), "rows_out": len(institutions)}
    return register, institutions


def _extract_pdfs(out_dir, log):
    cutoff_rows, fee_rows, report = [], [], []
    for filename in sorted(os.listdir(UNICAST_DIR)):
        if not filename.lower().endswith(".pdf"):
            continue
        path = os.path.join(UNICAST_DIR, filename)
        lowered = filename.lower()
        if "fee" in lowered and "cut" not in lowered:
            rows, rep = extract_mod.extract_fees(path)
            fee_rows.extend(rows)
        elif "cut" in lowered and ("point" in lowered or "pujab" in lowered):
            rows, rep = extract_mod.extract_cutoffs(path)
            cutoff_rows.extend(rows)
        else:
            rep = {"file": filename, "pages": "", "status": "skipped",
                   "rows": 0, "method": "", "notes": "not a cut-off or fee document"}
        report.append(rep)

    cutoffs = pd.DataFrame(cutoff_rows)
    fees = pd.DataFrame(fee_rows)
    _write(cutoffs, out_dir, "extracted_cutoffs.csv")
    _write(fees, out_dir, "extracted_fees.csv")
    _write(pd.DataFrame(report), out_dir, "pdf_extraction_report.csv")
    log["pdf_extraction"] = {
        "cutoff_rows": len(cutoffs),
        "fee_rows": len(fees),
        "documents": len(report),
        "needs_review": sum(1 for r in report if r["status"] == "needs_review"),
    }
    return cutoffs, fees, report


def _build_merged(out_dir, programmes, catalogues, cutoffs, nche, log):
    programmes = programmes.copy()
    programmes["_key"] = programmes["programme"].map(lambda v: clean_mod.clean_text(v).lower())

    merged = programmes
    lineage = [{"stage": "start", "rows": len(merged)}]

    if not nche.empty:
        nche_small = nche.copy()
        nche_small["_key"] = nche_small["programme"].map(lambda v: clean_mod.clean_text(v).lower())
        nche_small = nche_small.drop_duplicates(subset=["_key"])
        attach = nche_small[["_key", "discipline", "institution_type", "review_year"]]
        merged = merged.merge(attach, on="_key", how="left", suffixes=("", "_nche"))
        merged = merged.rename(columns={"discipline": "nche_discipline",
                                        "institution_type": "nche_institution_type",
                                        "review_year": "nche_review_year"})
        lineage.append({"stage": "attach_nche_accreditation", "rows": len(merged)})

    if not cutoffs.empty:
        cuts = cutoffs.copy()
        cuts["_key"] = cuts["programme"].map(lambda v: clean_mod.clean_text(v).lower())
        cuts = cuts.drop_duplicates(subset=["_key"])
        cuts = cuts[["_key", "cutoff_primary", "scheme", "academic_year", "source_document"]]
        cuts = cuts.rename(columns={"cutoff_primary": "pdf_cutoff_primary",
                                    "academic_year": "pdf_academic_year",
                                    "source_document": "pdf_source_document"})
        merged = merged.merge(cuts, on="_key", how="left")
        lineage.append({"stage": "attach_pdf_cutoffs", "rows": len(merged)})

    merged = merged.drop(columns=["_key"])
    _write(merged, out_dir, "uniguide_merged_dataset.csv")
    log["merged"] = {"rows_out": len(merged), "stages": lineage}
    return merged, lineage


def _build_training(out_dir, register, log):
    if register.empty:
        _write(register, out_dir, "uniguide_training_dataset.csv")
        log["training"] = {"rows_out": 0}
        return register
    training = register[["programme", "institution", "qualification_level",
                         "institution_type", "discipline", "district"]].copy()
    training = training[training["discipline"].astype(str).str.strip() != ""]
    training = training.reset_index(drop=True)
    _write(training, out_dir, "uniguide_training_dataset.csv")
    log["training"] = {"rows_out": len(training),
                       "label": "discipline",
                       "classes": int(training["discipline"].nunique()) if len(training) else 0}
    return training


def run_pipeline(root=ROOT, run_id=None):
    out_dir = os.path.join(PROCESSED_DIR, run_id or datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_dir, exist_ok=True)
    log = {"run_id": os.path.basename(out_dir),
           "started": datetime.now().isoformat(timespec="seconds"),
           "data_dir": os.path.relpath(DATA_DIR, root)}
    column_report, quarantine_all, duplicate_report, missing_all, quality = [], [], [], [], []

    univ_result, universities = _clean_universities(out_dir, log)
    column_report.extend(univ_result["column_report"])
    missing_all.extend(univ_result["missing"])
    if len(univ_result["quarantine"]):
        quarantine_all.append(univ_result["quarantine"])

    prog_result, prog_cols, prog_missing, prog_quarantine = _clean_programmes(out_dir, log)
    column_report.extend(prog_cols)
    missing_all.extend(prog_missing)
    quarantine_all.extend(prog_quarantine)
    duplicate_report.extend(prog_result["duplicates"])

    cat_result, cat_cols, cat_quarantine = _clean_catalogues(out_dir, log)
    column_report.extend(cat_cols)
    quarantine_all.extend(cat_quarantine)
    duplicate_report.extend(cat_result["duplicates"])

    career_result, careers = _clean_careers(out_dir, log)
    column_report.extend(career_result["column_report"])

    register, institutions = _clean_nche(out_dir, log)
    cutoffs, fees, pdf_report = _extract_pdfs(out_dir, log)

    merged, lineage = _build_merged(out_dir, prog_result["clean"], cat_result["clean"],
                                    cutoffs, register, log)
    training = _build_training(out_dir, register, log)

    quality.append(validate_mod.validate_dataset(
        prog_result["clean"],
        {"name": "programmes", "required": ["university", "programme"],
         "key": ["university", "programme"], "year_column": "academic_year",
         "valid_years": CURRENT_YEARS, "source_column": "official_source",
         "grades_column": "minimum_grades", "min_rows": 10}))
    quality.append(validate_mod.validate_dataset(
        cat_result["clean"],
        {"name": "catalogues", "required": ["university", "programme"],
         "min_rows": 50}))
    quality.append(validate_mod.validate_dataset(
        register,
        {"name": "nche_register", "required": ["institution", "programme"],
         "label_column": "discipline", "min_rows": 100}))
    quality.append(validate_mod.validate_dataset(
        training,
        {"name": "training", "required": ["programme", "discipline"],
         "label_column": "discipline", "min_rows": 100}))

    quality_rows = [row for q in quality for row in q["findings"]]
    _write(pd.DataFrame(quality_rows), out_dir, "uniguide_data_quality_report.csv")
    _write(pd.DataFrame(column_report), out_dir, "column_mapping_report.csv")
    _write(pd.DataFrame(duplicate_report), out_dir, "duplicate_report.csv")
    _write(pd.DataFrame(missing_all), out_dir, "missing_values_report.csv")
    _write(pd.DataFrame(lineage), out_dir, "lineage_report.csv")
    if quarantine_all:
        _write(pd.concat(quarantine_all, ignore_index=True), out_dir, "quarantine_records.csv")
    else:
        _write(pd.DataFrame(), out_dir, "quarantine_records.csv")

    log["quality"] = {q["dataset"]: {"rows": q["rows"], "readiness": q["readiness"]} for q in quality}
    log["finished"] = datetime.now().isoformat(timespec="seconds")
    log["output_dir"] = os.path.relpath(out_dir, root)

    with open(os.path.join(out_dir, "processing_log.json"), "w", encoding="utf-8") as handle:
        json.dump(log, handle, indent=2)

    latest = os.path.join(PROCESSED_DIR, "latest.json")
    with open(latest, "w", encoding="utf-8") as handle:
        json.dump({"run_id": log["run_id"], "output_dir": log["output_dir"],
                   "finished": log["finished"]}, handle, indent=2)

    publish_cleaned(out_dir)
    return {"output_dir": out_dir, "log": log}


def publish_cleaned(out_dir=None):
    """Mirror the newest run's outputs into `data/cleaned/` for easy access.

    Old files in `data/cleaned/` are cleared first so it always reflects one run.
    Returns the destination directory.
    """
    if out_dir is None:
        out_dir = latest_run_dir()
    if not out_dir or not os.path.isdir(out_dir):
        return None
    os.makedirs(CLEANED_DIR, exist_ok=True)
    for name in os.listdir(CLEANED_DIR):
        path = os.path.join(CLEANED_DIR, name)
        if os.path.isfile(path):
            os.remove(path)
    for name in sorted(os.listdir(out_dir)):
        source = os.path.join(out_dir, name)
        if os.path.isfile(source):
            shutil.copy2(source, os.path.join(CLEANED_DIR, name))
    run_id = os.path.basename(out_dir)
    with open(os.path.join(CLEANED_DIR, "RUN.txt"), "w", encoding="utf-8") as handle:
        handle.write("Cleaned datasets from run: {0}\n"
                     "Regenerated by: python -m datapipeline.pipeline\n".format(run_id))
    return CLEANED_DIR


def latest_run_dir():
    pointer = os.path.join(PROCESSED_DIR, "latest.json")
    if not os.path.exists(pointer):
        return None
    with open(pointer, encoding="utf-8") as handle:
        return os.path.join(ROOT, json.load(handle)["output_dir"])


if __name__ == "__main__":
    result = run_pipeline()
    print("Pipeline finished: {0}".format(result["log"]["output_dir"]))
