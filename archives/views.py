import requests
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from archives.forms import ActsForm, CustomFacultyForm
from archives.models import EduForm, Acts, CategoryForm, StudentsAct
from bsadmin.consts import API_URL
from bsadmin.models import Faculty
from stepper.models import EduYear
from utils.filter_pagination import Pagination

from datetime import date


def act_index(request):
    faculties = Faculty.objects.all().order_by('title')
    edu_form = EduForm.objects.all()

    prefetch_students = Prefetch("studentsact_set",
                                 queryset=StudentsAct.objects.only("id", "student_fio", "myedu_id", "act_id"))

    q = request.GET.get('q')

    acts = (
        Acts
        .objects
        .all()
        .prefetch_related(prefetch_students)
        .select_related('faculty', 'edu_form', 'confirm_user', 'created_user', 'edu_year', 'category_form')
        .order_by('is_confirm', '-id')
    )
    if q == '1':
        acts = acts.filter(is_confirm=False)
    elif q == '2':
        acts = acts.filter(is_confirm=True)

    page_number = request.GET.get('page', None)
    search = ""
    if request.method == "POST":
        if request.POST.get('action') == 'create_act':
            form = ActsForm(request.POST)
            if form.is_valid():
                act = form.save(commit=False)
                act.created_user = request.user
                act.save()
                messages.success(request, "Вы успешно создали акт")
                return redirect("archive:act-detail", id=act.id)
            else:
                messages.error(request, form.errors)
        elif request.POST.get('action') == 'search_act':
            search = request.POST.get("search", "").strip()
            if search.isdigit():
                acts = acts.filter(
                    Q(id=int(search)) |
                    Q(studentsact__myedu_id__icontains=search) |
                    Q(studentsact__student_fio__icontains=search)
                )
            else:
                acts = acts.filter(
                    Q(studentsact__myedu_id__icontains=search) |
                    Q(studentsact__student_fio__icontains=search)
                )

            acts = acts.distinct()

    acts_pagination = Pagination(request, acts)
    edu_year = EduYear.objects.all().order_by('-title')
    category_form = CategoryForm.objects.all()
    context = {
        "navbar": "archive-index",
        "faculties": faculties,
        "edu_form": edu_form,
        "edu_year": edu_year,
        "category_form": category_form,
        "current_user": request.user,
        "search": search,
        "acts": acts_pagination.pagination(page_number)
    }
    return render(request, "teachers/archive/index.html", context)


def act_edit(request, pk):
    act = get_object_or_404(Acts, pk=pk)

    if request.method == "POST":
        form = ActsForm(request.POST, instance=act)
        if form.is_valid():
            form.save()
            html_row = render_to_string(
                "teachers/archive/includes/act_row.html",
                {"act": act, "current_user": request.user},
                request=request
            )
            return JsonResponse({
                "success": True,
                "html_row": html_row,
                "act_id": act.id
            })
        else:
            return JsonResponse({
                "success": False,
                "html_form": render_to_string(
                    "teachers/archive/includes/act_edit_form.html",
                    {"form": form, "act": act},
                    request=request
                )
            })
    else:
        form = ActsForm(instance=act)
        html_form = render_to_string(
            "teachers/archive/includes/act_edit_form.html",
            {"form": form, "act": act},
            request=request
        )
        return JsonResponse({"html_form": html_form})


@require_POST
@csrf_exempt
def act_delete(request, pk):
    act = Acts.objects.filter(pk=pk).first()
    if not act:
        return JsonResponse({"success": False, "error": "Акт не найден"})
    if act.created_user != request.user:
        return JsonResponse({"success": False, "error": "Нет прав на удаление"})
    if act.is_confirm:
        return JsonResponse({"success": False, "error": "Акт подтверждён"})

    students = StudentsAct.objects.filter(act=act)
    if students:
        return JsonResponse({"success": False, "error": "Удалите связанные студенты"})

    act.delete()
    return JsonResponse({"success": True, "act_id": pk, "message": "Акт успешно удален"})


def act_detail(request, id):
    act = (
        Acts.objects.filter(id=id)
        .select_related('edu_form', 'confirm_user', 'created_user', 'category_form', 'edu_year')
        .first()
    )
    students = []
    search = ""

    if request.method == "POST":
        if "search-act" in request.POST:
            search = request.POST.get('search', '')
            students = handle_students_search(request, search)
            if not students:
                messages.error(request, "Список пуст")
        elif "save-act" in request.POST:
            myedu_id = request.POST.get("myedu_id", 0)
            doc = request.POST.get("doc")
            fio = request.POST.get("fio")
            info = request.POST.get("info")
            movement_info = request.POST.get("movement_info")
            movement_date = request.POST.get("movement_date")

            StudentsAct.objects.create(
                act=act,
                myedu_id=myedu_id,
                doc_number=doc,
                student_fio=fio,
                order=info,
                order_date=movement_date,
                order_status=movement_info,
            )
            messages.success(request, "Вы успешно добавили студента в акт")
        elif "delete-act" in request.POST:
            student_id = request.POST.get("delete_student_id", None)
            if student_id:
                student = StudentsAct.objects.filter(
                    act=act,
                    id=student_id
                ).first()
                if student:
                    student.delete()
                    messages.success(request, f"Студент {student.student_fio} исключен из акта")
                    return redirect("archive:act-detail", id=act.id)
            messages.error(request, "Студент не найден")
        else:
            messages.error(request, "Выберите доступные параметры")
    students_act = StudentsAct.objects.filter(act=act)
    context = {
        "act": act,
        "navbar": "archive-index",
        "students": students,
        "search": search,
        "students_act": students_act
    }

    return render(request, "teachers/archive/act-detail.html", context)


def act_custom(request, act_id):
    act = Acts.objects.filter(id=act_id).first()
    if request.method == "POST":
        extra_fio = request.POST.get("extra_fio", None)
        extra_doc = request.POST.get("extra_doc", None)
        if act:
            StudentsAct.objects.create(
                act=act,
                myedu_id=0,
                doc_number=extra_doc,
                student_fio=extra_fio
            )
            messages.success(request, "Вы успешно добавили студента в акт!")
        else:
            messages.error(request, "Акт не найден")

    return redirect("archive:act-detail", id=act_id)


def act_confirm(request, act_id):
    act = Acts.objects.filter(id=act_id).first()
    if request.method == "POST":
        if act:
            act.is_confirm = True
            act.confirm_date = date.today()
            act.confirm_user = request.user
            act.save()
            messages.success(request, "Вы успешно подтвердили акт!")
        else:
            messages.error(request, "Акт не найден")

    return redirect("archive:act-detail", id=act_id)


def custom_faculty(request):
    faculties = Faculty.objects.filter(is_myedu=False).order_by('title')

    page_number = request.GET.get('page', None)
    faculties_pagination = Pagination(request, faculties)

    if request.method == "POST":
        custom_title = request.POST.get("title", None)
        custom_short_name = request.POST.get("short_name", None)

        if custom_title and custom_short_name:
            Faculty.objects.create(
                title=custom_title,
                short_name=custom_short_name,
                visit=False,
                is_myedu=False,
                myedu_faculty_id=0
            )
            messages.success(request, f"Факультет {custom_title} успешно создан")
        else:
            messages.error(request, "Заполните все поля")
    context = {
        "navbar": "archive-index",
        "faculties": faculties_pagination.pagination(page_number)
    }
    return render(request, "teachers/archive/custom-faculty.html", context)


def custom_faculty_edit(request, pk):
    faculty = get_object_or_404(Faculty, pk=pk)

    if request.method == "POST":
        form = CustomFacultyForm(request.POST, instance=faculty)
        if form.is_valid():
            form.save()
            html_row = render_to_string(
                "teachers/archive/includes/faculty-row.html",
                {"faculty": faculty},
                request=request
            )
            return JsonResponse({
                "success": True,
                "html_row": html_row,
                "faculty_id": faculty.id
            })
        else:
            return JsonResponse({
                "success": False,
                "html_form": render_to_string(
                    "teachers/archive/includes/faculty-edit-form.html",
                    {"form": form, "faculty": faculty},
                    request=request
                )
            })
    else:
        form = CustomFacultyForm(instance=faculty)
        html_form = render_to_string(
            "teachers/archive/includes/faculty-edit-form.html",
            {"form": form, "faculty": faculty},
            request=request
        )
        return JsonResponse({"html_form": html_form})


def handle_students_search(request, search):
    response = requests.post(API_URL + "/obhadnoi/searchstudent", data={"search": search})
    return response.json() if response.status_code == 200 else []
