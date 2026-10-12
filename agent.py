"""
agent.py

Nyaya - Ask the Pipeline (Step 3 of 3)
========================================
5 hardcoded questions, one per source document / format, so a single run
proves Nyaya is grounded across ALL FIVE formats (PDF, Word, HTML, CSV,
JSON) - not just whichever one happened to be easiest to parse.

IMPORTANT: app.py must already be running in a separate terminal
(uvicorn app:app --reload --port 8000) before you run this file.

Run:
    python agent.py
"""
import requests

BASE_URL = "http://localhost:8000/ask"

# One question per document/format, in the same order as documents/.
QUESTIONS = [
    "What is the limitation of liability cap in our standard MSA?",                 # PDF (MSA)
    "What is the deadline for submitting the quarterly compliance report?",         # Word (circular)
    "Who do I contact to request an urgent contract review?",                       # HTML (FAQ) - tests PII redaction
    "Which compliance audit findings are still open?",                              # CSV (audit log)
    "Which regulatory filings are overdue or due within the next 30 days?",         # JSON (filing tracker)
]

# Bonus: a question no document covers - should trigger the "I don't know"
# guardrail, and app.py should report llm_called: false.
GUARDRAIL_QUESTION = "What is our policy on international arbitration seat selection?"

# Bonus: one question run through all three retrieval patterns, so the
# differences (chunk counts, scores) are visible directly.
COMPARISON_QUESTION = "What are the standard and expedited turnaround times for contract reviews?"


def ask_nyaya(question: str, pattern: str = "topk", k: int = 3) -> dict:
    response = requests.get(
        BASE_URL, params={"q": question, "pattern": pattern, "k": k}, timeout=60
    )
    response.raise_for_status()
    return response.json()


def main():
    print("=" * 60)
    print("Nyaya - Legal & Compliance Document Intelligence Pipeline")
    print("=" * 60)

    for i, question in enumerate(QUESTIONS, start=1):
        print(f"\nQ{i}: {question}")
        try:
            result = ask_nyaya(question)
        except requests.exceptions.ConnectionError:
            print("ERROR: Could not reach Nyaya. Is app.py running in another "
                  "terminal? (uvicorn app:app --reload --port 8000)")
            return

        if not result["retrieved_chunks"]:
            print("  (No chunks cleared the confidence threshold.)")
        for chunk in result["retrieved_chunks"]:
            print(f"    - {chunk['source']}  (score={chunk['relevance_score']})  "
                  f"metadata={chunk['metadata']}")
            print(f"      \"{chunk['text_preview']}\"")

        print(f"\nA{i}: {result['answer']}")
        print(f"     (Sources: {', '.join(result['sources']) if result['sources'] else 'none'})")

    print("\n" + "=" * 60)
    print("GUARDRAIL - a question no document covers")
    print("=" * 60)
    print(f"Question: {GUARDRAIL_QUESTION}\n")
    try:
        result = ask_nyaya(GUARDRAIL_QUESTION)
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not reach Nyaya. Is app.py still running?")
        return
    print(f"Chunks retrieved: {len(result['retrieved_chunks'])}")
    print(f"LLM called: {result['llm_called']}")
    print(f"Answer: {result['answer']}")

    print("\n" + "=" * 60)
    print("BONUS - comparing retrieval patterns on ONE question")
    print("=" * 60)
    print(f"Question: {COMPARISON_QUESTION}\n")
    for pattern in ["topk", "threshold", "mmr"]:
        print(f"--- Pattern: {pattern} ---")
        result = ask_nyaya(COMPARISON_QUESTION, pattern=pattern)
        print(f"Chunks retrieved: {len(result['retrieved_chunks'])}")
        for chunk in result["retrieved_chunks"]:
            print(f"    - {chunk['source']} (score={chunk['relevance_score']})")
        print(f"Answer preview: {result['answer'][:150]}...\n")

    print("=" * 60)
    print("Done! Try editing QUESTIONS above, or the chunking strategy used")
    print("to build the store, to see how retrieval quality changes.")
    print("=" * 60)


if __name__ == "__main__":
    main()
