import base64
import io
import os
import random
import re
import string
from datetime import datetime, timedelta
from urllib.parse import urlencode

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, FileResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import localdate
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from bsadmin.forms import FacultyTranscriptForm, FailFacultyTranscriptForm
from bsadmin.models import RegistrationTranscript, RegHistoryTranscript, Faculty, CategoryTranscript, \
    FacultyTranscript, Speciality
from bsadmin.services import UserService
from utils.errors import handle_error
from utils.filter_pagination import Pagination
from utils.myedu import MyEduService


def faculty(request):
    user_service = UserService()
    faculties = user_service.active_faculties()
    context = {"navbar": "faculty", "faculties": faculties}
    if request.method == 'POST':
        faculties, error = user_service.fetch_and_update_faculties()
        if error:
            context.update({"error": error})
            return handle_error(
                request,
                context,
                template_name="teachers/base/faculty.html",
                message=error
            )
        messages.success(request, "Данные успешно синхронизированы!")
        return redirect("bsadmin:faculty")
    return render(request, "teachers/base/faculty.html", context)


def speciality(request, faculty_id):
    user_service = UserService()
    faculty_detail = user_service.get_faculty_by_id_or_404(faculty_id)
    specialities = user_service.active_specialities_by_faculty(faculty_id)
    context = {
        "navbar": "faculty",
        "specialities": specialities,
        "faculty": faculty_detail,
        "access": "bsadmin"
    }
    if request.method == 'POST':
        specialities, error = user_service.fetch_and_update_specialities_by_faculty(faculty_detail)
        if error:
            context.update({"error": error})
            return handle_error(
                request,
                context,
                template_name="teachers/base/speciality.html",
                message=error
            )
        messages.success(request, "Данные успешно синхронизированы!")
        return redirect("bsadmin:speciality", faculty_id=faculty_id)
    return render(request, "teachers/base/speciality.html", context)


def faculty_index(request):
    if not request.user.is_authenticated:
        return redirect("integrator:next-teacher-login")
    request.session['access'] = 'bsadmin'
    user_service = UserService()
    if request.method == "POST":
        # Старая форма проверки: ведём на полноценную страницу проверки справки.
        number = request.POST.get("transcript_number", "").strip()
        return redirect(reverse("bsadmin:at-search") + ("?" + urlencode({"q": number}) if number else ""))

    faculties = list(user_service.active_faculties_transcripts())
    for faculty in faculties:
        total = faculty["total_documents"]
        faculty["used_percent"] = round(faculty["used_documents"] * 100 / total) if total else 0
        faculty["defective_percent"] = round(faculty["defective_documents"] * 100 / total) if total else 0
    totals = {key: sum(f[key] for f in faculties)
              for key in ("total_documents", "free_documents", "used_documents", "defective_documents")}

    context = {
        "navbar": "index",
        "faculties": faculties,
        "totals": totals,
        "without_free": sum(1 for f in faculties if f["total_documents"] and not f["free_documents"]),
    }
    return render(request, "teachers/transcripts/index.html", context)


TRANSCRIPT_LEVELS = {
    "ВПО": "Высшее профессиональное образование",
    "СПО": "Среднее профессиональное образование",
    "НПО": "Начальное профессиональное образование",
}


def _transcript_level(category):
    """Расшифровка категории бланка по префиксу названия (ВПО*1 → высшее проф. образование)."""
    title = (category.title or "").upper()
    for prefix, label in TRANSCRIPT_LEVELS.items():
        if title.startswith(prefix):
            return label
    return category.get_category_display() or ""


TRANSCRIPT_STATUSES = {
    "free": "Обычные",
    "used": "Записанные",
    "defective": "Повреждённые",
}


def faculty_transcript_category(request, faculty_id):
    user_service = UserService()

    faculty_detail = user_service.get_faculty_by_id_or_404(faculty_id)

    categories = user_service.categories()
    sort_order = request.GET.get('sort', 'is_used')
    if sort_order not in ["is_used", "-is_used"]:
        sort_order = "is_used"
    query = request.GET.get('q', '').replace(" ", "").strip()
    status = request.GET.get('status', '')
    if status not in TRANSCRIPT_STATUSES:
        status = ''
    faculty_categories = [category for category in categories if category.category == faculty_detail.category]
    category_id = request.GET.get('category', '')
    selected_category = next((c for c in faculty_categories if str(c.id) == category_id), None)
    page_number = request.GET.get('page', None)
    transcripts = user_service.academic_transcripts_by_faculty_id(
        faculty_id, sort_order, query, status, selected_category.id if selected_category else None)

    stats = user_service.academic_transcript_category_stats(faculty_id)
    category_cards = [
        {
            "category": category,
            "level": _transcript_level(category),
            "stats": stats.get(category.id, {"total": 0, "free": 0, "used": 0, "defective": 0}),
        }
        for category in faculty_categories
    ]
    pagination_util = Pagination(request, transcripts)

    context = {
        "navbar": "index",
        "faculty": faculty_detail,
        "category_cards": category_cards,
        "selected_category": selected_category,
        "all_count": sum(card["stats"]["total"] for card in category_cards),
        "transcripts": pagination_util.pagination(page_number),
        "query": query,
        "status": status,
        "status_choices": TRANSCRIPT_STATUSES.items(),
        "counts": user_service.academic_transcript_status_counts(
            faculty_id, selected_category.id if selected_category else None),
    }
    return render(request, "teachers/transcripts/academictranscript_category.html", context)


def registration_academic_transcript_faculty(request, faculty_id, category_id):
    user_service = UserService()

    faculty_detail = user_service.get_faculty_by_id_or_404(faculty_id)
    category_detail = user_service.get_category_transcript_by_id_or_404(category_id)

    if request.method == "POST":
        form = FacultyTranscriptForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.faculty_id = faculty_id
            instance.category_id = category_id
            instance.save()
            messages.success(request, f"Бланк № {instance.transcript_number} зарегистрирован.")
            # Post/Redirect/Get: обновление страницы не отправит форму повторно.
            return redirect(f"{request.path}?added={instance.id}")
    else:
        form = FacultyTranscriptForm()

    query = request.GET.get('q', '').replace(" ", "").strip()
    status = request.GET.get('status', '')
    if status not in TRANSCRIPT_STATUSES:
        status = ''
    # Тот же запрос, что и в журнале факультета: со статусом выдачи и данными студента.
    academic_transcripts = user_service.academic_transcripts_by_faculty_id(
        faculty_id, '-id', query, status, category_id)
    pagination_util = Pagination(request, academic_transcripts)

    added_id = _parse_int_param(request.GET.get('added'))
    context = {
        "navbar": "index",
        "facultytranscript_list": pagination_util.pagination(request.GET.get('page', None)),
        "faculty": faculty_detail,
        "form": form,
        "category": category_detail,
        "level": _transcript_level(category_detail),
        "counts": user_service.academic_transcript_status_counts(faculty_id, category_id),
        "query": query,
        "status": status,
        "status_choices": [("", "Все"), ("free", "Свободные"), ("used", "Выданные"), ("defective", "Повреждённые")],
        "added_id": added_id,
        "added": FacultyTranscript.objects.filter(id=added_id, faculty_id=faculty_id).first() if added_id else None,
    }

    template_name = "teachers/transcripts/academictranscript_faculty.html"
    return render(request, template_name, context)


def _parse_int_param(value):
    return int(value) if value and str(value).isdigit() else None


def _transcript_locked_reason(transcript):
    """Выданный или повреждённый бланк нельзя менять и удалять из журнала регистрации."""
    if transcript.is_defective:
        return "Бланк отмечен как повреждённый — изменить или удалить его нельзя."
    if RegistrationTranscript.objects.filter(faculty_transcript=transcript).exists():
        return "Бланк уже выдан студенту — изменить или удалить его нельзя."
    return None


def update_faculty_transcript(request, id):
    user_service = UserService()
    faculty_transcript = user_service.get_academic_transcript_by_id_or_none(id)
    if not faculty_transcript:
        return JsonResponse({'status': 'error', 'message': 'Справка не найдена'})

    if request.method == 'GET':
        data = {
            'transcript_number': faculty_transcript.transcript_number,
        }
        return JsonResponse({'status': 'success', 'data': data})

    if request.method == 'POST':
        locked = _transcript_locked_reason(faculty_transcript)
        if locked:
            return JsonResponse({'status': 'error', 'message': locked})
        form = FacultyTranscriptForm(request.POST, instance=faculty_transcript)
        if form.is_valid():
            form.save()
            return JsonResponse(
                {'status': 'success', 'message': f'Номер изменён на {form.instance.transcript_number}',
                 'data': form.instance.to_ft_dict()})
        errors = [e for field_errors in form.errors.values() for e in field_errors]
        return JsonResponse({'status': 'error', 'message': " ".join(errors) or 'Ошибка при обновлении'})

    return JsonResponse({'status': 'error', 'message': 'Неверный метод'})


@csrf_exempt
def delete_faculty_transcript(request, id):
    user_service = UserService()
    faculty_transcript = user_service.get_academic_transcript_by_id_or_none(id)
    if not faculty_transcript:
        return JsonResponse({'status': 'error', 'message': 'Запись не найдена'})
    locked = _transcript_locked_reason(faculty_transcript)
    if locked:
        return JsonResponse({'status': 'error', 'message': locked})
    number = faculty_transcript.transcript_number
    faculty_transcript.delete()
    return JsonResponse({'status': 'success', 'message': f'Бланк № {number} удалён'})


@csrf_exempt
def delete_registry_faculty_transcript(request, id):
    user_service = UserService()

    faculty_transcript = user_service.get_academic_transcript_by_id_or_none(id)
    if not faculty_transcript:
        return JsonResponse(
            {'status': 'error', 'message': 'Запись не найдена'},
            status=404
        )

    with transaction.atomic():
        reg_transcript = (
            RegistrationTranscript.objects
            .select_related('faculty', 'speciality', 'faculty_transcript')
            .filter(faculty_transcript=faculty_transcript)
            .first()
        )

        if reg_transcript:
            RegHistoryTranscript.objects.create(
                transcript_number=reg_transcript.faculty_transcript.transcript_number,
                student_uuid=reg_transcript.student_uuid,
                student_fio=reg_transcript.student_fio,
                faculty=reg_transcript.faculty.title,
                speciality=reg_transcript.speciality.title,
                created_by=request.user
            )

            reg_transcript.delete()

    return JsonResponse(
        {'status': 'success', 'message': 'Запись удалена'}
    )


def registration_academic_transcript_student(request):
    user_service = UserService()
    faculties = user_service.active_faculties()
    query = (request.GET.get("q") or "").strip()

    students, search_failed, custom_data = None, False, {}
    mode = request.GET.get("mode") if request.GET.get("mode") in ("search", "manual") else "search"

    if request.method == "POST" and request.POST.get("manual_entry"):
        mode = "manual"
        saved, custom_data = handle_manual_entry(request, user_service)
        if saved:
            return redirect(f"{request.path}?mode=manual")
    elif query:
        result = MyEduService.search_students(query)
        if result is None:
            search_failed = True
        else:
            students = result if isinstance(result, list) else []
            issued = user_service.issued_transcripts_by_students([s.get("student_id") for s in students])
            for student in students:
                student["issued"] = issued.get(str(student.get("student_id")), [])

    context = {
        "navbar": "at-register-student",
        "query": query,
        "mode": mode,
        "students": students,
        "search_failed": search_failed,
        "faculties": faculties,
        "custom_data": custom_data,
        "back_url": request.get_full_path(),
    }
    return render(request, "teachers/transcripts/academictranscript_student.html", context)


def _issue_transcript(request, transcript_number, **registration):
    """Выдаёт бланк в транзакции с блокировкой строки, чтобы два сотрудника не выдали один бланк."""
    user_service = UserService()
    with transaction.atomic():
        transcript, error = user_service.check_transcript_for_issue(transcript_number)
        if transcript:
            transcript = FacultyTranscript.objects.select_for_update().get(pk=transcript.pk)
            transcript, error = user_service.check_transcript_for_issue(transcript.transcript_number)
        if error:
            messages.error(request, error)
            return False
        RegistrationTranscript.objects.create(faculty_transcript=transcript, **registration)
    messages.success(request, f"Справка № {transcript.transcript_number} выдана: {registration['student_fio']}.")
    return True


def handle_manual_entry(request, user_service):
    """Ручная выдача, если студента нет в MyEDU. Возвращает (сохранено, данные формы)."""
    faculty_id = request.POST.get('custom_faculty_id', "")
    speciality_id = request.POST.get("custom_speciality_id", "")
    custom_data = {
        "custom_student_fio": request.POST.get('custom_student_fio', "").strip(),
        "custom_faculty_id": faculty_id,
        "custom_speciality_id": speciality_id,
        "custom_transcript_number": request.POST.get('custom_transcript_number', "").replace(" ", "").strip(),
        "specialities": user_service.active_specialities_by_faculty(faculty_id) if faculty_id.isdigit() else None,
    }

    faculty = Faculty.objects.filter(id=faculty_id).first() if faculty_id.isdigit() else None
    speciality = (Speciality.objects.filter(id=speciality_id, faculty=faculty).first()
                  if faculty and speciality_id.isdigit() else None)
    missing = [label for label, ok in (("факультет", faculty), ("специальность", speciality),
                                       ("ФИО студента", custom_data["custom_student_fio"]),
                                       ("номер справки", custom_data["custom_transcript_number"])) if not ok]
    if missing:
        messages.error(request, "Заполните: " + ", ".join(missing) + ".")
        return False, custom_data

    saved = _issue_transcript(
        request, custom_data["custom_transcript_number"],
        student_uuid=0,
        student_fio=custom_data["custom_student_fio"],
        faculty=faculty,
        faculty_history=faculty.title,
        speciality=speciality,
        speciality_history=speciality.title,
    )
    return saved, custom_data


def _safe_back_url(request, fallback):
    url = request.POST.get("next") or ""
    return url if url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}) else fallback


def save_academic_transcript_student(request):
    fallback = reverse("bsadmin:academic-transcript-student")
    if request.method != "POST":
        messages.error(request, "Этот метод не поддерживается")
        return redirect(fallback)
    back = _safe_back_url(request, fallback)

    student_id = request.POST.get("student_id")
    student_fio = (request.POST.get("student_fio") or "").strip()
    faculty_id = request.POST.get("faculty_id")
    faculty_title = request.POST.get("faculty_title")
    speciality_id = request.POST.get("speciality_id")
    speciality_title = request.POST.get("speciality_title")

    if not all([student_id, student_fio, faculty_id, faculty_title, speciality_id, speciality_title]):
        messages.error(request, "Недостаточно данных о студенте из MyEDU. Повторите поиск.")
        return redirect(back)

    user_service = UserService()
    faculty_detail = user_service.get_faculty_by_myedu_faculty_id_or_none(faculty_id)
    if not faculty_detail:
        messages.error(request, f"Факультет «{faculty_title}» не найден в системе. Синхронизируйте факультеты.")
        return redirect(back)
    speciality_detail = user_service.get_spec_by_myedu_spec_id_or_none(speciality_id)
    if not speciality_detail:
        messages.error(request, f"Специальность «{speciality_title}» не найдена в системе. Синхронизируйте специальности.")
        return redirect(back)

    _issue_transcript(
        request, request.POST.get("transcript_number", ""),
        student_uuid=student_id,
        student_fio=student_fio,
        faculty=faculty_detail,
        faculty_history=faculty_title,
        speciality=speciality_detail,
        speciality_history=speciality_title,
    )
    return redirect(back)


def check_transcript_number(request):
    """Проверка номера «на лету» перед выдачей."""
    transcript, error = UserService().check_transcript_for_issue(request.GET.get("number", ""))
    if error:
        return JsonResponse({"ok": False, "message": error})
    return JsonResponse({
        "ok": True,
        "message": f"Свободен · {transcript.category.title} · {transcript.faculty.short_name or transcript.faculty.title}",
        "number": transcript.transcript_number,
        "category": f"{transcript.category.title} · {transcript.category.page_count} л.",
        "faculty_id": transcript.faculty_id,
        "faculty_title": transcript.faculty.title,
        "faculty_myedu_id": transcript.faculty.myedu_faculty_id,
    })


class ReportFacultyRegAcademicTranscript(ListView):
    model = RegistrationTranscript
    user_service = UserService()
    template_name = "teachers/transcripts/academictranscript_faculty_report.html"

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        return self.user_service.report_faculty_reg_academic_transcript(self.kwargs.get("faculty_id", None), query)

    def get_context_data(self, **kwargs):
        context = super(ReportFacultyRegAcademicTranscript, self).get_context_data(**kwargs)
        regtranscripts = self.get_queryset()
        pagination_util = Pagination(self.request, regtranscripts)
        page_number = self.request.GET.get('page', None)
        context['regtranscripts'] = pagination_util.pagination(page_number)

        context['navbar'] = 'index'
        context['query'] = self.request.GET.get('q', '').strip()
        context['faculty'] = self.user_service.get_faculty_by_id_or_404(self.kwargs.get("faculty_id", None))
        return context


REPORT_SORT_CHOICES = (
    ("faculty", "По факультету"),
    ("new", "Сначала новые"),
    ("old", "Сначала старые"),
    ("fio", "По ФИО"),
)


def _report_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        return None


class ReportAllFacultyRegAcademicTranscript(ListView):
    model = RegistrationTranscript
    user_service = UserService()
    template_name = "teachers/transcripts/academictranscript_all_faculty_report.html"

    def get_filters(self):
        get = self.request.GET
        sort = get.get("sort")
        return {
            "q": (get.get("q") or "").strip(),
            "faculty": _parse_int_param(get.get("faculty")),
            "category": _parse_int_param(get.get("category")),
            "date_from": _report_date(get.get("date_from")),
            "date_to": _report_date(get.get("date_to")),
            "sort": sort if sort in dict(REPORT_SORT_CHOICES) else "faculty",
        }

    def get_queryset(self):
        return self.user_service.report_all_faculty_reg_academic_transcript(self.get_filters())

    def get_context_data(self, **kwargs):
        context = super(ReportAllFacultyRegAcademicTranscript, self).get_context_data(**kwargs)
        filters = self.get_filters()
        pagination_util = Pagination(self.request, self.object_list)
        context['regtranscripts'] = pagination_util.pagination(self.request.GET.get('page', None))
        context['navbar'] = 'index'

        def url(**changes):
            params = {**filters, **changes}
            query = {key: (value.isoformat() if hasattr(value, "isoformat") else value)
                     for key, value in params.items()
                     if value not in (None, "") and not (key == "sort" and value == "faculty")}
            return self.request.path + ("?" + urlencode(query) if query else "")

        faculties = list(Faculty.objects.filter(visit=True).order_by('title').values_list('id', 'title'))
        categories = list(CategoryTranscript.objects.order_by('title').values_list('id', 'title'))
        today = localdate()
        presets = [
            ("Сегодня", today, today),
            ("7 дней", today - timedelta(days=6), today),
            ("30 дней", today - timedelta(days=29), today),
            ("Этот месяц", today.replace(day=1), today),
            ("Этот год", today.replace(month=1, day=1), today),
        ]
        active = []
        if filters["q"]:
            active.append((f"Поиск: «{filters['q']}»", url(q="")))
        if filters["faculty"]:
            active.append((f"Факультет: {dict(faculties).get(filters['faculty'], filters['faculty'])}", url(faculty=None)))
        if filters["category"]:
            active.append((f"Категория: {dict(categories).get(filters['category'], filters['category'])}", url(category=None)))
        if filters["date_from"] or filters["date_to"]:
            period = " – ".join(d.strftime("%d.%m.%Y") for d in (filters["date_from"], filters["date_to"]) if d)
            active.append((f"Выдана: {period}", url(date_from=None, date_to=None)))

        context.update({
            "filters": filters,
            "faculties": faculties,
            "categories": categories,
            "sort_choices": REPORT_SORT_CHOICES,
            "date_links": [{"label": label, "url": url(date_from=start, date_to=finish),
                            "active": filters["date_from"] == start and filters["date_to"] == finish}
                           for label, start, finish in presets],
            "active_filters": active,
            "reset_url": self.request.path,
        })
        return context


SEARCH_SIMILAR_LIMIT = 30


def at_search(request):
    user_service = UserService()
    query = request.GET.get("q", "").strip()
    exact, similar = None, []
    if query:
        exact, similar = user_service.find_academic_transcript(query, SEARCH_SIMILAR_LIMIT)

    context = {
        "navbar": "at-search",
        "query": query,
        "exact": exact,
        "similar": similar[:SEARCH_SIMILAR_LIMIT],
        "similar_more": len(similar) > SEARCH_SIMILAR_LIMIT,
    }
    return render(request, "teachers/transcripts/academictranscript_search.html", context)


def fail_transcript(request):
    if request.method == "POST":
        user_service = UserService()
        transcript_number = request.POST.get("transcript_number", "").replace(" ", "").strip()
        transcript = user_service.get_academic_transcript_by_number(transcript_number)

        if transcript:
            form = FailFacultyTranscriptForm(request.POST, request.FILES, instance=transcript)
            if form.is_valid():
                old_transcript = user_service.is_reg_academic_transcript_for_student(transcript.id)
                if old_transcript:
                    old_transcript.delete()
                transcript_instance = form.save(commit=False)
                transcript_instance.is_defective = True
                transcript_instance.save()
                messages.success(request, "Данные успешно сохранены в базу")
                return JsonResponse({"success": True})
            else:
                errors = [e for field_errors in form.errors.values() for e in field_errors]
                return JsonResponse({"error": " ".join(errors) or "Ошибка в данных. Проверьте введённые данные (PDF)."})
        else:
            return JsonResponse({"not_found": "Справка с таким номером не найдена."})
    return JsonResponse({"success": False, "error": "Некорректный запрос."})


def specialities_by_faculty(request):
    user_service = UserService()
    faculty_id = request.GET.get("faculty_id", 0)
    specialities = user_service.specialities_values_by_faculty(faculty_id)
    return JsonResponse({"specialities": list(specialities)}, status=200)


def auth_required_view(request):
    return render(request, 'errors/auth_required.html')


def get_back_url(request):
    """
    Автоматически определяет, откуда пришел пользователь.
    """
    # 1. Достаем из сессии
    back_url = request.session.get('previous_url')

    # 2. Если нет в сессии, берем реферер
    if not back_url:
        back_url = request.META.get('HTTP_REFERER')

    if back_url:
        current_url = request.build_absolute_uri()

        # Если ссылки полностью совпадают (мы на той же странице) -> не возвращаем кнопку
        if back_url == current_url:
            return None

        # Проверка "свой/чужой".
        # Если в сохраненной ссылке есть наш текущий хост (например next.oshsu.kg), то ссылка наша.
        if request.get_host() in back_url:
            return back_url

    return None


def handler400(request, exception=None):
    """Ошибка 400: Неверный запрос"""
    context = {
        'title': 'Неверный запрос',
        'code': '400',
        'message': 'Сервер не смог обработать ваш запрос.',
        'back_url': get_back_url(request)  # <- Вот здесь мы передаем ссылку в шаблон
    }
    return render(request, 'errors/error_base.html', context, status=400)


def handler403(request, exception=None):
    """Ошибка 403: Доступ запрещен"""
    context = {
        'title': 'Доступ запрещен',
        'code': '403',
        'message': 'У вас нет прав для просмотра этой страницы.',
        'back_url': get_back_url(request)
    }
    return render(request, 'errors/error_base.html', context, status=403)


def handler404(request, exception):
    """Ошибка 404: Страница не найдена"""
    context = {
        'title': 'Страница не найдена',
        'code': '404',
        'message': 'К сожалению, запрашиваемая страница не существует или была удалена.',
        'back_url': get_back_url(request)
    }
    return render(request, 'errors/error_base.html', context, status=404)


def handler500(request):
    """Ошибка 500: Внутренняя ошибка сервера"""
    context = {
        'title': 'Ошибка сервера',
        'code': '500',
        'message': 'Произошла внутренняя ошибка. Мы уже работаем над её устранением.',
        'back_url': get_back_url(request)
    }
    return render(request, 'errors/error_base.html', context, status=500)


def invitation_view(request):
    # --- НАСТРОЙКИ ---
    X_OFFSET = 480
    Y_COORDINATE = 742
    FONT_SIZE = 40
    # -----------------

    guest_name = ""
    img_str = None

    if request.method == "POST":
        guest_name = request.POST.get("guest_name", "").strip()
        # Твой путь к картинке
        image_path = os.path.join(settings.BASE_DIR, 'static', 'static_dirs', 'img', 'invite.jpg')

        try:
            img = Image.open(image_path).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Шрифт (Ubuntu)
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            try:
                font = ImageFont.truetype(font_path, FONT_SIZE)
            except:
                font = ImageFont.load_default()

            # Рисуем
            draw.text((X_OFFSET, Y_COORDINATE), guest_name, fill=(101, 80, 46), font=font, anchor="ls")

            # --- ЛОГИКА СКАЧИВАНИЯ ---
            if 'download_action' in request.POST:
                # Генерим хвост
                suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=5))

                # Чистим имя: оставляем буквы и цифры, остальное нахер, пробелы в нижнее подчеркивание
                # Фильтр re.U позволяет корректно работать с кириллицей
                clean_name = re.sub(r'[^\w\s]', '', guest_name, flags=re.U).strip().replace(" ", "_")

                if not clean_name:
                    clean_name = "invitation"

                filename = f"{clean_name}_{suffix}.jpg"

                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=100)
                buffer.seek(0)

                # Используем FileResponse — он сам выставит нужные заголовки для скачивания
                response = FileResponse(buffer, as_attachment=True, filename=filename)
                # Явно прописываем тип, чтобы браузер не тупил
                response['Content-Type'] = 'image/jpeg'
                return response

            # --- ПРЕДПРОСМОТР ---
            preview_buffer = io.BytesIO()
            img.save(preview_buffer, format="JPEG")
            img_str = base64.b64encode(preview_buffer.getvalue()).decode()

        except Exception as e:
            print(f"Ошибка: {e}")

    return render(request, 'errors/invitation.html', {
        'preview_img': img_str,
        'guest_name': guest_name
    })


def invitation_view_2(request):
    # --- НАСТРОЙКИ ---

    CENTER_X = 420  # центр имени по ширине картинки
    Y_COORDINATE = 345  # высота имени

    MAX_FONT_SIZE = 38
    MIN_FONT_SIZE = 28

    MAX_TEXT_WIDTH = 500

    TEXT_COLOR = (111, 80, 46)  # #BFA88A

    # -----------------

    guest_name = ""
    img_str = None

    if request.method == "POST":

        guest_name = request.POST.get(
            "guest_name",
            ""
        ).strip()

        image_path = os.path.join(
            settings.BASE_DIR,
            'static',
            'static_dirs',
            'img',
            'ap.jpg'
        )

        try:

            img = Image.open(image_path).convert("RGB")

            draw = ImageDraw.Draw(img)

            # --- ПОИСК ШРИФТА ---

            font_candidates = [
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]

            font_path = None

            for path in font_candidates:
                if os.path.exists(path):
                    font_path = path
                    break

            # --- АДАПТИВНЫЙ РАЗМЕР ШРИФТА ---

            if font_path:

                font_size = MAX_FONT_SIZE

                while font_size > MIN_FONT_SIZE:

                    font = ImageFont.truetype(
                        font_path,
                        font_size
                    )

                    bbox = draw.textbbox(
                        (0, 0),
                        guest_name,
                        font=font
                    )

                    text_width = bbox[2] - bbox[0]

                    if text_width <= MAX_TEXT_WIDTH:
                        break

                    font_size -= 2

                font = ImageFont.truetype(
                    font_path,
                    font_size
                )


            else:

                font = ImageFont.load_default()

            # --- ВЫЧИСЛЯЕМ ШИРИНУ ИМЕНИ ---

            bbox = draw.textbbox(
                (0, 0),
                guest_name,
                font=font
            )

            text_width = bbox[2] - bbox[0]

            # --- РИСУЕМ СТРОГО ПО ЦЕНТРУ ---

            draw.text(
                (
                    CENTER_X - text_width / 2,
                    Y_COORDINATE
                ),
                guest_name,
                fill=TEXT_COLOR,
                font=font
            )

            # --- СКАЧИВАНИЕ ---

            if 'download_action' in request.POST:

                suffix = ''.join(
                    random.choices(
                        string.ascii_letters + string.digits,
                        k=5
                    )
                )

                clean_name = re.sub(
                    r'[^\w\s]',
                    '',
                    guest_name,
                    flags=re.U
                ).strip().replace(
                    " ",
                    "_"
                )

                if not clean_name:
                    clean_name = "invitation"

                filename = f"{clean_name}_{suffix}.jpg"

                buffer = io.BytesIO()

                img.save(
                    buffer,
                    format="JPEG",
                    quality=100
                )

                buffer.seek(0)

                response = FileResponse(
                    buffer,
                    as_attachment=True,
                    filename=filename
                )

                response["Content-Type"] = "image/jpeg"

                return response

            # --- PREVIEW ---

            preview_buffer = io.BytesIO()

            img.save(
                preview_buffer,
                format="JPEG"
            )

            img_str = base64.b64encode(
                preview_buffer.getvalue()
            ).decode()



        except Exception as e:

            print(f"Ошибка: {e}")

    return render(
        request,
        'errors/invitation.html',
        {
            'preview_img': img_str,
            'guest_name': guest_name
        }
    )
