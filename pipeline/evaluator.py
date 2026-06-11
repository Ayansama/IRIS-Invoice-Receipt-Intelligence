# pipeline/evaluator.py

import pytesseract
from PIL import Image
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OCR_LANG, TESSERACT_PSM

# -------------------------------------------------------------------
# CONCEPT: Tesseract internally assigns a confidence score (0-100)
# to every word it detects. A score of 90+ means it's very sure.
# A score below 50 means it's guessing.
# By averaging these scores across the whole page, we get a single
# number that represents overall OCR quality.
# -------------------------------------------------------------------

def get_ocr_stats(image: Image.Image, label: str = "") -> dict:
    """
    Run OCR and return quality statistics.
    Returns a dict with:
      - avg_confidence : mean Tesseract confidence across all words
      - word_count     : number of words detected
      - low_conf_words : words Tesseract was unsure about (conf < 50)
      - text           : full extracted text
    """
    config = f"--psm {TESSERACT_PSM}"
    data = pytesseract.image_to_data(
        image,
        lang=OCR_LANG,
        config=config,
        output_type=pytesseract.Output.DICT
    )

    confidences = []
    words = []
    low_conf_words = []

    for i, word in enumerate(data["text"]):
        if word.strip() == "":
            continue

        conf = int(data["conf"][i])
        if conf == -1:       # Tesseract returns -1 for non-text regions
            continue

        confidences.append(conf)
        words.append(word)

        if conf < 50:
            low_conf_words.append((word, conf))

    avg_conf = sum(confidences) / len(confidences) if confidences else 0

    # Full text for character-level comparison
    text = pytesseract.image_to_string(image, lang=OCR_LANG, config=config)

    stats = {
        "label":          label,
        "word_count":     len(words),
        "avg_confidence": round(avg_conf, 2),
        "low_conf_words": low_conf_words,
        "char_count":     len(text.strip()),
        "text":           text,
    }

    return stats


def print_comparison(stats_before: dict, stats_after: dict):
    """
    Print a side-by-side comparison of before/after preprocessing stats.
    """
    print("\n" + "="*55)
    print("  OCR QUALITY COMPARISON")
    print("="*55)

    metrics = [
        ("Words detected",    "word_count"),
        ("Avg confidence",    "avg_confidence"),
        ("Characters found",  "char_count"),
    ]

    for label, key in metrics:
        before = stats_before[key]
        after  = stats_after[key]

        # Calculate improvement
        if isinstance(before, float):
            diff = f"{after - before:+.2f}"
        else:
            diff = f"{after - before:+d}"

        print(f"\n  {label}:")
        print(f"    Before  : {before}")
        print(f"    After   : {after}")
        print(f"    Change  : {diff}")

    # Low confidence words comparison
    print(f"\n  Low-confidence words (<50) before : "
          f"{len(stats_before['low_conf_words'])}")
    print(f"  Low-confidence words (<50) after  : "
          f"{len(stats_after['low_conf_words'])}")

    if stats_after["low_conf_words"]:
        print("\n  Still struggling with:")
        for word, conf in stats_after["low_conf_words"][:5]:
            print(f"    '{word}' (conf={conf})")

    print("\n" + "="*55)

    # Overall verdict
    before_conf = stats_before["avg_confidence"]
    after_conf  = stats_after["avg_confidence"]
    improvement = after_conf - before_conf

    if improvement > 5:
        print(f"  ✓ Preprocessing HELPED (+{improvement:.1f} confidence)")
    elif improvement > 0:
        print(f"  ~ Marginal improvement (+{improvement:.1f} confidence)")
    elif improvement == 0:
        print(f"  = No change in confidence")
    else:
        print(f"  ✗ Preprocessing HURT ({improvement:.1f} confidence)")
        print(f"    Consider adjusting THRESH_BLOCK_SIZE or THRESH_C")

    print("="*55 + "\n")