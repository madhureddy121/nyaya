"""
pii.py

Nyaya - PII-Safe Ingestion
============================
Before any chunk is embedded and stored, it passes through this redaction
step. This is intentionally simple: a handful of regex patterns catching
the most common PII shapes (emails, Indian phone numbers, PAN-style IDs).

It is NOT a substitute for a proper NER-based PII detector in production:
pattern matching cannot catch a person's name written in plain prose. The
Legal FAQ document deliberately contains one email and one phone number,
placed there so you can watch this step redact them during ingestion.
"""
import re

PATTERNS = {
    "EMAIL": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "PHONE_INDIA": re.compile(r"(?:\+91[\s-]?)?(?:[6-9]\d{9}|[6-9]\d{4}[\s-]\d{5})\b"),
    "PAN_LIKE_ID": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
}


def redact_pii(text: str) -> tuple:
    """Replace any matched PII with a labelled placeholder.
    Returns the redacted text AND a count of what was redacted, so the
    build script can report what it found without ever printing the
    actual PII to a terminal or log file."""
    counts = {}
    redacted = text
    for label, pattern in PATTERNS.items():
        matches = pattern.findall(redacted)
        if matches:
            counts[label] = len(matches)
            redacted = pattern.sub(f"[REDACTED_{label}]", redacted)
    return redacted, counts
