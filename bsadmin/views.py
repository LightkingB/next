import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from bsadmin.consts import API_URL
from bsadmin.forms import LoginForm, FacultyTranscriptForm, FailFacultyTranscriptForm
from bsadmin.models import RegistrationTranscript
from bsadmin.services import UserService, HttpMyEduServiceAPI
from utils.filter_pagination import Pagination


def sign_in_view(request):
    user_service = UserService()
    if request.user.is_authenticated:
        return redirect("index")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email', None)
            password = form.cleaned_data.get('password', None)
            user = authenticate(email=email, password=password)

            if user is None:
                myedu_data, success = HttpMyEduServiceAPI.get_myedu_data(email, password)
                if success:
                    user = user_service.update_or_create_user(email, password, myedu_data)
                else:
                    return _handle_error(
                        request,
                        {"form": form},
                        template_name="teachers/profile/login.html",
                        message="Проверьте правильность данных и повторите попытку."
                    )

            request.session['user_id'] = user.id
            login(request, user)
            return redirect("index")

    return render(request, "teachers/profile/login.html", {"form": LoginForm()})


def sign_out_view(request):
    if request.session.get('user_data', None):
        del request.session['user_data']
    logout(request)
    return redirect("index")


def faculty(request):
    user_service = UserService()
    faculties = user_service.active_faculties()
    context = {"navbar": "faculty", "faculties": faculties}
    if request.method == 'POST':
        faculties, error = user_service.fetch_and_update_faculties()
        if error:
            context.update({"error": error})
            return _handle_error(
                request,
                context,
                template_name="teachers/faculty.html",
                message=error
            )
        messages.success(request, "Данные успешно синхронизированы!")
        return redirect("faculty")
    return render(request, "teachers/faculty.html", context)


def faculty_index(request):
    if not request.user.is_authenticated:
        return redirect("login")

    user_service = UserService()

    faculties = user_service.active_faculties_transcripts()

    context = {
        "navbar": "index",
        "faculties": faculties
    }
    return render(request, "index.html", context)


def faculty_transcript_category(request, faculty_id):
    user_service = UserService()

    faculty_detail = user_service.get_faculty_by_id_or_404(faculty_id)

    categories = user_service.categories()

    page_number = request.GET.get('page', None)
    transcripts = user_service.academic_transcripts_by_faculty_id(faculty_id)
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


# def registration_academic_transcript_student(request):
#     user_service = UserService()
#     students = None
#     custom_data = {}
#     manual_entry_checked = False
#
#     if request.method == "POST":
#         is_manual_entry = request.POST.get('manual_entry', None)
#
#         if is_manual_entry:
#             manual_entry_checked = True
#             student_fio = request.POST.get('custom_student_fio', None)
#             faculty_id = request.POST.get('custom_faculty_id', None)
#             transcript_number = request.POST.get('custom_transcript_number', None)
#             faculty_transcript = user_service.get_academic_transcript_by_number(transcript_number)
#
#             custom_data = {
#                 "custom_student_fio": student_fio,
#                 "custom_faculty_id": faculty_id,
#                 "custom_transcript_number": transcript_number
#             }
#
#             if faculty_transcript:
#                 if user_service.is_reg_academic_transcript_for_student(faculty_transcript.id):
#                     messages.error(request, "Этот номер уже зарегистрирован!")
#                 else:
#                     try:
#                         RegistrationTranscript.objects.create(
#                             faculty_transcript_id=faculty_transcript.id,
#                             student_uuid=0,
#                             student_fio=student_fio,
#                             faculty_id=faculty_id
#                         )
#                         messages.success(request, "Данные успешно сохранены")
#                         return redirect(request.path)
#                     except Exception as _:
#                         messages.error(request, "Повторите попытку...")
#
#         else:
#             student = request.POST.get("student", None)
#             students_response = requests.post(API_URL + "/obhadnoi/searchstudent", data={"search": student})
#             if students_response.status_code == 200:
#                 students = students_response.json()
#
#     faculties = user_service.active_faculties()
#     context = {
#         "navbar": "at-register-student",
#         "students": students,
#         "faculties": faculties,
#         "custom_data": custom_data,
#         "manual_entry_checked": manual_entry_checked
#     }
#     template_name = "teachers/transcripts/academictranscript_student.html"
#     return render(request, template_name, context)
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
    student_fio = request.POST.get('custom_student_fio')
    faculty_id = request.POST.get('custom_faculty_id')
    transcript_number = request.POST.get('custom_transcript_number')

    custom_data = {
        "custom_student_fio": student_fio,
        "custom_faculty_id": faculty_id,
        "custom_transcript_number": transcript_number
    }

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
            faculty_id=faculty_id
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
        return redirect("academic-transcript-student")

    transcript_number = request.POST.get("transcript_number", "").replace(" ", "").strip()
    student_id = request.POST.get("student_id")
    student_fio = request.POST.get("student_fio")
    faculty_id = request.POST.get("faculty_id")

    user_service = UserService()
    transcript = user_service.get_active_academic_transcript_by_number(transcript_number)

    if not transcript:
        messages.error(request, "Этот номер не найден!")
        return redirect("academic-transcript-student")

    faculty_detail = user_service.get_faculty_by_myedu_faculty_id_or_none(faculty_id)
    if not faculty_detail:
        messages.error(request, "Факультет не найден!")
        return redirect("academic-transcript-student")

    if user_service.is_reg_academic_transcript_for_student(transcript.id):
        messages.error(request, "Этот номер уже зарегистрирован!")
        return redirect("academic-transcript-student")
    try:
        RegistrationTranscript.objects.create(
            faculty_transcript_id=transcript.id,
            student_uuid=student_id,
            student_fio=student_fio,
            faculty=faculty_detail
        )
        messages.success(request, "Данные успешно сохранены")
    except Exception as _:
        messages.error(request, "Повторите попытку...")

    return redirect("academic-transcript-student")


class ReportFacultyRegAcademicTranscript(ListView):
    model = RegistrationTranscript
    user_service = UserService()
    template_name = "teachers/transcripts/academictranscript_report.html"
    context_object_name = "regtranscripts"

    def get_queryset(self):
        return self.user_service.report_faculty_reg_academic_transcript(self.kwargs.get("faculty_id", None))

    def get_context_data(self, **kwargs):
        context = super(ReportFacultyRegAcademicTranscript, self).get_context_data(**kwargs)
        context['navbar'] = 'index'
        context['faculty'] = self.user_service.get_faculty_by_id_or_404(self.kwargs.get("faculty_id", None))
        return context


def fail_transcript(request):
    if request.method == "POST":
        user_service = UserService()
        transcript_number = request.POST.get('transcript_number')
        transcript = user_service.get_academic_transcript_by_number(transcript_number)

        if transcript:
            if user_service.is_reg_academic_transcript_for_student(transcript.id):
                return JsonResponse({"error": "Номер уже зарегистрирован"})
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


def _handle_error(request, context, template_name, message=None):
    messages.error(request, message)
    return render(request, template_name, context)
