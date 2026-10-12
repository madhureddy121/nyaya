# Reflection — Nyaya

> **Before submitting:** complete the marked `[FILL IN]` item after running
> `agent.py` with your API key, and put the wording in your own voice.
> The chunking observations in Q1 can be reproduced offline with
> `python build_vectorstore.py --dry-run --strategy fixed` / `--strategy heading_aware`.

## 1. Which chunking strategy produced better results for your MSA document, and why?

`heading_aware` produced better chunks, because of the MSA's structure:
it is organised as numbered clauses ("1. Scope", "3. Limitation of
Liability", "4. Indemnification"), and heading_aware splits at exactly
those boundaries, so every chunk is one complete clause. On page 2, which
carries the liability cap, heading_aware kept Section 3 whole — including
the sentence that fixes the cap at twelve months' fees — with nothing cut
off. Fixed-size chunking (500 characters) ignored the clause structure:
on the same page its first chunk ends mid-sentence inside Section 4, and
the next chunk begins mid-sentence. Because retrieval returns whole
chunks, a clause cut in half can only ever be retrieved half-complete,
which risks a half-complete answer.

## 2. Describe one case where the two retrieval patterns returned meaningfully different chunks.

`[FILL IN from the BONUS section of agent.py's output — e.g. topk vs.
threshold on the turnaround-time question: how many chunks each pattern
returned, their scores, and which resulting answer was better, and why.]`

## 3. If Legal & Compliance asked to add 20 more contract documents next month, what would need to change, and what wouldn't?

Ingestion would not change: new PDF or Word files drop into `documents/`
and `build_vectorstore.py` re-ingests them with no code edits, and the
app, retrieval, and context layers stay as they are. What would need
attention: metadata. With 25 contracts, `source` alone is no longer
enough, so I would filter retrieval by contract ID or counterparty to
ensure answers come from the right document. I would also re-check the
chunking strategy for the new documents' structures, and note that the
build re-embeds everything from scratch — fine at 5 documents, a real API
cost and build time at 25.
