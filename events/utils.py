import qrcode
import qrcode.image.svg
from io import BytesIO
import base64


def generate_qr_code(data: str, box_size: int = 10, border: int = 4) -> str:
    """
    Generate a QR code for the given data and return it as a base64 PNG string.
    Usage in template: <img src="data:image/png;base64,{{ qr_code }}">
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_base64
