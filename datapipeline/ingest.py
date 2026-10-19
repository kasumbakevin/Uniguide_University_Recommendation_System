"""Safe ingestion of CSV, Excel and PDF files.

All functions operate on provided paths and never modify the source file.
Upload handlers are used by the admin dashboard; they enforce extension,
size and filename rules before a file is stored.
"""

import os
import re
import unicodedata

import pandas as pd

ALLOWED_TABULAR = {".csv", ".xlsx", ".xls"}
ALLOWED_PDF = {".pdf"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")


class IngestError(ValueError):
    """Raised when a file cannot be safely ingested."""


def safe_filename(name):
    """Return a filesystem-safe filename (no paths, no traversal, no control chars)."""
    name = unicodedata.normalize("NFKD", str(name or ""))
    name = os.path.basename(name.replace("\\", "/"))
    name = SAFE_NAME.sub("_", name).strip(" .")
    if not name:
        raise IngestError("Empty or invalid filename.")
    if name.startswith("."):
        name = "file" + name
    return name[:180]


def validate_upload(filename, size, allowed):
    """Validate an upload without touching the filesystem."""
    safe = safe_filename(filename)
    ext = os.path.splitext(safe)[1].lower()
    if ext not in allowed:
        raise IngestError("Unsupported file type: {0}".format(ext or "none"))
    if size is None or size <= 0:
        raise IngestError("File is empty.")
    if size > MAX_UPLOAD_BYTES:
        raise IngestError("File exceeds the {0} MB limit.".format(MAX_UPLOAD_BYTES // (1024 * 1024)))
    return safe


def load_csv(path, **kwargs):
    kwargs.setdefault("low_memory", False)
    try:
        return pd.read_csv(path, **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", **kwargs)


def load_excel(path, sheet=0, **kwargs):
    return pd.read_excel(path, sheet_name=sheet, **kwargs)


def load_tabular(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return load_csv(path)
    if ext in (".xlsx", ".xls"):
        return load_excel(path)
    raise IngestError("Not a tabular file: {0}".format(ext or "none"))


def open_pdf(path):
    """Open a PDF with pdfplumber. The caller is responsible for closing it."""
    import pdfplumber

    return pdfplumber.open(path)
