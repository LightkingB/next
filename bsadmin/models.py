from datetime import datetime

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import FileExtensionValidator
from django.db import models

from bsadmin.manager import CustomUserManager
from utils.validator import validate_file_size


class Role(models.Model):
    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    name = models.CharField(max_length=150, unique=True, verbose_name="Название")

    def __str__(self):
        return self.name


class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    email = models.EmailField(unique=True)
    myedu_id = models.CharField(max_length=150, unique=True)
    last_name = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    fathers_name = models.CharField(max_length=150, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_worker = models.BooleanField(default=False)

    roles = models.ManyToManyField("Role", related_name="users")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "myedu_id"]

    def __str__(self):
        return self.email


class Faculty(models.Model):
    COLLEGE = "CLE"
    FFACULTY = "FACT"
    SCHOOL = "SCH"

    CATEGORIES = (
        (COLLEGE, "Колледж"),
        (FFACULTY, "Факультет"),
        (SCHOOL, "Школа")
    )

    class Meta:
        verbose_name = 'Факультет'
        verbose_name_plural = 'Факультеты'

    title = models.CharField(max_length=255, verbose_name="Название")
    myedu_faculty_id = models.PositiveIntegerField(unique=True, verbose_name="MyEDU Факультет ID")
    short_name = models.CharField(max_length=150, verbose_name="Короткое название")
    visit = models.BooleanField(default=True, verbose_name="Показывать")
    category = models.CharField(max_length=15, choices=CATEGORIES, default=FFACULTY, null=True, blank=True)

    def __str__(self):
        return self.title


class Speciality(models.Model):
    class Meta:
        verbose_name = 'Специальность'
        verbose_name_plural = 'Специальности'

    title = models.CharField(max_length=255, verbose_name="Название")
    myedu_spec_id = models.PositiveIntegerField(unique=True, verbose_name="MyEDU Специальность ID")
    short_name = models.CharField(max_length=150, verbose_name="Короткое название")
    visit = models.BooleanField(default=True, verbose_name="Показывать")
    code = models.CharField(verbose_name="Шифр", max_length=255, null=True, blank=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, verbose_name="Факультет")

    def __str__(self):
        return self.title


class CategoryTranscript(models.Model):
    COLLEGE = "CLE"
    FFACULTY = "FACT"
    SCHOOL = "SCH"

    CATEGORIES = (
        (COLLEGE, "Колледж"),
        (FFACULTY, "Факультет"),
        (SCHOOL, "Школа")
    )

    class Meta:
        verbose_name = 'Категория академической справки'
        verbose_name_plural = 'Категории академической справки'

    title = models.CharField(max_length=255, verbose_name="Название")
    page_count = models.PositiveIntegerField(default=0, verbose_name="Количество страниц")
    category = models.CharField(max_length=15, choices=CATEGORIES, default=FFACULTY, null=True, blank=True)

    def __str__(self):
        return f'{self.title} - {self.page_count}'


class FacultyTranscript(models.Model):
    class Meta:
        verbose_name = 'Академическая справка'
        verbose_name_plural = 'Академические справки'
        unique_together = ('transcript_number',)

    transcript_number = models.CharField(max_length=255, unique=True, verbose_name="Введите № академической справки")
    category = models.ForeignKey(CategoryTranscript, on_delete=models.PROTECT, verbose_name="Категория")
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, verbose_name="Факультет")
    is_defective = models.BooleanField(default=False)
    files = models.FileField(upload_to="transcripts/fails/", verbose_name="Документ", blank=True, null=True,
                             validators=[
                                 FileExtensionValidator(allowed_extensions=['pdf']),
                                 validate_file_size,
                             ])

    def __str__(self):
        return f'{self.transcript_number}'

    def to_ft_dict(self):
        return {
            'id': self.id,
            'transcript_number': self.transcript_number,
            'category': {
                'id': self.category.id,
                'title': self.category.title,
                'count': self.category.page_count
            }
        }


class RegistrationTranscript(models.Model):
    class Meta:
        verbose_name = 'Регистрация студента'
        verbose_name_plural = 'Регистрация студентов'

    faculty_transcript = models.ForeignKey(FacultyTranscript, on_delete=models.PROTECT,
                                           verbose_name="Академическая справка")
    student_uuid = models.CharField(max_length=100, verbose_name="Уникальный номер студента")
    student_fio = models.CharField(max_length=150, verbose_name="ФИО студента")
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, verbose_name="Факультет студента")
    faculty_history = models.CharField(max_length=255, verbose_name="История факультета", null=True, blank=True)
    speciality = models.ForeignKey(Speciality, on_delete=models.PROTECT, verbose_name="Специальность студента")
    speciality_history = models.CharField(max_length=255, verbose_name="История специальности", null=True, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.student_uuid} - {self.faculty_transcript.transcript_number}'
