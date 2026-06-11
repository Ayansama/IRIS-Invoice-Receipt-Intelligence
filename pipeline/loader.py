import os
from PIL import Image
from pdf2image import convert_from_path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OCR_DPI

SUPPORTED_IMAGE_FORMATS = [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]

def load_document(file_path: str) -> list:
  
  if not os.path.exists(file_path):
    raise FileNotFoundError(f"File not found: {file_path}")
  
  ext = os.path.splitext(file_path)[1].lower()
  
  if ext == ".pdf":
    return _load_pdf(file_path)
  
  elif ext in SUPPORTED_IMAGE_FORMATS:
    return _load_image(file_path)
  
  else:
    raise ValueError(
      f"Unsupported format: '{ext}'. "
      f"Supported: .pdf,{','.join(SUPPORTED_IMAGE_FORMATS)}"
    )
    
def _load_pdf(file_path: str) -> list:
  print(f"[loader] Converting PDF -> images at {OCR_DPI} DPi....")
  pages = convert_from_path(file_path, dpi=OCR_DPI)
  print(f"[loader]Loader{len(pages)} page(s) from PDF")
  return pages

def _load_image(file_path: str) -> list:
  
  print(f"[loader] Loading image:{file_path}")
  img = Image.open(file_path).convert("RGB")
  return [img]


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python pipeline/loader.py <file_path>")
    else:
        pages = load_document(path)
        print(f"[test] Got {len(pages)} page(s), type: {type(pages[0])}")
        pages[0].show()