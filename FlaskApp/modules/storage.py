# modules/storage.py
import os
import datetime
import shutil
import json
import cv2
import logging
from config import IMAGES_FOLDER

logger = logging.getLogger(__name__)

def create_scan_directory():
    """Create a new directory for a scan with appropriate subdirectories"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_dir = os.path.join(IMAGES_FOLDER, f"scan_{timestamp}")
    os.makedirs(scan_dir, exist_ok=True)
    os.makedirs(os.path.join(scan_dir, "laser_on"), exist_ok=True)
    os.makedirs(os.path.join(scan_dir, "laser_off"), exist_ok=True)
    return scan_dir

def get_all_scans():
    """Get list of all scans with metadata"""
    scans = []
    scan_dirs = [d for d in os.listdir(IMAGES_FOLDER) 
                if os.path.isdir(os.path.join(IMAGES_FOLDER, d)) and d.startswith("scan_")]
    
    for scan_dir in sorted(scan_dirs, reverse=True):
        scan_path = os.path.join(IMAGES_FOLDER, scan_dir)
        
        # Get timestamp from directory name
        timestamp_str = scan_dir.replace("scan_", "")
        try:
            timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            formatted_date = timestamp.strftime("%B %d, %Y")
            formatted_time = timestamp.strftime("%I:%M %p")
        except ValueError:
            formatted_date = "Unknown"
            formatted_time = "Unknown"
        
        # Count images in each subfolder
        laser_on_count = len([f for f in os.listdir(os.path.join(scan_path, "laser_on")) 
                            if os.path.isfile(os.path.join(scan_path, "laser_on", f)) 
                            and f.endswith(('.jpg', '.jpeg', '.png'))])
        
        laser_off_count = len([f for f in os.listdir(os.path.join(scan_path, "laser_off")) 
                            if os.path.isfile(os.path.join(scan_path, "laser_off", f)) 
                            and f.endswith(('.jpg', '.jpeg', '.png'))])
        
        # Get total folder size
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(scan_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        
        # Convert size to appropriate unit
        if total_size < 1024:
            size_str = f"{total_size} B"
        elif total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        else:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        
        # Check if this scan has been processed
        processed = os.path.exists(os.path.join(scan_path, "processed"))
        
        scans.append({
            'id': scan_dir,
            'date': formatted_date,
            'time': formatted_time,
            'laser_on_images': laser_on_count,
            'laser_off_images': laser_off_count,
            'total_images': laser_on_count + laser_off_count,
            'size': size_str,
            'processed': processed
        })
    
    return scans

def delete_scan(scan_id):
    """Delete a scan directory"""
    try:
        scan_path = os.path.join(IMAGES_FOLDER, scan_id)
        if os.path.exists(scan_path) and scan_id.startswith("scan_"):
            shutil.rmtree(scan_path)
            return {"success": True, "message": f"Deleted scan: {scan_id}"}
        else:
            return {"success": False, "message": "Invalid scan ID"}
    except Exception as e:
        logger.error(f"Error deleting scan: {str(e)}")
        return {"success": False, "message": f"Error deleting scan: {str(e)}"}