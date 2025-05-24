import cv2
import numpy as np
import os
import re
import logging
from math import radians, cos, sin, tan
from PIL import Image

logger = logging.getLogger(__name__)

def extract_metadata(filename):
    """Extract angle and step from filename"""
    img_num_match = re.search(r'image_(\d+)\.(?:jpg|jpeg|png)$', filename)
    
    if img_num_match:
        img_num = int(img_num_match.group(1))
        # Calculate angle based on image number
        angle = 1.8 * img_num
        return img_num, angle
    else:
        raise ValueError(f"Cannot extract metadata from filename: {filename}")

def preprocess_and_extract_line(laser_on, laser_off, scan_dir, img_num, angle, camera_matrix=None, dist_coeffs=None):
    """Preprocess images and extract laser line"""
    # Create directories for intermediate results
    gray_on_dir = os.path.join(scan_dir, 'Gray_on')
    gray_off_dir = os.path.join(scan_dir, 'Gray_off')
    diff_dir = os.path.join(scan_dir, 'difference')
    blur_dir = os.path.join(scan_dir, 'blurred')
    
    # Create folders if they don't exist
    for directory in [gray_on_dir, gray_off_dir, diff_dir, blur_dir]:
        os.makedirs(directory, exist_ok=True)
    
    # Generate timestamp for filenames
    timestamp = os.path.basename(scan_dir)
    
    # Convert to grayscale
    gray_on = cv2.cvtColor(laser_on, cv2.COLOR_BGR2GRAY)
    gray_off = cv2.cvtColor(laser_off, cv2.COLOR_BGR2GRAY)
    
    # Undistort if camera parameters are provided
    if camera_matrix is not None and dist_coeffs is not None:
        gray_on = cv2.undistort(gray_on, camera_matrix, dist_coeffs)
        gray_off = cv2.undistort(gray_off, camera_matrix, dist_coeffs)
    
    # Save grayscale images
    cv2.imwrite(os.path.join(gray_on_dir, f"{timestamp}_{img_num}_gray_on.png"), gray_on)
    cv2.imwrite(os.path.join(gray_off_dir, f"{timestamp}_{img_num}_gray_off.png"), gray_off)
    
    # Subtract background
    diff = cv2.subtract(gray_on, gray_off)
    
    # Save difference image
    cv2.imwrite(os.path.join(diff_dir, f"{timestamp}_diff.png"), diff)
    
    # Apply Gaussian blur to reduce noise
    processed_image = cv2.GaussianBlur(diff, (5, 5), 0)
    
    # Save blurred image
    cv2.imwrite(os.path.join(blur_dir, f"{timestamp}_blurred.png"), processed_image)
    
    return processed_image, diff

def extract_laser_points(processed_image):
    """Extract 2D laser line points from the processed image"""
    height, width = processed_image.shape
    points = []
    
    # For each row, find the brightest point (laser line)
    for y in range(height):
        row = processed_image[y, :]
        
        # Skip empty rows
        if np.max(row) == 0:
            continue
        
        # Find the brightest point in this row
        x = np.argmax(row)
        
        # Only include points that have some brightness
        if row[x] > 0:
            points.append((x, y))
    
    return np.array(points)

def crop_images(scan_id, crop_coords, base_dir="C:/Users/shiva/OneDrive/Desktop/Programs/Projects/3DScanner/FlaskApp/scan_images"):
    """Apply cropping to all images in a scan"""
    try:
        scan_dir = os.path.join(base_dir, scan_id)
        laser_on_dir = os.path.join(scan_dir, "laser_on")
        laser_off_dir = os.path.join(scan_dir, "laser_off")
        cropped_dir = os.path.join(scan_dir, "cropped")
        
        # Create cropped directory
        os.makedirs(os.path.join(cropped_dir, "laser_on"), exist_ok=True)
        os.makedirs(os.path.join(cropped_dir, "laser_off"), exist_ok=True)
        
        # Extract crop coordinates
        x = int(crop_coords['x'])
        y = int(crop_coords['y'])
        width = int(crop_coords['width'])
        height = int(crop_coords['height'])
        
        # Process laser-on images
        laser_on_files = sorted([f for f in os.listdir(laser_on_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        for img_file in laser_on_files:
            img_path = os.path.join(laser_on_dir, img_file)
            img = Image.open(img_path)
            cropped_img = img.crop((x, y, x + width, y + height))
            cropped_img.save(os.path.join(cropped_dir, "laser_on", img_file))
        
        # Process laser-off images
        laser_off_files = sorted([f for f in os.listdir(laser_off_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        for img_file in laser_off_files:
            img_path = os.path.join(laser_off_dir, img_file)
            img = Image.open(img_path)
            cropped_img = img.crop((x, y, x + width, y + height))
            cropped_img.save(os.path.join(cropped_dir, "laser_off", img_file))
        
        return {"success": True, "message": f"Applied cropping to {len(laser_on_files) + len(laser_off_files)} images"}
    
    except Exception as e:
        logger.error(f"Error cropping images: {str(e)}")
        return {"success": False, "message": f"Error cropping images: {str(e)}"}