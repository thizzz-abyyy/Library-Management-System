import qrcode
import os
import uuid
from pathlib import Path
from flask import current_app

def generate_book_qr(book_id, isbn, title, author, location_path=None):
    """
    Generates a high-quality QR code image for a library book.
    Contains structured payload suitable for automated scanner detection and location tracking.
    """
    qr_dir = Path(current_app.config['QR_CODES_FOLDER'])
    qr_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"qr_book_{book_id}_{uuid.uuid4().hex[:8]}.png"
    filepath = qr_dir / filename
    
    # Payload format recognized by scanner with exact physical shelf location
    loc_part = f"|LOC:{location_path}" if location_path else ""
    payload = f"BOOK|ID:{book_id}|ISBN:{isbn}|TITLE:{title}{loc_part}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#0d6efd", back_color="white")
    img.save(filepath)
    
    return filename

def generate_student_qr(student_id, name, department):
    """
    Generates a QR code image for Student Library ID card.
    """
    qr_dir = Path(current_app.config['QR_CODES_FOLDER'])
    qr_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"qr_stu_{student_id}_{uuid.uuid4().hex[:8]}.png"
    filepath = qr_dir / filename
    
    payload = f"STUDENT|ID:{student_id}|NAME:{name}|DEPT:{department}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="#198754", back_color="white")
    img.save(filepath)
    
    return filename

