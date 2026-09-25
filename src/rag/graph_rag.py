import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_ollama import OllamaLLM

load_dotenv()

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "mahavamsa123")
MODEL_NAME   = "llama3.2:3b"

# Known entities for query matching
KNOWN_ENTITIES = [
    "විජය", "පරාක්‍රමබාහු", "දුටුගැමුණු", "කාශ්‍යප", "මහින්ද",
    "විජයබාහු", "එළාර", "පණ්ඩුකාභය", "රාජසිංහ", "මහාසේන",
    "අනුරාධපුරය", "පොළොන්නරුව", "සිගිරිය", "ලංකාව", "රුහුණ",
    "මහා විහාරය", "ථූපාරාමය", "රුවන්වැලි සෑය", "අභයගිරිය",
    "Vijaya", "Dutugamunu", "Anuradhapura", "Polonnaruwa",
    "Sigiriya", "Mahavihara", "Mahinda", "Parakramabahu",
]


def find_entities_in_query(query):
    """Find known entities mentioned in the user query."""
    found = []
    query_lower = query.lower()
    for entity in KNOWN_ENTITIES:
        if entity.lower() in query_lower:
            found.append(entity)
    return found


def query_graph(driver, entities):
    """
    Pull the subgraph around the mentioned entities from Neo4j.
    Returns a list of relationship triples.
    """
    if not entities:
        return []

    triples = []

    with driver.session() as session:
        for entity in entities:
            # Get all direct relationships
            result = session.run(
                """
                MATCH (a {name: $name})-[r]->(b)
                RETURN a.name AS subject,
                       r.relation AS relation,
                       b.name AS object,
                       labels(a)[0] AS subject_type,
                       labels(b)[0] AS object_type
                LIMIT 30
                """,
                name=entity
            )
            for record in result:
                triples.append({
                    "subject":      record["subject"],
                    "relation":     record["relation"],
                    "object":       record["object"],
                    "subject_type": record["subject_type"],
                    "object_type":  record["object_type"],
                })

            # Also get incoming relationships
            result = session.run(
                """
                MATCH (a)-[r]->(b {name: $name})
                RETURN a.name AS subject,
                       r.relation AS relation,
                       b.name AS object,
                       labels(a)[0] AS subject_type,
                       labels(b)[0] AS object_type
                LIMIT 30
                """,
                name=entity
            )
            for record in result:
                triples.append({
                    "subject":      record["subject"],
                    "relation":     record["relation"],
                    "object":       record["object"],
                    "subject_type": record["subject_type"],
                    "object_type":  record["object_type"],
                })

    return triples


def format_graph_context(triples):
    """Convert graph triples into readable text for the LLM."""
    if not triples:
        return "No graph data found for this query."

    lines = ["Knowledge graph facts:"]
    seen = set()
    for triple in triples:
        line = (f"  {triple['subject']} "
                f"--[{triple['relation']}]--> "
                f"{triple['object']}")
        if line not in seen:
            seen.add(line)
            lines.append(line)

    return "\n".join(lines)


def ask_question(driver, llm, question):
    print(f"\nQuestion: {question}")
    print("-" * 50)

    # Step 1: Find entities in the question
    entities = find_entities_in_query(question)
    print(f"Entities detected: {entities if entities else 'none — using general search'}")

    # Step 2: Pull subgraph from Neo4j
    if entities:
        triples = query_graph(driver, entities)
    else:
        # Fall back to pulling a broad sample from the graph
        triples = []
        with driver.session() as session:
            result = session.run(
                """
                MATCH (a:PERSON)-[r]->(b)
                RETURN a.name AS subject,
                       r.relation AS relation,
                       b.name AS object,
                       labels(a)[0] AS subject_type,
                       labels(b)[0] AS object_type
                LIMIT 50
                """
            )
            for record in result:
                triples.append({
                    "subject":      record["subject"],
                    "relation":     record["relation"],
                    "object":       record["object"],
                    "subject_type": record["subject_type"],
                    "object_type":  record["object_type"],
                })

    graph_context = format_graph_context(triples)
    print(f"Graph triples retrieved: {len(triples)}")

    # Step 3: Build prompt with graph context
    prompt = f"""You are an expert guide on the Mahavamsa,
the ancient Sri Lankan chronicle.
You have access to a knowledge graph extracted from the Mahavamsa.
Use the graph facts below to answer the question accurately.
Answer in clear English with historical context.

{graph_context}

Question: {question}

Answer:"""

    # Step 4: Get LLM response
    response = llm.invoke(prompt)
    print(f"Answer: {response}")
    return response


def main():
    print("\n=== GraphRAG System ===\n")

    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    print("Loading LLM...")
    llm = OllamaLLM(model=MODEL_NAME, temperature=0.1)

    # Test questions
    test_questions = [
        "Who was Vijaya and what is he connected to?",
        "Tell me about Anuradhapura and its historical significance.",
        "What did Dutugamunu do?",
    ]

    for question in test_questions:
        ask_question(driver, llm, question)
        print()

    # Interactive mode
    print("\n--- Interactive Mode ---")
    print("Type your question or 'quit' to exit\n")
    while True:
        user_input = input("Your question: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if user_input:
            ask_question(driver, llm, user_input)

    driver.close()


if __name__ == "__main__":
    main()