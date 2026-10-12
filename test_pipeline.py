"""
test_pipeline.py

Nyaya - Offline Smoke Tests (no API key needed)
=================================================
Checks the parts of the pipeline that do NOT require OpenAI: loaders,
PII redaction, chunking, context assembly, and the retrieval dispatch
table. Run it after cloning or editing, before spending any API credits:

    python test_pipeline.py
"""
import glob
import os
import sys

from langchain_core.documents import Document

from loaders import load_document
from pii import redact_pii
from chunking import chunk_text, STRATEGIES
from context import assemble_context
from retrieval import PATTERNS, retrieve

DOCS = sorted(glob.glob("documents/*"))

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def main():
    print("=" * 64)
    print("Nyaya - offline smoke tests (no API key needed)")
    print("=" * 64)

    # --- loaders ------------------------------------------------------
    print("\n[loaders]")
    check("5 source documents found", len(DOCS) == 5, f"found {len(DOCS)}")

    units_by_source = {}
    for path in DOCS:
        units = load_document(path)
        name = os.path.basename(path)
        units_by_source[name] = units
        check(f"{name}: loads at least 1 unit", len(units) >= 1, f"got {len(units)}")

    check("PDF loads 3 pages",
          len(units_by_source["01_msa_excerpt.pdf"]) == 3,
          f"got {len(units_by_source['01_msa_excerpt.pdf'])}")
    check("HTML loads header + 5 sections",
          len(units_by_source["03_legal_faq.html"]) == 6,
          f"got {len(units_by_source['03_legal_faq.html'])}")
    check("CSV loads 8 rows",
          len(units_by_source["04_compliance_audit_log.csv"]) == 8,
          f"got {len(units_by_source['04_compliance_audit_log.csv'])}")
    check("JSON loads header + 6 filings",
          len(units_by_source["05_regulatory_filing_tracker.json"]) == 7,
          f"got {len(units_by_source['05_regulatory_filing_tracker.json'])}")

    # --- PII redaction ------------------------------------------------
    print("\n[pii]")
    totals = {}
    faq_redacted = []
    for name, units in units_by_source.items():
        for unit in units:
            redacted, counts = redact_pii(unit["text"])
            for label, count in counts.items():
                totals[label] = totals.get(label, 0) + count
            if name == "03_legal_faq.html" and "REDACTED" in redacted:
                faq_redacted.append(redacted)

    check("exactly 1 email redacted across all docs", totals.get("EMAIL") == 1, f"got {totals}")
    check("exactly 1 Indian phone redacted across all docs",
          totals.get("PHONE_INDIA") == 1, f"got {totals}")
    check("exactly 1 PAN-style ID redacted across all docs",
          totals.get("PAN_LIKE_ID") == 1, f"got {totals}")
    check("FAQ contact section contains [REDACTED_EMAIL]",
          any("[REDACTED_EMAIL]" in t for t in faq_redacted))
    check("FAQ contact section contains [REDACTED_PHONE_INDIA]",
          any("[REDACTED_PHONE_INDIA]" in t for t in faq_redacted))
    check("raw email no longer present after redaction",
          not any("rohan.mehta@ncstelco.example" in t for t in faq_redacted))

    # --- document facts (the answers depend on these) -----------------
    print("\n[document facts]")

    def all_text(name):
        return "\n".join(u["text"] for u in units_by_source[name])

    msa = all_text("01_msa_excerpt.pdf")
    check("MSA contains the 'twelve (12) months' liability cap",
          "twelve (12) months" in msa)

    circular = all_text("02_regulatory_compliance_circular.docx")
    check("circular contains the deadline '15 October 2026'",
          "15 October 2026" in circular)

    faq = all_text("03_legal_faq.html")
    check("FAQ contains the standard turnaround 'five (5) business days'",
          "five (5) business days" in faq)

    csv_units = units_by_source["04_compliance_audit_log.csv"]
    opens = [u for u in csv_units if "status: Open" in u["text"]]
    check("audit log has at least 3 Open findings", len(opens) >= 3, f"got {len(opens)}")

    json_units = units_by_source["05_regulatory_filing_tracker.json"]
    check("filing tracker has one Overdue filing",
          sum(1 for u in json_units if "status: Overdue" in u["text"]) == 1)
    check("filing tracker has a filing flagged due within 30 days",
          any("Due Soon" in u["text"] for u in json_units))

    # --- chunking -----------------------------------------------------
    print("\n[chunking]")
    for name in STRATEGIES:
        chunks = chunk_text(msa, strategy=name)
        check(f"strategy '{name}' produces at least 1 chunk from the MSA",
              len(chunks) >= 1, f"got {len(chunks)}")

    heading = chunk_text(msa, strategy="heading_aware")
    check("heading_aware keeps the liability clause (with the cap) whole",
          any(c.startswith("3. Limitation of Liability") and "twelve (12) months" in c
              for c in heading))

    overlap = chunk_text(msa, strategy="overlap")
    fixed = chunk_text(msa, strategy="fixed")
    check("overlap chunk count >= fixed chunk count",
          len(overlap) >= len(fixed), f"fixed={len(fixed)} overlap={len(overlap)}")

    # --- context assembly ----------------------------------------------
    print("\n[context]")
    d1 = Document(page_content="Clause 3 covers the twelve (12) month liability cap.",
                  metadata={"source": "msa.pdf"})
    d2 = Document(page_content="Clause 3 covers the twelve (12) month liability cap.",
                  metadata={"source": "msa.pdf"})
    d3 = Document(page_content="The QCR is due on 15 October 2026.",
                  metadata={"source": "circular.docx"})
    context_text, used = assemble_context([(d1, 0.9), (d2, 0.8), (d3, 0.7)])
    check("near-duplicate chunks are deduplicated", len(used) == 2, f"got {len(used)}")
    check("context includes both distinct sources",
          "msa.pdf" in context_text and "circular.docx" in context_text)

    many = [(Document(page_content="x" * 400, metadata={"source": f"f{i}.txt"}), 0.5)
            for i in range(20)]
    packed, _ = assemble_context(many, max_chars=3000)
    check("context length stays within the character budget", len(packed) <= 3000,
          f"len={len(packed)}")

    # --- retrieval ------------------------------------------------------
    print("\n[retrieval]")
    check("three retrieval patterns registered",
          set(PATTERNS) == {"topk", "mmr", "threshold"})
    try:
        retrieve(None, "question", pattern="nope")
        check("unknown pattern raises ValueError", False, "no error raised")
    except ValueError:
        check("unknown pattern raises ValueError", True)

    print("\n" + "=" * 64)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 64)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
