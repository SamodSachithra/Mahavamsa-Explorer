import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from tqdm import tqdm

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "mahavamsa123")
OUTPUT_DIR     = os.getenv("CLEANED_OUTPUT", "data/cleaned/")


def load_data():
    ner_path = os.path.join(OUTPUT_DIR, "ner_results.json")
    rel_path = os.path.join(OUTPUT_DIR, "relationships.json")

    with open(ner_path, "r", encoding="utf-8") as f:
        ner_results = json.load(f)
    with open(rel_path, "r", encoding="utf-8") as f:
        relationships = json.load(f)

    return ner_results, relationships


def clear_database(session):
    print("Clearing existing data...")
    session.run("MATCH (n) DETACH DELETE n")
    print("Database cleared.")


def create_constraints(session):
    print("Creating constraints...")
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PERSON)     REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PLACE)      REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (e:EVENT)      REQUIRE e.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:STRUCTURE)  REQUIRE s.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:CHAPTER)    REQUIRE c.number IS UNIQUE",
    ]
    for constraint in constraints:
        session.run(constraint)
    print("Constraints created.")


def load_chapters(session, ner_results):
    print("Loading chapter nodes...")
    for chapter in tqdm(ner_results, desc="Chapters"):
        session.run(
            """
            MERGE (c:CHAPTER {number: $number})
            SET c.title = $title,
                c.entity_count = $entity_count
            """,
            number=chapter["chapter_number"],
            title=chapter["title"],
            entity_count=chapter["entity_count"]
        )


def load_entities(session, ner_results):
    print("Loading entity nodes...")

    type_map = {
        "PERSON":       "PERSON",
        "PLACE":        "PLACE",
        "EVENT":        "EVENT",
        "STRUCTURE":    "STRUCTURE",
        "ORGANIZATION": "ORGANIZATION",
        "DATE":         "DATE",
    }

    for chapter in tqdm(ner_results, desc="Entities"):
        chapter_number = chapter["chapter_number"]

        for entity_type, entities in chapter["entities"].items():
            neo4j_label = type_map.get(entity_type, "ENTITY")

            for entity_name in entities:
                # Create entity node
                session.run(
                    f"""
                    MERGE (e:{neo4j_label} {{name: $name}})
                    SET e.type = $type
                    """,
                    name=entity_name,
                    type=entity_type
                )

                # Link entity to its chapter
                session.run(
                    f"""
                    MATCH (e:{neo4j_label} {{name: $name}})
                    MATCH (c:CHAPTER {{number: $chapter_number}})
                    MERGE (e)-[:APPEARS_IN]->(c)
                    """,
                    name=entity_name,
                    chapter_number=chapter_number
                )


def load_relationships(session, relationships):
    print("Loading relationships...")

    # Group by relation type for efficiency
    skipped = 0
    loaded  = 0

    for rel in tqdm(relationships, desc="Relationships"):
        subject  = rel["subject"]
        obj      = rel["object"]
        relation = rel["relation"]
        chapter  = rel.get("chapter", 0)
        conf     = rel.get("confidence", 0.5)

        try:
            session.run(
                """
                MERGE (a {name: $subject})
                MERGE (b {name: $object})
                MERGE (a)-[r:RELATES_TO {type: $relation}]->(b)
                SET r.relation    = $relation,
                    r.chapter     = $chapter,
                    r.confidence  = $confidence
                """,
                subject=subject,
                object=obj,
                relation=relation,
                chapter=chapter,
                confidence=conf
            )
            loaded += 1
        except Exception as e:
            skipped += 1

    print(f"Loaded: {loaded}, Skipped: {skipped}")


def print_stats(session):
    print("\n--- Graph Statistics ---")
    result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC")
    for record in result:
        label = record['label'] if record['label'] is not None else "Unknown"
        print(f"  {label:<15} {record['count']} nodes")

    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    for record in result:
        print(f"  {'Relationships':<15} {record['count']}")


def main():
    print("\n=== Loading Knowledge Graph into Neo4j ===\n")

    print("Loading data files...")
    ner_results, relationships = load_data()
    print(f"Chapters: {len(ner_results)}")
    print(f"Relationships: {len(relationships)}")

    print("\nConnecting to Neo4j...")
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    with driver.session() as session:
        clear_database(session)
        create_constraints(session)
        load_chapters(session, ner_results)
        load_entities(session, ner_results)
        load_relationships(session, relationships)
        print_stats(session)

    driver.close()
    print("\n=== Neo4j loading complete! ===")
    print("Open Neo4j Desktop and click 'Open Browser' to explore your graph.")


if __name__ == "__main__":
    main()