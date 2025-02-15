import json

import requests
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from bsadmin.consts import API_URL
from bsadmin.forms import LoginForm, AcademicTranscriptForm, FacultyTranscriptForm
from bsadmin.mixins import HomeLoginRequiredMixin
from bsadmin.models import AcademicTranscript, RegistrationTranscript, CategoryTranscript
from bsadmin.services import UserService, HttpMyEduServiceAPI
from cms.ajax import AjaxCreateView, AjaxUpdateView, AjaxDeleteView


def sign_in_view(request):
    user_service = UserService()
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")

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
            return HttpResponseRedirect("/")

    return render(request, "teachers/profile/login.html", {"form": LoginForm()})


def sign_out_view(request):
    if request.session.get('user_data', None):
        del request.session['user_data']
    logout(request)
    return HttpResponseRedirect("/login/")


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


class AcademicTranscriptView(HomeLoginRequiredMixin, ListView):
    model = AcademicTranscript
    queryset = AcademicTranscript.objects.all()
    context_object_name = "academictranscript_list"
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(AcademicTranscriptView, self).get_context_data(**kwargs)
        context['navbar'] = 'index'
        return context


def detail_academic_transcript_for_faculty(request, pk):
    user_service = UserService()
    academic_transcript = user_service.get_academic_transcript_by_id_or_404(pk)

    faculties = user_service.reg_academic_transcript_faculties(pk)

    context = {
        "navbar": "index",
        "transcript": academic_transcript,
        "faculties": faculties
    }

    template_name = "teachers/transcripts/academictranscript_faculty.html"
    return render(request, template_name, context)


def registration_academic_transcript_for_faculty(request, pk, faculty_id):
    user_service = UserService()
    academic_transcript = user_service.get_academic_transcript_by_id_or_404(pk)

    faculty = user_service.get_faculty_by_id_or_404(faculty_id)

    academic_transcripts = user_service.reg_academic_transcript_faculty(faculty_id, pk)

    if request.method == "POST":
        form = FacultyTranscriptForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.faculty = faculty
            instance.academic_transcript = academic_transcript
            instance.save()
    else:
        form = FacultyTranscriptForm()
    categories = CategoryTranscript.objects.all()
    context = {
        "navbar": "index",
        "transcript": academic_transcript,
        "facultytranscript_list": academic_transcripts,
        "faculty": faculty,
        "form": form,
        "categories": categories
    }

    template_name = "teachers/transcripts/academictranscript_registration.html"
    return render(request, template_name, context)


def update_faculty_transcript(request, id):
    user_service = UserService()
    faculty_transcript = user_service.get_academic_transcript_by_id_or_none(id)
    if not faculty_transcript:
        return JsonResponse({'status': 'error', 'message': 'Справка не найдена'})

    if request.method == 'GET':
        categories = user_service.get_all_category_transcript()
        selected_category_id = faculty_transcript.category.id

        data = {
            'transcript_number': faculty_transcript.transcript_number,
            'categories': [{'id': category.id, 'title': category.title} for category in categories],
            'selected_category_id': selected_category_id,
        }

        return JsonResponse({'status': 'success', 'data': data})

    if request.method == 'POST':
        form = FacultyTranscriptForm(request.POST, instance=faculty_transcript)
        if form.is_valid():
            form.save()
            return JsonResponse({'status': 'success', 'message': 'Запись обновлена', 'data': form.instance.to_dict()})
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
    students = None
    if request.method == "POST":
        student = request.POST.get("student", None)
        students_response = requests.post(API_URL + "/obhadnoi/searchstudent", data={"search": student})
        if students_response.status_code == 200:
            students = students_response.json()

    context = {
        "navbar": "at-register-student",
        "students": students
    }
    template_name = "teachers/transcripts/academictranscript_student.html"
    return render(request, template_name, context)


@csrf_exempt
def save_student_academic_transcript(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Недопустимый метод запроса!"}, status=405)

    try:
        data = json.loads(request.body)
        transcript_number = data.get("unique_number", None)
        student_id = data.get("student_id", None)
        student_fio = data.get("student_fio", None)
        faculty_id = data.get("faculty_id", None)

        user_service = UserService()
        transcript = user_service.get_academic_transcript_by_number(transcript_number)

        if not transcript:
            return JsonResponse({"success": False, "message": "Этот номер не найден!"})

        faculty = user_service.get_faculty_by_myedu_faculty_id_or_none(faculty_id)
        if not faculty:
            return JsonResponse({"success": False, "message": "Факультет не найден!"})

        reg_transcript = user_service.is_reg_academic_transcript_for_student(transcript.id)
        if reg_transcript:
            return JsonResponse({"success": False, "message": "Этот номер уже зарегистрирован!"})

        RegistrationTranscript.objects.create(
            faculty_transcript_id=transcript.id,
            student_uuid=student_id,
            student_fio=student_fio,
            faculty=faculty

        )

        return JsonResponse({"success": True, "message": "Студент успешно сохранен!"})

    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Некорректный JSON!"}, status=400)
    except Exception as e:
        return JsonResponse({"success": False, "message": "Повторите попытку!"}, status=500)


class AcademicTranscriptCreateView(HomeLoginRequiredMixin, AjaxCreateView):
    model = AcademicTranscript
    form_class = AcademicTranscriptForm
    ajax_modal = 'ajax/form_modal.html'
    ajax_list = 'teachers/transcripts/academictranscript_list.html'


class AcademicTranscriptUpdateView(HomeLoginRequiredMixin, AjaxUpdateView):
    model = AcademicTranscript
    form_class = AcademicTranscriptForm
    ajax_modal = 'ajax/form_modal.html'
    ajax_list = 'teachers/transcripts/academictranscript_list.html'


class AcademicTranscriptDeleteView(HomeLoginRequiredMixin, AjaxDeleteView):
    model = AcademicTranscript
    ajax_modal = 'ajax/delete_modal.html'
    ajax_list = 'teachers/transcripts/academictranscript_list.html'


class ReportRegAcademicTranscript(ListView):
    model = RegistrationTranscript
    user_service = UserService()
    template_name = "teachers/transcripts/academictranscript_report.html"
    context_object_name = "regtranscripts"

    def get_queryset(self):
        return self.user_service.report_all_reg_academic_transcript_by_transcript_id(
            self.kwargs.get("transcript_id", None))

    def get_context_data(self, **kwargs):
        context = super(ReportRegAcademicTranscript, self).get_context_data(**kwargs)
        context['navbar'] = 'index'
        return context


def _handle_error(request, context, template_name, message=None):
    messages.error(request, message)
    return render(request, template_name, context)
