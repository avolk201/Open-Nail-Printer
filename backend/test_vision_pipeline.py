import cv2
import numpy as np
import logging
from cv_pipeline import apply_warping, halftone_image

logging.basicConfig(level=logging.INFO)

def main():
    # Load a test image
    img_path = "uploads/christmas.jpeg"
    img = cv2.imread(img_path)
    
    if img is None:
        print(f"Failed to load image from {img_path}")
        return
        
    # Resize image for faster processing during test
    img = cv2.resize(img, (300, 300))
    
    print("Applying warping...")
    warped = apply_warping(img)
    
    print("Applying halftoning...")
    halftoned = halftone_image(warped)
    
    cv2.imwrite("warped_test.png", warped)
    cv2.imwrite("halftoned_test.png", halftoned)
    
    print("Done! Check warped_test.png and halftoned_test.png")

if __name__ == "__main__":
    main()
