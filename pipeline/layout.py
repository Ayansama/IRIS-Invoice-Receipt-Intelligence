import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# -------------------------------------------------------------------
# CONCEPT: Tesseract gives us a FLAT list of words with coordinates.
# Layout analysis gives these words STRUCTURE by grouping them
# spatially — first into lines, then into blocks, then into regions.
#
# Think of it like reading a page:
#   Words  → you see individual words
#   Lines  → you group words left-to-right on the same row
#   Blocks → you group lines that are close together
#   Regions→ you label blocks: "this is the header", "this is items"
# -------------------------------------------------------------------


# ===================================================================
# STEP 1: GROUP WORDS INTO LINES
# ===================================================================

def group_words_into_lines(word_boxes: list) -> list:
    """
    Group flat list of word boxes into lines.
    Words are on the same line if their 'top' values are within
    a dynamic threshold based on average word height.

    Input:  [{"text":"Coke","left":42,"top":380,"height":20}, ...]
    Output: [
               [{"text":"Coke",...}, {"text":"1x",...}],  ← line 1
               [{"text":"Soya",...}, {"text":"Bean",...}], ← line 2
               ...
            ]
    """
    if not word_boxes:
        return []

    # Calculate dynamic threshold from average word height
    heights = [w["height"] for w in word_boxes if w["height"] > 0]
    avg_height = sum(heights) / len(heights) if heights else 20
    threshold  = avg_height * 0.7

    print(f"[layout] Avg word height: {avg_height:.1f}px, "
          f"line threshold: {threshold:.1f}px")

    # Sort words top-to-bottom, then left-to-right within same row
    sorted_words = sorted(word_boxes, key=lambda w: (w["top"], w["left"]))

    lines     = []
    used      = set()

    for i, word in enumerate(sorted_words):
        if i in used:
            continue

        # Start a new line with this word
        current_line = [word]
        used.add(i)

        # Find all other words on the same line
        for j, other in enumerate(sorted_words):
            if j in used:
                continue
            if abs(other["top"] - word["top"]) <= threshold:
                current_line.append(other)
                used.add(j)

        # Sort line words left-to-right
        current_line.sort(key=lambda w: w["left"])
        lines.append(current_line)

    # Sort lines top-to-bottom
    lines.sort(key=lambda line: line[0]["top"])

    print(f"[layout] Grouped {len(word_boxes)} words → {len(lines)} lines")
    return lines


# ===================================================================
# STEP 2: GROUP LINES INTO BLOCKS
# ===================================================================

def group_lines_into_blocks(lines: list) -> list:
    """
    Group lines into blocks (paragraphs / sections).
    Lines are in the same block if the vertical gap between them
    is small (less than block_gap_threshold).

    CONCEPT: A "block" is a region of text with no large vertical
    gaps. On a receipt:
      - Header (store name, address) = one block
      - Item list = one block
      - Totals section = one block
      - Footer (GST summary) = one block

    Input:  list of lines (each line is a list of word dicts)
    Output: list of blocks (each block is a list of lines)
    """
    if not lines:
        return []

    # Calculate average line height to set block gap threshold
    line_heights = []
    for line in lines:
        heights = [w["height"] for w in line]
        if heights:
            line_heights.append(max(heights))

    avg_line_height   = sum(line_heights) / len(line_heights) if line_heights else 20
    
    block_gap_threshold = avg_line_height * 1.2 #changed from 2.0 to 1.2

    print(f"[layout] Block gap threshold: {block_gap_threshold:.1f}px")

    blocks        = []
    current_block = [lines[0]]

    for i in range(1, len(lines)):
        prev_line = lines[i - 1]
        curr_line = lines[i]

        
        prev_bottom = max(w["top"] + w["height"] for w in prev_line)
        curr_top    = min(w["top"] for w in curr_line)
        gap         = curr_top - prev_bottom

        if gap > block_gap_threshold:
            # Large gap → start a new block
            blocks.append(current_block)
            current_block = [curr_line]
        else:
            current_block.append(curr_line)

    blocks.append(current_block)  

    print(f"[layout] Grouped {len(lines)} lines → {len(blocks)} blocks")
    return blocks


# ===================================================================
# STEP 3: CONVERT BLOCKS TO TEXT
# ===================================================================

def block_to_text(block: list) -> str:
    """
    Convert a block (list of lines, each line is list of word dicts)
    into a plain text string.

    Each line becomes one text row.
    Words within a line are joined by spaces.
    """
    text_lines = []
    for line in block:
        line_text = " ".join(w["text"] for w in line)
        text_lines.append(line_text)
    return "\n".join(text_lines)


# ===================================================================
# STEP 4: CLASSIFY REGIONS
# ===================================================================

def classify_blocks(blocks: list) -> dict:
    """
    Label each block as: header / items / totals / footer / unknown

    CONCEPT: We use keyword heuristics to classify:
      header  → contains store name, address, invoice number
      items   → contains quantity patterns like "1x" or prices
      totals  → contains "total", "subtotal", "tax", "cash"
      footer  → contains GST summary, thank-you messages

    Input:  list of blocks
    Output: dict mapping region name → block text
    {
      "header":  "RESTORAN WAN SHENG\n002043319-W\n...",
      "items":   "Coke\n1x 2.10 2.10\nSoya Bean\n...",
      "totals":  "TOTAL: 4.20\nCASH: 4.20\n...",
      "footer":  "GST Summary...",
    }
    """

    # Keywords that signal each region type
    region_keywords = {
    "totals": [
        r'\bTOTAL\b(?!\s+TAX)',  
        r'subtotal',
        r'amount due',
        r'grand total',
        r'\bcash\b',
        r'\bchange\b'
    ],
    "footer": [
        r'gst summary',
        r'tax summary',
        r'thank you',
        r'please come again',
        r'service charge'
    ],
    "items": [
        r'\d+x\b',
        r'\d+\.\d{2}',
    ],
    "header": [                          
        r'inv(?:oice)?\s*no',            
        r'receipt\s*no',
        r'tax\s+invoice',                
        r'cashier',
        r'gst\s+reg',
    ],
}
    classified = {
        "header":  [],
        "items":   [],
        "totals":  [],
        "footer":  [],
        "unknown": [],
    }

    for block in blocks:
        text = block_to_text(block).lower()
        matched = False 

        # Check each region type
        for region in ["footer", "totals", "header", "items"]:
            patterns = region_keywords.get(region, [])
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    classified[region].append(block_to_text(block))
                    matched = True
                    break
            if matched:
                break

    # First block is almost always the header
    # Move it from unknown to header if not already classified
    if classified["unknown"] and not classified["header"]:
        classified["header"].append(classified["unknown"].pop(0))

    # Join multiple blocks of same type
    return {k: "\n\n".join(v) for k, v in classified.items()}

# ===================================================================
# STEP 5: EXTRACT KEY-VALUE PAIRS
# ===================================================================

def extract_key_value_pairs(lines: list) -> dict:
    """
    Find lines that look like "Label : Value" and extract them.
    """
    kv_pairs = {}

    for line in lines:
        line_text = " ".join(w["text"] for w in line)

        match = re.match(r'^(.+?)\s*[：:]\s*(.+)$', line_text.strip())
        if not match:          
            continue           

        
        key   = match.group(1).strip().lower()
        value = match.group(2).strip()

        # Clean noisy OCR characters from key (removes +, *, # etc.)
        key = re.sub(r'[^a-z0-9\s()./-]', '', key).strip()
        key = re.sub(r'\s+', ' ', key)

        # Truncate value if it bleeds into next KV pair on same line
        truncate_match = re.search(
            r'\s+(?:cashier|date|time|ref|no|inv|order)\b.{0,10}:',
            value, re.IGNORECASE
        )
        if truncate_match:
            value = value[:truncate_match.start()].strip()

        # Skip if key is empty or too long after cleaning
        if not key or len(key.split()) > 4:
            continue

        kv_pairs[key] = value

    print(f"[layout] Extracted {len(kv_pairs)} key-value pairs")
    return kv_pairs


# ===================================================================
# MASTER FUNCTION
# ===================================================================

def analyze_layout(word_boxes: list) -> dict:
    """
    Full layout analysis pipeline.
    Input:  flat list of word boxes from Tesseract
    Output: dict with lines, blocks, regions, key-value pairs
    """
    print("[layout] Starting layout analysis...")

    lines    = group_words_into_lines(word_boxes)
    blocks   = group_lines_into_blocks(lines)
    regions  = classify_blocks(blocks)
    kv_pairs = extract_key_value_pairs(lines)

    result = {
        "lines":    lines,
        "blocks":   blocks,
        "regions":  regions,
        "kv_pairs": kv_pairs,
    }

    print("[layout] Layout analysis complete.")
    return result


def print_layout_summary(layout: dict):
    """Print a readable summary of layout analysis results."""

    print("\n" + "="*55)
    print("  LAYOUT ANALYSIS SUMMARY")
    print("="*55)

    print(f"\n  Lines detected  : {len(layout['lines'])}")
    print(f"  Blocks detected : {len(layout['blocks'])}")

    print("\n  --- REGIONS ---")
    for region, text in layout["regions"].items():
        if text.strip():
            preview = text[:80].replace('\n', ' | ')
            print(f"\n  [{region.upper()}]")
            print(f"  {preview}...")

    print("\n  --- KEY-VALUE PAIRS ---")
    for key, value in layout["kv_pairs"].items():
        print(f"  '{key}' → '{value}'")

    print("="*55)


# ===================================================================
# Quick test
# python pipeline/layout.py
# ===================================================================
if __name__ == "__main__":
    import sys
    from loader import load_document
    from preprocessor import preprocess
    from ocr import run_tesseract_with_boxes

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python pipeline/layout.py <file_path>")
        sys.exit(1)

    pages     = load_document(path)
    cleaned   = preprocess(pages[0])
    boxes     = run_tesseract_with_boxes(cleaned)
    layout    = analyze_layout(boxes)

    print_layout_summary(layout)