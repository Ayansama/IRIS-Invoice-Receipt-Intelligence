import os

# Paths
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR   = os.path.join(BASE_DIR, "input")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")

# OCR settings
OCR_DPI     = 300          # Higher = better quality but slower
OCR_LANG    = "eng"
TESSERACT_PSM = 6          # Page segmentation mode

# Preprocessing
THRESH_BLOCK_SIZE = 51     # For adaptive thresholding (must be odd)
THRESH_C          = 20     # Fine-tuning constant for threshold

QUALITY_SKIP_DENOISE    = 400   # above this → skip denoising
QUALITY_SKIP_THRESHOLD  = 600   # above this → skip thresholding