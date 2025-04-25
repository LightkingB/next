# employee_stage = employee.stage
# mandatory_stages = Stage.objects.filter(is_mandatory=True)
#
# subquery = Trajectory.objects.filter(
#     clearance_sheet=OuterRef("trajectory__clearance_sheet"),
#     stage__in=mandatory_stages,
#     stage__order__lt=OuterRef("trajectory__stage__order"),
#     completed_at__isnull=True
# ).values("id")[:1]
#
# students_with_stlib = (
#     ClearanceSheet.objects.filter(
#         trajectory__stage=employee_stage,
#         trajectory__completed_at__isnull=True,
#         completed_at__isnull=True
#     )
#     .annotate(
#         has_unfinished_previous_stage=Exists(subquery),
#         current_trajectory_id=F("trajectory__id"),
#         status=F("trajectory__completed_at")
#     )
#     .filter(
#         has_unfinished_previous_stage=False
#     )
#     .order_by('-trajectory__update_at')
#     .distinct()
# )


# from datetime import datetime
#
# from django.core.validators import FileExtensionValidator
# from django.db import models
# from django.db.models.signals import post_delete
# from django.dispatch import receiver
# from django.utils.timezone import now
# from django.utils.translation import gettext_lazy as _
#
# from bsadmin.models import CustomUser
# from utils.validator import delete_file, validate_file_size
#
#
# class Stage(models.Model):
#     """Этап обходного листа, который студент должен пройти."""
#
#     STUDENT = "student"
#     TEACHER = "teacher"
#     WORKER = "worker"
#
#     CATEGORIES = (
#         (STUDENT, "Студент"),
#         (TEACHER, "Преподаватель"),
#         (WORKER, "Работник")
#     )
#
#     name = models.CharField(max_length=100, unique=True, verbose_name=_("Название этапа"),
#                             help_text=_("Название этапа."))
#     is_mandatory = models.BooleanField(default=False, verbose_name=_("Обязательный этап"),
#                                        help_text=_("Является ли этап обязательным."))
#     category = models.CharField(max_length=20, choices=CATEGORIES, default=STUDENT, verbose_name=_("Категория"),
#                                 help_text=_("Категория сотрдников ОшГУ"))
#     order = models.PositiveIntegerField(verbose_name=_("Порядок"), help_text=_("Порядок прохождения этапа."))
#
#     class Meta:
#         verbose_name = _("Этап")
#         verbose_name_plural = _("Этапы")
#
#     def __str__(self):
#         return f"{self.name} - {self.get_category_display()}"
#
#
# class StageEmployee(models.Model):
#     """Связь между сотрудником и этапом обходного листа."""
#     stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name='stage_employees',
#                               verbose_name=_("Этап"), help_text=_("Этап, с которым связан сотрудник."))
#     employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='stage_employees',
#                                  verbose_name=_("Сотрудник"), help_text=_("Сотрудник, который работает с этапом."))
#     assigned_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата назначения"),
#                                          help_text=_("Дата назначения сотрудника на этап."))
#     is_active = models.BooleanField(default=True, verbose_name=_("Активен ли сотрудник на этом этапе"),
#                                     help_text=_("Отметка о том, активен ли сотрудник на данном этапе."))
#
#     class Meta:
#         verbose_name = _("Связь сотрудника с этапом")
#         verbose_name_plural = _("Связи сотрудников с этапами")
#         unique_together = ('stage', 'employee')
#
#     def __str__(self):
#         return f"{self.employee} - {self.stage}"
#
#
# class ClearanceSheet(models.Model):
#     """Обходной лист, который студент получает для прохождения этапов."""
#     myedu_id = models.PositiveIntegerField(verbose_name=_("Студент"),
#                                            help_text=_("Студент, которому принадлежит обходной лист."))
#     student_fio = models.CharField(max_length=255, verbose_name=_("ФИО"), null=True, blank=True)
#     duty = models.TextField(verbose_name=_("Долги"), null=True, blank=True)
#     myedu_faculty = models.CharField(max_length=255, verbose_name=_("Факультет"), null=True, blank=True)
#     myedu_spec = models.CharField(max_length=255, verbose_name=_("Специальность"), null=True, blank=True)
#     issued_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата выдачи"),
#                                      help_text=_("Дата выдачи обходного листа."))
#     completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата завершения"),
#                                         help_text=_("Дата завершения обходного листа."))
#
#     def update_completed_at(self):
#         has_null_trajectories = self.trajectory_set.filter(completed_at__isnull=True)
#         if not has_null_trajectories:
#             self.completed_at = datetime.now()
#             self.save(update_fields=['completed_at'])
#
#     class Meta:
#         verbose_name = _("Обходной лист")
#         verbose_name_plural = _("Обходные листы")
#
#     def __str__(self):
#         return f"{self.student_fio} - {self.myedu_id}"
#
# class Trajectory(models.Model):
#     """Траектория прохождения студента, назначенная старшим оператором."""
#     clearance_sheet = models.ForeignKey(ClearanceSheet, on_delete=models.PROTECT, verbose_name=_("Обходной лист"),
#                                         help_text=_("Обходной лист, к которому относится траектория."))
#     stage = models.ForeignKey(Stage, on_delete=models.CASCADE, verbose_name=_("Этап"),
#                               help_text=_("Этап, который проходит студент."))
#     assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата назначения"),
#                                        help_text=_("Дата назначения этапа."))
#     update_at = models.DateTimeField(verbose_name=_("Дата обновления"), default=now,
#                                      help_text=_("Дата обновления этого статуса."), null=True, blank=True)
#     completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Дата завершения"),
#                                         help_text=_("Дата завершения этапа."))
#     assigned_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT,
#                                     related_name='assigned_trajectories',
#                                     verbose_name=_("Назначил"), help_text=_("Кто назначил этап."))
#
#     class Meta:
#         verbose_name = _("Траектория")
#         verbose_name_plural = _("Траектории")
#
#     def __str__(self):
#         return f"{self.clearance_sheet.student_fio} - {self.stage.name} - {self.completed_at}"
#
#
# class StageStatus(models.Model):
#     """Статус обработки конкретного этапа студента с возможностью добавления комментариев."""
#     trajectory = models.ForeignKey(Trajectory, on_delete=models.PROTECT, verbose_name=_("Траектория"),
#                                    help_text=_("Связь с траекторией студента."))
#     processed_by = models.ForeignKey(CustomUser, on_delete=models.PROTECT, verbose_name=_("Обработал"),
#                                      help_text=_("Сотрудник, который обрабатывает этап."))
#     comment_text = models.TextField(verbose_name=_("Комментарий"), help_text=_("Комментарий для этого этапа."))
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"),
#                                       help_text=_("Дата добавления этого статуса."))
#
#     class Meta:
#         verbose_name = _("Статус этапа с комментарием")
#         verbose_name_plural = _("Статусы этапов с комментариями")
#
#     def __str__(self):
#         return f"{self.trajectory}"
#
#
# class Issuance(models.Model):
#     """Выдача обходного листа."""
#     student = models.PositiveIntegerField(verbose_name=_("Студент"),
#                                           help_text=_("Студент, которому принадлежит обходной лист."))
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"),
#                                       help_text=_("Дата создания обходного листа"))
#     date_issue = models.DateField(verbose_name=_("Дата выдачи"), help_text=_("Дата выдачи обходного листа"))
#     employee = models.ForeignKey(CustomUser, on_delete=models.PROTECT, verbose_name=_("Обработал"),
#                                  help_text=_("Сотрудник, который обрабатывает этап."))
#     doc_number = models.CharField(max_length=255, verbose_name=_("Дипломный номер"))
#     reg_number = models.CharField(max_length=255, verbose_name=_("Регистрационный номер"), null=True, blank=True)
#     files = models.FileField(upload_to="document/files/", verbose_name="Документ", blank=True, null=True,
#                              validators=[
#                                  FileExtensionValidator(allowed_extensions=['pdf']),
#                                  validate_file_size,
#                              ])
#     fio = models.CharField(max_length=150, verbose_name=_("ФИО"), null=True, blank=True)
#     phone = models.CharField(max_length=20, verbose_name=_("Телефон"), null=True, blank=True)
#     inn = models.CharField(verbose_name=_("ИНН"), max_length=100, blank=True, null=True)
#     signature = models.ImageField(upload_to="document/", null=True, blank=True)
#
#     class Meta:
#         verbose_name = _("Выдача обходного листа")
#         verbose_name_plural = _("Выдача обходных листов")
#
#     def __str__(self):
#         return f"{self.student}"
#
#
# @receiver(post_delete, sender=Issuance)
# def delete_issuance_file(sender, instance, *args, **kwargs):
#     if instance.files:
#         delete_file(instance.files.path)
#     if instance.signature:
#         delete_file(instance.signature.path)


# import json
# from datetime import datetime
#
# import requests
# from django.contrib import messages
# from django.db import transaction, IntegrityError
# from django.db.models import OuterRef, Exists, F, Window, Q, Prefetch
# from django.db.models.functions import RowNumber
# from django.http import HttpResponse, JsonResponse
# from django.shortcuts import render, redirect, get_object_or_404
# from django.utils.timezone import make_aware
# from django.views.decorators.csrf import csrf_exempt
#
# from bsadmin.consts import STADMIN, API_URL, MYEDU_LOGIN, MYEDU_PASSWORD
# from bsadmin.models import Faculty, Speciality
# from stepper.forms import TrajectoryForm, StageStatusForm, IssuanceForm
# from stepper.models import ClearanceSheet, Trajectory, StageStatus, Stage, StageEmployee
# from utils.convert import save_signature_image
# from utils.filter_pagination import Pagination
#
#
# def route(request):
#     if not request.user.is_authenticated:
#         return redirect("integrator:next-teacher-login")
#     roles = set(request.user.roles.values_list("name", flat=True))
#     if STADMIN in roles:
#         return redirect("stepper:index")
#     return HttpResponse("403 - Forbidden")
#
#
# def get_students_from_api(debt, search=None, faculty_id=0, specialty_id=0):
#     data = {
#         "login": MYEDU_LOGIN,
#         "password": MYEDU_PASSWORD,
#         "debt": debt,
#         "faculty_id": faculty_id,
#         "speciality_id": specialty_id
#     }
#     if search:
#         data["search"] = search
#
#     try:
#         response = requests.post(f"{API_URL}/obhadnoi/searchstudent/debt", data=data)
#
#         if response.status_code == 200:
#             return response.json()
#         return None
#     except requests.RequestException:
#         return None
#
#
# def base_students_view(request, template_name, navbar, debt, page_title):
#     if not request.user.is_authenticated:
#         return redirect("integrator:next-teacher-login")
#
#     if request.method == "POST":
#         search = request.POST.get("search", "")
#         faculty_id = request.POST.get("faculty_id", 0)
#         specialty_id = request.POST.get("specialty_id", 0)
#         students = get_students_from_api(debt, search, faculty_id, specialty_id)
#     else:
#         students = get_students_from_api(debt)
#
#     paginator = Pagination(request, students or [])
#     page_number = request.GET.get('page', 1)
#     students = paginator.pagination_with_filters_without_qs(page_number)
#
#     faculties = Faculty.objects.filter(visit=True).order_by("title")
#
#     context = {
#         "title": page_title,
#         "navbar": navbar,
#         "students": students,
#         "faculties": faculties
#     }
#
#     if navbar == "stepper":
#         request.session['access'] = 'stepper'
#         context["success"] = True
#
#     return render(request, template_name, context)
#
#
# def cs_index(request):
#     return base_students_view(
#         request=request,
#         template_name="teachers/steppers/index.html",
#         navbar="stepper",
#         debt=1,
#         page_title="Студенты с задолженностью по данным MyEDU"
#     )
#
#
# def spec(request):
#     request.session['access'] = 'stepper'
#     return base_students_view(
#         request=request,
#         template_name="teachers/steppers/spec.html",
#         navbar="spec",
#         debt=0,
#         page_title="Студенты без задолженности по данным MyEDU"
#     )
#
#
# def load_specialities(request):
#     myedu_faculty_id = request.GET.get('faculty_id')
#     faculty = Faculty.objects.filter(myedu_faculty_id=myedu_faculty_id).first()
#     specialities = Speciality.objects.filter(faculty_id=faculty.id, visit=True).values('myedu_spec_id', 'title')
#     return JsonResponse(list(specialities), safe=False)
#
#
# def spec_part(request, myeduid):
#     not_cs_finished = ClearanceSheet.objects.filter(
#         myedu_id=myeduid, completed_at__isnull=True
#     ).exists()
#
#     form = IssuanceForm(request.POST or None, request.FILES or None)
#
#     if request.method == "POST":
#         if form.is_valid():
#             signature_base64 = request.POST.get('signature')
#             if not signature_base64:
#                 messages.error(request, "Снимите студента на камеру")
#             else:
#                 instance = form.save(commit=False)
#                 instance.student = myeduid
#                 signature_file = save_signature_image(signature_base64)
#                 if signature_file:
#                     instance.signature = signature_file
#
#                 instance.employee = request.user
#                 instance.save()
#         else:
#             messages.error(request, "Введите корректные данные")
#
#     student = next(iter(get_students_from_api(debt=0, search=myeduid)), None)
#
#     context = {
#         "navbar": "spec",
#         "not_cs_finished": not_cs_finished,
#         "form": form,
#         "student": student
#     }
#     return render(request, "teachers/steppers/spec-part.html", context)
#
#
# def check_clearance_sheet(request):
#     student_id = request.GET.get("student_id")
#     sheet = ClearanceSheet.objects.filter(myedu_id=student_id, completed_at__isnull=True).first()
#     if sheet:
#         return JsonResponse({"exists": True, "sheet_id": sheet.id})
#     return JsonResponse({"exists": False})
#
#
# @csrf_exempt
# def create_clearance_sheet(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         sheet = ClearanceSheet.objects.create(
#             myedu_id=data["student"],
#             student_fio=data["student_fio"],
#             myedu_faculty=data["myedu_faculty"],
#             myedu_spec=data["myedu_spec"],
#             duty=data["duty"],
#         )
#         return JsonResponse({"sheet_id": sheet.id})
#
#
# def cs(request):
#     search_query = request.GET.get('search', '')
#     open_clearance_sheets = ClearanceSheet.objects.filter(
#         completed_at__isnull=True
#     )
#
#     if search_query:
#         open_clearance_sheets = open_clearance_sheets.filter(
#             Q(student_fio__icontains=search_query) | Q(myedu_id__icontains=search_query)
#         )
#
#     trajectories = (
#         Trajectory.objects
#         .filter(
#             clearance_sheet__in=open_clearance_sheets,
#             completed_at__isnull=True
#         )
#         .annotate(
#             row_number=Window(
#                 expression=RowNumber(),
#                 partition_by=F("clearance_sheet"),
#                 order_by=F("stage__order").asc()
#             )
#         )
#         .filter(row_number=1)
#         .select_related("clearance_sheet", "stage")
#     )
#
#     clearance_with_stage = {t.clearance_sheet_id: t.stage for t in trajectories}
#
#     students = [
#         {
#             "id": sheet.id,
#             "fio": sheet.student_fio,
#             "faculty_name": sheet.myedu_faculty,
#             "spec_name": sheet.myedu_spec,
#             "current_stage": clearance_with_stage.get(sheet.id)
#         }
#         for sheet in open_clearance_sheets
#     ]
#
#     paginator = Pagination(request, students)
#     page_number = request.GET.get('page', 1)
#     students = paginator.pagination_with_filters_without_qs(page_number)
#
#     context = {
#         "title": "Перечень сформированных обходных листов",
#         "students": students,
#         "navbar": "stepper"
#     }
#     return render(request, "teachers/steppers/cs.html", context)
#
#
# def cs_step_undo(request, cs_id):
#     student = get_object_or_404(ClearanceSheet, id=cs_id)
#     trajectories = list(
#         Trajectory.objects.filter(clearance_sheet=student).select_related('stage').order_by('stage__order')
#     )
#
#     if request.method == "POST":
#         updated_trajectories = []
#
#         for trajectory in trajectories:
#             checkbox_name = f"trajectory_{trajectory.id}"
#             if checkbox_name not in request.POST:
#                 trajectory.completed_at = None
#             updated_trajectories.append(trajectory)
#
#         if updated_trajectories:
#             Trajectory.objects.bulk_update(updated_trajectories, ["completed_at"])
#
#         return redirect('stepper:cs-detail', id=student.id)
#
#     context = {
#         'trajectories': trajectories,
#         'student': student,
#         'navbar': 'stepper'
#     }
#     return render(request, "teachers/steppers/cs-step-undo.html", context)
#
#
# def cs_history(request, myedu_id):
#     student = next(iter(get_students_from_api(debt=1, search=myedu_id)), None)
#     trajectory_prefetch = Prefetch(
#         'trajectory_set',
#         queryset=Trajectory.objects.select_related('stage', 'assigned_by')
#     )
#     cs_list = ClearanceSheet.objects.filter(myedu_id=myedu_id).prefetch_related(trajectory_prefetch)
#     context = {
#         "title": "История обходных листов",
#         "navbar": "stepper",
#         "cs_list": cs_list,
#         "student": student
#     }
#     return render(request, "teachers/steppers/cs-history.html", context)
#
#
# def cs_history_detail(request, cs_id):
#     student = get_object_or_404(ClearanceSheet, id=cs_id)
#     trajectories = (
#         Trajectory.objects.filter(clearance_sheet=student)
#         .select_related("stage")
#         .prefetch_related("stagestatus_set", "stagestatus_set__processed_by")
#     )
#
#     context = {
#         "student": student,
#         "trajectories": trajectories,
#         "navbar": "stepper"
#     }
#     return render(request, "teachers/steppers/cs-history-detail.html", context)
#
#
# def cs_detail(request, id):
#     student = get_object_or_404(ClearanceSheet, id=id)
#
#     if request.method == "POST":
#         form = TrajectoryForm(request.POST)
#         if form.is_valid():
#             selected_stages = form.cleaned_data["stages"]
#             try:
#                 with transaction.atomic():
#                     for stage in selected_stages:
#                         Trajectory.objects.create(
#                             clearance_sheet=student,
#                             stage=stage,
#                             assigned_by=request.user
#                         )
#                     messages.success(request, "Траектория успешно создана для всех этапов.")
#             except Exception as _:
#                 messages.error(request, f"Ошибка при создании траектории")
#         else:
#             messages.error(request, "Выберите этапы, которые обязательны к выполнению")
#     else:
#         form = TrajectoryForm()
#
#     trajectories = (
#         Trajectory.objects.filter(clearance_sheet=student)
#         .select_related("stage")
#         .prefetch_related("stagestatus_set", "stagestatus_set__processed_by")
#     )
#
#     context = {
#         "student": student,
#         "form": form,
#         "trajectories": trajectories,
#         "navbar": "stepper"
#     }
#     return render(request, "teachers/steppers/cs-detail.html", context)
#
#
# def step_remove(request, id):
#     student = get_object_or_404(ClearanceSheet, id=id)
#     if not student:
#         return redirect("stepper:index")
#     if request.method == "POST":
#         trajectories = Trajectory.objects.filter(clearance_sheet=student).only("id")
#         if not StageStatus.objects.filter(trajectory__in=trajectories).exists():
#             try:
#                 with transaction.atomic():
#                     trajectories.delete()
#                     messages.success(request, "Траектория успешно удалена.")
#             except Exception as _:
#                 messages.error(request, "Ошибка при удалении траектории")
#         else:
#             messages.error(request, "Невозможно удалить траекторию, так как есть связанные записи")
#     return redirect("stepper:cs-detail", id=student.id)
#
#
# def step_rating(request, id, trajectory_id):
#     trajectory = Trajectory.objects.filter(id=trajectory_id).first()
#     student = get_object_or_404(ClearanceSheet, id=id)
#     if not student:
#         return redirect("stepper:index")
#     if trajectory:
#         trajectory.update_at = make_aware(datetime.now())
#         trajectory.save()
#     return redirect("stepper:cs-detail", id=student.id)
#
#
# def debts(request):
#     request.session['access'] = 'stepper'
#
#     employee = StageEmployee.objects.filter(employee=request.user).first()
#
#     students_with_stlib = None
#     if employee:
#         employee_stage = employee.stage
#         mandatory_stages = Stage.objects.filter(is_mandatory=True, category=Stage.STUDENT)
#
#         subquery = Trajectory.objects.filter(
#             clearance_sheet=OuterRef("trajectory__clearance_sheet"),
#             stage__in=mandatory_stages,
#             stage__order__lt=OuterRef("trajectory__stage__order"),
#             completed_at__isnull=True
#         ).values("id")[:1]
#
#         students_with_stlib = (
#             ClearanceSheet.objects.filter(
#                 trajectory__stage=employee_stage,
#                 trajectory__completed_at__isnull=True,
#                 completed_at__isnull=True
#             )
#             .annotate(
#                 has_unfinished_previous_stage=Exists(subquery),
#                 current_trajectory_id=F("trajectory__id"),
#                 status=F("trajectory__completed_at")
#             )
#             .filter(
#                 has_unfinished_previous_stage=False
#             )
#             .order_by('-trajectory__update_at')
#             .distinct()
#         )
#     context = {
#         "navbar": "stepper",
#         "students": students_with_stlib
#     }
#     return render(request, "teachers/steppers/debts.html", context)
#
#
# def debts_comment(request, id):
#     trajectory = get_object_or_404(Trajectory.objects.select_related('clearance_sheet'), id=id)
#     form = StageStatusForm(request.POST or None)
#
#     if request.method == "POST" and form.is_valid():
#         try:
#             with transaction.atomic():
#                 instance = form.save(commit=False)
#                 instance.trajectory = trajectory
#                 instance.processed_by = request.user
#                 instance.save()
#
#                 if request.POST.get("end") == "on":
#                     trajectory.completed_at = datetime.now()
#                     trajectory.save(update_fields=["completed_at"])
#                     trajectory.clearance_sheet.update_completed_at()
#                     messages.success(request, "Данные успешно сохранены.")
#                     return redirect("stepper:debts")
#                 messages.success(request, "Данные успешно сохранены.")
#         except IntegrityError:
#             messages.error(request, "Произошла ошибка при сохранении данных.")
#
#     elif request.method == "POST":
#         messages.error(request, "Попробуйте ещё раз.")
#
#     context = {
#         "navbar": "stepper",
#         "trajectory": trajectory,
#         "students": StageStatus.objects.filter(trajectory=trajectory),
#         "form": form
#     }
#     return render(request, "teachers/steppers/debts-comment.html", context)
