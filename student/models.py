import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from student.choices import QuestionType


PHONE_PATTERN = re.compile(r"^\+?[\d\s\-()]{9,20}$")


def validate_work_phone(value):
    if not value or not PHONE_PATTERN.match(value.strip()):
        raise ValidationError(_("Введите корректный номер телефона."))


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name=_("Пользователь"),
    )
    work_phone = models.CharField(
        max_length=20,
        verbose_name=_("Рабочий телефон"),
        validators=[validate_work_phone],
    )

    class Meta:
        verbose_name = _("Профиль студента")
        verbose_name_plural = _("Профили студентов")

    def __str__(self):
        return f"{self.user.email} — {self.work_phone}"


class Survey(models.Model):
    title = models.CharField(max_length=255, verbose_name=_("Название"))
    description = models.TextField(blank=True, verbose_name=_("Описание"))
    is_active = models.BooleanField(default=False, verbose_name=_("Активна"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Создана"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Обновлена"))

    class Meta:
        verbose_name = _("Анкета")
        verbose_name_plural = _("Анкеты")
        ordering = ("-created_at",)

    def __str__(self):
        return self.title


class SurveyQuestion(models.Model):
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name=_("Анкета"),
    )
    text = models.TextField(verbose_name=_("Текст вопроса"))
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        verbose_name=_("Тип вопроса"),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_("Порядок"))

    class Meta:
        verbose_name = _("Вопрос анкеты")
        verbose_name_plural = _("Вопросы анкеты")
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.survey.title}: {self.text[:50]}"


class SurveyOption(models.Model):
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name=_("Вопрос"),
    )
    text = models.CharField(max_length=500, verbose_name=_("Текст варианта"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Порядок"))

    class Meta:
        verbose_name = _("Вариант ответа")
        verbose_name_plural = _("Варианты ответов")
        ordering = ("order", "id")

    def __str__(self):
        return self.text[:80]


class SurveySubmission(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="survey_submissions",
        verbose_name=_("Студент"),
    )
    survey = models.ForeignKey(
        Survey,
        on_delete=models.PROTECT,
        related_name="submissions",
        verbose_name=_("Анкета"),
    )
    edu_year = models.ForeignKey(
        "stepper.EduYear",
        on_delete=models.PROTECT,
        related_name="survey_submissions",
        verbose_name=_("Учебный год"),
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата прохождения"))
    student_fio = models.CharField(max_length=255, verbose_name=_("ФИО"))
    student_login = models.CharField(max_length=150, verbose_name=_("Логин"))
    student_group = models.CharField(max_length=255, blank=True, verbose_name=_("Группа"))

    class Meta:
        verbose_name = _("Прохождение анкеты")
        verbose_name_plural = _("Прохождения анкет")
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "survey", "edu_year"],
                name="unique_survey_submission_per_year",
            ),
        ]

    def __str__(self):
        return f"{self.student_fio} — {self.survey.title} ({self.edu_year})"


class SurveyAnswerItem(models.Model):
    submission = models.ForeignKey(
        SurveySubmission,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name=_("Прохождение"),
    )
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.PROTECT,
        related_name="answer_items",
        verbose_name=_("Вопрос"),
    )
    option = models.ForeignKey(
        SurveyOption,
        on_delete=models.PROTECT,
        related_name="answer_items",
        verbose_name=_("Вариант ответа"),
    )

    class Meta:
        verbose_name = _("Ответ")
        verbose_name_plural = _("Ответы")
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question", "option"],
                name="unique_survey_answer_option",
            ),
        ]

    def __str__(self):
        return f"{self.question_id}: {self.option.text[:40]}"
