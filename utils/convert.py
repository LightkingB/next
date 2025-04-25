import base64
import uuid

from django.core.files.base import ContentFile


def to_bool(value):
    if str(value).lower() in ("no", "n", "false", "f", "0", "0.0", "", "none", "None", "[]", "{}"):
        return False
    return True


def save_signature_image(base64_image):
    try:
        if not base64_image or ';base64,' not in base64_image:
            return None

        format, imgstr = base64_image.split(';base64,')
        imgdata = base64.b64decode(imgstr)

        filename = f"signatures/{uuid.uuid4()}.jpg"

        return ContentFile(imgdata, name=filename)
    except Exception:
        return None
