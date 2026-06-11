import pytesseract
from PIL import Image
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OCR_LANG, TESSERACT_PSM


def run_tesseract(image: Image.Image, psm: int = None) -> str:
    
    psm = psm or TESSERACT_PSM
    config = f"--psm {psm}"

    print(f"[ocr] Running Tesseract (lang={OCR_LANG}, psm={psm})...")
    text = pytesseract.image_to_string(image, lang=OCR_LANG, config=config)
    return text
  
  
def run_tesseract_with_boxes(image: Image.Image, psm: int = None) -> list:
    
    psm = psm or TESSERACT_PSM
    config = f"--psm {psm}"

    print(f"[ocr] Running Tesseract with bounding boxes...")
    data = pytesseract.image_to_data(
        image,
        lang=OCR_LANG,
        config=config,
        output_type=pytesseract.Output.DICT   # returns a dict of lists
    )

    
    words = []
    n = len(data["text"])
    for i in range(n):
        if data["text"][i].strip() == "":
            continue
        words.append({
            "text":       data["text"][i],
            "left":       data["left"][i],
            "top":        data["top"][i],
            "width":      data["width"][i],
            "height":     data["height"][i],
            "conf":       data["conf"][i],      # confidence 0–100
            "block_num":  data["block_num"][i],
            "line_num":   data["line_num"][i],
            "word_num":   data["word_num"][i],
        })

    print(f"[ocr] Detected {len(words)} words")
    return words


def save_text(text: str, output_path: str):
    """Saving raw OCR text to a .txt file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[ocr] Saved raw text → {output_path}")



if __name__ == "__main__":
    import sys
    from loader import load_document

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python pipeline/ocr.py <file_path>")
        sys.exit(1)

    pages = load_document(path)
    text  = run_tesseract(pages[0])
    words = run_tesseract_with_boxes(pages[0])

    print("\n--- RAW TEXT ---")
    print(text)
    print("\n--- FIRST 5 WORD BOXES ---")
    for w in words[:5]:
        print(w)