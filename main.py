import os
import sys
from config import INPUT_DIR, OUTPUT_DIR
from pipeline.loader import load_document
from pipeline.preprocessor import preprocess, save_debug_image
from pipeline.ocr    import run_tesseract, run_tesseract_with_boxes, save_text
from pipeline.evaluator import get_ocr_stats, print_comparison
from pipeline.parser import parse_receipt
from pipeline.layout import analyze_layout, print_layout_summary
from pipeline.table_extractor import extract_table_items, print_items_table
from pipeline.structurer import build_json_output, save_json, print_json_summary
from pipeline.evaluator  import get_ocr_stats   

def run_pipeline(file_path: str):
  print(f"\n{'='*55}")
  print(f"  Invoice Intelligence Pipeline")
  print(f"  Input: {file_path}")
  print(f"{'='*55}\n")
  
  #--- phase 1: Load--
  pages = load_document(file_path)
  
  for i,page in enumerate(pages):
    print(f"\n[main]--- Processing page{i+1}/{len(pages)} ---")
    # Save original for comparison
    save_debug_image(page, f"page_{i+1}_original.png", OUTPUT_DIR)
    
    # --- Phase 2: Preprocess ---
    cleaned = preprocess(page)
    save_debug_image(cleaned, f"page_{i+1}_preprocessed.png", OUTPUT_DIR)

    # --- Phase 1: OCR (now on cleaned image) ---
    raw_text     = run_tesseract(page)       # OCR on original
    cleaned_text = run_tesseract(cleaned)    # OCR on cleaned
    parsed = parse_receipt(cleaned_text)
    
    print("\n---Parsed Fields---")
    for key, value in parsed.items():
        if key != "raw_text":
         print(f"  {key}: {value}")
    

    # Compare side by side
    print("\n--- ORIGINAL OCR ---")
    print(raw_text[:300])
    print("\n--- PREPROCESSED OCR ---")
    print(cleaned_text[:300])
    
    # OCR ---
    
    raw_text = run_tesseract(page)
    word_boxes = run_tesseract_with_boxes(page)
    
    
    #Saving outputs
    os.makedirs(OUTPUT_DIR,exist_ok=True)
    txt_path = os.path.join(OUTPUT_DIR, f"page_{i+1}_raw.txt")
    save_text(raw_text, txt_path)
    
    
    stats_before = get_ocr_stats(page,    label="Original")
    stats_after  = get_ocr_stats(cleaned, label="Preprocessed")
    print_comparison(stats_before, stats_after)
    
    #Preview
    print(f"\n--- RAW TEXT PREVIEW (page {i+1}) ---")
    print(raw_text[:500])
    print(f"\n--- WORD BOX SAMPLE (first 5 words) ---")
    for w in word_boxes[:5]:
      print(f"  '{w['text']}' @ ({w['left']},{w['top']}) "
            f"conf={w['conf']}")
  
  
    #Phase 4: Layout
    layout = analyze_layout(word_boxes)
    print_layout_summary(layout)
    
    items = extract_table_items(layout)
    print_items_table(items)
    
    stats        = get_ocr_stats(cleaned, label="Final")
    confidence   = stats["avg_confidence"]
    
    structured   = build_json_output(
    parser_result = parsed,
    layout        = layout,
    items         = items,
    confidence    = confidence,
    page_count    = len(pages)
    )
    
    save_json(structured, filename=f"page_{i+1}_output.json")
    print_json_summary(structured)

    
  print(f"\n[main] Phase 1 complete. Check your output/ folder.")
  
  
if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default: pick first file in input/ folder
        files = os.listdir(INPUT_DIR)
        if not files:
            print("Drop an invoice into the input/ folder first.")
            sys.exit(1)
        file_path = os.path.join(INPUT_DIR, files[0])
    else:
        file_path = sys.argv[1]

    run_pipeline(file_path)
     