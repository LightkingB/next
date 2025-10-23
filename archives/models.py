from django.core.validators import FileExtensionValidator
from django.db import models

from bsadmin.models import Faculty, CustomUser
from stepper.models import EduYear
from utils.validator import validate_file_size


class CategoryForm(models.Model):
    class Meta:
        verbose_name = 'Форма категория'
        verbose_name_plural = 'Форма категории'

    title = models.CharField(max_length=100, verbose_name="Название")
    slug = models.CharField(max_length=50, verbose_name="Слаг")

    def __str__(self):
        return self.title


class EduForm(models.Model):
    class Meta:
        verbose_name = 'Форма обучения'
        verbose_name_plural = 'Форма обучения'

    title = models.CharField(max_length=100, verbose_name="Название")
    template_text = models.TextField(verbose_name="Шаблон текста", null=True, blank=True)

    def __str__(self):
        return self.title


class DocumentCategory(models.Model):
    class Meta:
        verbose_name = 'Категория документа'
        verbose_name_plural = 'Категории документа'

    title = models.CharField(max_length=100, verbose_name="Название")

    def __str__(self):
        return self.title


class Acts(models.Model):
    class Meta:
        verbose_name = 'Акт'
        verbose_name_plural = 'Акты'

    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, verbose_name="Факультет")
    notes = models.TextField(verbose_name="Примечание", null=True, blank=True)
    edu_form = models.ForeignKey(EduForm, on_delete=models.PROTECT, verbose_name="Форма обучения")
    edu_year = models.ForeignKey(EduYear, on_delete=models.SET_NULL, verbose_name="Учебный год", null=True, blank=True)
    category_form = models.ForeignKey(CategoryForm, on_delete=models.SET_NULL, verbose_name="Форма категории",
                                      null=True, blank=True)
    is_confirm = models.BooleanField(default=False, verbose_name="Подтверждение")
    confirm_date = models.DateField(verbose_name="Дата подтверждения", null=True, blank=True)
    confirm_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Архив",
                                     related_name="archive_user")
    created_user = models.ForeignKey(CustomUser, on_delete=models.PROTECT,
                                     verbose_name="Отдел кадров",
                                     related_name="ok_user")
    created_date = models.DateField(auto_now_add=True, verbose_name="Дата создания")
    updated_date = models.DateField(auto_now=True, verbose_name="Дата обновления")
    bundle_number = models.CharField(max_length=255, verbose_name="Номер связки", null=True, blank=True)
    rack = models.CharField(max_length=255, verbose_name="Стеллаж", null=True, blank=True)

    def __str__(self):
        return f'{self.created_user.first_name} {self.created_user.last_name} - {self.id}'


class StudentsAct(models.Model):
    class Meta:
        verbose_name = 'Акт студентов'
        verbose_name_plural = 'Акты студентов'

    act = models.ForeignKey(Acts, on_delete=models.PROTECT, verbose_name="Акт")
    myedu_id = models.CharField(max_length=255, verbose_name="Студент номер из MyEDU",
                                help_text="Студент, которому принадлежит обходной лист.", null=True, blank=True)
    order_date = models.CharField(max_length=255, verbose_name="Дата приказа", null=True, blank=True)
    order = models.CharField(max_length=255, verbose_name="Приказ", null=True, blank=True)
    order_status = models.CharField(max_length=255, verbose_name="Статус", null=True, blank=True)
    student_fio = models.CharField(max_length=255, verbose_name="ФИО", null=True, blank=True)
    status = models.BooleanField(default=False, verbose_name="Статус возвращения")
    return_date = models.DateField(verbose_name="Дата возвращения", null=True, blank=True)
    created_date = models.DateField(auto_now_add=True, verbose_name="Дата создания")
    updated_date = models.DateField(auto_now=True, verbose_name="Дата обновления")
    doc_number = models.CharField(verbose_name="Примечание", max_length=255, null=True, blank=True)
    info = models.TextField(verbose_name="Примечание", null=True, blank=True)

    def __str__(self):
        if self.student_fio:
            return f'{self.myedu_id} {self.student_fio}'
        return f'{self.myedu_id}'


class StudentDocuments(models.Model):
    class Meta:
        verbose_name = 'Документ студента'
        verbose_name_plural = 'Документы студента'

    student_act = models.ForeignKey(StudentsAct, on_delete=models.PROTECT, verbose_name="Акт студента")
    doc_category = models.ForeignKey(DocumentCategory, on_delete=models.PROTECT, verbose_name="Категория документа")
    status = models.BooleanField(default=False, verbose_name="Статус возвращения")
    return_date = models.DateField(verbose_name="Дата возвращения", null=True, blank=True)
    created_date = models.DateField(auto_now_add=True, verbose_name="Дата создания")
    updated_date = models.DateField(auto_now=True, verbose_name="Дата обновления")
    doc_number = models.CharField(verbose_name="Примечание", max_length=255, null=True, blank=True)
    info = models.TextField(verbose_name="Примечание", null=True, blank=True)

    def __str__(self):
        return f'{self.student_act} - {self.doc_category} : {self.status}'


class StudentDocFiles(models.Model):
    class Meta:
        verbose_name = 'Загружаемый документ'
        verbose_name_plural = 'Загруженные документы'

    student_document = models.ForeignKey(StudentDocuments, on_delete=models.PROTECT, verbose_name="Документ студента")
    files = models.FileField(upload_to="transcripts/fails/", verbose_name="Документ",
                             validators=[
                                 FileExtensionValidator(allowed_extensions=['pdf']),
                                 validate_file_size,
                             ])
