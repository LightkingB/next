from django.db import models


class TypeChoices(models.TextChoices):
    SPEC = "speciality", "Спец. часть"
    OTHER = "other", "Остальные"


class CategoriesChoices(models.TextChoices):
    STUDENT = "student", "Студент"
    TEACHER = "teacher", "Преподаватель"
    WORKER = "worker", "Работник"


class StatusChoices(models.TextChoices):
    RECEIVED = "received", "Получил"
    DOUBLE = "double", "Дубликат"
