import os

from django.core.exceptions import ValidationError


def validate_file_size(value):
    filesize = value.size

    if filesize > 10485760:
        raise ValidationError("Максимальный загружаемый файл не должен превышать 10MB")
    else:
        return value


def delete_file(path):
    if os.path.isfile(path):
        os.remove(path)
