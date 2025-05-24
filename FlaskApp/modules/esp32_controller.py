# modules/esp32_controller.py
import requests
import logging
from config import ESP32_IP
import cv2

logger = logging.getLogger(__name__)

def send_tcp_command(command):
    """Send HTTP command to ESP32"""
    try:
        url = f"http://{ESP32_IP}{command}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

def esp32_laser_on():
    """Turn the laser on"""
    return send_tcp_command("/esp32/laser-on")

def esp32_laser_off():
    """Turn the laser off"""
    return send_tcp_command("/esp32/laser-off")

def esp32_step_motor():
    """Step the motor 360 degrees"""
    return send_tcp_command("/esp32/step360")

def esp32_check_status():
    """Check ESP32 status"""
    return send_tcp_command("/esp32/status")