import json
import time
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL    = "http://localhost:8000/ask"
OUTPUT_DIR = "data/evaluation"

# ══════════════════════════════════════════════════════════════════
# GROUND TRUTH DATASET
# Each question has a verified correct answer written by YOU after
# reading the actual Mahavamsa / Kings.pdf passage.
# Fill in / edit these to match what the source text actually says.
# ══════════════════════════════════════════════════════════════════

GROUND_TRUTH_QUESTIONS = [
    {
        "id": "GT01",
        "question": "Who was Vijaya?",
        "ground_truth": (
            "Vijaya was a prince exiled from India by his father "
            "Sinhabahu for violent and unruly behaviour. He landed "
            "in Sri Lanka at Tambapanni with 700 followers on the "
            "day of the Buddha's death, around 543 BCE. He married "
            "Kuveni, a local yaksha princess who helped him, but "
            "later abandoned her to marry a Pandyan princess from "
            "India. He is considered the founder of the Sinhalese "
            "royal lineage and ruled for about 38 years."
        ),
        "must_contain": ["vijaya", "prince", "tambapanni", "sinhalese", "kuveni"],
        "category": "Person",
        "difficulty": "easy",
        "mode": "graph",
    },
    {
        "id": "GT02",
        "question": "Who defeated Elara?",
        "ground_truth": (
            "King Dutugamunu of Ruhuna defeated King Elara, a Tamil "
            "Chola ruler who had governed Anuradhapura for 44 years, "
            "in single combat at the Vijithapura battle around 161 "
            "BCE. Despite being an invader, Elara was respected by "
            "Dutugamunu as a righteous king, and after the victory "
            "Dutugamunu gave him a royal funeral and built a "
            "monument over his cremation site, known as Elara's tomb."
        ),
        "must_contain": ["dutugamunu", "elara", "defeated", "anuradhapura"],
        "category": "Battle",
        "difficulty": "medium",
        "mode": "graph",
    },
    {
        "id": "GT03",
        "question": "What did Dutugamunu build after winning the war?",
        "ground_truth": (
            "After defeating Elara and unifying Sri Lanka, King "
            "Dutugamunu built the Ruwanwelisaya stupa (also called "
            "Mahathupa or Swarnamali) in Anuradhapura, enshrining "
            "relics of the Buddha. He also built other structures "
            "including Miriswetiya, Thuparamaya restorations, the "
            "Lovamahapaya (Brazen Palace), and several Buddhist "
            "monasteries."
        ),
        "must_contain": ["ruwanweli", "stupa", "anuradhapura", "built"],
        "category": "Structure",
        "difficulty": "medium",
        "mode": "graph",
    },
    {
        "id": "GT04",
        "question": "Who was King Kashyapa and what is his connection to Sigiriya?",
        "ground_truth": (
            "King Kashyapa I (Kassapa I) ruled from around 473 to "
            "495 CE. He seized the throne after imprisoning and "
            "killing his father, King Dhatusena, fearing retaliation "
            "from his half-brother Moggallana, the rightful heir who "
            "fled to India. Fearing Moggallana's return, Kashyapa "
            "built his royal capital and palace on top of the "
            "Sigiriya rock fortress for both military defence and "
            "as a pleasure palace. When Moggallana returned with an "
            "army in 495 CE, Kashyapa came down to fight and, facing "
            "defeat, killed himself with his own sword."
        ),
        "must_contain": ["kassapa", "sigiriya", "dhatusena", "moggallana"],
        "category": "Person",
        "difficulty": "hard",
        "mode": "graph",
    },
    {
        "id": "GT05",
        "question": "How did Buddhism arrive in Sri Lanka?",
        "ground_truth": (
            "Buddhism was introduced to Sri Lanka by the Arahant "
            "Mahinda, son of Emperor Ashoka of India, during the "
            "reign of King Devanampiyatissa around 247 BCE. Mahinda "
            "preached to the king at Mihintale, after which the king "
            "converted and Buddhism became the state religion. "
            "Shortly after, Sanghamitta, Mahinda's sister, brought "
            "a sapling of the sacred Bo tree from Bodh Gaya and "
            "planted it in Anuradhapura, and established the order "
            "of nuns (bhikkhuni sasana) in Sri Lanka."
        ),
        "must_contain": ["mahinda", "devanampiyatissa", "buddhism", "mihintale"],
        "category": "Event",
        "difficulty": "hard",
        "mode": "graph",
    },
]


def keyword_score(answer, must_contain):
    """Basic check — did the answer mention the essential facts."""
    answer_lower = answer.lower()
    matched = [kw for kw in must_contain if kw.lower() in answer_lower]
    return len(matched) / len(must_contain), matched


def word_overlap_score(answer, ground_truth):
    """
    Token overlap score between answer and ground truth.
    This is a simple proxy for semantic similarity without
    needing an embedding model — measures how many ground truth
    words appear in the answer (recall-oriented).
    """
    def tokenize(text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        words = text.split()
        # remove common stopwords for a cleaner score
        stopwords = {
            "the", "a", "an", "is", "was", "were", "are", "of", "in",
            "to", "and", "his", "her", "he", "she", "it", "by", "on",
            "at", "with", "for", "as", "that", "this", "who", "what",
            "after", "before", "from", "be", "been", "has", "had"
        }
        return [w for w in words if w not in stopwords and len(w) > 2]

    gt_words     = set(tokenize(ground_truth))
    answer_words = set(tokenize(answer))

    if not gt_words:
        return 0.0

    overlap = gt_words & answer_words
    return len(overlap) / len(gt_words)


def hallucination_check(answer, ground_truth, must_contain):
    """
    Very simple heuristic flag — if the answer contradicts or
    omits ALL key facts, flag as a potential hallucination risk.
    This does NOT replace human review, just flags the candidates
    most worth your manual reading time.
    """
    answer_lower = answer.lower()
    matched = [kw for kw in must_contain if kw.lower() in answer_lower]
    if len(matched) == 0:
        return True
    return False


def evaluate_against_ground_truth(mode_filter=None):
    print("\n=== Ground Truth Evaluation ===\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []

    for q in GROUND_TRUTH_QUESTIONS:
        mode = mode_filter or q["mode"]
        print(f"[{q['id']}] {q['question']}  (mode={mode})")

        try:
            start    = time.time()
            response = requests.post(API_URL, json={
                "question": q["question"],
                "mode":     mode
            }, timeout=120)
            elapsed = time.time() - start

            data   = response.json()
            answer = data.get("answer", "")

            kw_score, matched   = keyword_score(answer, q["must_contain"])
            overlap_score       = word_overlap_score(answer, q["ground_truth"])
            possible_hallucination = hallucination_check(
                answer, q["ground_truth"], q["must_contain"]
            )

            # Combined score — average of keyword and overlap scores
            combined_score = round((kw_score + overlap_score) / 2, 2)

            result = {
                "id":                     q["id"],
                "question":               q["question"],
                "category":               q["category"],
                "difficulty":             q["difficulty"],
                "mode":                   mode,
                "ground_truth":           q["ground_truth"],
                "model_answer":           answer,
                "keyword_score":          round(kw_score, 2),
                "keywords_matched":       matched,
                "word_overlap_score":     round(overlap_score, 2),
                "combined_score":         combined_score,
                "possible_hallucination": possible_hallucination,
                "response_time_seconds":  round(elapsed, 2),
            }
            results.append(result)

            flag = " ⚠ POSSIBLE HALLUCINATION" if possible_hallucination else ""
            print(f"   Keyword score : {kw_score:.0%}")
            print(f"   Overlap score : {overlap_score:.0%}")
            print(f"   Combined      : {combined_score:.0%}{flag}")
            print()

        except Exception as e:
            print(f"   ERROR: {e}\n")
            results.append({
                "id": q["id"], "question": q["question"],
                "category": q["category"], "difficulty": q["difficulty"],
                "mode": mode, "ground_truth": q["ground_truth"],
                "model_answer": f"ERROR: {e}",
                "keyword_score": 0, "keywords_matched": [],
                "word_overlap_score": 0, "combined_score": 0,
                "possible_hallucination": True,
                "response_time_seconds": 0,
            })

    # ── Summary ──────────────────────────────────────────────────
    avg_keyword  = sum(r["keyword_score"] for r in results) / len(results)
    avg_overlap  = sum(r["word_overlap_score"] for r in results) / len(results)
    avg_combined = sum(r["combined_score"] for r in results) / len(results)
    hallucination_count = sum(1 for r in results if r["possible_hallucination"])

    summary = {
        "total_questions":        len(results),
        "average_keyword_score":  round(avg_keyword, 2),
        "average_overlap_score":  round(avg_overlap, 2),
        "average_combined_score": round(avg_combined, 2),
        "possible_hallucinations": hallucination_count,
    }

    # ── Save JSON ────────────────────────────────────────────────
    out_path = os.path.join(OUTPUT_DIR, "ground_truth_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f,
                   ensure_ascii=False, indent=2)
    print(f"Saved: {out_path}")

    # ── Save readable report ─────────────────────────────────────
    report_path = os.path.join(OUTPUT_DIR, "ground_truth_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("GROUND TRUTH EVALUATION REPORT\n")
        f.write("=" * 65 + "\n\n")
        f.write(f"Total questions          : {summary['total_questions']}\n")
        f.write(f"Average keyword score    : {summary['average_keyword_score']:.0%}\n")
        f.write(f"Average overlap score    : {summary['average_overlap_score']:.0%}\n")
        f.write(f"Average combined score   : {summary['average_combined_score']:.0%}\n")
        f.write(f"Possible hallucinations  : {summary['possible_hallucinations']} / {summary['total_questions']}\n\n")

        f.write("DETAILED COMPARISON (for report Appendix / Section 5.2)\n")
        f.write("=" * 65 + "\n")
        for r in results:
            f.write(f"\n{r['id']} [{r['difficulty'].upper()}] — {r['category']} — mode: {r['mode']}\n")
            f.write(f"Q: {r['question']}\n\n")
            f.write(f"GROUND TRUTH:\n{r['ground_truth']}\n\n")
            f.write(f"MODEL ANSWER:\n{r['model_answer']}\n\n")
            f.write(f"Keyword score   : {r['keyword_score']:.0%}  "
                    f"(matched: {', '.join(r['keywords_matched']) if r['keywords_matched'] else 'none'})\n")
            f.write(f"Overlap score   : {r['word_overlap_score']:.0%}\n")
            f.write(f"Combined score  : {r['combined_score']:.0%}\n")
            f.write(f"Hallucination risk : {'YES — review manually' if r['possible_hallucination'] else 'No'}\n")
            f.write("-" * 65 + "\n")

    print(f"Saved: {report_path}")

    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Average keyword score  : {avg_keyword:.0%}")
    print(f"Average overlap score  : {avg_overlap:.0%}")
    print(f"Average combined score : {avg_combined:.0%}")
    print(f"Possible hallucinations: {hallucination_count}/{len(results)}")


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else None
    evaluate_against_ground_truth(mode_filter=mode)