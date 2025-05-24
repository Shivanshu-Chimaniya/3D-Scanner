# modules/utils.py
import qrcode
from io import BytesIO
import base64
import logging
import cv2
import os

logger = logging.getLogger(__name__)

def generate_qr_code(url):
    """Generate QR code for phone connection"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")