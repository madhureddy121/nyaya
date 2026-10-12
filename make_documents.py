"""
make_documents.py

Nyaya - Generate the Five Fictional Source Documents
======================================================
Creates the five legal & compliance documents used by the Nyaya pipeline,
one per file format, each following the same header convention:

    Document ID / Version / Effective Date

Run once from the repo root:
    python make_documents.py

Outputs (into documents/):
    01_msa_excerpt.pdf                       PyMuPDF (multi-page PDF)
    02_regulatory_compliance_circular.docx   python-docx
    03_legal_faq.html                        plain file write
    04_compliance_audit_log.csv              csv module ("#" metadata header)
    05_regulatory_filing_tracker.json        json module

All content is fictional, prepared for this training lab. Not legal advice.
"""
import csv
import json
import os
import textwrap

import fitz   # PyMuPDF
import docx   # python-docx

OUT_DIR = "documents"


# --------------------------------------------------------------------- PDF ---

MSA_BLOCKS = [
    ("title", "Master Service Agreement (Excerpt)"),
    ("meta", "Document ID: NCS-LC-MSA-001 | Version: 4.1 | Effective Date: 01 April 2026"),
    ("note", "Fictional sample document prepared for the Nyaya training lab. Not legal advice, and not a real agreement."),
    ("h", "1. Scope"),
    ("p", "This excerpt from the Master Service Agreement (the \"Agreement\") governs the enterprise network services provided by NCS Telco+ to the Customer. It sets out fees and payment terms, the limitation of liability, indemnities, and governing law. Capitalised terms have the meanings given in the full Agreement."),
    ("h", "2. Fees and Payment"),
    ("p", "All invoices are payable within thirty (30) days of receipt. Late payments accrue interest at 1.5% per month on the outstanding amount. Fees are exclusive of applicable taxes."),
    ("pagebreak", ""),
    ("h", "3. Limitation of Liability"),
    ("p", "Except for the indemnities in Section 4, the aggregate liability of either party under this Agreement, whether in contract, tort, or otherwise, shall not exceed the total fees paid or payable by the Customer in the twelve (12) months immediately preceding the event giving rise to the claim. Neither party shall be liable for indirect, incidental, or consequential damages, including loss of profits, revenue, or data."),
    ("h", "4. Indemnification"),
    ("p", "Each party (the \"Indemnifying Party\") shall indemnify the other against third-party claims arising from: (a) infringement of intellectual property rights; (b) breach of confidentiality obligations; (c) gross negligence or wilful misconduct; and (d) breach of applicable data protection laws. The indemnified party must notify the Indemnifying Party promptly and must not settle any claim without the Indemnifying Party's consent."),
    ("pagebreak", ""),
    ("h", "5. Governing Law and Jurisdiction"),
    ("p", "This Agreement is governed by the laws of India. The courts at Mumbai shall have exclusive jurisdiction over any dispute arising out of or in connection with this Agreement."),
    ("h", "6. Term and Termination"),
    ("p", "The initial term is thirty-six (36) months from the Effective Date, renewing automatically for successive twelve (12) month periods unless either party gives ninety (90) days' written notice. Either party may terminate for material breach if the breach is not cured within thirty (30) days of written notice."),
    ("h", "Execution"),
    ("p", "Signed for and on behalf of NCS Telco+. Authorised signatory PAN on record: QWERT4821M."),
]


def render_pdf(path, blocks):
    doc = fitz.open()
    page = doc.new_page()
    y = 72

    for kind, text in blocks:
        if kind == "pagebreak":
            page = doc.new_page()
            y = 72
            continue

        if kind == "title":
            font, size = "hebo", 14
        elif kind == "meta":
            font, size = "helv", 9
        elif kind == "note":
            font, size = "heit", 9
        elif kind == "h":
            font, size = "hebo", 11
        else:  # paragraph
            font, size = "helv", 10

        for line in textwrap.wrap(text, width=92) or [""]:
            if y > 770:
                page = doc.new_page()
                y = 72
            page.insert_text((72, y), line, fontsize=size, fontname=font)
            y += size + 4
        y += 6

    doc.save(path)
    doc.close()


# -------------------------------------------------------------------- DOCX ---

CIRCULAR_SECTIONS = [
    ("1. Purpose",
     "This circular sets out the periodic reporting obligations applicable to holders of the Unified Network Services licence, and the penalties that apply to late filing."),
    ("2. Quarterly Compliance Report (QCR)",
     "Licensees must submit a Quarterly Compliance Report (QCR) within fifteen (15) days of the end of each financial quarter. For the quarter ended 30 September 2026, the QCR must be submitted by 15 October 2026. Reports must be filed through the NTRB e-filing portal, and a copy must be retained by the Licensee's Legal & Compliance team."),
    ("3. Penalty for Late Filing",
     "A late fee of Rs 25,000 per calendar day applies to each late QCR, capped at Rs 5,00,000 per report. Three or more late filings in a single financial year may trigger a licence review."),
    ("4. Annual Network Audit Certificate",
     "Licensees must file an annual network audit certificate by 31 December each year, covering the network as operated on 30 November."),
    ("5. Queries",
     "Queries about this circular may be raised through the NTRB portal. Licensees should not approach NTRB officers directly outside the portal."),
]


def render_docx(path):
    d = docx.Document()
    d.add_heading("National Telecom Regulatory Bureau (NTRB)", level=1)
    d.add_heading("Compliance Circular NTRB/2026/07 - Quarterly Compliance Reporting", level=2)
    d.add_paragraph("Document ID: NCS-LC-REG-002 | Version: 2.0 | Effective Date: 01 July 2026")
    d.add_paragraph("Fictional regulator and fictional requirements, prepared for the Nyaya training lab. Not legal advice.")
    for heading, body in CIRCULAR_SECTIONS:
        d.add_heading(heading, level=2)
        d.add_paragraph(body)
    d.save(path)


# -------------------------------------------------------------------- HTML ---

FAQ_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Legal &amp; Compliance - Contract Lifecycle Portal FAQ</title>
</head>
<body>
  <h1>Legal &amp; Compliance - Contract Lifecycle Portal FAQ</h1>
  <p>Document ID: NCS-LC-FAQ-003 | Version: 5.0 | Effective Date: 15 August 2026</p>
  <h2>How do I request a contract review?</h2>
  <p>Raise a review request from the Contract Lifecycle Portal, attach the draft or deal summary, and select the counterparty risk tier. Requests are triaged daily by the Legal Operations team.</p>
  <h2>How do I request an urgent contract review?</h2>
  <p>Mark the request as "Urgent" in the portal and attach your department head's approval note. Urgent requests are triaged within one business hour of submission.</p>
  <h2>What are the standard and expedited turnaround times?</h2>
  <p>A standard review takes five (5) business days from triage. An expedited review takes 48 hours (two business days) from triage, and requires the approval described above.</p>
  <h2>Who do I contact for an urgent escalation?</h2>
  <p>Escalate through Rohan Mehta, Senior Legal Counsel - email rohan.mehta@ncstelco.example, phone +91-98201-44567. Outside business hours, use the same number and follow the on-call prompts.</p>
  <h2>What approvals are required for contract deviations?</h2>
  <p>Any deviation from standard terms requires Legal approval and Deal Desk sign-off. Discounts above 15 percent additionally require CFO approval.</p>
</body>
</html>
"""


def render_html(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(FAQ_HTML)


# --------------------------------------------------------------------- CSV ---

AUDIT_ROWS = [
    ["AUD-2026-011", "2026-06-10", "Network Security", "Firewall rules review was overdue by two quarters", "High", "Closed"],
    ["AUD-2026-014", "2026-06-24", "Change Management", "Two emergency changes had no post-implementation review", "Medium", "Closed"],
    ["AUD-2026-016", "2026-07-08", "Data Protection", "Consent records missing for 12 marketing contacts", "Medium", "Closed"],
    ["AUD-2026-018", "2026-07-30", "Vendor Management", "NDA renewals overdue for 3 active suppliers", "Medium", "Open"],
    ["AUD-2026-020", "2026-08-06", "Business Continuity", "DR test evidence not documented for Q1", "Low", "Closed"],
    ["AUD-2026-021", "2026-08-12", "Data Protection", "Retention schedule not applied to legacy CRM exports", "High", "Open"],
    ["AUD-2026-023", "2026-09-03", "Access Control", "Quarterly access review for the finance share was not completed", "High", "Open"],
    ["AUD-2026-025", "2026-09-18", "Training", "Compliance training completion below the 90 percent threshold in the NOC team", "Low", "Open"],
]


def render_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write("# Document ID: NCS-LC-AUD-004\n")
        f.write("# Version: 1.3\n")
        f.write("# Effective Date: 2026-08-01\n")
        writer = csv.writer(f)
        writer.writerow(["audit_id", "date", "area_audited", "finding", "severity", "status"])
        writer.writerows(AUDIT_ROWS)


# -------------------------------------------------------------------- JSON ---

FILING_TRACKER = {
    "document": {
        "id": "NCS-LC-TRK-005",
        "title": "Regulatory Filing Tracker",
        "version": "3.2",
        "effective_date": "2026-10-01",
    },
    "as_of": "2026-10-01",
    "filings": [
        {
            "filing_id": "FIL-2026-011",
            "jurisdiction": "Maharashtra",
            "description": "Quarterly GST return (GSTR-3B) for the quarter ended 30 September 2026",
            "due_date": "2026-09-20",
            "status": "Overdue",
            "notes": "Missed the 2026-09-20 deadline; late fee exposure flagged to Finance.",
        },
        {
            "filing_id": "FIL-2026-012",
            "jurisdiction": "Central",
            "description": "Quarterly compliance report (QCR) to NTRB for the quarter ended 30 September 2026",
            "due_date": "2026-10-15",
            "status": "In Progress",
            "notes": "Draft under review by Legal; due within 30 days of the 2026-10-01 report date.",
        },
        {
            "filing_id": "FIL-2026-009",
            "jurisdiction": "Central",
            "description": "Annual safety compliance certificate renewal",
            "due_date": "2026-10-20",
            "status": "Due Soon",
            "notes": "Due within 30 days of the 2026-10-01 report date.",
        },
        {
            "filing_id": "FIL-2026-014",
            "jurisdiction": "Tamil Nadu",
            "description": "Tower infrastructure annual return",
            "due_date": "2026-11-30",
            "status": "Pending",
            "notes": "No action required before November; owner assigned.",
        },
        {
            "filing_id": "FIL-2026-016",
            "jurisdiction": "Central",
            "description": "Annual network audit certificate",
            "due_date": "2026-12-31",
            "status": "Pending",
            "notes": "Audit fieldwork scheduled for November.",
        },
        {
            "filing_id": "FIL-2026-010",
            "jurisdiction": "Gujarat",
            "description": "Spectrum usage fee statement for FY2025-26",
            "due_date": "2026-08-31",
            "status": "Submitted",
            "notes": "Submitted on 2026-08-28; acknowledgement received.",
        },
    ],
}


def render_json(path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(FILING_TRACKER, f, indent=2)
        f.write("\n")


# -------------------------------------------------------------------- main ---

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = {
        "01_msa_excerpt.pdf": lambda p: render_pdf(p, MSA_BLOCKS),
        "02_regulatory_compliance_circular.docx": render_docx,
        "03_legal_faq.html": render_html,
        "04_compliance_audit_log.csv": render_csv,
        "05_regulatory_filing_tracker.json": render_json,
    }
    for name, fn in files.items():
        path = os.path.join(OUT_DIR, name)
        fn(path)
        print(f"wrote {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
