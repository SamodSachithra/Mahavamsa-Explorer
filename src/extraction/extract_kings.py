import pdfplumber
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

KINGS_PDF_PATH = os.getenv("KINGS_PDF_PATH", "data/raw/Kings.pdf")
OUTPUT_DIR     = os.getenv("CLEANED_OUTPUT", "data/cleaned/")


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.replace('\f', '')
    return text.strip()


def extract_kings_pdf(pdf_path):
    pages = []
    print(f"Opening: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"Total pages: {total}")
        for i in range(total):
            try:
                text = pdf.pages[i].extract_text()
                cleaned = clean_text(text)
                if cleaned:
                    pages.append({
                        "page_number": i + 1,
                        "source": "Kings.pdf",
                        "text": cleaned
                    })
            except Exception:
                pass
    print(f"Extracted: {len(pages)} pages")
    return pages


def split_into_king_profiles(pages):
    """
    Each king profile starts with their name as a heading.
    Split the full text into individual king profiles.
    """
    full_text = "\n\n".join([p["text"] for p in pages])

    # Known king names from the PDF
    king_names = [
        "පළමුවන පරාක්‍රමබාහු",
        "විජය රජු",
        "පළමුවන කාශ්‍යප රජු",
        "පස්වන මහින්ද රජු",
        "පළමුවන විජයබාහු රජු",
        "ගෞතම බුදුරජාණන්",
        "මහා දුටුගැමුණු රජු",
        "පළමුවන ගජබාහු රජු",
        "පළමුවන රාජසිංහ රජු",
        "උත්තිය රජු",
        "උපිස්ස රජු",
        "පළමුවන උදය රජු",
        "පේුකාභය රජු",
        "සංඝමිත්තා",
        "එළාර රජු",
        "මහානාම රජු",
        "දප්තපුල රජවරු",
        "කීර්ති ශ්‍රී රාජසිංහ රජු",
        "මහාරිට්ඨ ඇමතියා",
        "වලගම්බා රජු",
        "ශ්‍රී වික්‍රමරාජසිංහ රජු",
        "වසභ රජු",
        "බුද්ධදාස රජු",
        "මහාදාඨික මහානාග රජු",
        "කණිට්ඨතිස්ස රජු",
    ]

    profiles = []
    lines = full_text.split("\n")
    current_profile = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line starts a new king profile
        matched_king = None
        for king in king_names:
            if king in line and len(line) < 120:
                matched_king = king
                break

        if matched_king:
            if current_profile:
                profiles.append(current_profile)
            current_profile = {
                "king_name": matched_king,
                "title": line,
                "source": "Kings.pdf",
                "text": line + "\n"
            }
        else:
            if current_profile:
                current_profile["text"] += line + "\n"
            else:
                current_profile = {
                    "king_name": "General",
                    "title": "Introduction",
                    "source": "Kings.pdf",
                    "text": line + "\n"
                }

    if current_profile:
        profiles.append(current_profile)

    return profiles


def merge_with_existing(new_pages, new_profiles):
    """Merge Kings.pdf data with existing extracted data."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load existing all_pages.json
    pages_path = os.path.join(OUTPUT_DIR, "all_pages.json")
    if os.path.exists(pages_path):
        with open(pages_path, "r", encoding="utf-8") as f:
            existing_pages = json.load(f)
        print(f"Existing pages: {len(existing_pages)}")
    else:
        existing_pages = []
        print("No existing pages found — creating new file")

    # Adjust page numbers for new pages
    max_page = max([p["page_number"] for p in existing_pages], default=0)
    for p in new_pages:
        p["page_number"] = max_page + p["page_number"]

    combined_pages = existing_pages + new_pages
    with open(pages_path, "w", encoding="utf-8") as f:
        json.dump(combined_pages, f, ensure_ascii=False, indent=2)
    print(f"Combined pages saved: {len(combined_pages)} total")

    # Save king profiles separately
    kings_path = os.path.join(OUTPUT_DIR, "kings_profiles.json")
    with open(kings_path, "w", encoding="utf-8") as f:
        json.dump(new_profiles, f, ensure_ascii=False, indent=2)
    print(f"King profiles saved: {len(new_profiles)} profiles → {kings_path}")

    # Save plain text version
    kings_text_path = os.path.join(OUTPUT_DIR, "kings_full_text.txt")
    with open(kings_text_path, "w", encoding="utf-8") as f:
        for profile in new_profiles:
            f.write(f"\n{'='*60}\n")
            f.write(f"KING: {profile['king_name']}\n")
            f.write(f"{'='*60}\n")
            f.write(profile["text"])
            f.write("\n")
    print(f"Kings text saved: {kings_text_path}")


def main():
    print("\n=== Kings PDF Extraction ===\n")

    pages    = extract_kings_pdf(KINGS_PDF_PATH)
    profiles = split_into_king_profiles(pages)

    print(f"\nKing profiles found: {len(profiles)}")
    for p in profiles:
        word_count = len(p["text"].split())
        print(f"  {p['king_name'][:50]:<50} ({word_count} words)")

    merge_with_existing(pages, profiles)

    print("\n=== Kings extraction complete! ===")
    print("Check data/cleaned/kings_profiles.json")


if __name__ == "__main__":
    main()