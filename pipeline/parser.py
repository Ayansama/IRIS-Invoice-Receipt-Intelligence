import re
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def extract_date(text: str) -> str | None:
  """Extract date from OCR text.
    Handles multiple formats:
      DD-MM-YYYY  → 30-06-2018
      DD/MM/YYYY  → 30/06/2018
      DD.MM.YYYY  → 30.06.2018
      YYYY-MM-DD  → 2018-06-30  (ISO format)

    Strategy:
      First try to find a date NEAR a keyword like "Date".
      If that fails, find any date pattern anywhere in the text."""
      
  # Pattern 1: DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
  pattern_dmy = r'\d{2}[-/.]\d{2}[-/.]\d{4}'
  
  # Pattern 2: YYYY-MM-DD (ISO format)
  pattern_ymd = r'\d{4}[-/.]\d{2}[-/.]\d{2}'
  
  lines = text.split('\n')
  for line in lines:
    if re.search(r'\bdate\b ', line, re.IGNORECASE):
      match = re.search(pattern_dmy,line)
      if match:
        return _normalize_date(match.group())
      match = re.search(pattern_ymd,line)
      if match:
        return _normalize_date(match.group())
  
  #find any date pattern in the full text
  match = re.search(pattern_dmy,text)
  if match:
    return _normalize_date(match.group())
  
  match = re.search(pattern_ymd,text)
  if match:
    return _normalize_date(match.group())
  
  return None
      
      
  
def _normalize_date(date_str: str) -> str:
    """
    Normalize all date formats to DD-MM-YYYY.
    Example: "30/06/2018" → "30-06-2018"
             "2018-06-30" → "30-06-2018"
    """
    # Replace slashes and dots with dashes
    normalized = date_str.replace('/', '-').replace('.', '-')
    parts = normalized.split('-')

    # If year is first (ISO format: YYYY-MM-DD), reverse it
    if len(parts[0]) == 4:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"

    return normalized
  
#Extracting Total Amount

def extract_total(text: str) -> str | None:
    """
    Extract the final total amount.

    CONCEPT: Receipts often have multiple amounts (subtotal, tax,
    total). We want the FINAL total. Strategy:
      1. Look for lines with strong keywords: "TOTAL", "GRAND TOTAL"
      2. Extract the amount from that line
      3. If multiple matches, take the LAST one (usually the final total)

    Amount pattern: one or more digits, then . or , then 2 digits
    Examples: 4.20  |  4,20  |  14.99  |  1,234.56
    """

    amount_pattern = r'\d{1,3}(?:[.,]\d{3})*[.,]\d{2}'

    # Keywords ranked by priority (stronger signal first)
    total_keywords = [
        r'grand\s+total',   # "Grand Total"
        r'\btotal\b',       # "TOTAL" (word boundary — won't match "subtotal")
        r'amount\s+due',    # "Amount Due"
        r'total\s+amount',  # "Total Amount"
    ]

    candidates = []  # collect all matches, pick the best

    lines = text.split('\n')
    for line in lines:
        for keyword in total_keywords:
            if re.search(keyword, line, re.IGNORECASE):
                match = re.search(amount_pattern, line)
                if match:
                    candidates.append(match.group())
                break  # don't double-match on same line

    if candidates:
        # Return the last candidate — on most receipts the final
        # TOTAL line appears after subtotal/tax lines
        return _normalize_amount(candidates[-1])

    # Fallback: find any amount in the text
    match = re.search(amount_pattern, text)
    if match:
        return _normalize_amount(match.group())

    return None
  
def _normalize_amount(amount_str: str) -> str:
    """
    Normalize amount to use '.' as decimal separator.
    Example: "4,20" → "4.20"   (European format)
             "4.20" → "4.20"   (already correct)
    """
    # If comma is used as decimal separator (e.g. "4,20")
    # detect by checking if comma is followed by exactly 2 digits at end
    if re.search(r',\d{2}$', amount_str):
        return amount_str.replace(',', '.')
    # Otherwise remove thousands-separator commas
    return amount_str.replace(',', '')

# Vendor name extraction

def extract_vendor(text: str) -> str | None:
    """
    Extract vendor/restaurant/store name.

    CONCEPT: The vendor name is almost always at the TOP of the
    receipt, before any transaction details. It's the hardest field
    to extract with regex alone because it has no fixed pattern —
    it's just text.

    Strategy:
      1. Skip empty lines at the top
      2. Take the first non-empty, non-numeric line
      3. Clean it up
    """
    lines = text.split('\n')

    for line in lines:
        cleaned = line.strip()

        # Skip empty lines
        if not cleaned:
            continue

        # Skip lines that are mostly numbers or symbols
        # (these are usually receipt numbers, not vendor names)
        alpha_ratio = sum(c.isalpha() for c in cleaned) / len(cleaned)
        if alpha_ratio < 0.4:
            continue

        # Skip very short lines (likely artifacts)
        if len(cleaned) < 4:
            continue

        
        return cleaned

    return None

# Invoice No extraction

#def extract_invoice_number(text: str) -> str | None:
    """
    Extract invoice or receipt number.

    Examples from receipts:
      "INV No.: 1219461"
      "Invoice #: 00234"
      "Receipt No: 8821"
      "Order: 4421-B"
    """

    # Pattern: keyword followed by optional separators and the number
    pattern = r'(?:inv(?:oice)?|receipt|order)[\s#.:no-]*([A-Z0-9-]{4,})'

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None

def extract_invoice_number(text: str) -> str | None:
    """
    Extract invoice or receipt number.
    Fixed: patterns are now ordered from most specific to least,
    and we avoid matching 'Invoice' as a standalone word.
    """

    # Pattern 1: "INV No.: 1219461" or "INV #: 1234"
    # Requires "INV" or "Invoice" followed by No/# then the number
    pattern1 = r'(?:inv\.?\s*no|invoice\s*no|invoice\s*#)[.:\s#]*([A-Z0-9-]{4,})'

    # Pattern 2: "Receipt No: 8821" or "Order: 4421-B"
    pattern2 = r'(?:receipt|order)[\s#.:no-]*([A-Z0-9-]{4,})'

    # Pattern 3: standalone "No.: 1219461" 
    pattern3 = r'\bno\.?:?\s*([0-9]{4,})'

    for pattern in [pattern1, pattern2, pattern3]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None
  
# Line items extraction

def extract_line_items(text: str) -> list:
    """
    Extract purchased items with quantity, unit price, total.

    CONCEPT: Line items are the hardest to extract with regex because
    their format varies enormously across receipts. We use a heuristic:
    a line item usually has:
      - A description (text)
      - A quantity (number, often "1x" or just "1")
      - A price (decimal number)

    We look for lines matching: <text> <qty> <price> <price>
    This is a SIMPLIFIED extractor. Phase 4 and 5 will do this
    much more accurately using bounding boxes and table detection.

    Example line: "Coke        1x  2.10  2.10  ZRL"
    """

    items = []

    # Pattern: captures description, then qty, then two prices
    # This handles formats like "Coke 1x 2.10 2.10" 
    line_item_pattern = re.compile(
        r'^(.+?)'                          # description (non-greedy)
        r'\s+(\d+x?)\s+'                  # quantity: "1" or "1x"
        r'(\d+[.,]\d{2})'                 # unit price
        r'\s+(\d+[.,]\d{2})',             # total price
        re.MULTILINE
    )

    for match in line_item_pattern.finditer(text):
        description = match.group(1).strip()
        quantity    = match.group(2).replace('x', '')
        unit_price  = _normalize_amount(match.group(3))
        total_price = _normalize_amount(match.group(4))

        # Filter out header rows (Description, Qty, etc.)
        skip_keywords = ['description', 'qty', 'item', 'price',
                         'total', 'amount']
        if any(kw in description.lower() for kw in skip_keywords):
            continue

        items.append({
            "description": description,
            "quantity":    quantity,
            "unit_price":  float(unit_price),
            "total_price": float(total_price),
        })

    return items
  
#Master Parse Function

def parse_receipt(text: str) -> dict:
    """
    Run all extractors on OCR text.
    Returns a structured dict with all extracted fields.
    """
    print("[parser] Extracting fields from OCR text...")

    vendor         = extract_vendor(text)
    date           = extract_date(text)
    invoice_number = extract_invoice_number(text)
    total          = extract_total(text)
    line_items     = extract_line_items(text)

    result = {
        "vendor":         vendor,
        "date":           date,
        "invoice_number": invoice_number,
        "total":          total,
        "line_items":     line_items,
        "raw_text":       text.strip(),
    }

    # Print extraction summary
    print(f"[parser] Vendor         : {vendor}")
    print(f"[parser] Date           : {date}")
    print(f"[parser] Invoice number : {invoice_number}")
    print(f"[parser] Total          : {total}")
    print(f"[parser] Line items     : {len(line_items)} found")

    return result
  
#For quick test

if __name__ == "__main__":
    # Testing with a hardcoded sample matching receipt
    sample_text = """
RESTORAN WAN SHENG
002043319-W
No.2, Jalan Temenggung 19/9,
Seksyen 9, Bandar Mahkota Cheras,
43200 Cheras, Selangor
GST REG NO: 001335787520
Tax Invoice
INV No.: 1219461 Cashier: Thandar
Date : 30-06-2018 22:16:06
Description Qty U.price Total TAX
Coke
1x 2.10 2.10 ZRL
Soya Bean
1x 2.10 2.10 ZRL
Total QTy: 2
Total (Excluding GST): 4.20
Total (Inclusive of GST): 4.20
TOTAL: 4.20
CASH : 4.20
    """

    result = parse_receipt(sample_text)

    print("\n--- PARSED RESULT ---")
    for key, value in result.items():
        if key != "raw_text":
            print(f"  {key}: {value}")
  