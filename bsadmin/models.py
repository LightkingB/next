from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from bsadmin.manager import CustomUserManager


class Role(models.Model):
    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

    name = models.CharField(max_length=150, unique=True)

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

    roles = models.ManyToManyField("Role", related_name="users")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return self.email


class Faculty(models.Model):
    class Meta:
        verbose_name = 'Факультет'
        verbose_name_plural = 'Факультеты'

    title = models.CharField(max_length=255, verbose_name="Название")
    myedu_faculty_id = models.PositiveIntegerField(unique=True, verbose_name="MyEDU Факультет ID")
    short_name = models.CharField(max_length=150, verbose_name="Короткое название")
    visit = models.BooleanField(default=True, verbose_name="Показывать")

    def __str__(self):
        return self.title


class CategoryTranscript(models.Model):
    class Meta:
        verbose_name = 'Категория академической справки'
        verbose_name_plural = 'Категории академической справки'

    title = models.CharField(max_length=255, verbose_name="Название")

    def __str__(self):
        return self.title


class AcademicTranscript(models.Model):
    class Meta:
        verbose_name = 'Информация о академичской справки'
        verbose_name_plural = 'Информации о академичской справки'

    title = models.CharField(max_length=255, verbose_name="Название")
    count = models.PositiveIntegerField(verbose_name="Количество")
    create_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title


class FacultyTranscript(models.Model):
    class Meta:
        verbose_name = 'Академическая справка'
        verbose_name_plural = 'Академические справки'

    transcript_number = models.CharField(max_length=255, unique=True, verbose_name="Уникальный идентификатор")
    category = models.ForeignKey(CategoryTranscript, on_delete=models.PROTECT, verbose_name="Категория")
    academic_transcript = models.ForeignKey(AcademicTranscript, on_delete=models.PROTECT,
                                            verbose_name="Академическая справка")
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, verbose_name="Факультет")

    def __str__(self):
        return f'{self.transcript_number} - {self.academic_transcript.title}'

    def to_dict(self):
        return {
            'id': self.id,
            'transcript_number': self.transcript_number,
            'category': {
                'id': self.category.id,
                'title': self.category.title
            }
        }


class RegistrationTranscript(models.Model):
    class Meta:
        verbose_name = 'Регистрация студента'
        verbose_name_plural = 'Регистрация студентов'

    faculty_transcript = models.ForeignKey(FacultyTranscript, on_delete=models.PROTECT,
                                           verbose_name="Академическая справка")
    student_uuid = models.CharField(max_length=100, unique=True, verbose_name="Уникальный номер студента")
    student_fio = models.CharField(max_length=150, verbose_name="ФИО студента")
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT,
                                verbose_name="Факультет студента")

    def __str__(self):
        return f'{self.student_uuid} - {self.faculty_transcript.transcript_number}'
