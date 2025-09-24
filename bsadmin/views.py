import requests
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from bsadmin.consts import API_URL
from bsadmin.forms import FacultyTranscriptForm, FailFacultyTranscriptForm
from bsadmin.models import RegistrationTranscript
from bsadmin.services import UserService
from utils.errors import handle_error
from utils.filter_pagination import Pagination


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
        transcript_number = request.POST.get("transcript_number", "").replace(" ", "").strip()
        academic_transcript = user_service.get_active_academic_transcript_by_number(transcript_number)
        if academic_transcript:
            messages.success(request, "Академическая справка зарегистрирована в системе. Факультет: " + str(
                academic_transcript.faculty.title))
        else:
            messages.error(request, "Академическая справка не зарегистрирована в системе.")

    faculties = user_service.active_faculties_transcripts()

    context = {
        "navbar": "index",
        "faculties": faculties
    }
    return render(request, "teachers/transcripts/index.html", context)


def faculty_transcript_category(request, faculty_id):
    user_service = UserService()

    faculty_detail = user_service.get_faculty_by_id_or_404(faculty_id)

    categories = user_service.categories()
    sort_order = request.GET.get('sort', 'is_used')
    if sort_order not in ["is_used", "-is_used"]:
        sort_order = "is_used"
    page_number = request.GET.get('page', None)
    transcripts = user_service.academic_transcripts_by_faculty_id(faculty_id, sort_order)
    pagination_util = Pagination(request, transcripts)

    context = {
        "navbar": "index",
        "faculty": faculty_detail,
        "category_list": categories,
        "transcripts": pagination_util.pagination(page_number)
    }
    return render(request, "teachers/transcripts/academictranscript_category.html", context)


def registration_academic_transcript_faculty(request, faculty_id, category_id):
    user_service = UserService()

    faculty_detail = user_service.get_faculty_by_id_or_404(faculty_id)
    category_detail = user_service.get_category_transcript_by_id_or_404(category_id)

    page_number = request.GET.get('page', None)
    academic_transcripts = user_service.reg_academic_transcript_faculty(faculty_id, category_id)
    pagination_util = Pagination(request, academic_transcripts)

    if request.method == "POST":
        form = FacultyTranscriptForm(request.POST)
        if form.is_valid():
            try:
                transcript_number = str(form.cleaned_data.get('transcript_number', None)).replace(" ", "")
                instance = form.save(commit=False)
                instance.transcript_number = transcript_number
                instance.faculty_id = faculty_id
                instance.category_id = category_id
                instance.save()
            except Exception as _:
                form.add_error('transcript_number', "Такой номер уже существует в данной категории.")
    else:
        form = FacultyTranscriptForm()

    context = {
        "navbar": "index",
        "facultytranscript_list": pagination_util.pagination(page_number),
        "faculty": faculty_detail,
        "form": form,
        "category": category_detail
    }

    template_name = "teachers/transcripts/academictranscript_faculty.html"
    return render(request, template_name, context)


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
        form = FacultyTranscriptForm(request.POST, instance=faculty_transcript)
        if form.is_valid():
            form.save()
            return JsonResponse(
                {'status': 'success', 'message': 'Запись обновлена', 'data': form.instance.to_ft_dict()})
        else:
            return JsonResponse({'status': 'error', 'message': 'Ошибка при обновлении'})

    return JsonResponse({'status': 'error', 'message': 'Неверный метод'})


@csrf_exempt
def delete_faculty_transcript(request, id):
    user_service = UserService()
    faculty_transcript = user_service.get_academic_transcript_by_id_or_none(id)
    if faculty_transcript:
        faculty_transcript.delete()
        return JsonResponse({'status': 'success', 'message': 'Запись удалена'})
    return JsonResponse({'status': 'error', 'message': 'Запись не найдена'})


def registration_academic_transcript_student(request):
    user_service = UserService()
    faculties = user_service.active_faculties()

    students, custom_data, manual_entry_checked = None, {}, False

    if request.method == "POST":
        if request.POST.get('manual_entry'):
            students, custom_data, manual_entry_checked = handle_manual_entry(request, user_service)
        else:
            students = handle_student_search(request)
    context = {
        "navbar": "at-register-student",
        "students": students,
        "faculties": faculties,
        "custom_data": custom_data,
        "manual_entry_checked": manual_entry_checked
    }
    return render(request, "teachers/transcripts/academictranscript_student.html", context)


def handle_manual_entry(request, user_service):
    student_fio = request.POST.get('custom_student_fio', "")
    faculty_id = request.POST.get('custom_faculty_id', "")
    faculty_title = request.POST.get('custom_faculty_title', "").strip()

    speciality_id = request.POST.get("custom_speciality_id", "")
    speciality_title = request.POST.get("custom_speciality_title", "").strip()

    transcript_number = request.POST.get('custom_transcript_number', "").replace(" ", "").strip()

    specialities = None
    if faculty_id:
        specialities = user_service.active_specialities_by_faculty(faculty_id)

    custom_data = {
        "custom_student_fio": student_fio,
        "custom_faculty_id": faculty_id,
        "custom_faculty_title": faculty_title,
        "custom_transcript_number": transcript_number,
        "custom_speciality_title": speciality_title,
        "custom_speciality_id": speciality_id,
        "specialities": specialities
    }

    if not student_fio or not faculty_id or not faculty_title or not speciality_id or not speciality_title:
        messages.error(request, "Заполните обязательные поля.")
        return None, custom_data, True

    faculty_transcript = user_service.get_active_academic_transcript_by_number(transcript_number)

    if not faculty_transcript:
        messages.error(request, "Академическая справка не найдена.")
        return None, custom_data, True

    if user_service.is_reg_academic_transcript_for_student(faculty_transcript.id):
        messages.error(request, "Этот номер уже зарегистрирован!")
        return None, custom_data, True

    try:
        RegistrationTranscript.objects.create(
            faculty_transcript=faculty_transcript,
            student_uuid=0,
            student_fio=student_fio,
            faculty_id=faculty_id,
            speciality_id=speciality_id,
            faculty_history=faculty_title,
            speciality_history=speciality_title
        )
        messages.success(request, "Данные успешно сохранены")
        return None, {}, False
    except Exception:
        messages.error(request, "Ошибка сохранения. Повторите попытку.")
        return None, custom_data, True


def handle_student_search(request):
    student_query = request.POST.get("student")
    response = requests.post(API_URL + "/obhadnoi/searchstudent", data={"search": student_query})
    return response.json() if response.status_code == 200 else None


def save_academic_transcript_student(request):
    if request.method != "POST":
        messages.error(request, "Этот метод не поддерживается")
        return redirect("bsadmin:academic-transcript-student")

    transcript_number = request.POST.get("transcript_number", "").replace(" ", "").strip()

    student_id = request.POST.get("student_id")
    student_fio = request.POST.get("student_fio")

    faculty_id = request.POST.get("faculty_id")
    faculty_title = request.POST.get("faculty_title")

    speciality_title = request.POST.get("speciality_title")
    speciality_id = request.POST.get("speciality_id")

    if not student_id or not student_fio or not faculty_id or not faculty_title or not speciality_id or not speciality_title:
        messages.error(request, "Заполните обязательные поля.")
        return redirect("bsadmin:academic-transcript-student")

    user_service = UserService()
    transcript = user_service.get_active_academic_transcript_by_number(transcript_number)

    if not transcript:
        messages.error(request, "Этот номер не найден!")
        return redirect("bsadmin:academic-transcript-student")

    faculty_detail = user_service.get_faculty_by_myedu_faculty_id_or_none(faculty_id)
    if not faculty_detail:
        messages.error(request, "Факультет не найден!")
        return redirect("bsadmin:academic-transcript-student")

    speciality_detail = user_service.get_spec_by_myedu_spec_id_or_none(speciality_id)
    if not speciality_detail:
        messages.error(request, "Специальность не найдена!")
        return redirect("bsadmin:academic-transcript-student")

    if user_service.is_reg_academic_transcript_for_student(transcript.id):
        messages.error(request, "Этот номер уже зарегистрирован!")
        return redirect("bsadmin:academic-transcript-student")
    try:
        RegistrationTranscript.objects.create(
            faculty_transcript_id=transcript.id,
            student_uuid=student_id,
            student_fio=student_fio,
            faculty=faculty_detail,
            faculty_history=faculty_title,
            speciality=speciality_detail,
            speciality_history=speciality_title
        )
        messages.success(request, "Данные успешно сохранены")
    except Exception as _:
        messages.error(request, "Повторите попытку...")

    return redirect("bsadmin:academic-transcript-student")


class ReportFacultyRegAcademicTranscript(ListView):
    model = RegistrationTranscript
    user_service = UserService()
    template_name = "teachers/transcripts/academictranscript_faculty_report.html"

    def get_queryset(self):
        return self.user_service.report_faculty_reg_academic_transcript(self.kwargs.get("faculty_id", None))

    def get_context_data(self, **kwargs):
        context = super(ReportFacultyRegAcademicTranscript, self).get_context_data(**kwargs)
        regtranscripts = self.get_queryset()
        pagination_util = Pagination(self.request, regtranscripts)
        page_number = self.request.GET.get('page', None)
        context['regtranscripts'] = pagination_util.pagination(page_number)

        context['navbar'] = 'index'
        context['faculty'] = self.user_service.get_faculty_by_id_or_404(self.kwargs.get("faculty_id", None))
        return context


class ReportAllFacultyRegAcademicTranscript(ListView):
    model = RegistrationTranscript
    user_service = UserService()
    template_name = "teachers/transcripts/academictranscript_all_faculty_report.html"

    def get_context_data(self, **kwargs):
        context = super(ReportAllFacultyRegAcademicTranscript, self).get_context_data(**kwargs)
        regtranscripts = self.user_service.report_all_faculty_reg_academic_transcript()
        pagination_util = Pagination(self.request, regtranscripts)
        page_number = self.request.GET.get('page', None)
        context['regtranscripts'] = pagination_util.pagination(page_number)
        context['navbar'] = 'index'

        return context


def at_search(request):
    user_service = UserService()
    if request.method == "POST":
        transcript_number = request.POST.get("transcript_number", "").replace(" ", "").strip()
        if not transcript_number:
            messages.error(request, "Обязательно к заполнению")
        else:
            reg_transcript_number = user_service.search_academic_transcript_number(transcript_number)
            if reg_transcript_number:
                message = f"""Академическая справка подтверждена.
                ФИО: {reg_transcript_number.student_fio}
                Факультет: {reg_transcript_number.faculty_history}
                Специальность: {reg_transcript_number.speciality_history}
                """
                messages.success(request, message)
            else:
                messages.error(request, "Академическая справка не выдана.")

    context = {
        "navbar": "at-search",
    }
    return render(request, "teachers/transcripts/academictranscript_search.html", context)


def fail_transcript(request):
    if request.method == "POST":
        user_service = UserService()
        transcript_number = request.POST.get("transcript_number", "").replace(" ", "").strip()
        transcript = user_service.get_academic_transcript_by_number(transcript_number)

        if transcript:
            old_transcript = user_service.is_reg_academic_transcript_for_student(transcript.id)
            if old_transcript:
                old_transcript.delete()
                # return JsonResponse({"error": "Номер уже зарегистрирован"})
            form = FailFacultyTranscriptForm(request.POST, request.FILES, instance=transcript)
            if form.is_valid():
                transcript_instance = form.save(commit=False)
                transcript_instance.is_defective = True
                transcript_instance.save()
                messages.success(request, "Данные успешно сохранены в базу")
                return JsonResponse({"success": True})
            else:
                return JsonResponse({"error": "Ошибка в данных. Проверьте введённые данные (PDF)."})
        else:
            return JsonResponse({"not_found": "Справка с таким номером не найдена."})
    return JsonResponse({"success": False, "error": "Некорректный запрос."})


def specialities_by_faculty(request):
    user_service = UserService()
    faculty_id = request.GET.get("faculty_id", 0)
    specialities = user_service.specialities_values_by_faculty(faculty_id)
    return JsonResponse({"specialities": list(specialities)}, status=200)
