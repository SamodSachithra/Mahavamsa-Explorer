import os
import json
import pymupdf4llm
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = os.getenv("CLEANED_OUTPUT", "data/cleaned/")
MARKDOWN_DIR = "data/markdown"


def convert_pdf_to_markdown(pdf_path, output_name):
    print(f"\nConverting: {pdf_path}")
    os.makedirs(MARKDOWN_DIR, exist_ok=True)

    # Convert PDF to markdown
    md_text = pymupdf4llm.to_markdown(pdf_path)

    # Save full markdown file
    md_path = os.path.join(MARKDOWN_DIR, f"{output_name}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)
    print(f"Saved: {md_path}")

    # Split into chunks for RAG
    chunks = split_markdown_chunks(md_text, output_name)
    chunks_path = os.path.join(MARKDOWN_DIR, f"{output_name}_chunks.json")
    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved: {chunks_path} ({len(chunks)} chunks)")

    return md_text, chunks


def split_markdown_chunks(md_text, source_name):
    """
    Split markdown by headings and paragraphs into chunks.
    Each chunk keeps its heading context.
    """
    chunks = []
    lines  = md_text.split("\n")

    current_heading = ""
    current_text    = []
    chunk_id        = 0

    for line in lines:
        # Detect markdown headings
        if line.startswith("# "):
            if current_text:
                text = "\n".join(current_text).strip()
                if len(text) > 50:
                    chunks.append({
                        "id":      f"{source_name}_{chunk_id}",
                        "source":  source_name,
                        "heading": current_heading,
                        "text":    text,
                        "type":    "section",
                    })
                    chunk_id += 1
            current_heading = line.replace("# ", "").strip()
            current_text    = []

        elif line.startswith("## "):
            if current_text:
                text = "\n".join(current_text).strip()
                if len(text) > 50:
                    chunks.append({
                        "id":      f"{source_name}_{chunk_id}",
                        "source":  source_name,
                        "heading": current_heading,
                        "text":    text,
                        "type":    "subsection",
                    })
                    chunk_id += 1
            current_heading = line.replace("## ", "").strip()
            current_text    = []

        elif line.startswith("### "):
            if current_text:
                text = "\n".join(current_text).strip()
                if len(text) > 50:
                    chunks.append({
                        "id":      f"{source_name}_{chunk_id}",
                        "source":  source_name,
                        "heading": current_heading,
                        "text":    text,
                        "type":    "subsubsection",
                    })
                    chunk_id += 1
            current_heading = line.replace("### ", "").strip()
            current_text    = []

        else:
            current_text.append(line)

    # Save last chunk
    if current_text:
        text = "\n".join(current_text).strip()
        if len(text) > 50:
            chunks.append({
                "id":      f"{source_name}_{chunk_id}",
                "source":  source_name,
                "heading": current_heading,
                "text":    text,
                "type":    "section",
            })

    return chunks


def merge_chunks_to_pages(all_chunks):
    """
    Convert markdown chunks to the same format as all_pages.json
    so they work with the existing RAG pipeline.
    """
    pages = []
    for i, chunk in enumerate(all_chunks):
        # Include heading in text for better context
        text = f"{chunk['heading']}\n\n{chunk['text']}" if chunk["heading"] else chunk["text"]
        pages.append({
            "page_number": 10000 + i,  # High number to avoid collision
            "source":      chunk["source"],
            "heading":     chunk["heading"],
            "text":        text,
        })
    return pages


def merge_with_existing_pages(new_pages):
    """Add markdown pages to existing all_pages.json"""
    pages_path = os.path.join(OUTPUT_DIR, "all_pages.json")

    if os.path.exists(pages_path):
        with open(pages_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"Existing pages: {len(existing)}")
    else:
        existing = []

    # Remove any previously added markdown pages (page_number >= 10000)
    existing = [p for p in existing if p.get("page_number", 0) < 10000]

    combined = existing + new_pages
    with open(pages_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"Combined pages saved: {len(combined)} total")


def save_markdown_report(mahavamsa_chunks, kings_chunks):
    report_path = os.path.join(MARKDOWN_DIR, "markdown_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("MARKDOWN CONVERSION REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"mahavamsa.pdf chunks : {len(mahavamsa_chunks)}\n")
        f.write(f"Kings.pdf chunks     : {len(kings_chunks)}\n")
        f.write(f"Total chunks         : {len(mahavamsa_chunks) + len(kings_chunks)}\n\n")

        f.write("MAHAVAMSA CHUNKS:\n")
        f.write("-" * 40 + "\n")
        for ch in mahavamsa_chunks[:20]:
            f.write(f"  [{ch['type']}] {ch['heading'][:60]} ({len(ch['text'].split())} words)\n")

        f.write("\nKINGS.PDF CHUNKS:\n")
        f.write("-" * 40 + "\n")
        for ch in kings_chunks[:20]:
            f.write(f"  [{ch['type']}] {ch['heading'][:60]} ({len(ch['text'].split())} words)\n")

    print(f"Saved: {report_path}")


def main():
    print("\n=== PDF to Markdown Conversion ===\n")

    # Convert both PDFs
    mahavamsa_md, mahavamsa_chunks = convert_pdf_to_markdown(
        "data/raw/mahavamsa.pdf",
        "mahavamsa"
    )

    kings_md, kings_chunks = convert_pdf_to_markdown(
        "data/raw/Kings.pdf",
        "kings"
    )

    # Save combined markdown chunks as JSON
    all_chunks = mahavamsa_chunks + kings_chunks
    all_path   = os.path.join(MARKDOWN_DIR, "all_chunks.json")
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"\nAll chunks saved: {all_path} ({len(all_chunks)} total)")

    # Convert chunks to pages format and merge with existing data
    print("\nMerging with existing all_pages.json...")
    new_pages = merge_chunks_to_pages(all_chunks)
    merge_with_existing_pages(new_pages)

    # Save report
    save_markdown_report(mahavamsa_chunks, kings_chunks)

    print("\n=== Markdown conversion complete! ===")
    print(f"Check data/markdown/ folder for output files.")
    print(f"\nFiles created:")
    print(f"  data/markdown/mahavamsa.md       — Mahavamsa in markdown")
    print(f"  data/markdown/kings.md           — Kings PDF in markdown")
    print(f"  data/markdown/all_chunks.json    — All chunks combined")
    print(f"  data/markdown/markdown_report.txt — Summary report")


if __name__ == "__main__":
    main()