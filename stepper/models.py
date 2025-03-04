# from django.db import models
# from django.utils.translation import gettext_lazy as _
#
# from bsadmin.models import CustomUser
#
#
# class Stage(models.Model):
#     """Этап обходного листа, который студент должен пройти."""
#     name = models.CharField(max_length=100, unique=True, verbose_name=_("Название этапа"),
#                             help_text=_("Название этапа."))
#     is_mandatory = models.BooleanField(default=False, verbose_name=_("Обязательный этап"),
#                                        help_text=_("Является ли этап обязательным."))
#     order = models.PositiveIntegerField(verbose_name=_("Порядок"), help_text=_("Порядок прохождения этапа."))
#     employees = models.ManyToManyField(CustomUser, related_name="stages", blank=True, verbose_name=_("Сотрудники"),
#                                        help_text=_("Сотрудники, которые могут работать с этим этапом."))
#
#     class Meta:
#         verbose_name = _("Этап")
#         verbose_name_plural = _("Этапы")
#
#     def __str__(self):
#         return self.name
#
#
# class ClearanceSheet(models.Model):
#     """Обходной лист, который студент получает для прохождения этапов."""
#     student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("Студент"),
#                                 help_text=_("Студент, которому принадлежит обходной лист."))
#     issued_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата выдачи"),
#                                      help_text=_("Дата выдачи обходного листа."))
#     completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата завершения"),
#                                         help_text=_("Дата завершения обходного листа."))
#     current_stage = models.ForeignKey(Stage, null=True, blank=True, on_delete=models.SET_NULL,
#                                       related_name='current_clearance_sheet', verbose_name=_("Текущий этап"),
#                                       help_text=_("Этап, на котором сейчас находится студент."))
#
#     class Meta:
#         verbose_name = _("Обходной лист")
#         verbose_name_plural = _("Обходные листы")
#
#     def __str__(self):
#         return f"{self.student.last_name}"
#
#
# class Trajectory(models.Model):
#     """Траектория прохождения студента, назначенная старшим оператором."""
#     clearance_sheet = models.ForeignKey(ClearanceSheet, on_delete=models.CASCADE, verbose_name=_("Обходной лист"),
#                                         help_text=_("Обходной лист, к которому относится траектория."))
#     stage = models.ForeignKey(Stage, on_delete=models.CASCADE, verbose_name=_("Этап"),
#                               help_text=_("Этап, который проходит студент."))
#     assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата назначения"),
#                                        help_text=_("Дата назначения этапа."))
#     completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата завершения"),
#                                         help_text=_("Дата завершения этапа."))
#     assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True,
#                                     related_name='assigned_trajectories',
#                                     verbose_name=_("Назначил"), help_text=_("Кто назначил этап."))
#
#     class Meta:
#         verbose_name = _("Траектория")
#         verbose_name_plural = _("Траектории")
#
#     def __str__(self):
#         return f"{self.clearance_sheet.student.last_name} - {self.stage.name}"
#
#
# class StageStatus(models.Model):
#     """Статус обработки конкретного этапа студента с возможностью добавления комментариев."""
#     trajectory = models.ForeignKey(Trajectory, on_delete=models.CASCADE, verbose_name=_("Траектория"),
#                                    help_text=_("Связь с траекторией студента."))
#     processed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, verbose_name=_("Обработал"),
#                                      help_text=_("Сотрудник, который обрабатывает этап."))
#     status = models.CharField(max_length=20, choices=[
#         ('pending', _('В ожидании')),
#         ('in_progress', _('В работе')),
#         ('completed', _('Завершено')),
#         ('deferred', _('Отложено')),
#     ], default='pending', verbose_name=_("Статус"), help_text=_("Текущий статус обработки этапа."))
#     updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"),
#                                       help_text=_("Дата последнего обновления статуса."))
#     comment_text = models.TextField(null=True, blank=True, verbose_name=_("Комментарий"),
#                                     help_text=_("Комментарий для этого этапа."))
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"),
#                                       help_text=_("Дата добавления этого статуса."))
#
#     class Meta:
#         verbose_name = _("Статус этапа с комментарием")
#         verbose_name_plural = _("Статусы этапов с комментариями")
#
#     def __str__(self):
#         return f"{self.trajectory} - {self.status}"
#
#
# class CommentHistory(models.Model):
#     """История изменений комментариев."""
#     stage_status = models.ForeignKey(StageStatus, related_name="history", on_delete=models.CASCADE,
#                                      verbose_name=_("Статус обработки конкретного этапа студента"),
#                                      help_text=_("Связь с комментариями, к которым относится история изменений."))
#     text = models.TextField(verbose_name=_("Текст комментария"), help_text=_("Текст комментария в момент изменения."))
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("Автор"),
#                              help_text=_("Автор комментария."))
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"),
#                                       help_text=_("Дата добавления старой версии комментария."))
#
#     class Meta:
#         verbose_name = _("История комментариев")
#         verbose_name_plural = _("Истории комментариев")
#
#     def __str__(self):
#         return f"История для комментария от {self.user} на {self.created_at}"
