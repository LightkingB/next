import json
from datetime import datetime

from django.contrib import messages
from django.db import transaction, DatabaseError
from django.db.models import Q, OuterRef, Exists, Subquery, F, Value, CharField
from django.db.models.functions import Concat
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from bsadmin.consts import STADMIN
from bsadmin.models import CustomUser, Faculty, Speciality
from stepper.choices import TypeChoices
from stepper.consts import STUDENT_STEPPER_URL, TEACHER_STEPPER_URL, STUDENT_CS, TEACHER_CS
from stepper.decorators import with_stepper
from stepper.entity import StudentInfo
from stepper.exceptions import ClearanceCreationError
from stepper.filters import StageEmployeeStudentFilter, CSFilter
from stepper.forms import StudentTrajectoryForm, StageStatusForm, IssuanceForm, StageEmployeeForm, DiplomaForm
from stepper.models import ClearanceSheet, Trajectory, StageStatus, TemplateStep, StageEmployee, Issuance, \
    IssuanceHistory, Diploma
from utils.filter_pagination import Pagination


def route(request):
    if not request.user.is_authenticated:
        return redirect("integrator:next-teacher-login")
    roles = set(request.user.roles.values_list("name", flat=True))
    if STADMIN in roles:
        return redirect("stepper:index")
    return HttpResponse("403 - Forbidden")


@with_stepper
def cs_index(request):
    request.session['access'] = 'stepper'

    if not request.user.is_authenticated:
        return redirect("integrator:next-teacher-login")

    if request.method == "POST":
        search = request.POST.get("search", "")
        faculty_id = request.POST.get("faculty_id", 0)
        specialty_id = request.POST.get("specialty_id", 0)
        students_qs = request.stepper.get_stepper_data_from_api(STUDENT_STEPPER_URL, search, faculty_id, specialty_id)
    else:
        students_qs = request.stepper.get_stepper_data_from_api(STUDENT_STEPPER_URL)

    student_ids = [str(student["student_id"]) for student in students_qs]

    existing_ids = set(
        ClearanceSheet.objects.filter(myedu_id__in=student_ids)
        .values_list('myedu_id', flat=True)
    )
    for student in students_qs:
        student["exist"] = str(student["student_id"]) in existing_ids

    paginator = Pagination(request, students_qs or [])
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    faculties = request.bs.active_faculties()

    context = {
        "title": "Студенты с задолженностями по данным MyEDU",
        "navbar": "stepper",
        "objects": students,
        "faculties": faculties,
        "success": True
    }

    return render(request, "teachers/steppers/index.html", context)


def spec(request):
    request.session['access'] = 'stepper'
    if not request.user.is_authenticated:
        return redirect("integrator:next-teacher-login")

    issuance_subquery = Issuance.objects.filter(
        student=OuterRef('myedu_id'),
        type_choices=TypeChoices.SPEC,
        cs_id=OuterRef('id')
    )

    qs = ClearanceSheet.objects.annotate(
        has_spec=Exists(issuance_subquery)
    ).filter(has_spec=False, completed_at__isnull=False, type_choices=TypeChoices.SPEC).order_by('-id')

    filterset = CSFilter(request.GET or None, queryset=qs)

    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination_with_filters(page_number)

    context = {
        "title": "Студенты без задолженности по данным MyEDU",
        "navbar": "spec",
        "objects": students,
        "form": filterset.form,
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

    students_qs = request.stepper.get_stepper_data_from_api(
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


def archive(request):
    request.session['access'] = 'stepper'
    if not request.user.is_authenticated:
        return redirect("integrator:next-teacher-login")

    issuance_subquery = Issuance.objects.filter(
        student=OuterRef('myedu_id'),
        type_choices=TypeChoices.OTHER,
        cs_id=OuterRef('id')
    )

    qs = ClearanceSheet.objects.annotate(
        has_archive=Exists(issuance_subquery)
    ).filter(has_archive=False, completed_at__isnull=False).order_by('-id')

    filterset = CSFilter(request.GET or None, queryset=qs)

    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination_with_filters(page_number)

    context = {
        "title": "Студенты без задолженности по данным MyEDU",
        "navbar": "archive",
        "objects": students,
        "form": filterset.form,
    }
    return render(request, "teachers/steppers/archive.html", context)


def spec_history(request):
    issuance_subquery = Issuance.objects.filter(
        student=OuterRef('myedu_id'),
        type_choices=TypeChoices.SPEC,
        cs_id=OuterRef('id')
    )

    issuance_id_subquery = issuance_subquery.values('id')[:1]

    qs = ClearanceSheet.objects.annotate(
        issuance_id=Subquery(issuance_id_subquery),
        has_spec=Exists(issuance_subquery)
    ).filter(has_spec=True, completed_at__isnull=False).order_by('-id')

    filterset = CSFilter(request.GET or None, queryset=qs)

    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination_with_filters(page_number)

    context = {
        "title": "История студентов без задолженности по данным MyEDU",
        "navbar": "spec-history",
        "objects": students,
        "form": filterset.form,
        "history": True
    }
    return render(request, "teachers/steppers/spec.html", context)


def archive_history(request):
    issuance_subquery = Issuance.objects.filter(
        student=OuterRef('myedu_id'),
        type_choices=TypeChoices.OTHER,
        cs_id=OuterRef('id')
    )

    issuance_id_subquery = issuance_subquery.values('id')[:1]

    qs = ClearanceSheet.objects.annotate(
        issuance_id=Subquery(issuance_id_subquery),
        has_archive=Exists(issuance_subquery)
    ).filter(has_archive=True, completed_at__isnull=False).order_by('-id')

    filterset = CSFilter(request.GET or None, queryset=qs)

    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination_with_filters(page_number)

    context = {
        "title": "История студентов без задолженности по данным MyEDU",
        "navbar": "archive-history",
        "objects": students,
        "form": filterset.form,
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
        "navbar": "archive",
        "students": students,
        "faculties": faculties
    }
    return render(request, "teachers/steppers/archive-avn.html", context)


@with_stepper
def spec_part(request, id, myedu_id):
    has_active_cs = request.stepper.has_active_cs(myedu_id)

    student = get_object_or_404(ClearanceSheet, myedu_id=myedu_id, id=id)

    if request.method == "POST":
        form = IssuanceForm(request.POST, request.FILES)
        signature_base64 = request.POST.get('signature')
        instance, error = request.stepper.create_issuance_form(
            form=form,
            user=request.user,
            signature_base64=signature_base64,
            myeduid=myedu_id,
            cs_id=student.id,
            faculty_id=student.myedu_faculty_id,
            specialty_id=student.myedu_spec_id,
            type=Issuance.SPEC
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Данные успешно сохранены.")
            form = IssuanceForm()
    else:
        form = IssuanceForm()

    issuance = Issuance.objects.filter(student=myedu_id, type_choices=Issuance.SPEC).first()
    diploma = Diploma.objects.filter(student=myedu_id, sync=False).first()
    context = {
        "navbar": "spec",
        "has_active_cs": has_active_cs,
        "form": form,
        "student": student,
        "issuance": issuance,
        "diploma": diploma
    }
    return render(request, "teachers/steppers/spec-part.html", context)


@with_stepper
def archive_part(request, id, myedu_id):
    has_active_cs = request.stepper.has_active_cs(myedu_id)

    student = get_object_or_404(ClearanceSheet, myedu_id=myedu_id, id=id)

    if request.method == "POST":
        form = IssuanceForm(request.POST, request.FILES)
        signature_base64 = request.POST.get('signature')
        instance, error = request.stepper.create_issuance_form(
            form=form,
            user=request.user,
            signature_base64=signature_base64,
            myeduid=myedu_id,
            cs_id=student.id,
            faculty_id=student.myedu_faculty_id,
            specialty_id=student.myedu_spec_id,
            type=Issuance.OTHER
        )
        if error:
            messages.error(request, error)
        else:
            messages.success(request, "Данные успешно сохранены.")
            form = IssuanceForm()
    else:
        form = IssuanceForm()

    issuance = Issuance.objects.filter(student=myedu_id, type_choices=Issuance.OTHER).first()
    context = {
        "navbar": "archive",
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
            issuance = Issuance.objects.select_for_update().filter(student=myedu_id, type_choices=Issuance.SPEC).first()
            if not issuance:
                messages.error(request, "Не найдено подходящей записи для выдачи дубликата")
                return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)

            with transaction.atomic():
                issuance.status = Issuance.DOUBLE
                issuance.save()
                IssuanceHistory.objects.create(student=myedu_id, history=history, cs=id, type_choices=Issuance.SPEC)
                messages.success(request, "Обработка данных завершена успешно. Дубликат диплома выдан.")

        except DatabaseError:
            messages.error(request, "Не удалось выдать дубликат диплома")

    return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)


@with_stepper
def spec_part_remove(request, id, myedu_id):
    if request.method == "POST":
        try:
            student = ClearanceSheet.objects.filter(id=id, myedu_id=myedu_id).first()
            issuance = Issuance.objects.select_for_update().filter(student=myedu_id, type_choices=Issuance.SPEC).first()

            with transaction.atomic():
                if issuance:
                    IssuanceHistory.objects.filter(student=myedu_id, type_choices=Issuance.SPEC, cs=student.id).delete()
                    issuance.delete()

                messages.success(request, "Информация о дипломе успешно удалена")

        except DatabaseError:
            messages.error(request, "Ошибка при выдаче диплома-дубликата")

    return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)


@with_stepper
def spec_sync(request, id, myedu_id):
    if request.method == "POST":
        try:
            diploma = Diploma.objects.filter(student=myedu_id, sync=False).first()
            issuance = Issuance.objects.filter(student=myedu_id, type_choices=Issuance.SPEC).first()

            with transaction.atomic():
                if not issuance and diploma:
                    print("yes")
                    Issuance.objects.create(
                        student=diploma.student,
                        cs_id=id,
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
            print(e)
            messages.error(request, "Ошибка при синхронизации")

    return redirect("stepper:spec-part", id=id, myedu_id=myedu_id)


@with_stepper
def archive_part_remove(request, id, myedu_id):
    if request.method == "POST":
        try:
            student = ClearanceSheet.objects.filter(id=id, myedu_id=myedu_id).first()
            issuance = Issuance.objects.select_for_update().filter(student=myedu_id,
                                                                   type_choices=Issuance.OTHER).first()

            with transaction.atomic():
                if issuance:
                    IssuanceHistory.objects.filter(student=myedu_id, type_choices=Issuance.OTHER,
                                                   cs=student.id).delete()
                    issuance.delete()

                messages.success(request, "Информация о дипломе успешно удалена")

        except DatabaseError:
            messages.error(request, "Ошибка при выдаче диплома-дубликата")

    return redirect("stepper:archive-part", id=id, myedu_id=myedu_id)


@with_stepper
def load_specialities(request):
    faculty = request.bs.get_first_active_faculty(request.GET.get('faculty_id'))
    specialities = request.bs.faculty_specialities_with_values(faculty.id if faculty else 0)
    return JsonResponse(list(specialities), safe=False)


@with_stepper
def stage_employee(request):
    filterset = StageEmployeeStudentFilter(request.GET or None, queryset=request.stepper.get_stepper_employees())

    paginator = Pagination(request, filterset)
    page_number = request.GET.get('page', 1)
    employees = paginator.pagination_with_filters(page_number)

    context = {
        "navbar": "roles",
        "employees": employees,
        "form": filterset.form,
        "title": "Связь сотрудника с этапом процесса"
    }
    return render(request, "teachers/steppers/stage-employee.html", context)


def stage_employee_create(request):
    if request.method == 'POST':
        form = StageEmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('stepper:stage-employee')
        else:
            messages.error(request,
                           "Этот пользователь уже назначен. Пожалуйста, укажите другого пользователя.")
    else:
        form = StageEmployeeForm()
    return render(request, 'teachers/steppers/stage-employee-form.html', {
        'form': form,
        'is_edit': False,
        'navbar': 'roles'
    })


def stage_employee_update(request, pk):
    obj = get_object_or_404(StageEmployee, pk=pk)
    if request.method == 'POST':
        form = StageEmployeeForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect('stepper:stage-employee')
        else:
            messages.error(request,
                           "Этот пользователь уже назначен. Пожалуйста, укажите другого пользователя.")
    else:
        form = StageEmployeeForm(instance=obj)
    return render(request, 'teachers/steppers/stage-employee-form.html', {
        'form': form,
        'is_edit': True,
        'navbar': 'roles'
    })


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
def cs(request):
    search_query = request.GET.get('search')
    students_qs = request.stepper.get_open_clearance_sheets_with_stage(search_query, type_param=STUDENT_CS)

    paginator = Pagination(request, students_qs)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    stages = TemplateStep.objects.filter(category=TemplateStep.STUDENT, order__gt=0).select_related('stage')

    context = {
        "title": "Перечень сформированных обходных листов",
        "students": students,
        "navbar": "cs",
        "stages": stages
    }
    return render(request, "teachers/steppers/cs.html", context)


@with_stepper
def cs_done(request):
    search_query = request.GET.get('search')
    students_qs = request.stepper.cs_done_list(search_query)

    paginator = Pagination(request, students_qs)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    context = {
        "title": "История - Перечень завершенных обходных листов",
        "students": students,
        "navbar": "cs-done",
        "history": True
    }
    return render(request, "teachers/steppers/cs.html", context)


@with_stepper
def cs_debt_stage(request, stage):
    search_query = request.GET.get('search')
    students_qs = request.stepper.get_open_clearance_sheets_with_stage_filter(stage, search_query)

    paginator = Pagination(request, students_qs)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    stages = TemplateStep.objects.filter(category=TemplateStep.STUDENT, order__gt=0).select_related('stage')

    current_stage = TemplateStep.objects.filter(id=stage).select_related('stage').first()

    context = {
        "title": "Перечень сформированных обходных листов",
        "students": students,
        "navbar": "cs",
        "stage": True,
        "current_stage": current_stage,
        "stages": stages
    }
    return render(request, "teachers/steppers/cs.html", context)


@with_stepper
def cs_issuance(request):
    search_id = request.GET.get('search')
    if search_id:
        issuance_qs = Issuance.objects.filter(Q(id=search_id) | Q(cs_id=search_id)).select_related('faculty',
                                                                                                   'speciality').order_by(
            'id')
    else:
        issuance_qs = Issuance.objects.all().select_related('faculty', 'speciality').order_by('id')

    paginator = Pagination(request, issuance_qs)
    page_number = request.GET.get('page', 1)
    issuance = paginator.pagination(page_number)

    context = {
        "title": "Перечень студентов, получивших документы",
        "issuance": issuance,
        "navbar": "issuance"
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

    student = next(
        iter(request.stepper.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=clearance_sheet.myedu_id)),
        None
    )

    latest_status_qs = StageStatus.objects.filter(
        trajectory=OuterRef('pk')
    ).order_by('-created_at')

    trajectories = (
        Trajectory.objects
        .filter(clearance_sheet=clearance_sheet)
        .select_related('template_stage', 'template_stage__stage', 'assigned_by')
        .annotate(
            last_comment=Subquery(
                latest_status_qs.values('comment_text')[:1]
            ),
            last_processed_by_id=Subquery(
                latest_status_qs.values('processed_by')[:1]
            ),
        )
    )
    trajectories = trajectories.annotate(
        last_processed_by_name=Subquery(
            CustomUser.objects
            .filter(id=OuterRef('last_processed_by_id'))
            .annotate(
                full_name=Concat(
                    F('first_name'), Value(' '),
                    F('last_name'), Value(' '),
                    F('fathers_name')
                )
            )
            .values('full_name')[:1],
            output_field=CharField()
        )
    )

    context = {
        "title": "История - Перечень завершенных обходных листов",
        "student": student,
        "cs": clearance_sheet,
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
def cs_history(request, myedu_id):
    student = next(
        iter(request.stepper.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=myedu_id)),
        None
    )
    order = student.get("info") if student else None
    cs_student = ClearanceSheet.objects.filter(myedu_id=myedu_id, order=order).order_by('-issued_at').first()
    trajectories = request.stepper.cs_history_detail(cs_student)
    context = {
        "title": "История обходных листов",
        "navbar": "cs",
        "trajectories": trajectories,
        "cs_student": cs_student,
        "student": student
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
    student = next(
        iter(request.stepper.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=myedu_id)),
        None
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
        "navbar": "stepper",
        "type_choices": TypeChoices.choices,
    }
    return render(request, "teachers/steppers/cs-detail.html", context)


@with_stepper
def cs_force(request, myedu_id):
    student = next(
        iter(request.stepper.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=myedu_id)),
        None)

    process_cs = ClearanceSheet.objects.filter(myedu_id=myedu_id, completed_at__isnull=True)

    order = student.get("info") if student else None
    cs_student = ClearanceSheet.objects.filter(myedu_id=myedu_id, completed_at__isnull=True, order=order).order_by(
        '-issued_at').first()

    form = StudentTrajectoryForm()
    if request.method == "POST":
        if "request-order" in request.POST:
            cs_student = ClearanceSheet.objects.create(
                myedu_id=myedu_id,
                student_fio=student.get('student_fio', ''),
                myedu_faculty_id=student.get('faculty_id', 0),
                myedu_faculty=student.get('faculty_name', ''),
                myedu_spec_id=student.get('speciality_id', 0),
                myedu_spec=student.get('speciality_name', ''),
                order_status=student.get('id_movement_info', ''),
                order=student.get('info', ''),
                order_date=student.get('date_movement', '')
            )
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
            ClearanceSheet.objects.create(
                myedu_id=myedu_id,
                student_fio=student.get('student_fio', ''),
                myedu_faculty_id=student.get('faculty_id', 0),
                myedu_faculty=student.get('faculty_name', ''),
                myedu_spec_id=student.get('speciality_id', 0),
                myedu_spec=student.get('speciality_name', ''),
                order_status=student.get('id_movement_info', ''),
                order=student.get('info', ''),
                order_date=student.get('date_movement', '')
            )
            messages.success(request, "Обходной лист успешно создан")
        else:
            messages.error(request, "Студент не найден")
    return redirect("stepper:cs-detail", myedu_id=myedu_id)


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
            ClearanceSheet.objects.create(
                myedu_id=myedu_id,
                student_fio=student.get('student_fio', ''),
                myedu_faculty_id=student.get('faculty_id', 0),
                myedu_faculty=student.get('faculty_name', ''),
                myedu_spec_id=student.get('speciality_id', 0),
                myedu_spec=student.get('speciality_name', ''),
                order_status=student.get('id_movement_info', ''),
                order=student.get('info', ''),
                order_date=student.get('date_movement', ''),
                type_choices=type_choices,
                completed_at=make_aware(datetime.now())
            )
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
            messages.error(request, "Невозможно удалить траекторию, так как есть связанные записи")
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
    students_with_stlib = []

    search_query = request.GET.get('search')

    if employee:
        students_with_stlib = request.stepper.get_cs_employees_by_category(
            employee.template_stage,
            category=TemplateStep.STUDENT
        )
        if search_query:
            students_with_stlib = students_with_stlib.filter(
                Q(student_fio__icontains=search_query) | Q(myedu_id__icontains=search_query)
            )

    paginator = Pagination(request, students_with_stlib)
    page_number = request.GET.get('page', 1)
    students = paginator.pagination(page_number)

    context = {
        "navbar": "stepper",
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
        "form": form
    }
    return render(request, "teachers/steppers/debts-comment.html", context)


@with_stepper
def teachers(request):
    request.session['access'] = 'teacher'

    search = None
    if request.method == "POST":
        search = request.POST.get("search", "")

    teachers_qs = request.stepper.get_stepper_data_from_api(TEACHER_STEPPER_URL, search)

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
    teacher = next(iter(request.stepper.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=myedu_id)),
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
        iter(request.stepper.get_stepper_data_from_api(url=STUDENT_STEPPER_URL, search=request.user.myedu_id)),
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
