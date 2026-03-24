import cv2
import numpy as np
from PIL import Image

def extract_primary_listing_image(screenshot_path: str, output_path: str) -> bool:
    """
    Takes a full-page screenshot of an IDX real estate listing and crops out everything
    except the primary property image. Ideal for when direct image URLs are obfuscated
    or hotlink-protected.
    
    Args:
        screenshot_path: Absolute path to the raw browser screenshot
        output_path: Where to save the clean, cropped image
        
    Returns:
        bool: True if extraction was successful, False otherwise.
    """
    try:
        # Load the image using OpenCV
        img = cv2.imread(screenshot_path)
        if img is None:
            print(f"Error: Could not read {screenshot_path}")
            return False

        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply a bilateral filter to reduce noise while keeping edges sharp
        blurred = cv2.bilateralFilter(gray, 9, 75, 75)

        # Edge detection using Canny
        edges = cv2.Canny(blurred, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Sort contours by area in descending order
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        # Assuming the largest contour is the main property image
        # Real estate sites typically have the primary photo as the largest contiguous block
        if len(contours) > 0:
            largest_contour = contours[0]
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Add a slight padding buffer to ensure we don't clip the edges of the house
            # But not too much that we grab text
            pad = 10
            
            # Crop the original image
            # Ensure coordinates are within image bounds
            y_start = max(0, y - pad)
            y_end = min(img.shape[0], y + h + pad)
            x_start = max(0, x - pad)
            x_end = min(img.shape[1], x + w + pad)
            
            cropped_img = img[y_start:y_end, x_start:x_end]

            # Save the result
            cv2.imwrite(output_path, cropped_img)
            print(f"Successfully cropped and saved to {output_path}")
            return True
        else:
            print("Could not find any clear contours for the image.")
            return False

    except Exception as e:
        print(f"Exception during image cropping: {e}")
        return False

if __name__ == "__main__":
    # Example Usage for testing
    import sys
    if len(sys.argv) == 3:
        extract_primary_listing_image(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python no_api_image_scraper.py <input_screenshot.png> <output_image.png>")
