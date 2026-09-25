import pdfplumber
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

PDF_PATH = os.getenv("PDF_PATH", "data/raw/mahavamsa.pdf")
OUTPUT_DIR = os.getenv("CLEANED_OUTPUT", "data/cleaned/")


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.replace('\f', '')
    text = text.strip()
    return text


def extract_pages(pdf_path):
    pages = []
    skipped = []

    print(f"Opening PDF: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Total pages found: {total}")

        for i in range(total):
            try:
                page = pdf.pages[i]
                text = page.extract_text()
                cleaned = clean_text(text)
                if cleaned:
                    pages.append({
                        "page_number": i + 1,
                        "text": cleaned
                    })
            except Exception:
                skipped.append(i + 1)

            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{total} pages "
                      f"(extracted: {len(pages)}, skipped: {len(skipped)})")

    print(f"\nDone. Extracted: {len(pages)} pages, Skipped: {len(skipped)} pages")
    if skipped:
        print(f"Skipped page numbers: {skipped[:20]}"
              f"{'...' if len(skipped) > 20 else ''}")
    return pages


def group_into_chapters(pages):
    chapters = []
    current_chapter = None
    chapter_pattern = re.compile(r'^(\d+)\.\s+(.+)$', re.MULTILINE)

    for page in pages:
        text = page["text"]
        match = chapter_pattern.search(text)
        if match:
            if current_chapter:
                chapters.append(current_chapter)
            current_chapter = {
                "chapter_number": int(match.group(1)),
                "title": match.group(2).strip(),
                "pages": [page["page_number"]],
                "text": text
            }
        else:
            if current_chapter:
                current_chapter["text"] += "\n\n" + text
                current_chapter["pages"].append(page["page_number"])
            else:
                if chapters and chapters[-1]["chapter_number"] == 0:
                    chapters[-1]["text"] += "\n\n" + text
                    chapters[-1]["pages"].append(page["page_number"])
                else:
                    chapters.append({
                        "chapter_number": 0,
                        "title": "Preface",
                        "pages": [page["page_number"]],
                        "text": text
                    })

    if current_chapter:
        chapters.append(current_chapter)

    return chapters


def save_outputs(pages, chapters):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    pages_path = os.path.join(OUTPUT_DIR, "all_pages.json")
    with open(pages_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)
    print(f"Saved: {pages_path}")

    chapters_path = os.path.join(OUTPUT_DIR, "chapters.json")
    with open(chapters_path, "w", encoding="utf-8") as f:
        json.dump(chapters, f, ensure_ascii=False, indent=2)
    print(f"Saved: {chapters_path}")

    full_text_path = os.path.join(OUTPUT_DIR, "full_text.txt")
    with open(full_text_path, "w", encoding="utf-8") as f:
        for page in pages:
            f.write(f"\n--- Page {page['page_number']} ---\n")
            f.write(page["text"])
            f.write("\n")
    print(f"Saved: {full_text_path}")

    report_path = os.path.join(OUTPUT_DIR, "extraction_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("EXTRACTION REPORT\n")
        f.write("=" * 50 + "\n")
        f.write(f"Total pages extracted : {len(pages)}\n")
        f.write(f"Total chapters found  : {len(chapters)}\n\n")
        f.write(f"{'Ch.':<5} {'Title':<50} {'Pages':<15} {'Words'}\n")
        f.write("-" * 90 + "\n")
        for ch in chapters:
            page_range = (f"{ch['pages'][0]}–{ch['pages'][-1]}"
                          if len(ch['pages']) > 1
                          else str(ch['pages'][0]))
            word_count = len(ch['text'].split())
            f.write(f"{ch['chapter_number']:<5} "
                    f"{ch['title'][:50]:<50} "
                    f"{page_range:<15} "
                    f"{word_count}\n")
    print(f"Saved: {report_path}")


def main():
    print("\n=== Mahavamsa Text Extraction ===\n")
    pages = extract_pages(PDF_PATH)

    if not pages:
        print("ERROR: No pages extracted. Check your PDF path.")
        return

    print("\nGrouping pages into chapters...")
    chapters = group_into_chapters(pages)
    print(f"Found {len(chapters)} chapters.")

    save_outputs(pages, chapters)
    print("\n=== Extraction complete! ===")
    print(f"Check your data/cleaned/ folder.")


if __name__ == "__main__":
    main()