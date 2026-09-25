import json
import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL    = "http://localhost:8000/ask"
OUTPUT_DIR = "data/evaluation"

TEST_QUESTIONS = [
    # EASY — Person
    {
        "id": "Q01",
        "question": "Who was Vijaya?",
        "category": "Person",
        "expected_keywords": ["vijaya", "prince", "lanka", "arrived", "sinhabahu"],
        "difficulty": "easy"
    },
    {
        "id": "Q02",
        "question": "Who was King Pandukabhaya?",
        "category": "Person",
        "expected_keywords": ["pandukabhaya", "king", "anuradhapura", "founded", "capital"],
        "difficulty": "easy"
    },
    {
        "id": "Q03",
        "question": "Who was Mahinda?",
        "category": "Person",
        "expected_keywords": ["mahinda", "buddhism", "sri lanka", "mission", "thera"],
        "difficulty": "easy"
    },
    {
        "id": "Q04",
        "question": "Who was Sanghamitta?",
        "category": "Person",
        "expected_keywords": ["sanghamitta", "bo tree", "buddhism", "female", "theri"],
        "difficulty": "easy"
    },
    {
        "id": "Q05",
        "question": "Who was King Devanampiyatissa?",
        "category": "Person",
        "expected_keywords": ["devanampiyatissa", "buddhism", "mahinda", "king", "anuradhapura"],
        "difficulty": "easy"
    },

    # EASY — Place
    {
        "id": "Q06",
        "question": "What is the significance of Anuradhapura?",
        "category": "Place",
        "expected_keywords": ["anuradhapura", "capital", "ancient", "kingdom", "sacred"],
        "difficulty": "easy"
    },
    {
        "id": "Q07",
        "question": "Where is Sigiriya located?",
        "category": "Place",
        "expected_keywords": ["sigiriya", "rock", "fortress", "kassapa", "sri lanka"],
        "difficulty": "easy"
    },
    {
        "id": "Q08",
        "question": "How to visit Polonnaruwa?",
        "category": "Location",
        "expected_keywords": ["polonnaruwa", "medieval", "capital", "visit", "heritage"],
        "difficulty": "easy"
    },

    # MEDIUM — Battle / Event
    {
        "id": "Q09",
        "question": "Who defeated Elara?",
        "category": "Battle",
        "expected_keywords": ["dutugamunu", "elara", "defeated", "battle", "war"],
        "difficulty": "medium"
    },
    {
        "id": "Q10",
        "question": "What was the war between Dutugamunu and Elara about?",
        "category": "Battle",
        "expected_keywords": ["dutugamunu", "elara", "kingdom", "unification", "sinhalese"],
        "difficulty": "medium"
    },
    {
        "id": "Q11",
        "question": "What did Dutugamunu build after winning the war?",
        "category": "Structure",
        "expected_keywords": ["stupa", "ruwanweli", "temple", "built", "mahathupa"],
        "difficulty": "medium"
    },
    {
        "id": "Q12",
        "question": "What is the story of King Kashyapa and Sigiriya?",
        "category": "Person",
        "expected_keywords": ["kassapa", "sigiriya", "palace", "father", "moggallana"],
        "difficulty": "medium"
    },
    {
        "id": "Q13",
        "question": "When did Buddhism arrive in Sri Lanka?",
        "category": "Event",
        "expected_keywords": ["buddhism", "mahinda", "247", "bce", "devanampiyatissa"],
        "difficulty": "medium"
    },
    {
        "id": "Q14",
        "question": "What is the Mahavamsa?",
        "category": "General",
        "expected_keywords": ["mahavamsa", "chronicle", "sri lanka", "history", "pali"],
        "difficulty": "medium"
    },

    # HARD — Multi-hop
    {
        "id": "Q15",
        "question": "Which king built the Jetavanaramaya and why is it significant?",
        "category": "Multi-hop",
        "expected_keywords": ["mahasena", "jetavana", "stupa", "tallest", "built"],
        "difficulty": "hard"
    },
    {
        "id": "Q16",
        "question": "What is the connection between Vijaya and the founding of Sri Lanka?",
        "category": "Multi-hop",
        "expected_keywords": ["vijaya", "founded", "sri lanka", "tambaparni", "prince"],
        "difficulty": "hard"
    },
    {
        "id": "Q17",
        "question": "How did Mahinda introduce Buddhism to Sri Lanka and who was the king at that time?",
        "category": "Multi-hop",
        "expected_keywords": ["mahinda", "devanampiyatissa", "buddhism", "mihintale", "247"],
        "difficulty": "hard"
    },
    {
        "id": "Q18",
        "question": "What structures did Dutugamunu build in Anuradhapura?",
        "category": "Multi-hop",
        "expected_keywords": ["dutugamunu", "anuradhapura", "ruwanweli", "stupa", "brazen palace"],
        "difficulty": "hard"
    },
    {
        "id": "Q19",
        "question": "Who was Parakramabahu and what was his greatest achievement?",
        "category": "Multi-hop",
        "expected_keywords": ["parakramabahu", "polonnaruwa", "irrigation", "sea", "unified"],
        "difficulty": "hard"
    },
    {
        "id": "Q20",
        "question": "What is the relationship between Anuradhapura and the sacred Bo Tree?",
        "category": "Multi-hop",
        "expected_keywords": ["anuradhapura", "bo tree", "sanghamitta", "buddhism", "sacred"],
        "difficulty": "hard"
    },
]


def evaluate_answer(answer, expected_keywords):
    answer_lower = answer.lower()
    matched = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    score   = len(matched) / len(expected_keywords)
    return score, matched


def run_evaluation():
    print("\n=== GraphRAG Evaluation — 20 Questions ===\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results    = []
    total_score = 0
    total_time  = 0

    for q in TEST_QUESTIONS:
        print(f"[{q['id']}] {q['question']}")
        try:
            start    = time.time()
            response = requests.post(API_URL, json={
                "question": q["question"],
                "mode": "graph"
            }, timeout=120)
            elapsed = time.time() - start

            data     = response.json()
            answer   = data.get("answer", "")
            triples  = data.get("graph_triples", [])
            location = data.get("location_site")

            score, matched = evaluate_answer(answer, q["expected_keywords"])
            total_score   += score
            total_time    += elapsed

            result = {
                "id":                    q["id"],
                "question":              q["question"],
                "category":              q["category"],
                "difficulty":            q["difficulty"],
                "answer":                answer,
                "response_time_seconds": round(elapsed, 2),
                "accuracy_score":        round(score, 2),
                "keywords_matched":      matched,
                "keywords_expected":     q["expected_keywords"],
                "graph_triples_count":   len(triples),
                "location_detected":     location is not None,
            }
            results.append(result)
            bar = "█" * int(score * 10)
            print(f"       Score: {score:.0%} {bar:<10} | Time: {elapsed:.1f}s | Triples: {len(triples)}")

        except Exception as e:
            print(f"       ERROR: {e}")
            results.append({
                "id":                    q["id"],
                "question":              q["question"],
                "category":              q["category"],
                "difficulty":            q["difficulty"],
                "answer":                f"ERROR: {str(e)}",
                "response_time_seconds": 0,
                "accuracy_score":        0,
                "keywords_matched":      [],
                "keywords_expected":     q["expected_keywords"],
                "graph_triples_count":   0,
                "location_detected":     False,
            })

    # Summary
    avg_score = total_score / len(TEST_QUESTIONS)
    avg_time  = total_time  / len(TEST_QUESTIONS)

    def cat_score(cat):
        cat_r = [r for r in results if r["category"] == cat]
        return round(sum(r["accuracy_score"] for r in cat_r) / max(len(cat_r), 1), 2)

    def diff_score(diff):
        diff_r = [r for r in results if r["difficulty"] == diff]
        return round(sum(r["accuracy_score"] for r in diff_r) / max(len(diff_r), 1), 2)

    summary = {
        "total_questions":      len(TEST_QUESTIONS),
        "average_accuracy":     round(avg_score, 2),
        "average_response_time": round(avg_time, 2),
        "results_by_difficulty": {
            "easy":   diff_score("easy"),
            "medium": diff_score("medium"),
            "hard":   diff_score("hard"),
        },
        "results_by_category": {
            cat: cat_score(cat)
            for cat in sorted(set(r["category"] for r in results))
        },
    }

    # Save JSON
    results_path = os.path.join(OUTPUT_DIR, "evaluation_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=2)

    # Save readable report
    report_path = os.path.join(OUTPUT_DIR, "evaluation_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("MAHAVAMSA GRAPHRAG — EVALUATION REPORT\n")
        f.write("=" * 65 + "\n\n")
        f.write(f"System          : GraphRAG (Neo4j + Llama 3.2 3B)\n")
        f.write(f"Total questions : {summary['total_questions']}\n")
        f.write(f"Avg accuracy    : {summary['average_accuracy']:.0%}\n")
        f.write(f"Avg response    : {summary['average_response_time']:.1f} seconds\n\n")

        f.write("ACCURACY BY DIFFICULTY:\n")
        f.write("-" * 40 + "\n")
        for diff in ["easy", "medium", "hard"]:
            score = summary["results_by_difficulty"][diff]
            bar   = "█" * int(score * 20)
            f.write(f"  {diff:<8} {score:.0%}  {bar}\n")

        f.write("\nACCURACY BY CATEGORY:\n")
        f.write("-" * 40 + "\n")
        for cat, score in summary["results_by_category"].items():
            bar = "█" * int(score * 20)
            f.write(f"  {cat:<14} {score:.0%}  {bar}\n")

        f.write("\n\nDETAILED RESULTS:\n")
        f.write("=" * 65 + "\n")
        for r in results:
            f.write(f"\n{r['id']} [{r['difficulty'].upper()}] — {r['category']}\n")
            f.write(f"Q: {r['question']}\n")
            f.write(f"   Score    : {r['accuracy_score']:.0%}\n")
            f.write(f"   Time     : {r['response_time_seconds']}s\n")
            f.write(f"   Triples  : {r['graph_triples_count']}\n")
            f.write(f"   Matched  : {', '.join(r['keywords_matched']) if r['keywords_matched'] else 'none'}\n")
            f.write(f"   Missing  : {', '.join(kw for kw in r['keywords_expected'] if kw not in r['keywords_matched'])}\n")
            f.write(f"   Answer   : {r['answer'][:250]}...\n")

        f.write("\n\nSCORECARD TABLE (for report):\n")
        f.write("=" * 65 + "\n")
        f.write(f"{'ID':<5} {'Category':<14} {'Difficulty':<10} {'Score':<8} {'Time':<8} {'Triples'}\n")
        f.write("-" * 65 + "\n")
        for r in results:
            f.write(f"{r['id']:<5} {r['category']:<14} {r['difficulty']:<10} "
                    f"{r['accuracy_score']:.0%:<8} {r['response_time_seconds']:<8} {r['graph_triples_count']}\n")

    print(f"\n{'=' * 50}")
    print(f"EVALUATION COMPLETE")
    print(f"{'=' * 50}")
    print(f"Average accuracy : {avg_score:.0%}")
    print(f"Average time     : {avg_time:.1f}s")
    print(f"Easy questions   : {summary['results_by_difficulty']['easy']:.0%}")
    print(f"Medium questions : {summary['results_by_difficulty']['medium']:.0%}")
    print(f"Hard questions   : {summary['results_by_difficulty']['hard']:.0%}")
    print(f"\nReport saved to  : {report_path}")
    print(f"JSON saved to    : {results_path}")


if __name__ == "__main__":
    run_evaluation()