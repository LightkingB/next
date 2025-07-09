import base64
import uuid

from django.core.files.base import ContentFile

from stepper.consts import ALLOWED_EXTENSIONS


def to_bool(value):
    if str(value).lower() in ("no", "n", "false", "f", "0", "0.0", "", "none", "None", "[]", "{}"):
        return False
    return True


def save_signature_image(base64_image, storage="signatures"):
    try:
        if not base64_image or ';base64,' not in base64_image:
            return None

        header, imgstr = base64_image.split(';base64,')
        if not header.startswith('data:image/'):
            return None

        mime_type = header.split(':')[1]
        extension = mime_type.split('/')[-1].lower()

        if extension not in ALLOWED_EXTENSIONS:
            return None

        imgdata = base64.b64decode(imgstr)

        filename = f"{storage}/{uuid.uuid4()}.{extension}"
        return ContentFile(imgdata, name=filename)

    except Exception:
        return None
