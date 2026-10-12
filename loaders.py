"""
loaders.py

Nyaya - Multi-Format Document Loaders
=======================================
Each function below takes a file path and returns a list of plain Python
dicts: {"text": <string>, "metadata": {...}}.

Why one dict shape for every format? Because everything downstream
(chunking, embedding, storage) only needs to know "here is some text, and
here is where it came from" - it never needs to know whether that text
lived in a PDF, a Word document, an HTML page, a CSV row, or a JSON
record. That is the whole point of a document loader layer.

Kept deliberately simple and explainable:
  - PDF   -> PyMuPDF (fitz)       : one unit per page
  - Word  -> python-docx          : one unit for the whole document
  - HTML  -> BeautifulSoup        : one unit per <h2> section, plus header
  - CSV   -> built-in csv module  : one unit per row; "#" lines are the header
  - JSON  -> built-in json module : one unit per record in "filings"
"""
import csv
import json

import fitz  # PyMuPDF
import docx  # python-docx
from bs4 import BeautifulSoup


def load_pdf(filepath):
    """One unit per page - keeps citations pointing at a specific page."""
    units = []
    pdf = fitz.open(filepath)
    filename = filepath.split("/")[-1]
    for page_num, page in enumerate(pdf, start=1):
        text = page.get_text().strip()
        if text:
            units.append({
                "text": text,
                "metadata": {"source": filename, "page": page_num},
            })
    pdf.close()
    return units


def load_docx(filepath):
    """One unit for the whole document - the circular is short, and
    chunking splits it further. Headings are kept in the text."""
    d = docx.Document(filepath)
    lines = [p.text.strip() for p in d.paragraphs if p.text.strip()]
    filename = filepath.split("/")[-1]
    return [{
        "text": "\n".join(lines),
        "metadata": {"source": filename},
    }]


def load_html(filepath):
    """One header unit, then one unit per <h2> section. Each section
    includes every paragraph until the next <h2>, so a Q&A pair is never
    split apart."""
    filename = filepath.split("/")[-1]
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    units = []

    # Header unit: the <h1> title plus the document-id paragraph.
    h1 = soup.find("h1")
    meta = soup.find("p")
    header_text = " - ".join(
        t for t in [
            h1.get_text(strip=True) if h1 else "",
            meta.get_text(strip=True) if meta else "",
        ] if t
    )
    if header_text:
        units.append({
            "text": header_text,
            "metadata": {"source": filename, "section": "header"},
        })

    for h2 in soup.find_all("h2"):
        title = h2.get_text(strip=True)
        body_parts = []
        for sib in h2.find_next_siblings():
            if sib.name == "h2":
                break
            text = sib.get_text(" ", strip=True)
            if text:
                body_parts.append(text)
        section_text = title + "\n" + "\n".join(body_parts) if body_parts else title
        units.append({
            "text": section_text,
            "metadata": {"source": filename, "section": title},
        })
    return units


def load_csv(filepath):
    """One unit per row. Lines starting with '#' carry the document header
    (Document ID / Version / Effective Date) and are parsed separately -
    they never become rows."""
    filename = filepath.split("/")[-1]
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    header_meta = {}
    data_lines = []
    for line in lines:
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            if ":" in body:
                key, value = body.split(":", 1)
                header_meta[key.strip().lower().replace(" ", "_")] = value.strip()
        else:
            data_lines.append(line)

    reader = csv.DictReader(data_lines)
    units = []
    for row in reader:
        text = ", ".join(f"{k}: {v}" for k, v in row.items())
        units.append({
            "text": text,
            "metadata": {
                "source": filename,
                "row_id": row.get("audit_id", ""),
                "doc_id": header_meta.get("document_id", ""),
                "version": header_meta.get("version", ""),
                "effective_date": header_meta.get("effective_date", ""),
            },
        })
    return units


def load_json(filepath):
    """One unit for the report header, then one unit per filing record.
    Each record is stamped with the report date so that relative
    deadlines ("due within 30 days") stay answerable from any single
    retrieved record."""
    filename = filepath.split("/")[-1]
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    doc = data.get("document", {})
    as_of = data.get("as_of", "unknown")

    header = (
        f"{doc.get('title', 'Report')} - report as of {as_of}. "
        f"Document ID: {doc.get('id', '')} | Version: {doc.get('version', '')} | "
        f"Effective Date: {doc.get('effective_date', '')}. "
        f"All due dates in this report are compared against the report date of {as_of}."
    )
    units = [{
        "text": header,
        "metadata": {"source": filename, "section": "header"},
    }]

    for record in data.get("filings", []):
        text = ", ".join(f"{k}: {v}" for k, v in record.items())
        text = f"Report date: {as_of}, " + text
        units.append({
            "text": text,
            "metadata": {
                "source": filename,
                "filing_id": record.get("filing_id", ""),
                "status": record.get("status", ""),
            },
        })
    return units


# Dispatch table: pick the right loader based on file extension.
LOADERS = {
    ".pdf": load_pdf,
    ".docx": load_docx,
    ".html": load_html,
    ".csv": load_csv,
    ".json": load_json,
}


def load_document(filepath):
    """Single entry point - figures out which loader to use from the
    file extension."""
    ext = "." + filepath.rsplit(".", 1)[-1].lower()
    if ext not in LOADERS:
        raise ValueError(f"No loader registered for file type: {ext}")
    return LOADERS[ext](filepath)
