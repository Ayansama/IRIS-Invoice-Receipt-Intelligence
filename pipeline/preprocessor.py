import cv2
import numpy as np
from PIL import Image
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (THRESH_BLOCK_SIZE, THRESH_C,
                    QUALITY_SKIP_DENOISE, QUALITY_SKIP_THRESHOLD)


def pil_to_cv2(image: Image.Image) -> np.ndarray:
    """Convert PIL Image (RGB) → OpenCV array (BGR)."""
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def cv2_to_pil(array: np.ndarray) -> Image.Image:
    """Convert OpenCV array (BGR or GRAY) → PIL Image."""
    if len(array.shape) == 2:
        # Grayscale — no color conversion needed
        return Image.fromarray(array)
    return Image.fromarray(cv2.cvtColor(array, cv2.COLOR_BGR2RGB))


def to_grayscale(image: np.ndarray) -> np.ndarray:
  """Converting BGR image to single-channel grayscale ,
  cauz color adds no info for ocr."""
  if len(image.shape)==2:
    return image 
  return cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)


def resize_image(image: np.ndarray,target_height: int =2000) -> np.ndarray:
  h,w = image.shape[:2]
  
  if h>= target_height:
    print(f"[preprocess] Image already {h}px tall, skipping resize")
    return image
  
  scale = target_height / h
  new_w = int(w*scale)
  new_h = target_height
  
  resized = cv2.resize(image,(new_w,new_h),interpolation=cv2.INTER_CUBIC)
  print(f"[preprocess] Resized {w}x{h} -> {new_w}x{new_h}")
  return resized

# -------------------------------------------------------------------
# STEP 3: Denoising
# CONCEPT: Noise = random pixel variations that look like characters
# to Tesseract. We use two techniques:
#
#   Gaussian Blur: smooths the image by averaging pixels with their
#   neighbors, weighted by a bell curve. Good for general noise.
#
#   fastNlMeansDenoising: OpenCV's dedicated denoising algorithm.
#   Compares patches of pixels across the image to remove noise
#   while preserving edges (text strokes). Slower but better quality.
# -------------------------------------------------------------------

def denoise(image: np.ndarray,method: str = "gaussian") -> np.ndarray:
  
  if method == "gaussian":
    # Kernel size (5,5): larger = more blur = more noise removed
    # but too large blurs the text itself
    return cv2.GaussianBlur(image,(5,5),0)
  
  elif method == "nlmeans":
    # h=10: filter strength. Higher removes more noise but
    # can erase thin strokes in small text
    return cv2.fastNlMeansDenoising(image,h=10)
  
  else:
    raise ValueError(f"Unknown method: {method}")
  

def threshold(image: np.ndarray,method:str = "adaptive") -> np.ndarray:
  if method == "simple":
    _, binary = cv2.threshold(
      image,127,255, cv2.THRESH_BINARY
      )
    return binary
  
  elif method == "adaptive":
    return cv2.adaptiveThreshold(
      image,
      255,
      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
      cv2.THRESH_BINARY,
      THRESH_BLOCK_SIZE,
      THRESH_C
      
    )
  elif method == "otsu":
    #otsu's method: automatically finds the optimal global
    #threshold by analyzing the images's histogram 
    _, binary= cv2.threshold(
      image,0,255,
      cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return binary
  
  else:
    raise ValueError(f"Unknown method:{method}")
  

def deskew(image: np.ndarray) -> np.ndarray:
    """
    Detect and correct skew in a binary/grayscale image.
    Returns deskewed image.
    """
    # Find coordinates of all dark (text) pixels
    # We invert because minAreaRect works best on white-on-black
    coords = np.column_stack(np.where(image < 128))

    if len(coords) == 0:
        print("[preprocess] No text pixels found, skipping deskew")
        return image

    # Fit a minimum bounding rectangle around all text pixels
    angle = cv2.minAreaRect(coords)[-1]

    # minAreaRect returns angles in [-90, 0)
    # We convert to a human-readable rotation angle
    if angle < -45:
        angle = 90 + angle
    else:
        angle = angle

    print(f"[preprocess] Detected skew angle: {angle:.2f}°")

    # Only correct if skew is significant (ignore tiny angles)
    if abs(angle) < 0.5:
        print("[preprocess] Skew negligible, skipping correction")
        return image

    # Rotate the image around its center
    h,w = image.shape[:2]
    center = (w//2,h//2)
    M= cv2.getRotationMatrix2D(center,angle,scale=1.0)
    deskewed = cv2.warpAffine(
      image,M,(w,h),
      flags = cv2.INTER_CUBIC,
      borderMode = cv2.BORDER_REPLICATE  #fills edge with border pixels
      
    )
    return deskewed


def estimate_image_quality(image: np.ndarray) -> float:
  """Estimate image quality using Laplacian variance.
    Higher variance = sharper image = less preprocessing needed.
    
    CONCEPT: The Laplacian operator detects edges. A sharp, 
    high-contrast image has strong edges = high variance.
    A blurry or noisy image has weak, smeared edges = low variance.
    
    Empirical thresholds (tune per your dataset):
      > 500  : high quality, preprocessing may hurt
      100-500: medium quality, light preprocessing
      < 100  : low quality, aggressive preprocessing needed"""
  gray = to_grayscale(image) if len(image.shape) == 3 else image
  variance = cv2.Laplacian(gray,cv2.CV_64F).var()
  print(f"[preprocess] Image sharpness score: {variance:.1f}")
  return variance
  
def preprocess(pil_image:Image.Image,
                 denoise_method: str = "gaussian",
                 threshold_method: str = "adaptive",
                 apply_deskew: bool = True) -> Image.Image:
    
    """
    Full preprocessing pipeline.
    Input:  PIL Image (original)
    Output: PIL Image (cleaned, ready for OCR)
    """
    
    print("[preprocess] Starting preprocessing pipeline...")
    img = pil_to_cv2(pil_image)
    #-- Quatlity check first
    quality = estimate_image_quality(img)
    
    img = to_grayscale(img)
    print ("[preprocess] Grayscaled")
    
    img = resize_image(img)
    print("[preprocess] Resize")
    
    #Skip denoising if image is already sharp
    
    if quality > QUALITY_SKIP_DENOISE :
      print(f"[preprocess] Sharpness {quality:.0f} > {QUALITY_SKIP_DENOISE}, "
          f"skipping denoise")
    else:
      img = denoise(img, method= denoise_method)
      print("[preprocess] Denoised")
      
    # Skip thresholding if image is already high contrast
    if quality > QUALITY_SKIP_THRESHOLD :
      print(f"[preprocess] Sharpness {quality:.0f} > {QUALITY_SKIP_THRESHOLD}, "
          f"skipping threshold")
      
    else:
      img = threshold(img, method=threshold_method)
      print("[preprocess] Threshold")
      
    if apply_deskew:
      img = deskew(img)
      print("[preprocess] Deskewed")
      
    print("[preprocess] Preprocessing Complete.")
    return cv2_to_pil(img)
    
    
def save_debug_image(image: Image.Image, name: str, output_dir: str):
    """Save an intermediate image for visual inspection."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, name)
    image.save(path)
    print(f"[preprocess] Debug image saved → {path}")
    
    
    

  
    


if __name__ == "__main__":
    import sys
    from loader import load_document

    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python pipeline/preprocessor.py <file_path>")
        sys.exit(1)

    pages = load_document(path)
    original = pages[0]

    # Save original for comparison
    original.save("output/debug_original.png")
    print("[test] Saved original → output/debug_original.png")

    # Run preprocessing
    cleaned = preprocess(original)

    # Save result
    cleaned.save("output/debug_preprocessed.png")
    print("[test] Saved cleaned → output/debug_preprocessed.png")

    print("\nOpen both images side by side to compare!")