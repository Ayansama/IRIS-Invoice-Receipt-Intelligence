import json
import os
import re
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OUTPUT_DIR


#   Priority strategy
#   layout kv_pairs  →  preferred (label-anchored)
#   parser result    →  fallback  (pattern-based)
#   None             →  field not found


def _safe_float(value: str) -> float | None:
  if value is None :
    return None
  
  #Remove Currency symbols and whitespace
  cleaned = re.sub(r'[^\d.,]', '', str(value)).strip()
  # Normalize comma decimal separator
  if re.search(r',\d{2}$', cleaned):
        cleaned = cleaned.replace(',', '.')
  else:
        cleaned = cleaned.replace(',', '')
  try:
        return round(float(cleaned), 2)
  except ValueError:
        return None

def _clean_date(date_str: str) -> str | None:
    
    if not date_str:
        return None
    # Take only the date portion before any space
    return date_str.split()[0].strip()

def _detect_currency(text: str, kv_pairs: dict) -> str:
    
    if "gst reg no" in kv_pairs or "gst" in text.lower():
        return "MYR"
    if re.search(r'\$', text):
        return "USD"
    if re.search(r'£', text):
        return "GBP"
    if re.search(r'€', text):
        return "EUR"
    return "UNKNOWN"
  
def _extract_tax_summary(kv_pairs: dict) -> dict:
    
    summary = {}

    if "gst reg no" in kv_pairs:
        summary["gst_reg_no"] = kv_pairs["gst reg no"]

    if "total (excluding gst)" in kv_pairs:
        summary["total_excluding_gst"] = _safe_float(
            kv_pairs["total (excluding gst)"]
        )

    if "total (inclusive of gst)" in kv_pairs:
        summary["total_including_gst"] = _safe_float(
            kv_pairs["total (inclusive of gst)"]
        )

    return summary
  
def _merge_fields(parser_result: dict,
                  layout: dict,
                  items: list) -> dict:
    """
    Priority:
      layout kv_pairs  > parser_result  > None
    """
    kv_pairs = layout.get("kv_pairs", {})
    raw_text = parser_result.get("raw_text", "")

    # --- Vendor ---
    # Parser wins here — no label exists for vendor on receipts
    vendor = parser_result.get("vendor")

    # --- Date ---
    # Layout wins — anchored to "Date:" label
    # Clean to date-only, stripping time component
    raw_date = (kv_pairs.get("date")
                or parser_result.get("date"))
    date = _clean_date(raw_date)

    # --- Invoice Number ---
    # Layout wins — anchored to "INV No." label
    invoice_number = (kv_pairs.get("inv no.")
                      or kv_pairs.get("invoice no")
                      or kv_pairs.get("receipt no")
                      or parser_result.get("invoice_number"))

    # --- Total ---
    # Layout wins — anchored to "TOTAL" label
    raw_total = (kv_pairs.get("total")
                 or parser_result.get("total"))
    total = _safe_float(raw_total)

    # --- Currency ---
    currency = _detect_currency(raw_text, kv_pairs)

    # --- Line Items ---
    # Always from table_extractor — most structured source
    line_items = [
        {
            "description": item["description"],
            "quantity":    item["quantity"],
            "unit_price":  item["unit_price"],
            "total_price": item["total_price"],
            "tax_code":    item.get("tax_code"),
        }
        for item in items
        if item.get("total_price") is not None
    ]

    # --- Tax Summary ---
    tax_summary = _extract_tax_summary(kv_pairs)

    # --- Remaining KV pairs (everything not already used) ---
    used_keys = {
        "date", "inv no.", "invoice no", "receipt no",
        "total", "gst reg no",
        "total (excluding gst)", "total (inclusive of gst)"
    }
    remaining_kv = {
        k: v for k, v in kv_pairs.items()
        if k not in used_keys
    }

    return {
        "vendor":         vendor,
        "date":           date,
        "invoice_number": invoice_number,
        "total":          total,
        "currency":       currency,
        "line_items":     line_items,
        "tax_summary":    tax_summary,
        "kv_pairs":       remaining_kv,
    }


def build_json_output(parser_result: dict,
                      layout: dict,
                      items: list,
                      confidence: float = None,
                      page_count: int = 1) -> dict:
    """
    Input:
      parser_result → output of parser.parse_receipt()
      layout        → output of layout.analyze_layout()
      items         → output of table_extractor.extract_table_items()
      confidence    → avg OCR confidence score from evaluator
      page_count    → number of pages processed

    Output: complete structured dict ready for JSON serialization
    """
    print("[structurer] Building structured output...")

    # Merge all phase outputs
    merged = _merge_fields(parser_result, layout, items)

    # Add metadata
    merged["metadata"] = {
        "pipeline_version": "1.0",
        "ocr_engine":       "tesseract",
        "processed_at":     datetime.now().isoformat(),
        "pages_processed":  page_count,
        "avg_confidence":   round(confidence, 2) if confidence else None,
    }

    print(f"[structurer] vendor         : {merged['vendor']}")
    print(f"[structurer] date           : {merged['date']}")
    print(f"[structurer] invoice_number : {merged['invoice_number']}")
    print(f"[structurer] total          : {merged['total']}")
    print(f"[structurer] line_items     : {len(merged['line_items'])} items")
    print(f"[structurer] currency       : {merged['currency']}")

    return merged

import re  # make sure this is at the top with other imports


class _FloatEncoder(json.JSONEncoder):
    """
    Serialize floats with exactly 2 decimal places.
    Works by post-processing the JSON string directly.
    """
    def encode(self, obj):
        raw = super().encode(obj)
        result = re.sub(
            r'(\d+\.\d)(?!\d)',
            r'\g<1>0',
            raw
        )
        return result


def save_json(data: dict, filename: str = "output.json") -> str:
    """Save structured data to a JSON file in OUTPUT_DIR."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2,
                  ensure_ascii=False, cls=_FloatEncoder)

    print(f"[structurer] Saved JSON → {output_path}")
    return output_path


def print_json_summary(data: dict):
    """Print the final JSON output to console."""
    print("\n" + "="*55)
    print("  FINAL STRUCTURED OUTPUT")
    print("="*55)
    print(json.dumps(data, indent=2,
                     ensure_ascii=False, cls=_FloatEncoder))
    print("="*55)
    
if __name__ == "__main__":
    test = {"total": 4.20, "unit_price": 2.10}
    print(json.dumps(test, indent=2, cls=_FloatEncoder))