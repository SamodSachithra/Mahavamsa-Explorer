import json
import os
import ollama
import chromadb
from dotenv import load_dotenv
from langchain_ollama import OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()

OUTPUT_DIR   = os.getenv("CLEANED_OUTPUT", "data/cleaned/")
CHROMA_PATH  = os.getenv("CHROMA_PATH", "data/chromadb")
MODEL_NAME   = "llama3.2:3b"
EMBED_MODEL  = "nomic-embed-text"
COLLECTION   = "mahavamsa"


def load_pages():
    path = os.path.join(OUTPUT_DIR, "all_pages.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_markdown_chunks():
    md_path = "data/markdown/all_chunks.json"
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)


def embed_text(text):
    """Embed a single text using ollama directly."""
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response.embeddings[0]


def embed_texts(texts):
    """Embed a list of texts using ollama directly."""
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response.embeddings


def build_vectorstore(pages, md_chunks):
    print("Building ChromaDB vector store...")
    print("This takes 10-20 minutes. Please wait and do not interrupt.")

    # Prepare all documents
    all_texts    = []
    all_metadata = []

    for page in pages:
        text = page.get("text", "").strip()
        if text:
            all_texts.append(text[:2000])  # Limit chunk size
            all_metadata.append({
                "page_number": str(page.get("page_number", 0)),
                "source":      page.get("source", "mahavamsa.pdf"),
                "type":        "page",
            })

    for chunk in md_chunks:
        text = chunk.get("text", "").strip()
        if text:
            heading = chunk.get("heading", "")
            full_text = f"{heading}\n\n{text}" if heading else text
            all_texts.append(full_text[:2000])
            all_metadata.append({
                "source":  chunk.get("source", "unknown"),
                "heading": heading,
                "type":    chunk.get("type", "chunk"),
            })

    print(f"Total texts to embed: {len(all_texts)}")

    # Set up ChromaDB
    os.makedirs(CHROMA_PATH, exist_ok=True)
    client     = get_chroma_client()

    # Delete existing collection if any
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )

    # Embed and add in batches
    batch_size    = 50
    total_batches = (len(all_texts) + batch_size - 1) // batch_size

    for i in range(0, len(all_texts), batch_size):
        batch_texts    = all_texts[i:i + batch_size]
        batch_metadata = all_metadata[i:i + batch_size]
        batch_ids      = [f"doc_{i + j}" for j in range(len(batch_texts))]
        batch_num      = i // batch_size + 1

        print(f"  Batch {batch_num}/{total_batches} ({len(batch_texts)} texts)...")

        try:
            embeddings = embed_texts(batch_texts)
            collection.add(
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=batch_metadata,
                ids=batch_ids,
            )
        except Exception as e:
            print(f"  Error in batch {batch_num}: {e}")
            continue

    count = collection.count()
    print(f"\nVector store built: {count} documents stored")
    print(f"Saved to: {CHROMA_PATH}")
    return collection


def load_vectorstore():
    print(f"Loading ChromaDB from: {CHROMA_PATH}")
    client     = get_chroma_client()
    collection = client.get_collection(COLLECTION)
    print(f"Loaded {collection.count()} documents")
    return collection


def ask_question(collection, llm, question):
    print(f"\nQuestion: {question}")
    print("-" * 50)

    # Embed the question
    query_embedding = embed_text(question)

    # Search ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=4,
        include=["documents", "metadatas"]
    )

    docs     = results["documents"][0]
    metas    = results["metadatas"][0]
    context  = "\n\n".join(docs)

    prompt = f"""You are an expert guide on the Mahavamsa,
the ancient Sri Lankan chronicle.
Use the following context to answer the question.
Answer in clear English.
If you cannot find the answer in the context, say so.

Context:
{context}

Question: {question}

Answer:"""

    response = llm.invoke(prompt)
    print(f"Answer: {response}")

    print(f"\nSources:")
    for meta in metas:
        source  = meta.get("source", "unknown")
        page    = meta.get("page_number", "")
        heading = meta.get("heading", "")
        if heading:
            print(f"  [{source}] {heading}")
        elif page:
            print(f"  [{source}] Page {page}")
        else:
            print(f"  [{source}]")

    return response


def chroma_exists():
    if not os.path.exists(CHROMA_PATH):
        return False
    try:
        client     = get_chroma_client()
        collection = client.get_collection(COLLECTION)
        return collection.count() > 0
    except Exception:
        return False


def main():
    print("\n=== Baseline RAG System ===\n")

    # Test Ollama connection
    try:
        models      = ollama.list()
        model_names = [m.model for m in models.models]
        print(f"Ollama connected. Models available: {len(model_names)}")
        if not any(EMBED_MODEL in m for m in model_names):
            print(f"ERROR: {EMBED_MODEL} not found.")
            print(f"Run: ollama pull {EMBED_MODEL}")
            return
        print(f"Embedding model ready: {EMBED_MODEL}")
    except Exception as e:
        print(f"Ollama connection error: {e}")
        return

    # Test embedding works
    print("Testing embedding connection...")
    try:
        test = embed_text("test")
        print(f"Embedding OK — dimension: {len(test)}")
    except Exception as e:
        print(f"Embedding test failed: {e}")
        return

    llm = OllamaLLM(model=MODEL_NAME, temperature=0.1)

    # Build or load
    if not chroma_exists():
        print("\nChromaDB not found. Building now...")
        pages      = load_pages()
        md_chunks  = load_markdown_chunks()
        print(f"Loaded {len(pages)} pages and {len(md_chunks)} markdown chunks")
        collection = build_vectorstore(pages, md_chunks)
    else:
        collection = load_vectorstore()

    # Test questions
    test_questions = [
        "Who was Vijaya and where did he come from?",
        "What temples did Dutugamunu build?",
        "What happened at Anuradhapura?",
    ]

    for question in test_questions:
        ask_question(collection, llm, question)
        print()

    # Interactive mode
    print("\n--- Interactive Mode ---")
    print("Type your question or 'quit' to exit\n")
    while True:
        user_input = input("Your question: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break
        if user_input:
            ask_question(collection, llm, user_input)


if __name__ == "__main__":
    main()