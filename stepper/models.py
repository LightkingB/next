from datetime import datetime

from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from bsadmin.models import CustomUser, Role, Faculty, Speciality
from stepper.choices import CategoriesChoices, TypeChoices, StatusChoices
from utils.validator import delete_file, validate_file_size


class EduYear(models.Model):
    """Учебный год """
    title = models.CharField(max_length=100, verbose_name="Название")
    active = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Учебный год")
        verbose_name_plural = _("Учебные года")

    def __str__(self):
        return self.title


class Stage(models.Model):
    """Этап обходного листа, который студент должен пройти."""

    name = models.CharField(max_length=100, unique=True, verbose_name=_("Название этапа"),
                            help_text=_("Название этапа."))
    is_mandatory = models.BooleanField(default=False, verbose_name=_("Обязательный этап"),
                                       help_text=_("Является ли этап обязательным."))

    class Meta:
        verbose_name = _("Этап")
        verbose_name_plural = _("Этапы")

    def __str__(self):
        return f"{self.name}"


class TemplateStep(models.Model):
    """Шаблонные шаги обходного листа."""

    STUDENT = CategoriesChoices.STUDENT
    TEACHER = CategoriesChoices.TEACHER
    WORKER = CategoriesChoices.WORKER

    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, verbose_name=_("Этап"),
                              help_text=_("Этап, который проходит студент."))
    category = models.CharField(max_length=20, choices=CategoriesChoices.choices, default=STUDENT,
                                verbose_name=_("Категория"),
                                help_text=_("Категория сотрдников ОшГУ"))
    order = models.PositiveIntegerField(verbose_name=_("Порядок"), help_text=_("Порядок прохождения этапа."))
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Роль")

    class Meta:
        verbose_name = _("Шаблон")
        verbose_name_plural = _("Шаблоны")

    def __str__(self):
        return f"{self.stage}"


class StageEmployee(models.Model):
    """Связь между сотрудником и этапом обходного листа."""

    template_stage = models.ForeignKey(TemplateStep, on_delete=models.CASCADE, verbose_name=_("Этап"),
                                       help_text=_("Этап, который проходит студент."))
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='stage_employees',
                                 verbose_name=_("Сотрудник"), help_text=_("Сотрудник, который работает с этапом."))
    assigned_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата назначения"),
                                         help_text=_("Дата назначения сотрудника на этап."))
    is_active = models.BooleanField(default=True, verbose_name=_("Активен ли сотрудник на этом этапе"),
                                    help_text=_("Отметка о том, активен ли сотрудник на данном этапе."))

    class Meta:
        verbose_name = _("Связь сотрудника с этапом")
        verbose_name_plural = _("Связи сотрудников с этапами")
        unique_together = ('template_stage', 'employee')

    def __str__(self):
        return f"{self.employee} - {self.template_stage}"


class ClearanceSheet(models.Model):
    """Обходной лист, который студент получает для прохождения этапов."""

    STUDENT = CategoriesChoices.STUDENT
    TEACHER = CategoriesChoices.TEACHER
    WORKER = CategoriesChoices.WORKER

    SPEC = TypeChoices.SPEC
    OTHER = TypeChoices.OTHER

    myedu_id = models.CharField(max_length=255, verbose_name=_("Студент"),
                                help_text=_("Студент, которому принадлежит обходной лист."))
    student_fio = models.CharField(max_length=255, verbose_name=_("ФИО"), null=True, blank=True)
    myedu_faculty_id = models.PositiveIntegerField(verbose_name=_("Факультет ID"), null=True, blank=True)
    myedu_faculty = models.CharField(max_length=255, verbose_name=_("Факультет"), null=True, blank=True)
    myedu_spec_id = models.PositiveIntegerField(verbose_name=_("Специальность ID"), null=True, blank=True)
    myedu_spec = models.CharField(max_length=255, verbose_name=_("Специальность"), null=True, blank=True)
    category = models.CharField(max_length=20, choices=CategoriesChoices.choices, default=STUDENT,
                                verbose_name=_("Категория"),
                                help_text=_("Категория сотрдников ОшГУ"))
    issued_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата выдачи"),
                                     help_text=_("Дата выдачи обходного листа."))
    order_date = models.CharField(max_length=255, verbose_name=_("Дата приказа"), null=True, blank=True)
    order = models.CharField(max_length=255, verbose_name=_("Приказ"), null=True, blank=True)
    order_status = models.CharField(max_length=255, verbose_name=_("Статус"), null=True, blank=True)
    type_choices = models.CharField(max_length=50, verbose_name=_("Выберите тип"), choices=TypeChoices.choices,
                                    null=True,
                                    blank=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата завершения"),
                                        help_text=_("Дата завершения обходного листа."))
    last_active = models.BooleanField(default=True, verbose_name=_("Последний активный обходной"))

    def update_completed_at(self):
        has_null_trajectories = self.trajectory_set.filter(completed_at__isnull=True)
        if not has_null_trajectories:
            self.completed_at = datetime.now()
            self.save(update_fields=['completed_at'])

    class Meta:
        verbose_name = _("Обходной лист")
        verbose_name_plural = _("Обходные листы")

    def __str__(self):
        return f"{self.student_fio} - {self.myedu_id}"


class Trajectory(models.Model):
    """Траектория прохождения студента, назначенная старшим оператором."""

    clearance_sheet = models.ForeignKey(ClearanceSheet, on_delete=models.PROTECT, verbose_name=_("Обходной лист"),
                                        help_text=_("Обходной лист, к которому относится траектория."))
    template_stage = models.ForeignKey(TemplateStep, on_delete=models.CASCADE, verbose_name=_("Этап"),
                                       help_text=_("Этап, который проходит студент."))
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата назначения"),
                                       help_text=_("Дата назначения этапа."))
    update_at = models.DateTimeField(verbose_name=_("Дата обновления"), default=now,
                                     help_text=_("Дата обновления этого статуса."), null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата завершения"),
                                        help_text=_("Дата завершения этапа."))
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT,
                                    related_name='assigned_trajectories',
                                    verbose_name=_("Назначил"), help_text=_("Кто назначил этап."))

    class Meta:
        verbose_name = _("Траектория")
        verbose_name_plural = _("Траектории")

    def __str__(self):
        return f"{self.clearance_sheet.student_fio} - {self.template_stage} - {self.completed_at}"


class StageStatus(models.Model):
    """Статус обработки конкретного этапа студента с возможностью добавления комментариев."""

    trajectory = models.ForeignKey(Trajectory, on_delete=models.PROTECT, verbose_name=_("Траектория"),
                                   help_text=_("Связь с траекторией студента."))
    processed_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, verbose_name=_("Обработал"),
                                     help_text=_("Сотрудник, который обрабатывает этап."))
    comment_text = models.TextField(verbose_name=_("Комментарий"), help_text=_("Комментарий для этого этапа."))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"),
                                      help_text=_("Дата добавления этого статуса."))

    class Meta:
        verbose_name = _("Статус этапа с комментарием")
        verbose_name_plural = _("Статусы этапов с комментариями")

    def __str__(self):
        return f"{self.trajectory}"


class Issuance(models.Model):
    """Выдача обходного листа."""

    RECEIVED = StatusChoices.RECEIVED
    DOUBLE = StatusChoices.DOUBLE

    SPEC = TypeChoices.SPEC
    OTHER = TypeChoices.OTHER

    student = models.CharField(max_length=255, verbose_name=_("Студент"),
                               help_text=_("Студент, которому принадлежит обходной лист."))
    cs = models.ForeignKey(ClearanceSheet, on_delete=models.SET_NULL, verbose_name=_("Обходной лист"), null=True,
                           blank=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, verbose_name="Факультет студента", null=True,
                                blank=True)
    speciality = models.ForeignKey(Speciality, on_delete=models.PROTECT, verbose_name="Специальность студента",
                                   null=True,
                                   blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"),
                                      help_text=_("Дата создания обходного листа"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата создания"),
                                      help_text=_("Дата обновления обходного листа"))
    date_issue = models.DateField(verbose_name=_("Дата выдачи"), help_text=_("Дата выдачи обходного листа"), null=True,
                                  blank=True)
    employee = models.ForeignKey(CustomUser, on_delete=models.PROTECT, verbose_name=_("Обработал"),
                                 help_text=_("Сотрудник, который обрабатывает этап."))
    doc_number = models.CharField(max_length=255, verbose_name=_("Дипломный номер"))
    reg_number = models.CharField(max_length=255, verbose_name=_("Регистрационный номер"), null=True, blank=True)
    files = models.FileField(upload_to="document/files/", verbose_name="Диплом", blank=True, null=True,
                             validators=[
                                 FileExtensionValidator(allowed_extensions=['pdf']),
                                 validate_file_size,
                             ])
    fio = models.CharField(max_length=150, verbose_name=_("ФИО"), null=True, blank=True)
    phone = models.CharField(max_length=20, verbose_name=_("Телефон"), null=True, blank=True)
    inn = models.CharField(verbose_name=_("ИНН"), max_length=100, blank=True, null=True)
    signature = models.ImageField(upload_to="document/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=StatusChoices.choices, verbose_name=_("Получил"), default=RECEIVED)
    type_choices = models.CharField(max_length=50, verbose_name=_("Выберите тип"), choices=TypeChoices.choices,
                                    default=OTHER)
    note = models.TextField(verbose_name="Заметка", null=True, blank=True)

    class Meta:
        verbose_name = _("Выдача обходного листа")
        verbose_name_plural = _("Выдача обходных листов")

    def __str__(self):
        return self.student


class IssuanceHistory(models.Model):
    """История выдачи обходного листа."""

    SPEC = TypeChoices.SPEC
    OTHER = TypeChoices.OTHER

    student = models.CharField(max_length=255, verbose_name=_("Студент"),
                               help_text=_("Студент, которому принадлежит обходной лист."))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"),
                                      help_text=_("Дата создания обходного листа"))
    cs = models.PositiveIntegerField(verbose_name=_("Обходной лист"), default=0)
    history = models.CharField(max_length=255, verbose_name=_("Причина"))
    type_choices = models.CharField(max_length=50, verbose_name=_("Выберите тип"), choices=TypeChoices.choices,
                                    default=OTHER)

    class Meta:
        verbose_name = _("История выдачи обходного листа")
        verbose_name_plural = _("История выдачи обходных листов")

    def __str__(self):
        return f"{self.student} - {self.history}"


class Diploma(models.Model):
    """ Диплом """

    class Meta:
        verbose_name = _("Диплом")
        verbose_name_plural = _("Дипломы")

    student = models.CharField(max_length=255, verbose_name=_("Студент"),
                               help_text=_("Студент, которому принадлежит диплом."))
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, verbose_name="Факультет студента", null=True,
                                blank=True)
    speciality = models.ForeignKey(Speciality, on_delete=models.PROTECT, verbose_name="Специальность студента",
                                   null=True,
                                   blank=True)
    doc_number = models.CharField(max_length=255, verbose_name=_("Дипломный номер"))
    reg_number = models.CharField(max_length=255, verbose_name=_("Регистрационный номер"), null=True, blank=True)
    gak_date = models.DateField(verbose_name=_("Дата ГАК"), null=True, blank=True)
    date_issue = models.DateField(verbose_name=_("Дата выдачи"), help_text=_("Дата выдачи обходного листа"), null=True,
                                  blank=True)
    sync = models.BooleanField(default=False, verbose_name=_("Синхронизировался"))
    edu_year = models.ForeignKey(EduYear, on_delete=models.PROTECT, verbose_name=_("Учебный год"))

    def __str__(self):
        return f"{self.student} - {self.doc_number}"


@receiver(post_delete, sender=Issuance)
def delete_issuance_file(sender, instance, *args, **kwargs):
    if instance.files:
        delete_file(instance.files.path)
    if instance.signature:
        delete_file(instance.signature.path)
