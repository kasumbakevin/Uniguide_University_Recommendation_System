"""PDF text and table extraction for official cut-off points and fee documents.

The extractor is intentionally conservative: it records a row only when a
programme cell plus a numeric cut-off (or fee) are both found, keeps the raw
column values alongside the parsed value, and reports confidence. Scanned
(image-only) documents are detected and flagged for human review instead of
being silently skipped.
"""

import json
import os
import re

from datapipeline.ingest import open_pdf

PROGRAMME_WORDS = (
    "bachelor", "diploma", "master", "doctor", "phd", "certificate",
    "postgraduate", "programme", "degree",
)
CODE_RE = re.compile(r"^[A-Z]{2,5}$")
NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
YEAR_RE = re.compile(r"(20\d{2})\s*[-/]\s*(\d{2,4})")


def detect_years(filename):
    """Return academic years found in a filename, e.g. ['2026/27']."""
    years = []
    for start, end in YEAR_RE.findall(filename):
        if len(end) == 2:
            end = start[:2] + end
        years.append("{0}/{1}".format(start, end[-2:]))
    return years


def detect_scheme(filename):
    name = filename.lower()
    if "government" in name:
        return "government"
    if "national-merit" in name or "national merit" in name or "merit" in name:
        return "national merit"
    if "private" in name:
        return "private"
    if "pujab" in name:
        return "government"
    return "unspecified"


def detect_institution(filename, text=""):
    haystack = (filename + " " + text).lower()
    if "mubs" in haystack and "mak" not in haystack:
        return "Makerere University Business School"
    if "makerere" in haystack or "mak" in haystack:
        return "Makerere University"
    if "kyambogo" in haystack:
        return "Kyambogo University"
    if "gulu" in haystack:
        return "Gulu University"
    if "busitema" in haystack:
        return "Busitema University"
    if "mbarara" in haystack or "must" in haystack:
        return "Mbarara University of Science and Technology"
    return ""


UNIV_MAP = {
    "mak": "Makerere University",
    "mubs": "Makerere University Business School",
    "kyu": "Kyambogo University",
    "gui": "Gulu University",
    "gu": "Gulu University",
    "bus": "Busitema University",
    "bsu": "Busitema University",
    "mbar": "Mbarara University of Science and Technology",
    "must": "Mbarara University of Science and Technology",
}

# Short institution codes that appear in cut-off tables.
CODE_INSTITUTION = {
    "MAK": "Makerere University",
    "MUBS": "Makerere University Business School",
    "KYU": "Kyambogo University",
    "GU": "Gulu University",
    "GUI": "Gulu University",
    "BSU": "Busitema University",
    "MUST": "Mbarara University of Science and Technology",
    "MUR": "Muteesa I Royal University",
}


def _is_number(value):
    return bool(value) and bool(NUMBER_RE.match(str(value).strip()))


def _strip_institution(programme):
    """Remove trailing institution tokens that leak into programme cells."""
    text = str(programme).strip()
    for token in (" MUBS", " MUBS.", " Mak.", " Mak", " MAK", " KYU", " GU", " BSU"):
        if text.endswith(token):
            text = text[: -len(token)].strip()
    return text


def _header_index(table):
    for index, row in enumerate(table[:6]):
        cells = [str(c or "").lower() for c in row]
        joined = " ".join(cells)
        if "programme" in joined and ("point" in joined or "code" in joined or "off" in joined):
            return index
    return None


def _parse_table(table, page_number, filename, scheme, years, institution_default):
    rows = []
    header_index = _header_index(table)
    if header_index is None:
        return rows

    header = [str(c or "").replace("\n", " ").strip() for c in table[header_index]]
    subheader = table[header_index + 1] if header_index + 1 < len(table) else []
    labels = []
    for col, label in enumerate(header):
        sub = str(subheader[col] or "").replace("\n", " ").strip() if col < len(subheader) else ""
        labels.append((label + " " + sub).strip().lower())

    prog_col = next((i for i, l in enumerate(labels) if "programme" in l), 1)
    code_col = next((i for i, l in enumerate(labels) if "code" in l), None)
    univ_col = next((i for i, l in enumerate(labels)
                     if l.strip() in ("univ", "university", "inst", "institution")), None)

    for row in table[header_index + 1:]:
        if not row or all(not c for c in row):
            continue
        programme = str(row[prog_col] or "").strip() if prog_col < len(row) else ""
        if not programme or len(programme) < 4:
            continue
        if programme.lower() in ("programme", "programmes"):
            continue
        if not any(word in programme.lower() for word in PROGRAMME_WORDS):
            continue

        code = ""
        if code_col is not None and code_col < len(row):
            candidate = str(row[code_col] or "").strip()
            if CODE_RE.match(candidate):
                code = candidate
        if not code:
            for cell in row:
                cell = str(cell or "").strip()
                if CODE_RE.match(cell):
                    code = cell
                    break

        values = {}
        for col, cell in enumerate(row):
            if col == 0 or col in (prog_col, code_col, univ_col):
                continue
            if not _is_number(cell):
                continue
            label = labels[col] if col < len(labels) else ""
            if not label.strip():
                continue
            values[label.strip()] = float(str(cell).strip())

        if not values:
            continue

        primary = None
        for key, value in values.items():
            if "all" in key or "other" in key:
                primary = value
                break
        if primary is None:
            male = [k for k in values if "male" in k or k.endswith(" m")]
            if male:
                primary = values[male[0]]
        if primary is None:
            primary = list(values.values())[0]

        institution = institution_default
        if univ_col is not None and univ_col < len(row):
            token = str(row[univ_col] or "").strip().lower()
            institution = UNIV_MAP.get(token, institution) or institution
        for cell in row:
            token = str(cell or "").strip()
            if token in CODE_INSTITUTION:
                institution = CODE_INSTITUTION[token]
                break
        if "mubs" in programme.lower():
            institution = "Makerere University Business School"
        programme = _strip_institution(programme)

        rows.append({
            "institution": institution,
            "programme": programme,
            "programme_code": code,
            "cutoff_primary": primary,
            "cutoff_raw": json.dumps(values, ensure_ascii=False),
            "scheme": scheme,
            "academic_year": years[0] if years else "",
            "source_document": os.path.basename(filename),
            "page_number": page_number,
            "extraction_method": "table",
            "confidence": "high" if code else "medium",
        })
    return rows


TEXT_LINE_RE = re.compile(
    r"^(?:\(?[ivxIVX]+\)?[\.\)]?\s*)?(?:\d+[\.\)]?\s*)?"
    r"([A-Z].{6,}?)\s+([A-Z]{2,5})\s+(\d{1,2}\.\d)\s*$"
)


def _parse_text(text, page_number, filename, scheme, years, institution_default):
    rows = []
    for line in (text or "").splitlines():
        line = line.strip()
        match = TEXT_LINE_RE.match(line)
        if not match:
            continue
        programme, code, cutoff = match.groups()
        if not any(word in programme.lower() for word in PROGRAMME_WORDS):
            continue
        rows.append({
            "institution": institution_default,
            "programme": programme.strip(),
            "programme_code": code,
            "cutoff_primary": float(cutoff),
            "cutoff_raw": json.dumps({"cut-off": float(cutoff)}),
            "scheme": scheme,
            "academic_year": years[0] if years else "",
            "source_document": os.path.basename(filename),
            "page_number": page_number,
            "extraction_method": "text",
            "confidence": "medium",
        })
    return rows


def extract_cutoffs(path):
    """Extract cut-off rows from one PDF. Returns (rows, report)."""
    filename = os.path.basename(path)
    scheme = detect_scheme(filename)
    years = detect_years(filename)
    rows = []
    pages = 0
    text_pages = 0
    table_pages = 0
    scanned_pages = 0

    try:
        with open_pdf(path) as pdf:
            pages = len(pdf.pages)
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    text_pages += 1
                else:
                    scanned_pages += 1
                institution = detect_institution(filename, text)
                try:
                    tables = page.extract_tables() or []
                except Exception:  # noqa: BLE001
                    tables = []
                page_rows = []
                for table in tables:
                    page_rows.extend(_parse_table(table, index, filename, scheme, years, institution))
                if page_rows:
                    table_pages += 1
                else:
                    page_rows = _parse_text(text, index, filename, scheme, years, institution)
                rows.extend(page_rows)
    except Exception as exc:  # noqa: BLE001
        return [], {
            "file": filename,
            "pages": 0,
            "status": "error",
            "rows": 0,
            "method": "",
            "notes": str(exc),
        }

    methods = sorted({row["extraction_method"] for row in rows})
    if pages and text_pages == 0:
        status = "needs_review"
        notes = "Scanned/image-only PDF - no selectable text, OCR not available. Flagged for human review."
    elif not rows:
        status = "no_rows"
        notes = "No programme cut-off rows detected."
    elif len(rows) < 5:
        status = "low_yield"
        notes = "Few rows extracted; verify manually."
    else:
        status = "extracted"
        notes = "{0} page(s) with text, {1} with tables.".format(text_pages, table_pages)

    return rows, {
        "file": filename,
        "pages": pages,
        "status": status,
        "rows": len(rows),
        "method": "+".join(methods),
        "notes": notes,
    }


FEE_LINE_RE = re.compile(
    r"^\(?[ivxIVX]+\)?[\.\)]?\s*([A-Z]{3})\s+(.{6,}?)\s+"
    r"(\d+)\s*Year[s]?\s+([\d,]+(?:\.\d{2})?)\s+([\d,]+(?:\.\d{2})?)\s*$"
)


def extract_fees(path):
    """Extract per-programme fee rows from a text-based fee PDF."""
    filename = os.path.basename(path)
    years = detect_years(filename)
    institution = detect_institution(filename)
    rows = []
    pages = 0
    text_pages = 0

    try:
        with open_pdf(path) as pdf:
            pages = len(pdf.pages)
            for index, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                text_pages += 1
                for line in text.splitlines():
                    match = FEE_LINE_RE.match(line.strip())
                    if not match:
                        continue
                    code, name, duration, national, international = match.groups()
                    rows.append({
                        "institution": institution,
                        "programme": name.strip(),
                        "programme_code": code,
                        "duration_years": int(duration),
                        "tuition_national_ugx": float(national.replace(",", "")),
                        "tuition_international_ugx": float(international.replace(",", "")),
                        "fee_period": "semester",
                        "academic_year": years[0] if years else "",
                        "source_document": filename,
                        "page_number": index,
                        "confidence": "medium",
                    })
    except Exception as exc:  # noqa: BLE001
        return [], {"file": filename, "pages": 0, "status": "error", "rows": 0, "method": "", "notes": str(exc)}

    if pages and text_pages == 0:
        status, notes = "needs_review", "Scanned/image-only PDF - flagged for human review."
    elif not rows:
        status, notes = "no_rows", "Fee lines not matched by the parser."
    else:
        status, notes = "extracted", "{0} fee row(s) parsed from text.".format(len(rows))

    return rows, {
        "file": filename,
        "pages": pages,
        "status": status,
        "rows": len(rows),
        "method": "text" if rows else "",
        "notes": notes,
    }
