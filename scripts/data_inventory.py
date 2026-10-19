"""Scan every dataset/document in data/ and write a data inventory report.

Read-only: never modifies any source file. Run from the project root:

    python scripts/data_inventory.py
"""

import csv
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DOCS_DIR = os.path.join(ROOT, "docs")

TABULAR_EXT = {".csv", ".xlsx", ".xls"}
DOC_EXT = {".pdf", ".doc", ".docx"}

RELEVANCE = [
    ("seed", "Core seed schema - drives the live recommendation engine"),
    ("catalogue", "University programme catalogue - merges into the programme database"),
    ("nche-register", "NCHE accreditation register - programme/university reference data"),
    ("nche-institutions", "NCHE institution directory - university reference data"),
    ("cutoff-source", "Official cut-off points PDF - admission requirement source"),
    ("fees-source", "Official fee structure PDF - tuition source"),
    ("statutes", "Legal/statutory document - background reference only"),
    ("career", "Career guidance data - drives career matching"),
    ("education-stats", "Uganda education statistics - contextual, not a recommendation input"),
    ("ml-demo", "Generic ML demo dataset - not Uganda admission data"),
    ("project-doc", "Project documentation - not a data source"),
    ("other", "Not relevant to recommendations"),
]


def relevance_for(rel_path, columns=None):
    name = rel_path.lower()
    cols = [str(c).lower() for c in (columns or [])]
    if name.endswith("project_report.pdf"):
        return "project-doc"
    if "admission_predict" in name:
        return "ml-demo"
    if "bec-data" in name:
        return "education-stats"
    if name.endswith("universities.csv"):
        return "seed"
    if name.endswith("programmes.csv") or name.endswith("programmes_mru.csv"):
        return "seed"
    if name.endswith("careers.csv"):
        return "career"
    if "tableexport" in name:
        if "institution category" in " ".join(cols):
            return "nche-institutions"
        return "nche-register"
    if name.endswith(".pdf") or name.endswith(".pdf.pdf"):
        if "fee" in name or "fees" in name:
            return "fees-source"
        if "cut" in name and "point" in name:
            return "cutoff-source"
        if "act" in name:
            return "statutes"
        if "pujab" in name:
            return "cutoff-source"
        return "other"
    if name.endswith(".doc") or name.endswith(".docx"):
        return "cutoff-source" if "cut" in name else "other"
    if name.endswith(".csv"):
        if any(c in cols for c in ("programme_name", "programme", "course", "program")):
            return "catalogue"
        return "other"
    return "other"


def scan_csv(path):
    info = {"ok": True, "error": ""}
    try:
        import pandas as pd

        frame = pd.read_csv(path, low_memory=False)
        info["rows"] = len(frame)
        info["cols"] = len(frame.columns)
        info["columns"] = list(frame.columns)
        info["dtypes"] = {c: str(t) for c, t in frame.dtypes.items()}
        info["null_pct"] = {
            c: round(float(frame[c].isna().mean() * 100), 1) for c in frame.columns
        }
        info["dupe_rows"] = int(frame.duplicated().sum())
        info["preview"] = frame.head(2).astype(str).to_dict(orient="records")
    except Exception as exc:  # noqa: BLE001 - inventory must survive bad files
        info["ok"] = False
        info["error"] = str(exc)
    return info


def scan_excel(path):
    info = {"ok": True, "error": ""}
    try:
        import pandas as pd

        frame = pd.read_excel(path)
        info["rows"] = len(frame)
        info["cols"] = len(frame.columns)
        info["columns"] = list(frame.columns)
        info["dtypes"] = {c: str(t) for c, t in frame.dtypes.items()}
        info["null_pct"] = {
            c: round(float(frame[c].isna().mean() * 100), 1) for c in frame.columns
        }
        info["dupe_rows"] = int(frame.duplicated().sum())
    except Exception as exc:  # noqa: BLE001
        info["ok"] = False
        info["error"] = str(exc)
    return info


def scan_pdf(path):
    info = {"ok": True, "error": ""}
    try:
        import pdfplumber

        pages = 0
        text_pages = 0
        text_chars = 0
        table_pages = 0
        with pdfplumber.open(path) as pdf:
            pages = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_chars += len(text.strip())
                if text.strip():
                    text_pages += 1
                try:
                    if page.extract_tables():
                        table_pages += 1
                except Exception:  # noqa: BLE001
                    pass
        info["pages"] = pages
        info["text_pages"] = text_pages
        info["text_chars"] = text_chars
        info["table_pages"] = table_pages
        if pages and text_pages == 0:
            info["scan_note"] = "SCANNED / image-only - no selectable text"
        elif text_pages < pages:
            info["scan_note"] = "mixed: {0} of {1} pages have text".format(text_pages, pages)
        else:
            info["scan_note"] = "selectable text on all pages"
    except Exception as exc:  # noqa: BLE001
        info["ok"] = False
        info["error"] = str(exc)
    return info


def collect_files():
    entries = []
    for dirpath, _dirnames, filenames in os.walk(DATA_DIR):
        for filename in sorted(filenames):
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, ROOT)
            ext = os.path.splitext(filename)[1].lower()
            if ext not in TABULAR_EXT and ext not in DOC_EXT:
                continue
            entries.append((full, rel, ext))
    entries.append(
        (os.path.join(ROOT, "PROJECT_REPORT.pdf"), "PROJECT_REPORT.pdf", ".pdf")
    )
    return entries


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    rows = []
    details = []

    for full, rel, ext in collect_files():
        size = os.path.getsize(full)
        columns = None
        if ext == ".csv":
            info = scan_csv(full)
            columns = info.get("columns")
        elif ext in (".xlsx", ".xls"):
            info = scan_excel(full)
            columns = info.get("columns")
        elif ext == ".pdf":
            info = scan_pdf(full)
        else:
            info = {"ok": True, "note": "legacy Word binary - not parsed"}
        kind = relevance_for(rel, columns)
        label = dict(RELEVANCE).get(kind, kind)
        row = {
            "file": rel.replace("\\", "/"),
            "type": ext.lstrip("."),
            "size_kb": round(size / 1024, 1),
            "rows": info.get("rows", ""),
            "cols": info.get("cols", ""),
            "pages": info.get("pages", ""),
            "text": info.get("scan_note", ""),
            "duplicate_rows": info.get("dupe_rows", ""),
            "relevance": kind,
            "notes": info.get("error", ""),
        }
        rows.append(row)
        details.append((row, label, info))

    out_csv = os.path.join(DOCS_DIR, "data_inventory.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# UniGuide Uganda - Data Inventory Report",
        "",
        "Generated: {0} by `scripts/data_inventory.py` (read-only scan)".format(stamp),
        "",
        "| File | Type | Size (KB) | Rows | Cols | Pages | Text | Dup rows | Relevance | Notes |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {file} | {type} | {size_kb} | {rows} | {cols} | {pages} | {text} | "
            "{duplicate_rows} | {relevance} | {notes} |".format(**row)
        )

    lines += ["", "## Classification key", ""]
    for key, description in RELEVANCE:
        lines.append("- **{0}** - {1}".format(key, description))

    lines += ["", "## Column detail (tabular files)", ""]
    for row, _label, info in details:
        if not info.get("columns"):
            continue
        lines.append("### `{0}`".format(row["file"]))
        lines.append("")
        lines.append("| Column | Type | Missing % |")
        lines.append("|---|---|---|")
        for column in info["columns"]:
            lines.append(
                "| {0} | {1} | {2} |".format(
                    column, info["dtypes"].get(column, "?"), info["null_pct"].get(column, "?")
                )
            )
        lines.append("")

    lines += [
        "## Key observations",
        "",
        "- The three `gulu_university_undergraduate_programmes*.csv` files hold the same 54",
        "  programmes (one adds a University column) - deduplication required.",
        "- `data/Unicast datasets/tableExport*.csv` are 100-row chunks of one NCHE",
        "  accreditation export - must be concatenated then de-duplicated before use.",
        "- `Admission_Predict.csv` is the public GRE/TOEFL Kaggle demo set; it contains no",
        "  Ugandan admission outcomes and is excluded from the production pipeline.",
        "- Image-only PDFs cannot be parsed as text and are flagged for human review",
        "  (no OCR engine is installed on this machine).",
        "",
    ]

    out_md = os.path.join(DOCS_DIR, "data_inventory.md")
    with open(out_md, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print("Wrote {0} ({1} files)".format(os.path.relpath(out_md, ROOT), len(rows)))
    print("Wrote {0}".format(os.path.relpath(out_csv, ROOT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
