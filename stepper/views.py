import base64
import json
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction, DatabaseError
from django.db.models import Q, Count, F
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import make_aware, localdate, now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from bsadmin.consts import STADMIN
from bsadmin.role_utils import user_role_names
from bsadmin.models import Faculty, Speciality
from stepper.choices import TypeChoices
from stepper.consts import STUDENT_STEPPER_URL, TEACHER_STEPPER_URL, STUDENT_CS, TEACHER_CS, CS_PROCESS, CS_FINISHED, VC_URL
from stepper.decorators import with_stepper
from stepper.entity import StudentInfo
from stepper.exceptions import ClearanceCreationError, IssuanceRemovalError
from stepper.filters import CSFilter, CsHistoryFilter, VCFilter
from stepper.forms import StudentTrajectoryForm, StageStatusForm, IssuanceForm, StageEmployeeForm, DiplomaForm
from stepper.models import ClearanceSheet, Trajectory, StageStatus, TemplateStep, StageEmployee, Issuance, \
    IssuanceHistory, Diploma, VacationCertificate, EduYear
from stepper.services import StepperService
from utils.caches import EntityCache
from utils.filter_pagination import Pagination
from utils.myedu import MyEduService
from student.stepper_survey import enrich_students_with_survey_status
from student.services import SurveyService


def route(request):
    # if not request.user.is_authenticated:
    #     return redirect("integrator:next-teacher-login")
    roles = set(request.user.roles.values_list("name", flat=True))
    if STADMIN in roles:
        return redirect("stepper:index")
    return HttpResponse("403 - Forbidden")


STUDENT_SORTS = {
    "fio": lambda st: (st.get("student_fio") or "").lower(),
    "debts": lambda st: -len(st.get("debt") or []),
    "faculty": lambda st: ((st.get("faculty_name") or "").lower(), (st.get("student_fio") or "").lower()),
}
STUDENT_SORT_CHOICES = (("fio", "По ФИО"), ("debts", "Больше долгов"), ("faculty", "По факультету"))
STUDENT_VIEWS = (
    ("", "Все"),
    ("debt", "С долгами"),
    ("clean", "Без долгов"),
    ("nocs", "Без обходного"),
    ("process", "Обходной в процессе"),
    ("done", "Обходной завершён"),
)


def _sheet_state(sheet):
    if not sheet:
        return "nocs"
    if sheet.type_choices:
        return "issued"
    return "done" if sheet.completed_at else "process"


@with_stepper
def cs_index(request):
    request.session['access'] = 'stepper'
    request.session['cs-nav'] = 'stepper'

    get = request.GET
    query = (get.get("q") or "").strip()
    faculty_id = _parse_int(get.get("faculty"))
    speciality_id = _parse_int(get.get("speciality"))
    view = get.get("view") if get.get("view") in dict(STUDENT_VIEWS) else ""
    sort = get.get("sort") if get.get("sort") in STUDENT_SORTS else "fio"
    searched = bool(query or faculty_id)

    students, api_failed = [], False
    if searched:
        # Результат MyEDU кэшируется на 5 минут: страницы и фильтры не ждут MyEDU заново.
        cache_key = f"stepper-students:{query.lower()}:{faculty_id or 0}:{speciality_id or 0}"
        students = cache.get(cache_key)
        if students is None:
            students = MyEduService.search_debt_students(STUDENT_STEPPER_URL, query, faculty_id, speciality_id)
            if students is None:
                api_failed, students = True, []
            else:
                cache.set(cache_key, students, 5 * 60)

    sheets = request.stepper.latest_sheets_by_myedu_ids([st.get("student_id") for st in students])
    for st in students:
        sheet = sheets.get(str(st.get("student_id")))
        st["sheet"] = sheet
        st["sheet_state"] = _sheet_state(sheet)
        st["debt_list"] = [d.get("type", "") for d in (st.get("debt") or []) if d.get("type")]

    counts = {
        "": len(students),
        "debt": sum(1 for st in students if st["debt_list"]),
        "clean": sum(1 for st in students if not st["debt_list"]),
        "nocs": sum(1 for st in students if st["sheet_state"] == "nocs"),
        "process": sum(1 for st in students if st["sheet_state"] == "process"),
        "done": sum(1 for st in students if st["sheet_state"] in ("done", "issued")),
    }
    matches = {
        "": lambda st: True,
        "debt": lambda st: bool(st["debt_list"]),
        "clean": lambda st: not st["debt_list"],
        "nocs": lambda st: st["sheet_state"] == "nocs",
        "process": lambda st: st["sheet_state"] == "process",
        "done": lambda st: st["sheet_state"] in ("done", "issued"),
    }
    visible = sorted((st for st in students if matches[view](st)), key=STUDENT_SORTS[sort])

    paginator = Pagination(request, visible)
    page = paginator.pagination(get.get('page', 1))
    enrich_students_with_survey_status(page, id_key="student_id")

    params = {"q": query, "faculty": faculty_id, "speciality": speciality_id, "sort": sort}

    def url(**changes):
        merged = {**params, "view": view, **changes}
        clean = {k: v for k, v in merged.items() if v not in (None, "") and not (k == "sort" and v == "fio")}
        return reverse("stepper:index") + ("?" + urlencode(clean) if clean else "")

    faculties = request.bs.active_faculties()
    selected_faculty = next((f for f in faculties if f.myedu_faculty_id == faculty_id), None)
    specialities = (request.bs.faculty_specialities_with_values(selected_faculty.id)
                    if selected_faculty else [])

    context = {
        "title": "Студенты по данным MyEDU",
        "navbar": "stepper",
        "objects": page,
        "faculties": faculties,
        "specialities": specialities,
        "query": query,
        "faculty_id": faculty_id,
        "speciality_id": speciality_id,
        "searched": searched,
        "api_failed": api_failed,
        "view": view,
        "sort": sort,
        "sort_choices": STUDENT_SORT_CHOICES,
        "view_links": [{"label": label, "count": counts[value], "active": view == value,
                        "url": url(view=value), "value": value or "all"} for value, label in STUDENT_VIEWS],
        "success": True,
    }
    return render(request, "teachers/steppers/index.html", context)


@with_stepper
def spec(request):
    request.session['access'] = 'stepper'
    request.session['nav-spec'] = 'spec'
    # if not request.user.is_authenticated:
    #     return redirect("integrator:next-teacher-login")

    qs = request.stepper.get_clearance_students(TypeChoices.SPEC, 'has_spec',
                                                extra_filter={'type_choices': TypeChoices.SPEC})
    students, form = get_cs_filtered_paginated(request, qs)

    context = {
        "title": "Студенты без задолженности по данным MyEDU",
        "navbar": "spec",
        "objects": students,
        "form": form,
    }
    return render(request, "teachers/steppers/spec.html", context)


@with_stepper
def spec_students(request):
    search = None
    faculty_id = request.session.get("faculty_id", 0)
    specialty_id = request.session.get("specialty_id", 0)

    if request.method == "POST":
        search = request.POST.get("search", "")
        faculty_id = request.POST.get("faculty_id")
        specialty_id = request.POST.get("specialty_id")

        request.session["faculty_id"] = faculty_id
        request.session["specialty_id"] = specialty_id

    students_qs = MyEduService.get_stepper_data_from_api(
        STUDENT_STEPPER_URL, search, faculty_id, specialty_id
    )

    paginator = Pagination(request, students_qs or [])
    page_number = request.GET.get('page', 1)
    students_paginator = paginator.pagination(page_number)

    student_ids = [str(item['student_id']) for item in students_paginator]

    existing_diplomas = set(
        Diploma.objects.filter(student__in=student_ids).values_list('student', flat=True)
    )

    students = []
    for item in students_paginator:
        student_copy = item.copy()
        student_copy['exists'] = str(item['student_id']) in existing_diplomas
        students.append(student_copy)

    context = {
        "title": "Студенты без задолженности по данным MyEDU",
        "navbar": "spec-students",
        "objects": students,
        "faculties": request.bs.active_faculties(),
    }

    return render(request, "teachers/steppers/spec-students.html", context)


@with_stepper
def spec_diploma(request):
    students_qs = Diploma.objects.all().select_related('faculty', 'speciality', 'edu_year').order_by('-id')

    search = request.GET.get("search")
    if search:
        students_qs = students_qs.filter(student=search)

    paginator = Pagination(request, students_qs or [])
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    context = {
        "title": "Список зарегистрированных дипломов",
        "navbar": "spec-students",
        "students": students
    }

    return render(request, "teachers/steppers/spec-diploma.html", context)


@with_stepper
def archive(request):
    request.session['access'] = 'stepper'
    # if not request.user.is_authenticated:
    #     return redirect("integrator:next-teacher-login")

    qs = request.stepper.get_clearance_students(TypeChoices.OTHER, 'has_archive')

    students, form = get_cs_filtered_paginated(request, qs)

    context = {
        "title": "Студенты без задолженности по данным MyEDU",
        "navbar": "archive",
        "objects": students,
        "form": form,
    }
    return render(request, "teachers/steppers/archive.html", context)


@with_stepper
def spec_history(request):
    request.session['nav-spec'] = 'spec-history'

    qs = request.stepper.get_clearance_history(TypeChoices.SPEC, 'has_spec')
    students, form = get_cs_history_filtered_paginated(request, qs)

    context = {
        "title": "История студентов без задолженности по данным MyEDU",
        "navbar": "spec-history",
        "objects": students,
        "form": form,
        "history": True
    }
    return render(request, "teachers/steppers/spec.html", context)


@with_stepper
def spec_report(request):
    active_edu_year = request.stepper.active_edu_year()
    edu_years = request.stepper.edu_years()

    if request.method == "POST":
        form_edu_year = request.POST.get("edu_year")
        if form_edu_year:
            active_edu_year = request.stepper.filter_edu_year_by_id(edu_year_id=form_edu_year)

    statistics = request.stepper.get_clearance_statistics_by_faculty(TypeChoices.SPEC, active_edu_year, 'has_spec')

    context = {
        "title": f"Обходной лист - отчёт за {active_edu_year} учебный год",
        "navbar": "spec-report",
        "statistics": statistics,
        "active_edu_year": active_edu_year,
        "edu_years": edu_years
    }
    return render(request, "teachers/steppers/reports/spec-report.html", context)


@with_stepper
def archive_history(request):
    qs = request.stepper.get_clearance_history(TypeChoices.OTHER, 'has_archive')
    students, form = get_cs_history_filtered_paginated(request, qs)

    context = {
        "title": "История студентов без задолженности по данным MyEDU",
        "navbar": "archive-history",
        "objects": students,
        "form": form,
        "history": True
    }
    return render(request, "teachers/steppers/archive.html", context)


@with_stepper
def spec_avn(request):
    student_qs = request.stepper.spec_issuance_students()

    form = IssuanceForm()
    if request.method == "POST":
        if 'search' in request.POST:
            fio = request.POST.get("fio", "")
            student_qs = request.stepper.spec_students_issuance_search(fio)
        elif 'create' in request.POST:
            form = IssuanceForm(request.POST, request.FILES)
            signature_base64 = request.POST.get('signature')
            faculty_id = request.POST.get('faculty_id', 0)
            specialty_id = request.POST.get('specialty_id', 0)
            instance, error = request.stepper.create_issuance_form(
                form=form,
                user=request.user,
                myeduid=0,
                signature_base64=signature_base64,
                faculty_id=faculty_id,
                specialty_id=specialty_id,
                type=Issuance.SPEC
            )

            if error:
                messages.error(request, error)
            else:
                messages.success(request, "Данные успешно сохранены")
                form = IssuanceForm()

    paginator = Pagination(request, student_qs or [])
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    faculties = request.bs.active_faculties()
    context = {
        "form": form,
        "navbar": "spec-avn",
        "students": students,
        "faculties": faculties
    }
    return render(request, "teachers/steppers/spec-avn.html", context)


@with_stepper
def archive_avn(request):
    student_qs = request.stepper.archive_issuance_students()

    form = IssuanceForm()
    if request.method == "POST":
        if 'search' in request.POST:
            fio = request.POST.get("fio", "")
            student_qs = request.stepper.archive_students_issuance_search(fio)
        elif 'create' in request.POST:
            form = IssuanceForm(request.POST, request.FILES)
            signature_base64 = request.POST.get('signature')
            faculty_id = request.POST.get('faculty_id', 0)
            specialty_id = request.POST.get('specialty_id', 0)
            instance, error = request.stepper.create_issuance_form(
                form=form,
                user=request.user,
                myeduid=0,
                signature_base64=signature_base64,
                faculty_id=faculty_id,
                specialty_id=specialty_id,
                type=Issuance.OTHER
            )

            if error:
                messages.error(request, error)
            else:
                messages.success(request, "Данные успешно сохранены")
                form = IssuanceForm()

    paginator = Pagination(request, student_qs or [])
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    faculties = request.bs.active_faculties()
    context = {
        "form": form,
        "navbar": "archive-avn",
        "students": students,
        "faculties": faculties
    }
    return render(request, "teachers/steppers/archive-avn.html", context)


@with_stepper
def spec_part(request, id, myedu_id):
    nav = request.session.get("nav-spec", "spec")
    has_active_cs = request.stepper.has_active_cs(myedu_id)

    student = get_object_or_404(ClearanceSheet, myedu_id=myedu_id, id=id)
    selected_edu_year_id = student.edu_year_id
    if request.method == "POST":
        form = IssuanceForm(request.POST)
        signature_base64 = request.POST.get('signature')
        profile_base64 = request.POST.get('profile')
        edu_year_id = request.POST.get('edu_year_id', 0)
        instance, error = request.stepper.create_issuance_form(
            form=form,
            user=request.user,
            signature_base64=signature_base64,
            myeduid=myedu_id,
            cs_id=student.id,
            faculty_id=student.myedu_faculty_id,
            specialty_id=student.myedu_spec_id,
            type=Issuance.SPEC,
            profile_base64=profile_base64,
            student_fio=student.student_fio,
        )
        if edu_year_id:
            selected_edu_year_id = int(edu_year_id)
        if error:
            messages.error(request, error)
        else:
            if edu_year_id:
                student.edu_year_id = edu_year_id
                student.save(update_fields=['edu_year_id'])
            messages.success(request, "Данные успешно сохранены.")
            return redirect('stepper:spec-part', id=id, myedu_id=myedu_id)
    else:
        form = IssuanceForm()

    issuance = Issuance.objects.filter(cs_id=id, student=myedu_id, type_choices=Issuance.SPEC).first()
    diploma = Diploma.objects.filter(student=myedu_id, sync=False).first()

    context = {
        "navbar": nav,
        "has_active_cs": has_active_cs,
        "form": form,
        "student": student,
        "issuance": issuance,
        "diploma": diploma,
        "years": request.stepper.edu_years(),
        "selected_edu_year_id": selected_edu_year_id
    }
    return render(request, "teachers/steppers/spec-part.html", context)


@with_stepper
def archive_part(request, id, myedu_id):
    has_active_cs = request.stepper.has_active_cs(myedu_id)

    student = get_object_or_404(ClearanceSheet, myedu_id=myedu_id, id=id)

    if request.method == "POST":
        form = IssuanceForm(request.POST)
        signature_base64 = request.POST.get('signature')
        instance, error = request.stepper.create_issuance_form(
            form=form,
            user=request.user,
            signature_base64=signature_base64,
            myeduid=myedu_id,
            cs_id=student.id,
            faculty_id=student.myedu_faculty_id,
            specialty_id=student.myedu_spec_id,
            type=Issuance.OTHER,
            student_fio=student.student_fio,
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Данные успешно сохранены.")
            return redirect('stepper:archive-part', id=id, myedu_id=myedu_id)
    else:
        form = IssuanceForm()

    issuance = Issuance.objects.filter(cs_id=id, student=myedu_id, type_choices=Issuance.OTHER).first()
    context = {
        "navbar": "archive-history",
        "has_active_cs": has_active_cs,
        "form": form,
        "student": student,
        "issuance": issuance
    }
    return render(request, "teachers/steppers/archive-part.html", context)


@with_stepper
def spec_part_double(request, id, myedu_id):
    if request.method == "POST":
        history = request.POST.get('history', "Дубликат")

        try:
            issuance = Issuance.objects.filter(student=myedu_id, type_choices=Issuance.SPEC).first()
            if not issuance:
                messages.error(request, "Не найдено подходящей записи для выдачи дубликата")
                return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)

            with transaction.atomic():
                issuance.status = Issuance.DOUBLE
                issuance.save()
                IssuanceHistory.objects.create(student=myedu_id, history=history, cs=id, type_choices=Issuance.SPEC)
                messages.success(request, "Обработка данных завершена успешно. Дубликат диплома выдан.")

        except DatabaseError as e:

            messages.error(request, "Не удалось выдать дубликат диплома")

    return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)


@with_stepper
def spec_part_remove(request, id, myedu_id):
    if request.method == "POST":
        student = get_object_or_404(ClearanceSheet, id=id, myedu_id=myedu_id)
        try:
            removed = request.stepper.remove_issuance_and_history(myedu_id, student.id, Issuance.SPEC)
            if removed:
                messages.success(request, "Информация о дипломе успешно удалена")
            else:
                messages.info(request, "Запись не найдена, удалять нечего")
        except IssuanceRemovalError:
            messages.error(request, "Ошибка при удалении информации о дипломе")
    return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)


@with_stepper
def spec_sync(request, id, myedu_id):
    if request.method == "POST":
        try:
            diploma = Diploma.objects.filter(student=myedu_id, sync=False).first()
            issuance = Issuance.objects.filter(student=myedu_id, type_choices=Issuance.SPEC).first()

            with transaction.atomic():
                if not issuance and diploma:
                    cs_sheet = ClearanceSheet.objects.filter(pk=id).only('student_fio').first()
                    Issuance.objects.create(
                        student=diploma.student,
                        cs_id=id,
                        fio=cs_sheet.student_fio if cs_sheet else None,
                        doc_number=diploma.doc_number,
                        reg_number=diploma.reg_number,
                        faculty=diploma.faculty,
                        speciality=diploma.speciality,
                        date_issue=diploma.date_issue,
                        employee=request.user,
                        type_choices=Issuance.SPEC
                    )
                    diploma.sync = True
                    diploma.save()
                    messages.success(request, "Информация о дипломе успешно синхронизирована")
                else:
                    messages.success(request, "Данные не найдены")
        except DatabaseError as e:
            messages.error(request, "Ошибка при синхронизации")

    return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)


@with_stepper
def archive_part_remove(request, id, myedu_id):
    if request.method == "POST":
        student = get_object_or_404(ClearanceSheet, id=id, myedu_id=myedu_id)
        try:
            removed = request.stepper.remove_issuance_and_history(myedu_id, student.id, Issuance.OTHER)
            if removed:
                messages.success(request, "Информация о дипломе успешно удалена")
            else:
                messages.info(request, "Запись не найдена, удалять нечего")
        except IssuanceRemovalError:
            messages.error(request, "Ошибка при удалении информации о дипломе")
    return redirect("stepper:archive-part", id=id, myedu_id=myedu_id)


@with_stepper
def load_specialities(request):
    faculty = request.bs.get_first_active_faculty(request.GET.get('faculty_id'))
    specialities = request.bs.faculty_specialities_with_values(faculty.id if faculty else 0)
    return JsonResponse(list(specialities), safe=False)


def _is_stadmin(request):
    return STADMIN in user_role_names(request)


def _deny(request):
    return render(request, "utils/_access.html", status=403) if request.method == "GET" \
        else HttpResponse("Недостаточно прав", status=403)


def _form_errors(form):
    return " ".join(e for errors in form.errors.values() for e in errors) or "Проверьте заполнение формы."


STAGE_EMPLOYEE_STATUSES = (("", "Все"), ("active", "Активные"), ("inactive", "Отключённые"))


@with_stepper
def stage_employee(request):
    get = request.GET
    query = (get.get("q") or "").strip()
    stage_id = get.get("stage") if (get.get("stage") or "").isdigit() else ""
    status = get.get("status") if get.get("status") in ("active", "inactive") else ""

    employees_qs = request.stepper.get_stepper_employees()
    if query:
        condition = Q(employee__email__icontains=query)
        for part in query.split():
            condition |= (Q(employee__last_name__icontains=part) | Q(employee__first_name__icontains=part) |
                          Q(employee__fathers_name__icontains=part))
        employees_qs = employees_qs.filter(condition)
    if stage_id:
        employees_qs = employees_qs.filter(template_stage_id=stage_id)
    if status:
        employees_qs = employees_qs.filter(is_active=status == "active")

    paginator = Pagination(request, employees_qs)
    employees = paginator.pagination(get.get('page', 1))

    overview = request.stepper.stage_employee_overview()
    context = {
        "navbar": "roles",
        "employees": employees,
        "overview": overview,
        "uncovered": [item for item in overview if not item["active"] and item["queue"]],
        "query": query,
        "stage_id": stage_id,
        "status": status,
        "statuses": STAGE_EMPLOYEE_STATUSES,
        "stages": [item["step"] for item in overview],
        "has_filters": bool(query or stage_id or status),
        "title": "Сотрудники этапов обходного листа",
    }
    return render(request, "teachers/steppers/stage-employee.html", context)


def stage_employee_create(request):
    if not _is_stadmin(request):
        return _deny(request)
    if request.method == 'POST':
        form = StageEmployeeForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{obj.employee.full_name} назначен(а) на этап «{obj.template_stage.stage.name}».")
            return redirect('stepper:stage-employee')
        messages.error(request, _form_errors(form))
    else:
        stage = request.GET.get("stage")
        form = StageEmployeeForm(initial={"template_stage": stage} if stage and stage.isdigit() else None)
    return render(request, 'teachers/steppers/stage-employee-form.html', {
        'form': form,
        'is_edit': False,
        'navbar': 'roles'
    })


def stage_employee_update(request, pk):
    if not _is_stadmin(request):
        return _deny(request)
    obj = get_object_or_404(StageEmployee, pk=pk)
    if request.method == 'POST':
        form = StageEmployeeForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Назначение сохранено: {obj.employee.full_name} — «{obj.template_stage.stage.name}»"
                                      f"{'' if obj.is_active else ' (отключён)'}.")
            return redirect('stepper:stage-employee')
        messages.error(request, _form_errors(form))
    else:
        form = StageEmployeeForm(instance=obj)
    return render(request, 'teachers/steppers/stage-employee-form.html', {
        'form': form,
        'is_edit': True,
        'navbar': 'roles'
    })


@require_POST
def stage_employee_toggle(request, pk):
    """Быстро включить/отключить сотрудника на этапе (роль доступа обновляется так же, как в форме)."""
    if not _is_stadmin(request):
        return _deny(request)
    obj = get_object_or_404(StageEmployee, pk=pk)
    data = {"template_stage": obj.template_stage_id, "employee": obj.employee_id}
    if not obj.is_active:
        data["is_active"] = "on"
    form = StageEmployeeForm(data, instance=obj)
    if form.is_valid():
        obj = form.save()
        state = "включён(а)" if obj.is_active else "отключён(а)"
        messages.success(request, f"{obj.employee.full_name} {state} на этапе «{obj.template_stage.stage.name}».")
    else:
        messages.error(request, _form_errors(form))
    back = request.POST.get("next") or ""
    return redirect(back if url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()})
                    else reverse('stepper:stage-employee'))


@with_stepper
def check_clearance_sheet(request):
    sheet = request.stepper.first_active_cs(request.GET.get("student_id"))
    if sheet:
        return JsonResponse({"exists": True, "sheet_id": sheet.id})
    return JsonResponse({"exists": False})


@csrf_exempt
@with_stepper
def create_clearance_sheet(request):
    if request.method == "POST":
        data = json.loads(request.body)
        sheet = request.stepper.create_cs(data)
        return JsonResponse({"sheet_id": sheet.id})


@with_stepper
def student_survey_submissions(request):
    myedu_id = request.GET.get("myedu_id")
    if not myedu_id:
        return HttpResponse("Не указан ID студента.", status=400)

    submissions = list(SurveyService.submissions_for_myedu_id(myedu_id))
    student_fio = submissions[0].student_fio if submissions else request.GET.get("fio", "")

    return render(
        request,
        "teachers/steppers/_survey_submissions_modal.html",
        {
            "submissions": submissions,
            "student_fio": student_fio,
            "myedu_id": myedu_id,
            "edu_year": SurveyService.commission_edu_year(),
        },
    )


CS_STATUSES = (
    ("active", "Все активные"),
    ("process", "В процессе"),
    ("ready", "Пройдены, ждут выдачи"),
    ("issued", "Выданы (история)"),
)
CS_DATE_FIELDS = (("issued_at", "Создан"), ("completed_at", "Завершён"))
CS_STUCK_CHOICES = ((3, "3 дней"), (7, "7 дней"), (14, "14 дней"), (30, "30 дней"))
CS_STUCK_WARN_DAYS = 7
CS_SORT_CHOICES = (
    ("new", "Сначала новые"),
    ("old", "Сначала старые"),
    ("completed", "Недавно завершённые"),
    ("fio", "По ФИО"),
)


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        return None


def _parse_int(value):
    return int(value) if value and str(value).isdigit() else None


def _cs_filters(request):
    get = request.GET
    filters = {
        "q": (get.get("q") or get.get("search") or "").strip(),
        "status": get.get("status") if get.get("status") in dict(CS_STATUSES) else "active",
        "stage": _parse_int(get.get("stage")),
        "faculty": _parse_int(get.get("faculty")),
        "order_status": (get.get("order_status") or "").strip(),
        "edu_year": _parse_int(get.get("edu_year")),
        "date_field": get.get("date_field") if get.get("date_field") in dict(CS_DATE_FIELDS) else "issued_at",
        "date_from": _parse_date(get.get("date_from")),
        "date_to": _parse_date(get.get("date_to")),
        "sort": get.get("sort") if get.get("sort") in dict(CS_SORT_CHOICES) else "new",
        "stuck_days": _parse_int(get.get("stuck_days")) if _parse_int(get.get("stuck_days")) in dict(CS_STUCK_CHOICES) else None,
    }
    if filters["stuck_days"] and filters["status"] in ("ready", "issued"):
        filters["status"] = "active"
    if filters["stage"] and filters["status"] not in ("active", "process"):
        filters["stage"] = None
    return filters


def _cs_url(filters, **changes):
    """Ссылка на перечень с изменёнными фильтрами (страница сбрасывается)."""
    params = {**filters, **changes}
    query = {}
    for key, value in params.items():
        if value in (None, "") or (key == "status" and value == "active") or (key == "sort" and value == "new") \
                or (key == "date_field" and value == "issued_at" and not (params.get("date_from") or params.get("date_to"))):
            continue
        query[key] = value.isoformat() if hasattr(value, "isoformat") else value
    return reverse("stepper:cs") + ("?" + urlencode(query) if query else "")


def _attach_cs_progress(sheets):
    """Добавляет к листам страницы прогресс по этапам: [{name, done, current}], одним запросом."""
    ids = [sheet.id for sheet in sheets]
    steps_by_sheet = {}
    for t in (Trajectory.objects.filter(clearance_sheet_id__in=ids)
              .select_related("template_stage__stage").order_by("template_stage__order")):
        steps_by_sheet.setdefault(t.clearance_sheet_id, []).append(t)
    for sheet in sheets:
        steps = steps_by_sheet.get(sheet.id, [])
        current_found = False
        progress = []
        for t in steps:
            done = t.completed_at is not None
            current = not done and not current_found
            current_found = current_found or current
            progress.append({"name": t.template_stage.stage.name, "done": done, "current": current,
                             "completed_at": t.completed_at})
        sheet.progress = progress
        sheet.progress_done = sum(step["done"] for step in progress)
        sheet.progress_total = len(progress)
        sheet.stage_days = None
        if not sheet.completed_at and not sheet.type_choices and getattr(sheet, "stage_since", None):
            sheet.stage_days = (now() - sheet.stage_since).days
            sheet.stage_stuck = sheet.stage_days >= CS_STUCK_WARN_DAYS


@with_stepper
def cs(request):
    request.session['cs-nav'] = 'cs'
    filters = _cs_filters(request)
    students_qs, status_counts, stage_counts = request.stepper.filter_student_clearance_sheets(filters)

    paginator = Pagination(request, students_qs)
    students = paginator.pagination(request.GET.get('page', 1))
    enrich_students_with_survey_status(students, id_key="myedu_id")
    _attach_cs_progress(students)

    stages = TemplateStep.objects.filter(category=TemplateStep.STUDENT, order__gt=0,
                                         stage__is_mandatory=True).select_related('stage').order_by('order')
    faculties = list(request.stepper.student_clearance_faculties())
    order_statuses = list(request.stepper.student_clearance_order_statuses())
    edu_years = list(EduYear.objects.order_by('-id').values_list('id', 'title'))

    # Единая полоса «где сейчас листы»: все → этапы по порядку → ждут выдачи → история.
    pipeline = [{"label": "Все активные", "count": status_counts["active"],
                 "active": filters["status"] == "active" and not filters["stage"],
                 "url": _cs_url(filters, status="active", stage=None), "kind": "all"}]
    for step in stages:
        pipeline.append({"label": step.stage.name, "count": stage_counts.get(step.id, 0),
                         "active": filters["stage"] == step.id,
                         "url": _cs_url(filters, status="process", stage=step.id), "kind": "stage"})
    pipeline.append({"label": "Ждут выдачи", "count": status_counts["ready"], "active": filters["status"] == "ready",
                     "url": _cs_url(filters, status="ready", stage=None), "kind": "ready"})
    history_link = {"label": "История", "count": status_counts["issued"], "active": filters["status"] == "issued",
                    "url": _cs_url(filters, status="issued", stage=None)}

    today = localdate()
    date_presets = [
        ("Сегодня", today, today),
        ("Вчера", today - timedelta(days=1), today - timedelta(days=1)),
        ("7 дней", today - timedelta(days=6), today),
        ("30 дней", today - timedelta(days=29), today),
        ("Этот месяц", today.replace(day=1), today),
    ]
    date_links = [
        {"label": label, "url": _cs_url(filters, date_from=start, date_to=finish),
         "active": filters["date_from"] == start and filters["date_to"] == finish}
        for label, start, finish in date_presets
    ]

    faculty_names = dict(faculties)
    date_label = dict(CS_DATE_FIELDS)[filters["date_field"]]
    active_filters = []
    if filters["q"]:
        active_filters.append((f"Поиск: «{filters['q']}»", _cs_url(filters, q="")))
    if filters["faculty"]:
        active_filters.append((f"Факультет: {faculty_names.get(filters['faculty'], filters['faculty'])}",
                               _cs_url(filters, faculty=None)))
    if filters["order_status"]:
        active_filters.append((f"Приказ: {filters['order_status']}", _cs_url(filters, order_status="")))
    if filters["edu_year"]:
        active_filters.append((f"Учебный год: {dict(edu_years).get(filters['edu_year'], filters['edu_year'])}",
                               _cs_url(filters, edu_year=None)))
    if filters["stuck_days"]:
        active_filters.append((f"На этапе дольше {dict(CS_STUCK_CHOICES)[filters['stuck_days']]}",
                               _cs_url(filters, stuck_days=None)))
    if filters["date_from"] or filters["date_to"]:
        period = " – ".join(d.strftime("%d.%m.%Y") for d in (filters["date_from"], filters["date_to"]) if d)
        if filters["date_from"] == filters["date_to"]:
            period = filters["date_from"].strftime("%d.%m.%Y")
        active_filters.append((f"{date_label}: {period}", _cs_url(filters, date_from=None, date_to=None)))

    is_history = filters["status"] == "issued"
    context = {
        "title": "История — выданные обходные листы" if is_history else "Перечень обходных листов",
        "students": students,
        "navbar": "cs-done" if is_history else "cs",
        "filters": filters,
        "pipeline": pipeline,
        "history_link": history_link,
        "date_links": date_links,
        "stuck_choices": CS_STUCK_CHOICES,
        "faculties": faculties,
        "order_statuses": order_statuses,
        "edu_years": edu_years,
        "date_fields": CS_DATE_FIELDS,
        "sort_choices": CS_SORT_CHOICES,
        "active_filters": active_filters,
        "reset_url": _cs_url({"status": filters["status"], "stage": filters["stage"]}),
        "sort_url": _cs_url(filters, sort=None),
    }
    return render(request, "teachers/steppers/cs.html", context)


@with_stepper
@require_POST
def cs_delete(request):
    cs_id = request.POST.get("cs_id")

    clearance_sheet_detail = ClearanceSheet.objects.filter(id=cs_id).first()
    if not clearance_sheet_detail:
        messages.error(request, f"Обходной лист №{cs_id} не найден.")
        return redirect("stepper:cs")

    has_trajectory = Trajectory.objects.filter(clearance_sheet_id=clearance_sheet_detail.id).exists()
    has_issuance = Issuance.objects.filter(cs_id=clearance_sheet_detail.id).exists()

    if not has_trajectory and not has_issuance:
        clearance_sheet_detail.delete()
        messages.success(request, f"Обходной лист №{cs_id} успешно удалён. ФИО: {clearance_sheet_detail.student_fio}")
    else:
        messages.error(
            request,
            f"Обходной лист №{cs_id} не может быть удалён, так как уже находится в процессе прохождения."
        )

    return redirect("stepper:cs")


@with_stepper
def cs_done(request):
    params = {"status": "issued"}
    if request.GET.get("search"):
        params["q"] = request.GET["search"]
    return redirect(reverse("stepper:cs") + "?" + urlencode(params))


@with_stepper
def cs_debt_stage(request, stage):
    """Старый адрес фильтра по этапу: принимает id шаблона этапа или (как раньше в ссылках) id этапа."""
    step = (TemplateStep.objects.filter(id=stage, category=TemplateStep.STUDENT).first()
            or TemplateStep.objects.filter(stage_id=stage, category=TemplateStep.STUDENT).first())
    params = {"status": "process"}
    if step:
        params["stage"] = step.id
    if request.GET.get("search"):
        params["q"] = request.GET["search"]
    return redirect(reverse("stepper:cs") + "?" + urlencode(params))


@with_stepper
def cs_status(request):
    raw_status = (request.POST.get("status") or request.GET.get("status") or "").strip()
    params = {"status": {str(CS_PROCESS): "process", str(CS_FINISHED): "ready"}.get(raw_status, "active")}
    if request.GET.get("search"):
        params["q"] = request.GET["search"]
    return redirect(reverse("stepper:cs") + "?" + urlencode(params))


ISSUANCE_SORTS = {
    "new": ("-created_at", "-id"),
    "old": ("created_at", "id"),
    "fio": ("fio", "-id"),
    "issue": (F("date_issue").desc(nulls_last=True), "-id"),
}
ISSUANCE_SORT_CHOICES = (
    ("new", "Сначала новые"),
    ("old", "Сначала старые"),
    ("issue", "По дате выдачи диплома"),
    ("fio", "По ФИО"),
)


@with_stepper
def cs_issuance(request):
    get = request.GET
    query = (get.get('q') or get.get('search') or '').strip()
    type_filter = get.get('type') if get.get('type') in (Issuance.SPEC, Issuance.OTHER) else ''
    status_filter = get.get('status') if get.get('status') in (Issuance.RECEIVED, Issuance.DOUBLE) else ''
    faculty_id = _parse_int(get.get('faculty'))
    date_from, date_to = _parse_date(get.get('date_from')), _parse_date(get.get('date_to'))
    sort = get.get('sort') if get.get('sort') in ISSUANCE_SORTS else 'new'

    base = (
        Issuance.objects
        .select_related('faculty', 'speciality', 'cs', 'employee')
        .only(
            'id', 'fio', 'student', 'doc_number', 'reg_number', 'date_issue', 'files',
            'cs_id', 'type_choices', 'status', 'created_at', 'faculty_id',
            'faculty__title', 'speciality__title', 'cs__student_fio',
            'employee__first_name', 'employee__last_name',
        )
    )
    # Общие фильтры (поиск, факультет, период) — от них считаются счётчики разделов.
    if query:
        condition = (Q(fio__icontains=query) | Q(cs__student_fio__icontains=query) |
                     Q(student__icontains=query) | Q(doc_number__icontains=query) | Q(reg_number__icontains=query))
        if query.isdigit():
            condition |= Q(id=int(query)) | Q(cs_id=int(query))
        base = base.filter(condition)
    if faculty_id:
        base = base.filter(faculty_id=faculty_id)
    if date_from:
        base = base.filter(created_at__date__gte=date_from)
    if date_to:
        base = base.filter(created_at__date__lte=date_to)

    counts = base.aggregate(
        total=Count('id'),
        spec=Count('id', filter=Q(type_choices=Issuance.SPEC)),
        archive=Count('id', filter=Q(type_choices=Issuance.OTHER)),
        double=Count('id', filter=Q(status=Issuance.DOUBLE)),
    )

    issuance_qs = base
    if type_filter:
        issuance_qs = issuance_qs.filter(type_choices=type_filter)
    if status_filter:
        issuance_qs = issuance_qs.filter(status=status_filter)
    issuance_qs = issuance_qs.order_by(*ISSUANCE_SORTS[sort])

    paginator = Pagination(request, issuance_qs)
    issuance = StepperService.enrich_issuance_page(paginator.pagination(get.get('page', 1)))

    filters = {"q": query, "type": type_filter, "status": status_filter, "faculty": faculty_id,
               "date_from": date_from, "date_to": date_to, "sort": sort}

    def url(**changes):
        params = {**filters, **changes}
        clean = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in params.items()
                 if v not in (None, "") and not (k == "sort" and v == "new")}
        return reverse("stepper:cs-issuance") + ("?" + urlencode(clean) if clean else "")

    faculties = list(Faculty.objects.filter(issuance__isnull=False).distinct()
                     .order_by('title').values_list('id', 'title'))
    today = localdate()
    presets = [("Сегодня", today, today), ("7 дней", today - timedelta(days=6), today),
               ("30 дней", today - timedelta(days=29), today), ("Этот месяц", today.replace(day=1), today)]

    active = []
    if query:
        active.append((f"Поиск: «{query}»", url(q="")))
    if faculty_id:
        active.append((f"Факультет: {dict(faculties).get(faculty_id, faculty_id)}", url(faculty=None)))
    if status_filter:
        active.append(("Только дубликаты" if status_filter == Issuance.DOUBLE else "Только получившие", url(status="")))
    if date_from or date_to:
        period = " – ".join(d.strftime("%d.%m.%Y") for d in (date_from, date_to) if d)
        active.append((f"Записано: {period}", url(date_from=None, date_to=None)))

    context = {
        "title": "Выданные документы",
        "issuance": issuance,
        "navbar": "issuance",
        "type_filter": type_filter,
        "filters": filters,
        "counts": counts,
        "section_links": [
            {"label": "Все", "count": counts["total"], "active": not type_filter, "url": url(type="")},
            {"label": "Спец. часть", "count": counts["spec"], "active": type_filter == Issuance.SPEC,
             "url": url(type=Issuance.SPEC), "icon": "fa-graduation-cap"},
            {"label": "Архив", "count": counts["archive"], "active": type_filter == Issuance.OTHER,
             "url": url(type=Issuance.OTHER), "icon": "fa-archive"},
        ],
        "double_link": {"count": counts["double"], "active": status_filter == Issuance.DOUBLE,
                        "url": url(status="" if status_filter == Issuance.DOUBLE else Issuance.DOUBLE)},
        "faculties": faculties,
        "sort_choices": ISSUANCE_SORT_CHOICES,
        "date_links": [{"label": label, "url": url(date_from=start, date_to=finish),
                        "active": date_from == start and date_to == finish} for label, start, finish in presets],
        "active_filters": active,
        "reset_url": url(q="", faculty=None, status="", date_from=None, date_to=None, sort="new"),
    }
    return render(request, "teachers/steppers/cs-issuance.html", context)


@require_POST
def cs_issuance_delete(request):
    doc_id = request.POST.get('id')
    try:
        Issuance.objects.get(id=doc_id).delete()
        return JsonResponse({'success': True})
    except Issuance.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


@with_stepper
def cs_report(request, cs_id):
    clearance_sheet = get_object_or_404(ClearanceSheet, id=cs_id)

    student = EntityCache.get_or_set(
        entity_id=clearance_sheet.myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": clearance_sheet.myedu_id,
        },
    )

    trajectories = request.stepper.get_trajectories_with_annotations(clearance_sheet)

    relative_url = reverse('stepper:qr-code-status', kwargs={'qr_id': cs_id})
    full_url = request.build_absolute_uri(relative_url)

    qr = qrcode.make(full_url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()

    context = {
        "title": "История - Перечень завершенных обходных листов",
        "student": student,
        "cs": clearance_sheet,
        "qr_code": img_str,
        "trajectories": trajectories,
        "navbar": "cs",
    }
    return render(request, "teachers/steppers/reports/cs-report.html", context)


@with_stepper
def cs_step_undo(request, cs_id):
    clearance_sheet = get_object_or_404(ClearanceSheet, id=cs_id)
    trajectories = request.stepper.get_trajectories_for_student(clearance_sheet)

    type_param = request.GET.get('type')

    redirect_map = {
        STUDENT_CS: lambda: redirect('stepper:cs-detail', myedu_id=clearance_sheet.myedu_id),
        TEACHER_CS: lambda: redirect('stepper:teacher-cs-detail', myedu_id=clearance_sheet.myedu_id),
    }

    navbar_map = {
        STUDENT_CS: 'stepper',
        TEACHER_CS: 'teachers',
    }

    if request.method == "POST":
        request.stepper.undo_trajectories(trajectories, request.POST)
        if type_param in redirect_map:
            return redirect_map[type_param]()
        raise Http404

    context = {
        'trajectories': trajectories,
        'clearance_sheet': clearance_sheet,
        'navbar': navbar_map.get(type_param, "stepper"),
    }
    return render(request, "teachers/steppers/cs-step-undo.html", context)


@with_stepper
def cs_history(request, myedu_id, cs_id):
    student = EntityCache.get_or_set(
        entity_id=myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": myedu_id,
        },
    )
    order = student.get("info") if student else None
    cs_student = ClearanceSheet.objects.filter(myedu_id=myedu_id, order=order, id=cs_id).order_by('-issued_at').first()
    trajectories = request.stepper.cs_history_detail(cs_student)

    issuances = Issuance.objects.filter(cs_id=cs_id)

    if request.method == "POST":
        cs_student.type_choices = ClearanceSheet.SPEC
        cs_student.save()
        messages.success(request, "Восстановление данных выполнено успешно.")

    context = {
        "title": "История обходных листов",
        "navbar": "cs-done",
        "trajectories": trajectories,
        "cs_student": cs_student,
        "student": student,
        "issuances": issuances
    }
    return render(request, "teachers/steppers/cs-history.html", context)


@with_stepper
def cs_history_detail(request, cs_id):
    student = get_object_or_404(ClearanceSheet, id=cs_id)
    trajectories = request.stepper.cs_history_detail(student)

    context = {
        "student": student,
        "trajectories": trajectories,
        "navbar": "stepper"
    }
    return render(request, "teachers/steppers/cs-history-detail.html", context)


@with_stepper
def cs_detail(request, myedu_id):
    nav = request.session.get("cs-nav", "stepper")
    student = EntityCache.get_or_set(
        entity_id=myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": myedu_id,
        },
    )
    order = student.get("info") if student else None
    cs_student = ClearanceSheet.objects.filter(myedu_id=myedu_id, order=order).order_by('-issued_at').first()

    form = StudentTrajectoryForm()
    if request.method == "POST":
        form = StudentTrajectoryForm(request.POST)
        if form.is_valid():
            selected_stages = form.cleaned_data["stages"]
            success, message = request.stepper.create_trajectories_for_student(cs_student, selected_stages,
                                                                               request.user)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        else:
            messages.error(request, "Выберите этапы, которые обязательны к выполнению")

    trajectories = request.stepper.cs_history_detail(cs_student)
    context = {
        "student": student,
        "student_data": json.dumps(student),
        "cs_student": cs_student,
        "form": form,
        "trajectories": trajectories,
        "navbar": nav,
        "type_choices": TypeChoices.choices,
    }
    return render(request, "teachers/steppers/cs-detail.html", context)


@with_stepper
def cs_force(request, myedu_id):
    student = EntityCache.get_or_set(
        entity_id=myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": myedu_id,
        },
    )

    process_cs = ClearanceSheet.objects.filter(myedu_id=myedu_id, completed_at__isnull=True)

    order = student.get("info") if student else None
    cs_student = ClearanceSheet.objects.filter(myedu_id=myedu_id, completed_at__isnull=True, order=order).order_by(
        '-issued_at').first()

    form = StudentTrajectoryForm()
    if request.method == "POST":
        if "request-order" in request.POST:
            with transaction.atomic():
                clearance_sheets_to_update = ClearanceSheet.objects.filter(
                    myedu_id=myedu_id
                )
                clearance_sheets_to_update.update(last_active=False)
                cs_student = request.stepper.create_clearance_sheet(student, myedu_id)
                return redirect("stepper:cs-detail", myedu_id=cs_student.myedu_id)
        else:
            form = StudentTrajectoryForm(request.POST)
            if form.is_valid():
                selected_stages = form.cleaned_data["stages"]
                success, message = request.stepper.create_trajectories_for_student(cs_student, selected_stages,
                                                                                   request.user)
                if success:
                    messages.success(request, message)
                    return redirect("stepper:cs-detail", myedu_id=myedu_id)
                else:
                    messages.error(request, message)
            else:
                messages.error(request, "Выберите этапы, которые обязательны к выполнению")

    context = {
        "student": student,
        "cs_student": cs_student,
        "form": form,
        "process_cs": process_cs,
        "navbar": "stepper"
    }
    return render(request, "teachers/steppers/cs-force.html", context)


@with_stepper
def request_cs(request, myedu_id):
    if request.method == "POST":
        student_data = request.POST.get('student')
        try:
            student = json.loads(student_data)
        except json.JSONDecodeError:
            messages.error(request, "Некорректные данные студента")
            return redirect("stepper:cs-detail", myedu_id=myedu_id)

        cs_student = ClearanceSheet.objects.filter(myedu_id=myedu_id).first()

        if not cs_student:
            request.stepper.create_clearance_sheet(student, myedu_id)
            messages.success(request, "Обходной лист успешно создан")
        else:
            messages.error(request, "Студент не найден")
    return redirect("stepper:cs-detail", myedu_id=myedu_id)


@with_stepper
def order_done(request, myedu_id):
    if request.method == "POST":
        student_data = request.POST.get('student')
        spec_choice = request.POST.get('spec')
        type_choices = TypeChoices.OTHER
        if spec_choice == "on":
            type_choices = TypeChoices.SPEC
        try:
            student = json.loads(student_data)
        except json.JSONDecodeError:
            messages.error(request, "Некорректные данные студента")
            return redirect("stepper:cs-detail", myedu_id=myedu_id)

        cs_student = ClearanceSheet.objects.filter(myedu_id=myedu_id).order_by('-issued_at').first()
        has_trajectory = Trajectory.objects.filter(clearance_sheet=cs_student).exists() if cs_student else False

        if cs_student:
            if not has_trajectory and not cs_student.completed_at:
                cs_student.completed_at = make_aware(datetime.now())
                cs_student.type_choices = type_choices
                cs_student.save()
                messages.success(request, "Обходной лист успешно завершён")
            elif cs_student.completed_at:
                cs_student.type_choices = type_choices
                cs_student.save()
            else:
                messages.error(request, "Обходной лист находится в процессе прохождения")
        else:
            request.stepper.create_clearance_sheet(student, myedu_id, type_choices=type_choices, completed=True)
            messages.success(request, "Обходной лист успешно создан и завершён")

    return redirect("stepper:cs-detail", myedu_id=myedu_id)


@with_stepper
def step_remove(request, id):
    student = get_object_or_404(ClearanceSheet, id=id)
    if request.method == "POST":
        trajectories_ids = request.stepper.student_trajectories_only_ids(student)
        if not request.stepper.has_stage_status_trajectories(trajectories_ids):
            try:
                with transaction.atomic():
                    trajectories_ids.delete()
                    messages.success(request, "Траектория успешно удалена.")
            except Exception as _:
                messages.error(request, "Ошибка при удалении траектории")
        else:
            messages.error(request, "Невозможно удалить траектории, так как есть связанные записи")
    return redirect("stepper:cs-detail", myedu_id=student.myedu_id)


def step_rating(request, id, trajectory_id):
    trajectory = get_object_or_404(Trajectory, id=trajectory_id)
    clearance_sheet = get_object_or_404(ClearanceSheet, id=id)
    trajectory.update_at = make_aware(datetime.now())
    trajectory.save()

    type_param = request.GET.get('type')
    if type_param == STUDENT_CS:
        return redirect("stepper:cs-detail", myedu_id=clearance_sheet.myedu_id)
    elif type_param == TEACHER_CS:
        return redirect("stepper:teacher-cs-detail", myedu_id=clearance_sheet.myedu_id)
    else:
        raise Http404


@with_stepper
def debts(request):
    request.session['access'] = 'stepper'
    employee = request.stepper.get_employee_for_user(request.user, TemplateStep.STUDENT)
    students_qs = []

    search_query = request.GET.get('search')

    status_param = None
    if request.method == "POST":
        status_param = int(request.POST.get("status"))
        if status_param == 3:
            return redirect("stepper:debts-history")

    if employee:
        students_qs = request.stepper.get_cs_employees_by_category(
            employee.template_stage,
            category=TemplateStep.STUDENT,
            status_filter=status_param
        )
        if search_query:
            students_qs = students_qs.filter(
                Q(student_fio__icontains=search_query) | Q(myedu_id__icontains=search_query)
            )

    paginator = Pagination(request, students_qs)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    context = {
        "navbar": "stepper",
        "students": students,
        "employee": employee
    }
    return render(request, "teachers/steppers/debts.html", context)


@with_stepper
def debts_history(request):
    request.session['access'] = 'stepper'
    employee = request.stepper.get_employee_for_user(request.user, TemplateStep.STUDENT)
    students_qs = []

    search_query = request.GET.get('search')

    if employee:
        students_qs = request.stepper.get_cs_history_employees_by_category(
            employee.template_stage
        )
        if search_query:
            students_qs = students_qs.filter(
                Q(student_fio__icontains=search_query) | Q(myedu_id__icontains=search_query)
            )

    paginator = Pagination(request, students_qs)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    context = {
        "navbar": "stepper-history",
        "history": True,
        "students": students,
        "employee": employee
    }
    return render(request, "teachers/steppers/debts.html", context)


@with_stepper
def debts_comment(request, id):
    trajectory = get_object_or_404(
        Trajectory.objects.select_related('clearance_sheet'),
        id=id
    )

    student = EntityCache.get_or_set(
        entity_id=trajectory.clearance_sheet.myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": trajectory.clearance_sheet.myedu_id,
        },
    )

    sync_myedu = True
    if not student:
        sync_myedu = False
        student = ClearanceSheet.objects.filter(id=trajectory.clearance_sheet_id).first()
    form = StageStatusForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            end_flag = request.POST.get("end")
            trajectory_detail = request.stepper.save_stage_status(
                form=form,
                trajectory=trajectory,
                user=request.user,
                end_flag=end_flag
            )
            if trajectory_detail:
                messages.success(request, "Данные успешно сохранены.")
                if trajectory_detail.completed_at:
                    return redirect("stepper:debts")
            else:
                messages.error(request, "Произошла ошибка при сохранении данных.")
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")

    context = {
        "navbar": "stepper",
        "trajectory": trajectory,
        "comments": StageStatus.objects.filter(trajectory=trajectory),
        "form": form,
        "student": student,
        "sync_myedu": sync_myedu
    }
    return render(request, "teachers/steppers/debts-comment.html", context)


@with_stepper
def debts_comment_history(request, id):
    trajectory = get_object_or_404(
        Trajectory.objects.select_related('clearance_sheet'),
        id=id
    )
    student = EntityCache.get_or_set(
        entity_id=trajectory.clearance_sheet.myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": trajectory.clearance_sheet.myedu_id,
        },
    )

    sync_myedu = True
    if not student:
        sync_myedu = False
        student = ClearanceSheet.objects.filter(id=trajectory.clearance_sheet_id).first()
    form = StageStatusForm(request.POST or None)

    context = {
        "navbar": "stepper-history",
        "history": True,
        "trajectory": trajectory,
        "comments": StageStatus.objects.filter(trajectory=trajectory),
        "form": form,
        "student": student,
        "sync_myedu": sync_myedu
    }
    return render(request, "teachers/steppers/debts-comment.html", context)


@with_stepper
def teachers(request):
    request.session['access'] = 'teacher'

    search = None
    if request.method == "POST":
        search = request.POST.get("search", "")

    teachers_qs = MyEduService.get_stepper_data_from_api(TEACHER_STEPPER_URL, search)

    paginator = Pagination(request, teachers_qs or [])
    page_number = request.GET.get('page', 1)
    teacher_list = paginator.pagination(page_number)

    context = {
        "title": "Преподаватели с задолженностью по данным MyEDU",
        "navbar": "teachers",
        "objects": teacher_list
    }

    return render(request, "teachers/steppers/teachers.html", context)


@with_stepper
def teacher_cs_detail(request, myedu_id):
    teacher = next(iter(MyEduService.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=myedu_id)),
                   None)
    if request.method == "POST":
        if teacher:
            student_info = StudentInfo(
                myedu_id=teacher['student_id'],
                full_name=teacher['student_fio'],
                faculty=teacher['faculty_name'],
                faculty_id=teacher['faculty_id'],
                specialty=teacher['speciality_name'],
                specialty_id=teacher['speciality_id']
            )
            try:
                clearance_sheet = request.stepper.create_clearance_sheet_with_trajectories(
                    student=student_info,
                    assigned_by=request.user
                )
                messages.success(request, f"Обходной лист #{clearance_sheet.id} успешно создан.")
            except ClearanceCreationError as e:
                messages.error(request, str(e))
    clearance_sheet = request.stepper.get_cs_by_myeduid_or_none(myedu_id)
    trajectories = request.stepper.cs_history_detail(clearance_sheet)

    context = {
        "teacher": teacher,
        "navbar": "teachers",
        "clearance_sheet": clearance_sheet,
        "trajectories": trajectories
    }
    return render(request, "teachers/steppers/teacher-cs-detail.html", context)


@with_stepper
def teachers_cs(request):
    teacher = next(
        iter(MyEduService.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=request.user.myedu_id)),
        None)

    search_query = request.GET.get('search')
    teacher_list = request.stepper.get_open_clearance_sheets_with_stage(search_query, type_param=TEACHER_CS,
                                                                        faculty_id=teacher)

    paginator = Pagination(request, teacher_list)
    page_number = request.GET.get('page', 1)
    teachers_qs = paginator.pagination(page_number)

    context = {
        "title": "Перечень сформированных обходных листов",
        "teachers": teachers_qs,
        "navbar": "teachers"
    }
    return render(request, "teachers/steppers/teachers-cs.html", context)


@with_stepper
def teacher_debts(request):
    request.session['access'] = 'teacher'
    employee = request.stepper.get_employee_for_user(request.user, TemplateStep.TEACHER)
    cs_employee = None

    if employee:
        cs_employee = request.stepper.get_cs_employees_by_category(
            employee.template_stage,
            category=TemplateStep.TEACHER
        )

    context = {
        "navbar": "teachers",
        "teachers": cs_employee,
        "employee": employee
    }
    return render(request, "teachers/steppers/teacher-debts.html", context)


@with_stepper
def teacher_debt_comments(request, id):
    trajectory = get_object_or_404(
        Trajectory.objects.select_related('clearance_sheet'),
        id=id
    )
    form = StageStatusForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            end_flag = request.POST.get("end")
            trajectory_detail = request.stepper.save_stage_status(
                form=form,
                trajectory=trajectory,
                user=request.user,
                end_flag=end_flag
            )
            if trajectory_detail:
                messages.success(request, "Данные успешно сохранены.")
                if trajectory_detail.completed_at:
                    return redirect("stepper:teacher-debts")
            else:
                messages.error(request, "Произошла ошибка при сохранении данных.")
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")

    context = {
        "navbar": "stepper",
        "trajectory": trajectory,
        "comments": StageStatus.objects.filter(trajectory=trajectory),
        "form": form
    }
    return render(request, "teachers/steppers/debts-comment.html", context)


def diploma_create_ajax(request):
    student_id = request.GET.get('student_id') or request.POST.get('student_id')
    faculty_id = request.GET.get('faculty_id') or request.POST.get('faculty_id')
    speciality_id = request.GET.get('speciality_id') or request.POST.get('speciality_id')

    if request.method == 'POST':
        form = DiplomaForm(request.POST)
        faculty = Faculty.objects.filter(myedu_faculty_id=faculty_id).first()
        speciality = Speciality.objects.filter(myedu_spec_id=speciality_id).first()
        if form.is_valid():
            diploma = form.save(commit=False)
            diploma.student = student_id
            diploma.faculty = faculty
            diploma.speciality = speciality

            diploma.save()

            return JsonResponse({'success': True})
        else:
            form_html = render(request, 'teachers/steppers/partials/partial_diploma_form.html',
                               {'form': form}).content.decode('utf-8')
            return JsonResponse({'success': False, 'form_html': form_html})
    else:
        form = DiplomaForm()
        form_html = render(request, 'teachers/steppers/partials/partial_diploma_form.html',
                           {'form': form}).content.decode('utf-8')
        return JsonResponse({'form_html': form_html})


def qr_code_status(request, qr_id):
    request.stepper = StepperService()
    clearance_sheet = ClearanceSheet.objects.filter(id=qr_id).first()
    student = None
    trajectories = None

    if clearance_sheet:
        student = EntityCache.get_or_set(
            entity_id=clearance_sheet.myedu_id,
            fetch_func=MyEduService.get_stepper_data_from_api,
            fetch_kwargs={
                "url": STUDENT_STEPPER_URL,
                "search": clearance_sheet.myedu_id,
            },
        )

        trajectories = request.stepper.get_trajectories_with_annotations(clearance_sheet)

    context = {
        "student": student,
        "cs": clearance_sheet,
        "trajectories": trajectories,
    }
    return render(request, "teachers/steppers/reports/qr-code-status.html", context)


@with_stepper
def vacation_certificate_students(request):
    students_qs = []
    search = ""
    if request.method == "POST":
        search = request.POST.get("search", "")

        students_qs = MyEduService.get_vc_data_from_api(VC_URL, search)

    context = {
        "navbar": "vacation-certificate",
        "title": "Каникулярная справка",
        "search": search,
        "students": students_qs
    }
    return render(request, "teachers/steppers/vacation/vacation_certificate_students.html", context)


def vacation_certificate_view(request):
    current_year = datetime.now().year
    student_data = request.session.get('certificate_data')

    if not student_data:
        return redirect('stepper:vacation-certificate-students')

    lang = student_data.get('lang', 'ru')
    template_name = "teachers/steppers/vacation/vacation_certificate.html"
    if lang == 'en':
        template_name = "teachers/steppers/vacation/vacation_certificate_en.html"
    elif lang == 'kg':
        template_name = "teachers/steppers/vacation/vacation_certificate_ky.html"

    if request.method == "POST":
        cert = VacationCertificate.objects.create(
            student_id=request.POST.get('student_id'),
            student_name=request.POST.get('student_name'),
            birth_info=request.POST.get('birth_info'),
            faculty_info=request.POST.get('faculty_info'),
            specialty_info=request.POST.get('specialty_info'),
            study_form=request.POST.get('study_form'),
            payment_form=request.POST.get('payment_form'),
            study_period=request.POST.get('study_period'),
            current_course=request.POST.get('current_course'),
            order_info=request.POST.get('order_info'),
            fall_semester=request.POST.get('fall_semester'),
            spring_semester=request.POST.get('spring_semester'),
            vacation_period=request.POST.get('vacation_period'),
            edu_year=request.POST.get('edu_year'),
            lang=lang,
            created_by=request.user
        )
        student_data['is_saved'] = True
        student_data['cert_id'] = cert.id
        request.session['certificate_data'] = student_data
        request.session.modified = True
        return redirect('stepper:vacation-certificate-view')

    if student_data.get('is_saved') and student_data.get('cert_id'):
        cert = get_object_or_404(VacationCertificate, id=student_data.get('cert_id'))

        saved_lang = cert.lang
        template_name = "teachers/steppers/vacation/vacation_certificate.html"
        if saved_lang == 'en':
            template_name = "teachers/steppers/vacation/vacation_certificate_en.html"
        elif saved_lang == 'kg':
            template_name = "teachers/steppers/vacation/vacation_certificate_ky.html"

        return render(request, template_name, {
            'is_saved': True, 'cert_number': cert.cert_number, 'student_id': cert.student_id,
            'student_name': cert.student_name, 'birth_info': cert.birth_info,
            'faculty_info': cert.faculty_info, 'specialty_info': cert.specialty_info,
            'study_form': cert.study_form, 'payment_form': cert.payment_form,
            'study_period': cert.study_period, 'current_course': cert.current_course,
            'order_info': cert.order_info, 'fall_semester': cert.fall_semester,
            'spring_semester': cert.spring_semester, 'vacation_period': cert.vacation_period,
            'edu_year': cert.edu_year,
            "title": "Каникулярная справка", "navbar": "vacation-certificate"
        })

    c, spec, b_day = student_data.get('course', ''), student_data.get('speciality_name', ''), student_data.get(
        'birthday', '')
    m_info, m_date = student_data.get('movement_info', ''), student_data.get('movement_date', '')

    birth_info = ""
    order_info = ""
    current_course = ""
    course = ""
    fall_semester = ""
    spring_semester = ""
    vacation_period = ""
    specialty_info = f"«{spec}»"

    if lang == 'ru':
        birth_info = f"{b_day} года рождения"
        current_course = f"{c} курсе"
        course = f"{c} курса"
        order_info = f"приказом №{m_info} от {m_date}"
        fall_semester = f"с 01 сентября {current_year - 1} года по 24 января {current_year} года"
        spring_semester = f"с 26 января {current_year} года по 13 июня {current_year} года"
        vacation_period = f"с 15 июня {current_year} года по 31 августа {current_year} года"
    elif lang == 'en':
        birth_info = f"{b_day}"
        current_course = f"{c}th year of study"
        course = f"{c}-year"
        order_info = f"Order No. {m_info} dated {m_date}"
        fall_semester = f"from September 1, {current_year - 1} to January 24, {current_year}"
        spring_semester = f"from January 26, {current_year} to June 13, {current_year}"
        vacation_period = f"from June 15, {current_year} to August 31, {current_year}"
    elif lang == 'kg':
        birth_info = f"{b_day}-жылы туулган"
        current_course = f"{c}-курста окуйт"
        course = f"{c}-курстун"
        order_info = f"№{m_info}"
        fall_semester = f"{current_year - 1}-жылдын 1-сентябрынан {current_year}-жылдын 24-январына чейин"
        spring_semester = f"{current_year}-жылдын 26-январынан {current_year}-жылдын 13-июнуна чейин"
        vacation_period = f"{current_year}-жылдын 15-июнунан {current_year}-жылдын 31-августуна чейин"

    context = {
        'is_saved': False, 'student_id': student_data.get('student_id'),
        'student_name': student_data.get('student_fio'), 'payment_form': student_data.get('payment_form'),
        'study_period': student_data.get('license_year'), 'faculty_info': student_data.get('faculty_name'),
        'study_form': student_data.get('edu_form'), 'lang': lang,
        'birth_info': birth_info, 'specialty_info': specialty_info,
        'current_course': current_course, 'course': course,
        'order_info': order_info,
        'fall_semester': fall_semester,
        'spring_semester': spring_semester,
        'vacation_period': vacation_period,
        'edu_year': student_data.get('edu_year'),
        "title": "Каниулярная справка", "navbar": "vacation-certificate"
    }
    return render(request, template_name, context)


def vacation_certificate_history(request):
    vc_qs = VacationCertificate.objects.all().select_related('created_by').order_by('-id', 'student_name')
    filterset = VCFilter(request.POST or None, queryset=vc_qs)
    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)

    context = {
        "title": "Каникулярная справка - История",
        "navbar": "vacation-certificate",
        "vc_list": paginator.pagination_with_filters(page_number)
    }
    return render(request, "teachers/steppers/vacation/vacation_certificate_history.html", context)


def vacation_certificate_session(request):
    if request.method == "POST":
        lang = request.POST.get('lang', 'kg')

        student_data = {
            'student_id': request.POST.get('student_id'),
            'student_fio': request.POST.get('student_fio'),
            'birthday': request.POST.get('birthday'),
            'course': request.POST.get('course'),

            'movement_date': request.POST.get('movement_date'),
            'movement_info': request.POST.get('movement_info'),

            'faculty_name': request.POST.get(f'faculty_{lang}'),
            'speciality_name': request.POST.get(f'speciality_{lang}'),
            'edu_form': request.POST.get(f'edu_form_{lang}'),
            'payment_form': request.POST.get(f'payment_form_{lang}'),
            'license_year': request.POST.get(f'license_year_{lang}'),

            'edu_year': request.POST.get('edu_year'),
            'lang': lang,
            'is_saved': False,
            'cert_id': None
        }

        request.session['certificate_data'] = student_data
        return redirect('stepper:vacation-certificate-view')

    return redirect('stepper:vacation-certificate-students')


def get_cs_filtered_paginated(request, queryset):
    filterset = CSFilter(request.GET or None, queryset=queryset)
    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)
    paginated = paginator.pagination_with_filters(page_number)
    return paginated, filterset.form


def get_cs_history_filtered_paginated(request, queryset):
    filterset = CsHistoryFilter(request.GET or None, queryset=queryset)
    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)
    paginated = paginator.pagination_with_filters(page_number)
    return paginated, filterset.form
