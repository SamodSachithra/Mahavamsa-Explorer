import json
import os
import re
import spacy
from tqdm import tqdm
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

CHAPTERS_PATH = os.getenv("CLEANED_OUTPUT", "data/cleaned/") + "chapters.json"
OUTPUT_DIR    = os.getenv("CLEANED_OUTPUT", "data/cleaned/")

# ------------------------------------------------------------------
# Known Sinhala entity lists
# ------------------------------------------------------------------

KNOWN_KINGS = [
    "විජය", "පණ්ඩුකාභය", "දේවානම්පියතිස්ස", "දුටුගැමුණු", "එළාර",
    "වලගම්බා", "වසභ", "කණිට්ඨතිස්ස", "මහාසේන", "කිත්සිරිමේවන්",
    "සිළාකාල", "ධාතුසේන", "කාශ්‍යප", "මොග්ගල්ලාන", "අග්‍රබෝධි",
    "සේන", "උදය", "මහින්ද", "පරාක්‍රමබාහු", "විජයබාහු",
    "නිස්සංකමල්ල", "භුවනෙකබාහු", "රාජසිංහ", "විමලධර්මසූරිය",
    "කීර්ති ශ්‍රී රාජසිංහ", "ශ්‍රී වික්‍රමරාජසිංහ",
    "පළමුවන පරාක්‍රමබාහු", "ගජබා", "බුද්ධදාස",
    "කණිට්ඨතිස්ස", "මහාදාඨික", "මහාරිට්ඨ",
    "දුටුගැමුණු", "උත්තිය", "උපිස්ස", "මහානාම",
    "දප්තපුල", "එළාර", "සංඝමිත්තා", "මහාරිට්ඨ",
    "ගෞතම", "බුදුරජාණන්",
]

KNOWN_PLACES = [
    "අනුරාධපුරය", "පොළොන්නරුව", "සිගිරිය", "කෑගල්ල", "කළුතර",
    "රුහුණ", "මහියංගනය", "කෙළනිය", "කොටියාගල", "රජරට",
    "ලංකාව", "දඹදිව", "ජම්බුද්වීප", "තම්බපන්නි", "ශ්‍රී ලංකාව",
    "තිස්සමහාරාම", "කතරගම", "මාතෘ", "ගිරිහඬු", "දිඹුලාගල",
    "මහවැලි", "කාවේරි", "ගංගා", "සීතාවක", "දෙවිනුවර",
    "යාපනය", "ත්‍රිකුණාමලය", "මාතලේ", "කඳිකාමය", "නුවරඑළිය",
    "පාටලිපුත්‍ර", "උරුවෙල්", "සාර්නාත්", "කුසිනාරා", "ලුම්බිනි",
    "මහනුවර", "දඹුල්ල", "මිහින්තලේ",
]

KNOWN_EVENTS = [
    "ධර්ම සංගායනා", "යුද්ධය", "රාජාභිෂේකය", "පැමිණීම",
    "නිර්මාණය", "ජයග්‍රහණය", "පලා යාම", "මරණය", "උපත",
    "සිංහාසනය", "ගිවිසුම", "ආක්‍රමණය", "ධර්ම දේශනා",
    "ස්තූප ඉදිකිරීම", "විහාර ඉදිකිරීම", "දායකත්වය",
    "පරිනිර්වාණය", "බුද්ධත්වය", "අභිෂේකය",
]

KNOWN_STRUCTURES = [
    "මහා විහාරය", "රුවන්වැලි සෑය", "ජේතවනාරාමය", "අභයගිරිය",
    "ථූපාරාමය", "මිරිසවැටිය", "ලෝවාමහාපාය", "බෝ රුක",
    "දළදා මාළිගාව", "ඇතුල්මැදුර", "රජමහා විහාරය",
    "සිගිරිය කොටුව", "පොළොන්නරු කොටුව",
    "පරාක්‍රම සමුද්‍රය", "ගල් විහාරය", "රත්න ප්‍රාසාදය",
    "අභයගිරි විහාරය", "මල්වතු විහාරය",
]


def load_chapters():
    with open(CHAPTERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def rule_based_ner(text):
    found = defaultdict(set)
    for king in KNOWN_KINGS:
        if king in text:
            found["PERSON"].add(king)
    for place in KNOWN_PLACES:
        if place in text:
            found["PLACE"].add(place)
    for event in KNOWN_EVENTS:
        if event in text:
            found["EVENT"].add(event)
    for structure in KNOWN_STRUCTURES:
        if structure in text:
            found["STRUCTURE"].add(structure)
    return {k: list(v) for k, v in found.items()}


def spacy_ner(nlp, text):
    found = defaultdict(set)
    chunk_size = 10000
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        doc = nlp(chunk)
        for ent in doc.ents:
            label       = ent.label_
            entity_text = ent.text.strip()
            if len(entity_text) > 1:
                if label in ("PER", "PERSON"):
                    found["PERSON"].add(entity_text)
                elif label in ("LOC", "GPE", "PLACE"):
                    found["PLACE"].add(entity_text)
                elif label in ("DATE", "TIME"):
                    found["DATE"].add(entity_text)
                elif label == "ORG":
                    found["ORGANIZATION"].add(entity_text)
    return {k: list(v) for k, v in found.items()}


def extract_dates(text):
    dates = []
    patterns = [
        r'\b\d{1,4}\s*(?:BCE|CE|BC|AD)\b',
        r'\b\d{1,4}(?:වන|වැනි)\s*සියවස',
        r'\bශතවර්ෂ\s*\d+\b',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates.extend(matches)
    return list(set(dates))


def merge_entities(rule_entities, spacy_entities):
    merged = defaultdict(set)
    for entity_type, entities in rule_entities.items():
        merged[entity_type].update(entities)
    for entity_type, entities in spacy_entities.items():
        merged[entity_type].update(entities)
    return {k: sorted(list(v)) for k, v in merged.items()}


def process_chapters(chapters, nlp):
    results = []
    print("\nRunning rule-based NER on all chapters...")
    for chapter in tqdm(chapters, desc="Processing chapters"):
        text = chapter["text"]

        rule_entities  = rule_based_ner(text)
        spacy_entities = spacy_ner(nlp, text)
        dates          = extract_dates(text)

        all_entities = merge_entities(rule_entities, spacy_entities)
        if dates:
            all_entities["DATE"] = sorted(
                list(set(all_entities.get("DATE", []) + dates))
            )

        total = sum(len(v) for v in all_entities.values())

        results.append({
            "chapter_number": chapter["chapter_number"],
            "title":          chapter["title"],
            "source":         chapter.get("source", "mahavamsa.pdf"),
            "entities":       all_entities,
            "entity_count":   total
        })

    return results


def save_results(results, sorted_global):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save full NER results
    ner_path = os.path.join(OUTPUT_DIR, "ner_results.json")
    with open(ner_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {ner_path}")

    # Save global entity map
    global_path = os.path.join(OUTPUT_DIR, "global_entities.json")
    with open(global_path, "w", encoding="utf-8") as f:
        json.dump(sorted_global, f, ensure_ascii=False, indent=2)
    print(f"Saved: {global_path}")

    # Save readable summary
    summary_path = os.path.join(OUTPUT_DIR, "ner_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("NER SUMMARY REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total documents processed : {len(results)}\n")
        f.write(f"Total entities found      : {sum(r['entity_count'] for r in results)}\n\n")

        for entity_type, entities in sorted_global.items():
            f.write(f"{entity_type} ({len(entities)} unique):\n")
            top = list(entities.items())[:20]
            for name, count in top:
                f.write(f"  {count:>4}x  {name}\n")
            f.write("\n")

        f.write("\nPER DOCUMENT SUMMARY:\n")
        f.write("-" * 60 + "\n")
        for ch in results:
            source = ch.get("source", "mahavamsa.pdf")
            f.write(f"  Ch.{ch['chapter_number']:>3}  "
                    f"{ch['title'][:40]:<40}  "
                    f"{ch['entity_count']} entities  "
                    f"[{source}]\n")

    print(f"Saved: {summary_path}")


def main():
    print("\n=== Mahavamsa NER Extraction ===\n")

    print("Loading spaCy multilingual model...")
    nlp = spacy.load("xx_ent_wiki_sm")

    print("Loading chapters...")
    chapters = load_chapters()
    print(f"Loaded {len(chapters)} chapters.")

    # Also load kings profiles if they exist
    kings_path = os.path.join(OUTPUT_DIR, "kings_profiles.json")
    if os.path.exists(kings_path):
        with open(kings_path, "r", encoding="utf-8") as f:
            kings_profiles = json.load(f)
        print(f"Loaded {len(kings_profiles)} king profiles from Kings.pdf")

        for i, profile in enumerate(kings_profiles):
            chapters.append({
                "chapter_number": 200 + i,
                "title":          profile["king_name"],
                "text":           profile["text"],
                "source":         "Kings.pdf"
            })
        print(f"Total documents to process: {len(chapters)}")

    results = process_chapters(chapters, nlp)

    total_entities = sum(r["entity_count"] for r in results)
    print(f"\nTotal entities found: {total_entities}")

    # Build global entity map
    global_entities = defaultdict(lambda: defaultdict(int))
    for chapter in results:
        for entity_type, entities in chapter["entities"].items():
            for entity in entities:
                global_entities[entity_type][entity] += 1

    sorted_global = {
        entity_type: dict(
            sorted(entities.items(), key=lambda x: x[1], reverse=True)
        )
        for entity_type, entities in global_entities.items()
    }

    save_results(results, sorted_global)

    print("\n=== NER complete! ===")
    print("Check data/cleaned/ner_summary.txt for results.")


if __name__ == "__main__":
    main()