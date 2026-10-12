# Nyaya — Legal & Compliance Document Intelligence Pipeline

*A hands-on RAG pipeline covering ingestion, chunking, retrieval, context
assembly, and grounded citation — built on the same pattern as Disha (the
RAG pipeline lab).*

---

## 1. What Is This, in Plain Language

Nyaya answers Legal & Compliance questions from five fictional source
documents — a Master Service Agreement excerpt (PDF), a regulatory
compliance circular (Word), a Legal FAQ page (HTML), a compliance audit
log (CSV), and a regulatory filing tracker (JSON).

Give it a question like *"What is the limitation of liability cap in our
standard MSA?"* and it retrieves the most relevant excerpts, answers from
those excerpts only, cites the source file behind every fact — and refuses
to answer ("I don't know") when nothing in the knowledge base is a
confident enough match, **without ever calling the LLM**.

This is the full RAG architecture, end to end:

```
ingest -> chunk -> embed -> index -> retrieve -> rerank/dedupe -> answer -> cite
```

Every one of those eight words maps to a real, runnable piece of code in
this repo.

## 2. The Five Documents, Five Formats

| # | File | Format | Loader used |
|---|------|--------|-------------|
| 1 | `01_msa_excerpt.pdf` | PDF | PyMuPDF (one unit per page) |
| 2 | `02_regulatory_compliance_circular.docx` | Word | python-docx (whole document) |
| 3 | `03_legal_faq.html` | HTML | BeautifulSoup (one unit per H2 section) |
| 4 | `04_compliance_audit_log.csv` | CSV | built-in `csv` (one unit per row) |
| 5 | `05_regulatory_filing_tracker.json` | JSON | built-in `json` (one unit per record) |

Every document follows the same header convention: **Document ID /
Version / Effective Date**, and every document contains specific,
checkable facts (a twelve-month liability cap, a 15 October 2026 filing
deadline, an overdue filing, open audit findings, and so on).

Doc 3 (the FAQ) contains a deliberately planted email address and phone
number so you can watch the PII redaction step catch and mask them during
ingestion. Doc 1 contains a planted PAN-style ID for the same reason.

All 5 documents are fictional samples and can be regenerated with
`python make_documents.py`.

## 3. Architecture — the Full Flow

```
STEP 1 -- build_vectorstore.py  (run once, or re-run per experiment)

    documents/*.{pdf,docx,html,csv,json}
        |
        |  loaders.py    -- one loader per format, same output shape
        v
    raw text units (one per page / row / section / record)
        |
        |  pii.py        -- redact emails, phone numbers, PAN-style IDs
        v
    redacted text
        |
        |  chunking.py   -- pick ONE of 5 strategies:
        |                   fixed | overlap | sentence | heading_aware | semantic
        v
    chunks, each tagged with source + chunk_index + chunking_strategy
        |
        |  LangChain + OpenAIEmbeddings  -- embed every chunk
        v
    ./chroma_store  (ChromaDB vector store, persisted to disk)


STEP 2 -- app.py  (FastAPI backend, keep running in Terminal 1)

    /ask?q=...&pattern=topk|mmr|threshold&k=3

    1. retrieval.py     -- run the chosen retrieval pattern
    2. confidence check -- if nothing clears MIN_CONFIDENCE, answer
                           "I don't know" and STOP (no LLM call at all;
                           the JSON response says "llm_called": false)
    3. context.py       -- deduplicate near-identical chunks, then pack
                           into a character budget (evidence packing)
    4. LLM call         -- system prompt requires a (Source: filename)
                           citation on every factual claim
    5. return JSON      -- {retrieved_chunks, answer, sources, llm_called}


STEP 3 -- agent.py  (run in Terminal 2, while app.py keeps running)

    Sends 5 hardcoded questions -- one per document format -- to /ask,
    then a GUARDRAIL question no document covers, then a BONUS section
    comparing topk vs. threshold vs. mmr on one question.


STEP 4 (recommended) -- inspect_vectorstore.py

    Peeks inside ./chroma_store -- through the ChromaDB API, then
    directly into the underlying chroma.sqlite3 file -- to show exactly
    where chunk text and metadata physically live on disk.
```

## 4. Setup — Step by Step

### Step 1 — Get the code
Unzip this repository (or clone its Git link), then:
```
cd nyaya
```

### Step 2 — Create your `.env` file
Copy `.env.example` to a new file named exactly `.env`:
```
OPENAI_API_KEY="paste-your-key-here"
```
**Never share this file or commit it to Git** — it is already in
`.gitignore`.

### Step 3 — Set up your environment and install dependencies
```
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 4 — Check everything offline (no API key needed)
```
python test_pipeline.py           # loaders + PII + chunking + context tests
python build_vectorstore.py --dry-run
```
The dry-run loads all 5 documents, redacts PII, chunks everything, and
reports the chunk counts — without making any API calls.

### Step 5 — Build the vector store (run once)
```
python build_vectorstore.py                      # default strategy: overlap
```
By default this uses the **overlap** chunking strategy. To compare a
different one:
```
python build_vectorstore.py --strategy heading_aware
python build_vectorstore.py --strategy fixed
python build_vectorstore.py --strategy sentence
python build_vectorstore.py --strategy semantic
```
Each run reports how many chunks it created, and what PII (if any) it
redacted along the way. Re-run this any time you change a document, or
want to try a different strategy — it always rebuilds `./chroma_store`
from scratch.

### Step 6 — Start Nyaya (Terminal 1)
```
uvicorn app:app --reload --port 8000
```
Leave this running. Visit `http://localhost:8000/docs` any time to try
questions interactively from a browser.

### Step 7 — Ask Nyaya your questions (Terminal 2)
```
python agent.py
```
You'll see all 5 hardcoded questions (one per document format), the
retrieved chunk metadata behind each answer, the grounded answer itself,
a guardrail check, and a bonus section comparing all 3 retrieval
patterns on one question.

## 5. The 5 Questions in `agent.py`

1. What is the limitation of liability cap in our standard MSA? → *PDF (MSA)*
2. What is the deadline for submitting the quarterly compliance report? → *Word (circular)*
3. Who do I contact to request an urgent contract review? → *HTML (FAQ) — also tests PII redaction*
4. Which compliance audit findings are still open? → *CSV (audit log)*
5. Which regulatory filings are overdue or due within the next 30 days? → *JSON (filing tracker)*

Plus a bonus GUARDRAIL question — *"What is our policy on international
arbitration seat selection?"* — which no document covers, and which must
produce a fixed refusal with `"llm_called": false`.

## 6. Feature Map

| Feature | Where it lives |
|---|---|
| Multi-format loaders (5 formats, genuinely different logic) | `loaders.py` |
| Chunking strategy comparison (5 strategies, switchable by flag) | `chunking.py`, `build_vectorstore.py --strategy` |
| PII-safe ingestion (email, phone, PAN-style ID) | `pii.py`, reported in `build_vectorstore.py` console output |
| Retrieval pattern comparison (topk / mmr / threshold) | `retrieval.py`, compared in `agent.py`'s BONUS section |
| Context assembly (dedupe + character budget) | `context.py` |
| Grounded, cited answers | `app.py` system prompt — every fact cites `(Source: <filename>)` |
| "I don't know" guardrail that skips the LLM | `app.py` — `MIN_CONFIDENCE` check *before* the LLM call, `"llm_called": false` |
| Three-script pattern | `build_vectorstore.py` + `app.py` + `agent.py` |
| Offline tests that need no API key | `test_pipeline.py` |
| Vector-store inspector | `inspect_vectorstore.py` |

## 7. Chunking Strategy Comparison

**The two strategies compared here: `fixed` vs. `heading_aware`, on the
MSA (PDF).**

Reproduce the counts with:
```
python build_vectorstore.py --dry-run --strategy fixed
python build_vectorstore.py --dry-run --strategy heading_aware
```

Observed on this repository's documents (chunks per document, processed
per loaded unit — the same order `build_vectorstore.py` uses):

| Document | `fixed` | `heading_aware` |
|---|---|---|
| `01_msa_excerpt.pdf` | 6 | 7 |
| `02_regulatory_compliance_circular.docx` | 3 | 6 |
| `03_legal_faq.html` | 6 | 6 |
| `04_compliance_audit_log.csv` | 8 | 8 |
| `05_regulatory_filing_tracker.json` | 7 | 7 |
| **Total** | **30** | **34** |

**Finding:** `heading_aware` produced better chunks for the MSA. The MSA
is structured as numbered clauses, and heading_aware splits at exactly
those boundaries — one complete clause per chunk. Page 2 (894 characters)
carries the two most important clauses:

- With `fixed` (500-character chunks, no awareness of structure), a chunk
  ends mid-sentence inside Section 4 — right after *"Each party (the
  "Indemnifying Party"* — and the next chunk resumes mid-sentence. Since
  retrieval returns whole chunks, a clause cut in half can only ever be
  retrieved half-complete.
- With `heading_aware`, Section 3 is one complete chunk (*"3. Limitation
  of Liability … loss of profits, revenue, or data."*) and Section 4 is
  another — the twelve-month liability cap can never be retrieved
  truncated.

The same effect shows on the circular: `heading_aware` produces one chunk
per numbered section (plus the document header), while `fixed` slicing
crosses section boundaries.

*Honest caveat:* `semantic` is an approximation here — it splits on blank
lines, and these documents use single newlines between sections, so it
under-performs on them. That limitation is documented in `chunking.py`.

## 8. Retrieval Pattern Comparison

Three patterns are implemented (`retrieval.py`): **topk**, **mmr**, and
**threshold**. The two compared here: **`topk` vs. `threshold`**, using one
question run through both (see the BONUS section of `agent.py`'s output).

Structural difference, visible directly in the code:

- `topk` always returns exactly `k` chunks, however weak the weakest match.
- `threshold` drops every chunk scoring below `min_score` — it can return
  **zero** chunks, which is what powers the "I don't know" guardrail.
- `mmr` returns `k` chunks chosen to be relevant *and* mutually different.

**Observed result (record your run here before submitting — this is one
of the graded comparison findings):**

```
Question: ...
topk:      returned N chunks (scores ...) -> answer ...
threshold: returned X chunks (scores ...) -> answer ...
Which result was better, and why: ...
```

To make the difference easy to see, run a question whose best match is
borderline (or the guardrail question): `topk` will still return 3 chunks,
while `threshold` will return fewer — or none at all.

## 9. PII-Safe Ingestion

`build_vectorstore.py` reports what it redacted, without ever printing the
raw values. On this repository's documents:

```
PII redacted during ingestion: {'PAN_LIKE_ID': 1, 'EMAIL': 1, 'PHONE_INDIA': 1}
```

- 1 email and 1 phone number from the Legal FAQ (the planted contact)
- 1 PAN-style ID from the MSA (the planted signatory ID)

`inspect_vectorstore.py` then shows the stored chunks containing
`[REDACTED_EMAIL]` / `[REDACTED_PHONE_INDIA]` — proof the raw values never
reached the vector store.

**Honest limitation:** this is pattern matching, not understanding. It
catches emails, phone numbers, and PAN-style IDs because their shapes are
predictable — it will **not** catch a person's name written in prose (the
FAQ contact's name is still present after redaction). A production system
needs a proper NER-based detector.

## 10. The "I Don't Know" Guardrail

Before the LLM is ever called, `app.py` checks whether the best retrieved
chunk's relevance score clears `MIN_CONFIDENCE` (default 0.3). If nothing
does, it returns a fixed refusal — and the JSON response contains
`"llm_called": false`, which proves no generation call happened:

```
curl "http://localhost:8000/ask?q=What+is+our+policy+on+international+arbitration+seat+selection%3F"
```

If Nyaya refuses questions you would expect it to answer, lower
`MIN_CONFIDENCE`; if it answers questions it should not be confident
about, raise it. This is a tuning knob, not a universal constant.

## 11. Project Structure

```
nyaya/
├── documents/                  # the 5 fictional source documents
├── app.py                      # FastAPI backend: retrieve -> guardrail -> context -> LLM
├── agent.py                    # client: 5 questions + guardrail + pattern comparison
├── build_vectorstore.py        # ingest -> redact -> chunk -> embed -> store
├── chunking.py                 # 5 chunking strategies
├── context.py                  # deduplication + evidence packing
├── inspect_vectorstore.py      # peek inside ./chroma_store
├── loaders.py                  # one loader per file format
├── make_documents.py           # regenerates the 5 documents (optional)
├── pii.py                      # regex-based PII redaction
├── retrieval.py                # topk / mmr / threshold retrieval patterns
├── test_pipeline.py            # offline tests (no API key needed)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── REFLECTION.md
```

## 12. Troubleshooting

| Problem | Likely cause |
|---|---|
| `ModuleNotFoundError` | Virtual environment not activated, or `pip install -r requirements.txt` not run |
| `AuthenticationError` | Check `.env` has your real key, correctly quoted |
| `build_vectorstore.py` fails on the PDF | Confirm `pymupdf` installed correctly — some environments need `pip install pymupdf` run separately |
| `app.py` fails with a "collection not found" error | Run `build_vectorstore.py` first, from this same folder |
| `agent.py` says "Could not reach Nyaya" | `app.py` is not running in the other terminal |
| Every answer is "I don't know" | `MIN_CONFIDENCE` may be set too high for your embedding model — see Section 10 |
| Model-not-found error on the chat call | Set `CHAT_MODEL` in `app.py` to a model your API key supports |

## 13. Notes

- `CHAT_MODEL` (`gpt-5.4-mini`) and `EMBED_MODEL`
  (`text-embedding-3-small`) are the models this lab was delivered with.
  Substitute whichever models your organisation has approved. `EMBED_MODEL`
  must match between `build_vectorstore.py` and `app.py`.
- `MIN_CONFIDENCE = 0.3` in `app.py` is a starting point, not a universal
  constant — see Section 10.
- Run `python test_pipeline.py` after any edit; it verifies the offline
  half of the pipeline (34 checks) without touching the API.
