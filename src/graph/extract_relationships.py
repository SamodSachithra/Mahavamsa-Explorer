import json
import os
import re
from dotenv import load_dotenv
from collections import defaultdict
from tqdm import tqdm

load_dotenv()

CHAPTERS_PATH  = os.getenv("CLEANED_OUTPUT", "data/cleaned/") + "chapters.json"
NER_PATH       = os.getenv("CLEANED_OUTPUT", "data/cleaned/") + "ner_results.json"
OUTPUT_DIR     = os.getenv("CLEANED_OUTPUT", "data/cleaned/")

# ------------------------------------------------------------------
# Rule-based relationship patterns (Sinhala)
# Each pattern: (regex, subject_group, object_group, relation_label)
# ------------------------------------------------------------------

RELATION_PATTERNS = [

    # Built / constructed
    (r'([\u0D80-\u0DFF\s]{3,25})\s+(?:විසින්\s+)?(\w*විහාර\w*|\w*සෑ\w*|\w*ස්තූප\w*|\w*මාළිගා\w*)\s+(?:ඉදිකළ|කරවූ|නිර්මාණය කළ|ඉදිකරවූ)',
     1, 2, "BUILT"),

    # Defeated / fought
    (r'([\u0D80-\u0DFF\s]{3,20})\s+(?:විසින්\s+)?([\u0D80-\u0DFF\s]{3,20})\s+(?:පරාජය කළ|පරදවූ|යුද්ධ කළ|ජය ගත්)',
     1, 2, "DEFEATED"),

    # Succeeded / became king after
    (r'([\u0D80-\u0DFF\s]{3,20})\s+(?:මරණයෙන්\s+පසු|ඇවෑමෙන්\s+පසු)\s+([\u0D80-\u0DFF\s]{3,20})\s+(?:රජ වූ|රාජ්‍යය ගත්|සිංහාසනය)',
     2, 1, "SUCCEEDED"),

    # Father / son relationship
    (r'([\u0D80-\u0DFF\s]{3,20})\s+(?:රජුගේ\s+)?පුත්‍ර(?:යා)?\s+([\u0D80-\u0DFF\s]{3,20})',
     2, 1, "SON_OF"),

    # Ruled / governed a place
    (r'([\u0D80-\u0DFF\s]{3,20})\s+(?:රජ|රාජ්‍යය)\s+([\u0D80-\u0DFF\s]{3,20})(?:හි|දී|ට)',
     1, 2, "RULED"),

    # Traveled to / arrived at
    (r'([\u0D80-\u0DFF\s]{3,20})\s+(?:වැඩිය|ගියේ|පැමිණියේ|පැමිණි)\s+([\u0D80-\u0DFF\s]{3,20})(?:ට|හි|දී)',
     1, 2, "TRAVELED_TO"),

    # Located at / found at
    (r'([\u0D80-\u0DFF\s]{3,20})\s+([\u0D80-\u0DFF\s]{3,20})(?:හි|දී)\s+(?:පිහිටා|ඇත|වේ|විය)',
     1, 2, "LOCATED_AT"),
]


def load_data():
    with open(CHAPTERS_PATH, "r", encoding="utf-8") as f:
        chapters = json.load(f)
    with open(NER_PATH, "r", encoding="utf-8") as f:
        ner_results = json.load(f)
    return chapters, ner_results


def build_entity_lookup(ner_results):
    """Build a flat lookup: entity_name -> entity_type"""
    lookup = {}
    for chapter in ner_results:
        for entity_type, entities in chapter["entities"].items():
            for entity in entities:
                lookup[entity] = entity_type
    return lookup


def extract_cooccurrence(chapters, ner_results):
    """
    If two entities appear in the same chapter paragraph,
    they are co-occurring — a weak but useful relationship.
    """
    relationships = []

    for i, chapter in enumerate(chapters):
        if i >= len(ner_results):
            continue

        entities = ner_results[i]["entities"]
        all_entities_in_chapter = []

        for entity_type, entity_list in entities.items():
            for entity in entity_list:
                all_entities_in_chapter.append((entity, entity_type))

        # Split chapter into paragraphs
        paragraphs = chapter["text"].split("\n\n")
        for para in paragraphs:
            para_entities = [
                (e, t) for e, t in all_entities_in_chapter
                if e in para
            ]

            # Create co-occurrence pairs
            for j in range(len(para_entities)):
                for k in range(j + 1, len(para_entities)):
                    e1, t1 = para_entities[j]
                    e2, t2 = para_entities[k]
                    if e1 != e2:
                        relationships.append({
                            "subject": e1,
                            "subject_type": t1,
                            "relation": "CO_OCCURS_WITH",
                            "object": e2,
                            "object_type": t2,
                            "chapter": chapter["chapter_number"],
                            "chapter_title": chapter["title"],
                            "confidence": 0.5
                        })

    return relationships


def extract_rule_based(chapters, entity_lookup):
    """Apply regex patterns to find typed relationships."""
    relationships = []

    for chapter in tqdm(chapters, desc="Rule-based extraction"):
        text = chapter["text"]
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            for pattern, subj_group, obj_group, relation in RELATION_PATTERNS:
                matches = re.finditer(pattern, para)
                for match in matches:
                    try:
                        subject = match.group(subj_group).strip()
                        obj     = match.group(obj_group).strip()

                        if len(subject) < 2 or len(obj) < 2:
                            continue
                        if subject == obj:
                            continue

                        subj_type = entity_lookup.get(subject, "UNKNOWN")
                        obj_type  = entity_lookup.get(obj, "UNKNOWN")

                        relationships.append({
                            "subject":       subject,
                            "subject_type":  subj_type,
                            "relation":      relation,
                            "object":        obj,
                            "object_type":   obj_type,
                            "chapter":       chapter["chapter_number"],
                            "chapter_title": chapter["title"],
                            "confidence":    0.85
                        })
                    except IndexError:
                        continue

    return relationships


def deduplicate(relationships):
    """Remove exact duplicate relationships."""
    seen = set()
    unique = []
    for rel in relationships:
        key = (rel["subject"], rel["relation"], rel["object"])
        if key not in seen:
            seen.add(key)
            unique.append(rel)
    return unique


def save_results(relationships):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Save full relationships JSON
    rel_path = os.path.join(OUTPUT_DIR, "relationships.json")
    with open(rel_path, "w", encoding="utf-8") as f:
        json.dump(relationships, f, ensure_ascii=False, indent=2)
    print(f"Saved: {rel_path}")

    # Count by relation type
    type_counts = defaultdict(int)
    for rel in relationships:
        type_counts[rel["relation"]] += 1

    # Save summary
    summary_path = os.path.join(OUTPUT_DIR, "relationships_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("RELATIONSHIP EXTRACTION SUMMARY\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total relationships : {len(relationships)}\n\n")
        f.write("By type:\n")
        for rel_type, count in sorted(
            type_counts.items(), key=lambda x: x[1], reverse=True
        ):
            f.write(f"  {count:>5}  {rel_type}\n")

        f.write("\n\nSample relationships:\n")
        f.write("-" * 50 + "\n")
        for rel in relationships[:30]:
            f.write(
                f"  {rel['subject'][:20]:<20} "
                f"--[{rel['relation']}]--> "
                f"{rel['object'][:20]}\n"
            )

    print(f"Saved: {summary_path}")
    print(f"\nTotal relationships extracted: {len(relationships)}")


def main():
    print("\n=== Relationship Extraction ===\n")

    print("Loading data...")
    chapters, ner_results = load_data()
    entity_lookup = build_entity_lookup(ner_results)
    print(f"Entity lookup built: {len(entity_lookup)} unique entities")

    print("\nExtracting rule-based relationships...")
    rule_rels = extract_rule_based(chapters, entity_lookup)
    print(f"Rule-based: {len(rule_rels)} relationships found")

    print("\nExtracting co-occurrence relationships...")
    cooc_rels = extract_cooccurrence(chapters, ner_results)
    print(f"Co-occurrence: {len(cooc_rels)} relationships found")

    print("\nMerging and deduplicating...")
    all_rels = deduplicate(rule_rels + cooc_rels)
    print(f"After dedup: {len(all_rels)} unique relationships")

    save_results(all_rels)
    print("\n=== Relationship extraction complete! ===")


if __name__ == "__main__":
    main()