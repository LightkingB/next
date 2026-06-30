from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from stepper.consts import STUDENT_STEPPER_URL
from stepper.decorators import with_stepper
from student.forms import StudentPhoneForm, build_survey_form
from student.models import StudentProfile
from student.services import SurveyService
from utils.caches import EntityCache
from utils.myedu import MyEduService


def _get_student_api_data(request):
    return EntityCache.get_or_set(
        entity_id=request.user.myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": request.user.myedu_id,
        },
    )


def _student_group(student_data):
    if not student_data:
        return ""
    return student_data.get("group_name") or student_data.get("info") or ""


def _student_fio(student_data, user):
    if student_data and student_data.get("student_fio"):
        return student_data["student_fio"]
    return user.full_name


def _phone_redirect(request, next_url):
    phone_url = reverse("students:survey-phone")
    return redirect(f"{phone_url}?next={next_url}")


@with_stepper
def survey_phone(request):
    profile = StudentProfile.objects.filter(user_id=request.user.pk).first()
    next_url = request.GET.get("next") or request.POST.get("next") or reverse("students:survey")

    if request.method == "POST":
        form = StudentPhoneForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Номер телефона сохранён.")
            return redirect(next_url)
    else:
        form = StudentPhoneForm(instance=profile)

    return render(request, "students/survey/phone.html", {"form": form, "next_url": next_url})


@with_stepper
def survey_index(request):
    edu_year, history, active_items = SurveyService.dashboard_for_user(request.user)

    return render(
        request,
        "students/survey/index.html",
        {
            "edu_year": edu_year,
            "active_items": active_items,
            "history": history,
        },
    )


@with_stepper
def survey_take(request, survey_id):
    if not SurveyService.user_has_profile(request.user):
        take_url = reverse("students:survey-take", kwargs={"survey_id": survey_id})
        return _phone_redirect(request, take_url)

    edu_year = SurveyService.commission_edu_year()
    if not edu_year:
        messages.error(request, "Не найден учебный год с активной комиссией.")
        return redirect("students:survey")

    survey = get_object_or_404(SurveyService.survey_for_take(survey_id, request.user, edu_year))

    if survey.already_submitted:
        messages.info(request, "Вы уже заполнили эту анкету за текущий учебный год.")
        return redirect("students:survey")

    if survey.question_count == 0:
        messages.error(request, "Анкета пока не содержит вопросов.")
        return redirect("students:survey")

    SurveyFormClass = build_survey_form(survey)

    if request.method == "POST":
        form = SurveyFormClass(request.POST)
        if form.is_valid():
            student_data = _get_student_api_data(request)
            submission, error = SurveyService.save_submission(
                user=request.user,
                survey=survey,
                edu_year=edu_year,
                cleaned_data=form.cleaned_data,
                student_data={
                    "student_fio": _student_fio(student_data, request.user),
                    "group": _student_group(student_data),
                },
            )
            if submission:
                messages.success(request, "Анкета успешно отправлена.")
                return redirect("students:survey")
            if isinstance(error, dict):
                for field, message in error.items():
                    form.add_error(field, message)
            else:
                messages.error(request, error)
    else:
        form = SurveyFormClass()

    return render(
        request,
        "students/survey/form.html",
        {
            "form": form,
            "survey": survey,
            "edu_year": edu_year,
        },
    )
