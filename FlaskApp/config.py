# config.py
import os

# Server configuration
SECRET_KEY = 'your-secret-key'
HOST = '0.0.0.0'
PORT = 5000
DEBUG = True

# ESP32 configuration
ESP32_IP = "192.168.236.90"
TIME_DELAY = 0.5

# Scanning parameters
TOTAL_STEPS = 400

# Storage configuration
IMAGES_FOLDER = "scan_images"
os.makedirs(IMAGES_FOLDER, exist_ok=True)