import re
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PRICE_PATTERN    = re.compile(r'\d+[.,]\d{2}')
QUANTITY_PATTERN = re.compile(r'\b\d+x?\b')
TAX_CODE_PATTERN = re.compile(r'\b[A-Z]{2,4}\b')

SKIP_PATTERNS = [
    re.compile(r'description', re.IGNORECASE),
    re.compile(r'u\.?price', re.IGNORECASE),
    re.compile(r'^\s*[-=_]{2,}\s*$'),   
    re.compile(r'^\s*$'),                
]

def is_price_line(line_text: str) -> bool:
    
    has_price    = bool(PRICE_PATTERN.search(line_text))
    has_quantity = bool(QUANTITY_PATTERN.search(line_text))
    return has_price and has_quantity
  
def is_name_line(line_text: str) -> bool:
    
    if PRICE_PATTERN.search(line_text):
        return False

    # Must have some alphabetic content
    alpha_chars = sum(c.isalpha() for c in line_text)
    return alpha_chars >= 2
  
def is_self_contained(line_text: str) -> bool:
    
    """
    Returns True ONLY if a REAL item name appears before the price.
    Rejects lines like "1x 2.10 2.10 ZRL" where only a quantity
    and tax code precede the price — no actual name present.
    """
    price_match = PRICE_PATTERN.search(line_text)
    if not price_match:
        return False

    has_quantity = bool(QUANTITY_PATTERN.search(line_text))
    if not has_quantity:
        return False

    # Get text before the first price
    text_before_price = line_text[:price_match.start()]

    # Count alphabetic characters before the price
    alpha_before = sum(c.isalpha() for c in text_before_price)

    # Reject if the only alpha content before price is a single
    # letter like 'x' in "1x" or a tax code like "ZRL"
    words_before = text_before_price.strip().split()

    # If only one word before price, it must not be a quantity or tax code
    if len(words_before) == 1:
        word = words_before[0]
        # "1x", "x", "ZRL" are NOT item names
        if re.match(r'^\d*x?$', word, re.IGNORECASE):
            return False
        if TAX_CODE_PATTERN.match(word):
            return False

    # Need at least 3 alpha chars before price to be a real name
    # "1x " has 1 alpha char → rejected
    # "Coke " has 4 alpha chars → accepted
    return alpha_before >= 3
  
def should_skip(line_text: str) -> bool:
    for pattern in SKIP_PATTERNS:
        if pattern.search(line_text):
            return True
    return False
  

#Step2: Parsing a price line into components

def parse_price_line(line_text: str) -> dict:
    """
    Extract quantity, unit_price, total_price from a price line.

    Handles these formats:
      "1x 2.10 2.10 ZRL"
      "2 x 2.10 2.10"
      "1  2.10  2.10"
      "2.10 2.10"          ← no explicit quantity, assume 1
    """
    result = {
        "quantity":    1,       # default if not found
        "unit_price":  None,
        "total_price": None,
        "tax_code":    None,
    }

    
    prices = PRICE_PATTERN.findall(line_text)

    prices = [_normalize_price(p) for p in prices]

    if len(prices) >= 2:
        # Last two numbers = unit_price, total_price
        result["unit_price"]  = float(prices[-2])
        result["total_price"] = float(prices[-1])
    elif len(prices) == 1:
        result["unit_price"]  = float(prices[0])
        result["total_price"] = float(prices[0])

    
    qty_match = re.search(r'\b(\d+)\s*x\b', line_text, re.IGNORECASE)
    if qty_match:
        result["quantity"] = int(qty_match.group(1))
    else:
        
        before_price = line_text[:line_text.find(prices[0])] if prices else ""
        qty_match = re.search(r'\b(\d+)\b', before_price)
        if qty_match:
            result["quantity"] = int(qty_match.group(1))

    
    tax_match = TAX_CODE_PATTERN.search(line_text)
    if tax_match:
        result["tax_code"] = tax_match.group()

    return result


def _normalize_price(price_str: str) -> str:
    
    if re.search(r',\d{2}$', price_str):
        return price_str.replace(',', '.')
    return price_str
  

#step 3: Pairing name lines with price lines 

def pair_lines_into_items(lines: list) -> list:
    items        = []
    pending_name = None

    for line_text in lines:
        line_text = line_text.strip()

        if should_skip(line_text):
            continue

        # If we have a pending name, a price line MUST pair with it
        # never treat it as self-contained
        if pending_name and is_price_line(line_text):
            price_data = parse_price_line(line_text)
            items.append({
                "description": pending_name,
                **price_data
            })
            pending_name = None

        elif is_self_contained(line_text):
            name_match = re.match(r'^([A-Za-z][A-Za-z\s]*?)\s+\d', line_text)
            name = name_match.group(1).strip() if name_match else line_text
            price_data = parse_price_line(line_text)
            items.append({
                "description": name,
                **price_data
            })
            pending_name = None

        elif is_price_line(line_text):
            price_data = parse_price_line(line_text)
            items.append({
                "description": pending_name or "Unknown",
                **price_data
            })
            pending_name = None

        elif is_name_line(line_text):
            if pending_name:
                items.append({
                    "description": pending_name,
                    "quantity":    None,
                    "unit_price":  None,
                    "total_price": None,
                    "tax_code":    None,
                })
            pending_name = line_text

    if pending_name:
        items.append({
            "description": pending_name,
            "quantity":    None,
            "unit_price":  None,
            "total_price": None,
            "tax_code":    None,
        })

    return items

#Step 4: Master Function

def extract_table_items(layout: dict) -> list:
    
    print("[table] Extracting line items from ITEMS region...")

    items_text = layout["regions"].get("items", "")
    
    
    

    if not items_text.strip():
        print("[table] No items region found in layout")
        return []

    
    lines = items_text.split('\n')
    print(f"[table] Processing {len(lines)} lines from items region")

    
    items = pair_lines_into_items(lines)

    
    valid_items = [
        item for item in items
        if item["total_price"] is not None
    ]

    print(f"[table] Extracted {len(valid_items)} line items")
    for item in valid_items:
        print(f"[table]   '{item['description']}' "
              f"qty={item['quantity']} "
              f"unit={item['unit_price']} "
              f"total={item['total_price']}")

    return valid_items


def print_items_table(items: list):
    """Print extracted items as a formatted table."""
    if not items:
        print("\n  No items extracted.")
        return

    print("\n" + "="*55)
    print("  EXTRACTED LINE ITEMS")
    print("="*55)
    print(f"  {'Description':<20} {'Qty':>4} {'Unit':>7} {'Total':>7} {'Tax':>5}")
    print(f"  {'-'*20} {'-'*4} {'-'*7} {'-'*7} {'-'*5}")

    for item in items:
        desc  = item['description'][:20]
        qty   = str(item['quantity'])   if item['quantity']    else '-'
        unit  = f"{item['unit_price']:.2f}"  if item['unit_price']  else '-'
        total = f"{item['total_price']:.2f}" if item['total_price'] else '-'
        tax   = item['tax_code'] or '-'
        print(f"  {desc:<20} {qty:>4} {unit:>7} {total:>7} {tax:>5}")

    print("="*55)



if __name__ == "__main__":
    import sys
    from loader import load_document
    from preprocessor import preprocess
    from ocr import run_tesseract_with_boxes
    from layout import analyze_layout

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python pipeline/table_extractor.py <file_path>")
        sys.exit(1)

    pages   = load_document(path)
    cleaned = preprocess(pages[0])
    boxes   = run_tesseract_with_boxes(cleaned)
    layout  = analyze_layout(boxes)
    items   = extract_table_items(layout)

    print_items_table(items)