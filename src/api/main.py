from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_ollama import OllamaLLM
from groq import Groq as GroqClient


load_dotenv()

app = FastAPI(title="Mahavamsa GraphRAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Config ---
NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "mahavamsa123")
MODEL_NAME     = "llama3.2:3b"
CHROMA_PATH    = "data/chromadb"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
groq_client  = GroqClient(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- Init connections ---
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
llm    = OllamaLLM(model=MODEL_NAME, temperature=0.1)

# Load ChromaDB using ollama directly
import chromadb as chromadb_client

chroma_collection = None
if os.path.exists(CHROMA_PATH):
    try:
        _client           = chromadb_client.PersistentClient(path=CHROMA_PATH)
        chroma_collection = _client.get_collection("mahavamsa")
        print(f"ChromaDB loaded: {chroma_collection.count()} documents")
    except Exception as e:
        print(f"ChromaDB load error: {e}")
    
# Known entities for graph lookup
KNOWN_ENTITIES = [
    "විජය", "පරාක්‍රමබාහු", "දුටුගැමුණු", "කාශ්‍යප", "මහින්ද",
    "විජයබාහු", "එළාර", "පණ්ඩුකාභය", "රාජසිංහ", "මහාසේන",
    "අනුරාධපුරය", "පොළොන්නරුව", "සිගිරිය", "ලංකාව", "රුහුණ",
    "මහා විහාරය", "ථූපාරාමය", "රුවන්වැලි සෑය", "අභයගිරිය",
    "Vijaya", "Dutugamunu", "Anuradhapura", "Polonnaruwa",
    "Sigiriya", "Mahavihara", "Mahinda", "Parakramabahu",
    "Elara", "Pandukabhaya", "Kassapa", "Vijayabahu",
]

# Historical sites with coordinates
HISTORICAL_SITES = [
    {
        "name": "Anuradhapura",
        "sinhala": "අනුරාධපුරය",
        "lat": 8.3114,
        "lng": 80.4037,
        "description": "Ancient capital of Sri Lanka, founded in the 4th century BCE. Home to sacred Bo Tree and great stupas.",
        "google_maps": "https://maps.google.com/?q=8.3114,80.4037",
        "wikidata": "Q271403",
        "keywords": ["anuradhapura", "anuradhapuraya", "අනුරාධපුරය", "ancient capital"],
    },
    {
        "name": "Polonnaruwa",
        "sinhala": "පොළොන්නරුව",
        "lat": 7.9403,
        "lng": 81.0188,
        "description": "Medieval capital of Sri Lanka (10th–13th century). Famous for Gal Vihara rock temple.",
        "google_maps": "https://maps.google.com/?q=7.9403,81.0188",
        "wikidata": "Q484609",
        "keywords": ["polonnaruwa", "polonnaruva", "පොළොන්නරුව", "medieval capital"],
    },
    {
        "name": "Sigiriya",
        "sinhala": "සිගිරිය",
        "lat": 7.9572,
        "lng": 80.7603,
        "description": "Rock fortress built by King Kassapa (477–495 CE). UNESCO World Heritage Site.",
        "google_maps": "https://maps.google.com/?q=7.9572,80.7603",
        "wikidata": "Q131184",
        "keywords": ["sigiriya", "sinhagiri", "සිගිරිය", "rock fortress", "kassapa"],
    },
    {
        "name": "Mahiyangana",
        "sinhala": "මහියංගනය",
        "lat": 7.3290,
        "lng": 81.0003,
        "description": "One of the oldest Buddhist sites in Sri Lanka, first visited by the Buddha.",
        "google_maps": "https://maps.google.com/?q=7.3290,81.0003",
        "keywords": ["mahiyangana", "mahiyangane", "මහියංගනය"],
    },
    {
        "name": "Kelaniya",
        "sinhala": "කෙළනිය",
        "lat": 7.0,
        "lng": 79.9167,
        "description": "Temple visited by the Buddha on his third visit to Sri Lanka.",
        "google_maps": "https://maps.google.com/?q=7.0,79.9167",
        "keywords": ["kelaniya", "kelaniye", "කෙළනිය"],
    },
    {
        "name": "Dambulla",
        "sinhala": "දඹුල්ල",
        "lat": 7.8731,
        "lng": 80.6480,
        "description": "Cave temple complex with over 150 Buddha statues. UNESCO World Heritage Site.",
        "google_maps": "https://maps.google.com/?q=7.8731,80.6480",
        "keywords": ["dambulla", "දඹුල්ල", "cave temple"],
    },
    {
        "name": "Tissamaharama",
        "sinhala": "තිස්සමහාරාම",
        "lat": 6.2833,
        "lng": 81.2833,
        "description": "Southern ancient city, seat of King Kavantissa and Prince Dutugamunu.",
        "google_maps": "https://maps.google.com/?q=6.2833,81.2833",
        "keywords": ["tissamaharama", "tissa", "තිස්සමහාරාම", "kavantissa"],
    },
    {
        "name": "Mihintale",
        "sinhala": "මිහින්තලේ",
        "lat": 8.3500,
        "lng": 80.5100,
        "description": "Where Mahinda introduced Buddhism to Sri Lanka in 247 BCE.",
        "google_maps": "https://maps.google.com/?q=8.3500,80.5100",
        "keywords": ["mihintale", "mihintalaya", "මිහින්තලේ", "mahinda", "buddhism arrived"],
    },
    {
        "name": "Yapahuwa",
        "sinhala": "යාපහුව",
        "lat": 7.8167,
        "lng": 80.3500,
        "description": "Medieval rock fortress that briefly housed the Tooth Relic.",
        "google_maps": "https://maps.google.com/?q=7.8167,80.3500",
        "keywords": ["yapahuwa", "යාපහුව"],
    },
    {
        "name": "Kandy",
        "sinhala": "මහනුවර",
        "lat": 7.2906,
        "lng": 80.6337,
        "description": "Last royal capital of Sri Lanka. Home to the Temple of the Tooth Relic.",
        "google_maps": "https://maps.google.com/?q=7.2906,80.6337",
        "keywords": ["kandy", "mahanuwara", "මහනුවර", "tooth relic", "dalada"],
    },
    {
        "name": "Ruwanwelisaya",
        "sinhala": "රුවන්වැලි සෑය",
        "lat": 8.3483,
        "lng": 80.3975,
        "description": "Great stupa built by King Dutugamunu in Anuradhapura, 2nd century BCE.",
        "google_maps": "https://maps.google.com/?q=8.3483,80.3975",
        "keywords": ["ruwanwelisaya", "ruwanweli", "රුවන්වැලි", "dutugamunu stupa"],
    },
    {
        "name": "Jetavanaramaya",
        "sinhala": "ජේතවනාරාමය",
        "lat": 8.3567,
        "lng": 80.3989,
        "description": "One of the tallest ancient structures in the world, built by King Mahasena.",
        "google_maps": "https://maps.google.com/?q=8.3567,80.3989",
        "keywords": ["jetavanaramaya", "jetavana", "ජේතවනාරාමය", "mahasena"],
    },
]

# Location keywords that trigger map focus
LOCATION_TRIGGER_WORDS = [
    "where is", "how to go", "how to get to", "directions to",
    "location of", "find", "visit", "travel to", "navigate to",
    "show me", "show on map", "map of", "where can i find",
    "කොහෙද", "කොහේද", "යන්නේ කෙසේද", "ස්ථානය",
]


def detect_location_query(question: str):
    """
    Check if the question is asking about a place's location.
    Returns the matching site dict or None.
    """
    q_lower = question.lower()

    # Check if question contains location trigger words
    is_location_query = any(trigger in q_lower for trigger in LOCATION_TRIGGER_WORDS)

    # Also check if question mentions a known site directly
    matched_site = None
    for site in HISTORICAL_SITES:
        for keyword in site["keywords"]:
            if keyword.lower() in q_lower:
                matched_site = site
                break
        if matched_site:
            break

    return matched_site if (is_location_query or matched_site) else None


def find_entities(query):
    found = []
    query_lower = query.lower()
    for entity in KNOWN_ENTITIES:
        if entity.lower() in query_lower:
            found.append(entity)
    return found


def query_neo4j(entities):
    triples = []
    with driver.session() as session:
        for entity in entities:
            for cypher in [
                "MATCH (a {name: $name})-[r]->(b) RETURN a.name AS subject, r.relation AS relation, b.name AS object LIMIT 20",
                "MATCH (a)-[r]->(b {name: $name}) RETURN a.name AS subject, r.relation AS relation, b.name AS object LIMIT 20",
            ]:
                result = session.run(cypher, name=entity)
                for record in result:
                    triples.append({
                        "subject":  record["subject"],
                        "relation": record["relation"],
                        "object":   record["object"],
                    })
    return triples


def format_triples(triples):
    if not triples:
        return "No specific graph data found."
    lines = ["Knowledge graph facts:"]
    seen  = set()
    for t in triples:
        line = f"  {t['subject']} --[{t['relation']}]--> {t['object']}"
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)


def ask_graph(question, location_site=None):
    entities = find_entities(question)
    triples  = query_neo4j(entities) if entities else []
    context  = format_triples(triples)

    # Add location context if relevant
    location_context = ""
    if location_site:
        location_context = f"""
Location Information:
  Name: {location_site['name']} ({location_site['sinhala']})
  Description: {location_site['description']}
  Coordinates: {location_site['lat']}, {location_site['lng']}
  Google Maps: {location_site['google_maps']}
"""

    prompt = f"""You are an expert guide on the Mahavamsa, the ancient Sri Lankan chronicle.
Use the knowledge graph facts and location information below to answer the question.
Answer in clear English with historical detail.
If the question is about visiting or directions, provide both historical context AND practical travel information.

{context}
{location_context}

Question: {question}

Answer:"""

    answer = llm.invoke(prompt)
    return answer, entities, triples


def ask_rag(question):
    if not chroma_collection:
        return "ChromaDB not built yet. Run baseline_rag.py first.", [], []

    try:
        # Embed question using ollama directly
        import ollama
        response        = ollama.embed(model="nomic-embed-text", input=question)
        query_embedding = response.embeddings[0]

        # Search ChromaDB
        results = chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=4,
            include=["documents", "metadatas"]
        )

        docs    = results["documents"][0]
        metas   = results["metadatas"][0]
        context = "\n\n".join(docs)

        prompt = f"""You are an expert guide on the Mahavamsa,
the ancient Sri Lankan chronicle.
Use the following context to answer the question.
Answer in clear English.

Context:
{context}

Question: {question}

Answer:"""

        answer  = llm.invoke(prompt)
        sources = [
            m.get("page_number", m.get("heading", "unknown"))
            for m in metas
        ]
        return answer, [], sources

    except Exception as e:
        return f"RAG error: {str(e)}", [], []


# --- Request models ---
class QuestionRequest(BaseModel):
    question: str
    mode: Optional[str] = "graph"


# --- API Routes ---
@app.get("/")
def root():
    return {"message": "Mahavamsa GraphRAG API is running"}


@app.get("/sites")
def get_sites():
    # Return sites without internal keywords field
    clean_sites = []
    for s in HISTORICAL_SITES:
        clean_sites.append({
            "name":        s["name"],
            "sinhala":     s["sinhala"],
            "lat":         s["lat"],
            "lng":         s["lng"],
            "description": s["description"],
            "google_maps": s.get("google_maps", ""),
        })
    return {"sites": clean_sites}


@app.get("/entities")
def get_entities():
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n)
            WHERE labels(n)[0] IN ['PERSON','PLACE','STRUCTURE','EVENT']
            RETURN labels(n)[0] AS type, n.name AS name
            ORDER BY type, name
            """
        )
        entities = {}
        for record in result:
            t = record["type"]
            if t not in entities:
                entities[t] = []
            entities[t].append(record["name"])
    return {"entities": entities}


@app.get("/graph/{entity_name}")
def get_entity_graph(entity_name: str):
    triples = query_neo4j([entity_name])
    return {"entity": entity_name, "relationships": triples}


@app.post("/ask")
def ask(request: QuestionRequest):
    try:
        # Detect if this is a location/directions query
        location_site = detect_location_query(request.question)

        if request.mode == "rag":
            answer, entities, sources = ask_rag(request.question)
            return {
                "question":      request.question,
                "answer":        answer,
                "mode":          "rag",
                "sources":       sources,
                "location_site": location_site,
            }
        else:
            answer, entities, triples = ask_graph(request.question, location_site)
            return {
                "question":        request.question,
                "answer":          answer,
                "mode":            "graph",
                "entities_found":  entities,
                "graph_triples":   triples[:10],
                "location_site":   location_site,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
def get_stats():
    with driver.session() as session:
        nodes = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count"
        )
        rels  = session.run("MATCH ()-[r]->() RETURN count(r) AS count")
        node_counts = {r["label"]: r["count"] for r in nodes}
        rel_count   = rels.single()["count"]
    return {
        "nodes":         node_counts,
        "relationships": rel_count,
    }
    
from deep_translator import GoogleTranslator

@app.post("/translate")
def translate_text(request: dict):
    try:
        text        = request.get("text", "")
        target_lang = request.get("target_lang", "si")

        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        # GoogleTranslator has a 5000 char limit per request
        # Split into chunks if needed
        chunk_size = 4500
        chunks     = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

        translated_chunks = []
        for chunk in chunks:
            translated = GoogleTranslator(
                source="auto",
                target=target_lang
            ).translate(chunk)
            translated_chunks.append(translated)

        translated_text = " ".join(translated_chunks)

        return {
            "original":    text,
            "translated":  translated_text,
            "target_lang": target_lang,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/languages")
def get_languages():
    languages = [
        {"code": "si", "name": "Sinhala", "flag": "🇱🇰"},
        {"code": "ta", "name": "Tamil",   "flag": "🇮🇳"},
        {"code": "hi", "name": "Hindi",   "flag": "🇮🇳"},
        {"code": "zh-CN", "name": "Chinese", "flag": "🇨🇳"},
        {"code": "ja", "name": "Japanese", "flag": "🇯🇵"},
        {"code": "ko", "name": "Korean",  "flag": "🇰🇷"},
        {"code": "fr", "name": "French",  "flag": "🇫🇷"},
        {"code": "de", "name": "German",  "flag": "🇩🇪"},
        {"code": "es", "name": "Spanish", "flag": "🇪🇸"},
        {"code": "ar", "name": "Arabic",  "flag": "🇸🇦"},
        {"code": "pt", "name": "Portuguese", "flag": "🇵🇹"},
        {"code": "ru", "name": "Russian", "flag": "🇷🇺"},
        {"code": "it", "name": "Italian", "flag": "🇮🇹"},
        {"code": "tr", "name": "Turkish", "flag": "🇹🇷"},
        {"code": "nl", "name": "Dutch",   "flag": "🇳🇱"},
        {"code": "pl", "name": "Polish",  "flag": "🇵🇱"},
        {"code": "th", "name": "Thai",    "flag": "🇹🇭"},
        {"code": "vi", "name": "Vietnamese", "flag": "🇻🇳"},
        {"code": "ms", "name": "Malay",   "flag": "🇲🇾"},
        {"code": "id", "name": "Indonesian", "flag": "🇮🇩"},
    ]
    return {"languages": languages}

# ── Dual Agent Endpoint ──────────────────────────────────────────────
class DualAgentRequest(BaseModel):
    question: str

@app.post("/ask_agents")
def ask_dual_agents(request: DualAgentRequest):
    try:
        question = request.question

        # ── Agent 1: Local GraphRAG (Neo4j + Llama 3.2 3B) ──────
        entities      = find_entities(question)
        triples       = query_neo4j(entities) if entities else []
        graph_context = format_triples(triples)

        agent1_prompt = f"""You are a knowledge graph expert on the Mahavamsa.
Using ONLY the knowledge graph facts below, answer the question.
Be concise and factual. List specific names, dates and relationships.

{graph_context}

Question: {question}
Answer:"""

        agent1_answer = llm.invoke(agent1_prompt)
        agent1_answer = agent1_answer[:400]  # Limit to 400 chars for combiner input
        print(f"Agent 1 done: {len(agent1_answer)} chars")

        # ── Agent 2: Groq Cloud RAG (ChromaDB + Llama 3.1 8B) ───
        if chroma_collection and groq_client:
            import ollama as ollama_lib
            query_embedding = ollama_lib.embed(
                model="nomic-embed-text",
                input=question
            ).embeddings[0]

            results = chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=2,
                include=["documents"]
            )
            rag_docs    = results["documents"][0]
            rag_context = "\n\n".join([doc[:300] for doc in rag_docs])

            agent2_prompt = f"""You are a text analysis expert on the Mahavamsa,
the ancient Sri Lankan chronicle.
Using ONLY the text passages below, answer the question.
Be descriptive and provide historical context and detail.

Context:
{rag_context}

Question: {question}
Answer:"""

            agent2_response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": agent2_prompt}],
                max_tokens=512,
            )
            agent2_answer = agent2_response.choices[0].message.content
            agent2_answer = agent2_answer[:400]  # Limit to 400 chars for combiner input
        else:
            agent2_answer = "RAG agent not available."

        print(f"Agent 2 done: {len(agent2_answer)} chars")

        # ── Combiner: Groq Cloud synthesizes both answers ────────
        if groq_client:
            combiner_prompt = f"""You are a Senior Historian specializing in ancient Sri Lanka.
Two expert agents have analysed the same question.

Agent 1 (Knowledge Graph Expert — Neo4j):
{agent1_answer}

Agent 2 (Text Analysis Expert — ChromaDB):
{agent2_answer}

Synthesize both into one comprehensive, accurate, well-structured answer.
Include specific facts from Agent 1 and historical context from Agent 2.
Do not repeat yourself. Write in clear English.

Question: {question}
Final Combined Answer:"""

            combiner_response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": combiner_prompt}],
                max_tokens=700,
            )
            final_answer = combiner_response.choices[0].message.content
        else:
            final_answer = agent1_answer

        print("Combiner done.")

        return {
            "question":      question,
            "agent1_answer": agent1_answer,
            "agent2_answer": agent2_answer,
            "final_answer":  final_answer,
            "graph_triples": triples[:10],
            "mode":          "dual_agent",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))