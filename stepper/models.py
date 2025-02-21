# from django.db import models
#
# from bsadmin.models import CustomUser
#
#
# class Step(models.Model):
#     class Meta:
#         verbose_name = 'Шаг'
#         verbose_name_plural = 'Шаги'
#
#     name = models.CharField(max_length=255, unique=True)
#
#     def __str__(self):
#         return self.name
#
#
# class PassSheetTemplate(models.Model):
#     class Meta:
#         verbose_name = 'Шаблон'
#         verbose_name_plural = 'Шаблоны'
#
#     name = models.CharField(max_length=255)
#     created_at = models.DateTimeField(auto_now_add=True)
#     is_active = models.BooleanField(default=False)
#
#     def __str__(self):
#         return self.name
#
#
# class PassSheetTemplateStep(models.Model):
#     class Meta:
#         verbose_name = 'Регистрация шагов на шаблон'
#         verbose_name_plural = 'Регистрация шагов на шаблоны'
#         unique_together = ('template', 'step')
#         ordering = ['order']
#
#     template = models.ForeignKey(PassSheetTemplate, on_delete=models.CASCADE)
#     step = models.ForeignKey(Step, on_delete=models.CASCADE)
#     order = models.PositiveIntegerField()
#
#     def __str__(self):
#         return self.template.name
#
#
# class PassSheet(models.Model):
#     class Meta:
#         verbose_name = 'Обходной лист'
#         verbose_name_plural = 'Обходные листы'
#
#     student = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
#     template = models.ForeignKey(PassSheetTemplate, on_delete=models.CASCADE)
#     current_step = models.ForeignKey(Step, on_delete=models.SET_NULL, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return self.student.first_name
#
#
# class PassSheetStep(models.Model):
#     class Meta:
#         unique_together = ('pass_sheet', 'step')
#         ordering = ['step__id']
#         verbose_name = 'Шаг обходного листа'
#         verbose_name_plural = 'Шаги обходного листа'
#
#     STATUS_CHOICES = [
#         ('pending', 'Ожидание'),
#         ('completed', 'Пройден'),
#         ('rejected', 'Отказано'),
#     ]
#
#     pass_sheet = models.ForeignKey(PassSheet, on_delete=models.CASCADE)
#     step = models.ForeignKey(Step, on_delete=models.CASCADE)
#     status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
#     remarks = models.TextField(blank=True, null=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return self.employee.first_name
#
#
# class PassSheetEmployee(models.Model):
#     class Meta:
#         verbose_name = 'Сотрудник обходного листа'
#         verbose_name_plural = 'Сотрудники обходного листа'
#
#     user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
#     step = models.ForeignKey(Step, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return self.user.first_name
