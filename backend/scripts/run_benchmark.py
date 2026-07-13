"""Run the GyanVriksh benchmark: answer all questions via the Copilot agent,
grade with LLM-as-judge, report accuracy/citation metrics per README section 10.

Resumable + incremental: already-graded questions are skipped, and results are
written after every question, so a long (100-question) run can survive an
interruption — just re-run the same command and it continues.
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents import copilot_agent
from app.services.llm_service import chat_json

QUESTIONS = Path(__file__).resolve().parent.parent / "data/benchmark_questions.json"
RESULTS = Path(__file__).resolve().parent.parent / "data/benchmark_results.json"

JUDGE_PROMPT = """You are grading a RAG system's answer against ground truth.
Score CORRECT if the answer contains the key facts of the ground truth (paraphrase is fine),
PARTIAL if some key facts present, WRONG otherwise.
Return JSON: {"grade": "CORRECT|PARTIAL|WRONG", "reason": "one line"}"""


def summarize(results: list) -> dict:
    graded = [r for r in results if r.get("grade") not in (None, "ERROR")]
    correct = sum(1 for r in graded if r["grade"] == "CORRECT")
    partial = sum(1 for r in graded if r["grade"] == "PARTIAL")
    cited = sum(1 for r in graded if r.get("citations"))
    times = [r["time_s"] for r in graded if "time_s" in r]
    summary = {
        "total": len(results),
        "correct": correct, "partial": partial,
        "wrong": len(graded) - correct - partial,
        "errors": sum(1 for r in results if r.get("grade") == "ERROR"),
        "accuracy_pct": round(100 * correct / max(len(graded), 1), 1),
        "accuracy_with_partial_pct": round(100 * (correct + 0.5 * partial) / max(len(graded), 1), 1),
        "answers_with_citations_pct": round(100 * cited / max(len(graded), 1), 1),
        "median_response_s": round(statistics.median(times), 2) if times else None,
        "by_category": {},
    }
    for cat in sorted({r.get("category", "?") for r in graded}):
        cat_r = [r for r in graded if r.get("category") == cat]
        summary["by_category"][cat] = {
            "n": len(cat_r),
            "correct": sum(1 for r in cat_r if r["grade"] == "CORRECT"),
        }
    return summary


def _save(results: list):
    RESULTS.write_text(json.dumps({"summary": summarize(results), "results": results}, indent=2))


def main(limit: int | None = None):
    questions = json.loads(QUESTIONS.read_text())
    if limit:
        questions = questions[:limit]

    # resume: reuse already-graded results from a previous run
    existing = {}
    if RESULTS.exists():
        try:
            prev = json.loads(RESULTS.read_text()).get("results", [])
            existing = {r["id"]: r for r in prev if r.get("grade") not in (None, "ERROR")}
        except Exception:
            existing = {}
    if existing:
        print(f"Resuming — {len(existing)} question(s) already graded will be skipped.")

    results = []
    for i, q in enumerate(questions):
        if q["id"] in existing:
            results.append(existing[q["id"]])
            print(f"[{i + 1}/{len(questions)}] {q['id']} cached ({existing[q['id']].get('grade')})")
            continue
        t0 = time.time()
        try:
            out = copilot_agent.answer_query(q["q"])
        except Exception as e:
            results.append({**q, "grade": "ERROR", "error": str(e)})
            _save(results)
            print(f"[{i + 1}/{len(questions)}] {q['id']} ERROR: {e}")
            continue
        elapsed = time.time() - t0
        grade = chat_json([
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": f"Question: {q['q']}\nGround truth: {q['truth']}\n"
                                        f"System answer: {out['answer']}"},
        ])
        results.append({**q, "answer": out["answer"], "confidence": out["confidence"],
                        "citations": out["citations"], "grade": grade.get("grade", "WRONG"),
                        "reason": grade.get("reason", ""), "time_s": round(elapsed, 2)})
        _save(results)  # incremental — survives interruption
        print(f"[{i + 1}/{len(questions)}] {q['id']} {grade.get('grade')} ({elapsed:.1f}s)")

    _save(results)
    print("\n=== BENCHMARK SUMMARY ===")
    print(json.dumps(summarize(results), indent=2))
    print(f"\nFull results: {RESULTS}")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit)
