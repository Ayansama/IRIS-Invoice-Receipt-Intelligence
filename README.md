# IRIS — Invoice & Receipt Intelligence System

A Python-based pipeline that extracts structured data from invoice
and receipt images using OCR, image preprocessing, and layout analysis.

> **Note:** This project was built for learning purposes, developed
> phase by phase as part of a structured mentorship program. The goal
> was to understand how real-world document intelligence pipelines
> work — from raw image input to structured JSON output.

---

## What It Does

Takes a receipt or invoice image (JPG, PNG, or PDF) and produces
structured JSON output:

```json
{
  "vendor": "RESTORAN WAN SHENG",
  "date": "30-06-2018",
  "invoice_number": "1219461",
  "total": 4.2,
  "currency": "MYR",
  "line_items": [
    {
      "description": "Coke",
      "quantity": 1,
      "unit_price": 2.1,
      "total_price": 2.1
    },
    {
      "description": "Soya Bean",
      "quantity": 1,
      "unit_price": 2.1,
      "total_price": 2.1
    }
  ],
  "tax_summary": {
    "gst_reg_no": "001335787520",
    "total_excluding_gst": 4.2,
    "total_including_gst": 4.2
  }
}
```

---

## Pipeline Architecture

Input (PDF / Image)
↓
Phase 1 — Load & OCR loader.py, ocr.py
↓
Phase 2 — Preprocessing preprocessor.py, evaluator.py
↓
Phase 3 — Text Parsing parser.py
↓
Phase 4 — Layout Analysis layout.py
↓
Phase 5 — Table Extraction table_extractor.py
↓
Phase 6 — Structured Output structurer.py
↓
output/page_1_output.json

---

## Tech Stack

- **Python 3.10+**
- **Tesseract OCR** — text extraction engine
- **OpenCV** — image preprocessing (grayscale, threshold, deskew)
- **Pillow** — image loading and format handling
- **pdf2image** — PDF to image conversion
- **pytesseract** — Python wrapper for Tesseract
- **NumPy** — array operations for image processing

---

## Project Structure

invoice_intelligence/
├── main.py # Entry point
├── config.py # Centralized settings
├── requirements.txt
├── input/ # Drop invoices/receipts here
├── output/ # JSON results saved here
└── pipeline/
├── loader.py # Phase 1: load PDF or image
├── ocr.py # Phase 1: run Tesseract OCR
├── preprocessor.py # Phase 2: image cleaning
├── evaluator.py # Phase 2: OCR quality comparison
├── parser.py # Phase 3: regex field extraction
├── layout.py # Phase 4: bounding box layout analysis
├── table_extractor.py # Phase 5: line item extraction
└── structurer.py # Phase 6: final JSON assembly

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/IRIS-Invoice-Receipt-Intelligence.git
cd IRIS-Invoice-Receipt-Intelligence
```

### 2. Create a virtual environment

```bash
python -m venv invoice_env

# Windows
invoice_env\Scripts\activate

# macOS / Linux
source invoice_env/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract

- **Windows:** Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS:** `brew install tesseract`
- **Ubuntu:** `sudo apt install tesseract-ocr`

### 5. Run the pipeline

```bash
# Drop your invoice/receipt into input/ then:
python main.py

# Or specify a file directly:
python main.py input/your_receipt.jpg
```

Results are saved to `output/page_1_output.json`.

---

## Key Features

- **Quality-aware preprocessing** — automatically skips denoising
  and thresholding for already-clean images using Laplacian variance
- **Dual extraction strategy** — layout-anchored extraction preferred
  over regex, with regex as fallback
- **Multi-format date handling** — DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
- **Split item pairing** — handles receipts where item names and
  prices appear on separate lines
- **Currency detection** — detects MYR, USD, GBP, EUR from context
- **OCR confidence scoring** — measures and compares OCR quality
  before and after preprocessing

---

## What I Learned

This project was built phase by phase, learning one concept at a time:

- How OCR engines work and why image quality matters
- The difference between global and adaptive thresholding
- Why preprocessing can hurt as much as help on clean images
- How bounding boxes enable spatial reasoning about documents
- The difference between pattern-based and position-based extraction
- How to merge data from multiple sources with a priority strategy
- Real debugging lessons — regex ambiguity, Python scoping bugs,
  classifier ordering bugs in pairing algorithms

---

## Tested On

- Malaysian restaurant receipt (RESTORAN WAN SHENG)
- Tesseract PSM mode 6
- Image resolution: 932×1654px upscaled to 1126×2000px

---

## Future Plans

- [ ] **SROIE Dataset Testing** — run pipeline against 600+ real
      receipts to find and fix edge cases, measure accuracy formally
- [ ] **LayoutLM Integration** — replace rule-based extraction with
      Microsoft's LayoutLM transformer model for layout-aware
      document understanding
- [ ] **Multi-language Support** — extend beyond English using
      Tesseract's language packs and multilingual LayoutLM
- [ ] **REST API** — wrap the pipeline in a FastAPI endpoint so it
      can be called from any application
- [ ] **Batch Processing** — process entire folders of invoices in
      parallel with progress tracking
- [ ] **Confidence Thresholding** — flag low-confidence extractions
      for human review instead of silently returning wrong values
- [ ] **Web UI** — simple drag-and-drop interface to upload receipts
      and view extracted JSON
- [ ] **CORD Dataset Support** — extend to handle structured invoices
      beyond receipts using the CORD benchmark dataset

---

## License

MIT License — free to use, modify, and distribute.

---

## Acknowledgements

Built as a learning project with step-by-step guidance, exploring
real-world document intelligence from first principles.
