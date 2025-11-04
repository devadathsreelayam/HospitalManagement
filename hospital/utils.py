import base64
from datetime import time, datetime, timedelta
from io import BytesIO

import qrcode


def generate_time_slots(start_time, end_time, slot_duration=60):
    """Generate slots for doctors"""

    slots = []
    current_time = start_time

    while current_time < end_time:
        slots.append(current_time.strftime('%H:%M'))
        # Add slot duration minutes
        current_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=slot_duration)).time()

    return slots


def generate_qr_code(data):
    """Generate QR code and return as base64 encoded string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)

    # Convert to base64 for embedding in HTML
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{image_base64}"