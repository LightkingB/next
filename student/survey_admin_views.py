from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from stepper.decorators import with_stepper
from student.consts import SURVEY_COMPLETIONS_PAGE_SIZE
from student.decorators import survey_admin_required
from student.forms import SurveyDeleteForm, SurveyForm, SurveyQuestionModalForm, SurveySubmissionFilterForm
from student.models import Survey, SurveyOption, SurveyQuestion, SurveySubmission
from student.services import SurveyService
from student.survey_export import SurveyExportService
from student.survey_ajax import (
    ajax_error,
    ajax_modal,
    ajax_success,
    is_ajax,
    render_modal,
)


def _questions_html(request, survey):
    return render_modal(
        request,
        "students/survey_admin/_questions_list.html",
        {"survey": survey},
    )


def _surveys_table_html(request, surveys):
    return render_modal(
        request,
        "students/survey_admin/_surveys_table.html",
        {"surveys": surveys},
    )


@with_stepper
@survey_admin_required
def survey_admin_list(request):
    surveys = Survey.objects.all()
    if request.method == "POST":
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey = form.save()
            if is_ajax(request):
                return ajax_success(
                    "Анкета создана.",
                    redirect=reverse("students:survey-admin-detail", kwargs={"survey_id": survey.id}),
                )
            messages.success(request, "Анкета создана.")
            return redirect("students:survey-admin-detail", survey_id=survey.id)
        if is_ajax(request):
            html = render_modal(
                request,
                "students/survey_admin/modals/survey_form.html",
                {"form": form, "action_url": request.path},
            )
            return ajax_error("Проверьте данные формы.", html)
    elif request.method == "GET" and is_ajax(request):
        form = SurveyForm()
        html = render_modal(
            request,
            "students/survey_admin/modals/survey_form.html",
            {"form": form, "action_url": reverse("students:survey-admin-list")},
        )
        return ajax_modal(html)

    return render(
        request,
        "students/survey_admin/survey_list.html",
        {"surveys": surveys, "navbar": "survey-admin", "title": "Анкетирование"},
    )


@with_stepper
@survey_admin_required
def survey_admin_detail(request, survey_id):
    survey = get_object_or_404(
        Survey.objects.prefetch_related("questions__options"),
        id=survey_id,
    )
    return render(
        request,
        "students/survey_admin/survey_detail.html",
        {"survey": survey, "navbar": "survey-admin", "title": survey.title},
    )


@with_stepper
@survey_admin_required
def survey_admin_edit(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    if request.method == "POST":
        form = SurveyForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            if is_ajax(request):
                return ajax_success("Анкета обновлена.", reload=True)
            messages.success(request, "Анкета обновлена.")
            return redirect("students:survey-admin-detail", survey_id=survey.id)
        if is_ajax(request):
            html = render_modal(
                request,
                "students/survey_admin/modals/survey_form.html",
                {"form": form, "survey": survey, "action_url": request.path},
            )
            return ajax_error("Проверьте данные формы.", html)
    elif is_ajax(request):
        form = SurveyForm(instance=survey)
        html = render_modal(
            request,
            "students/survey_admin/modals/survey_form.html",
            {"form": form, "survey": survey, "action_url": request.path},
        )
        return ajax_modal(html)

    return redirect("students:survey-admin-detail", survey_id=survey.id)


@with_stepper
@survey_admin_required
def survey_admin_delete(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    if request.method == "POST":
        form = SurveyDeleteForm(request.POST)
        if form.is_valid():
            survey.delete()
            if is_ajax(request):
                return ajax_success(
                    "Анкета удалена.",
                    redirect=reverse("students:survey-admin-list"),
                )
            messages.success(request, "Анкета удалена.")
            return redirect("students:survey-admin-list")
        if is_ajax(request):
            html = render_modal(
                request,
                "students/survey_admin/modals/survey_delete.html",
                {"form": form, "survey": survey, "action_url": request.path},
            )
            return ajax_error("Подтвердите удаление.", html)
    elif is_ajax(request):
        form = SurveyDeleteForm()
        html = render_modal(
            request,
            "students/survey_admin/modals/survey_delete.html",
            {"form": form, "survey": survey, "action_url": request.path},
        )
        return ajax_modal(html)

    return redirect("students:survey-admin-detail", survey_id=survey.id)


@with_stepper
@survey_admin_required
def survey_question_modal(request, survey_id, question_id=None):
    survey = get_object_or_404(Survey, id=survey_id)
    question = None
    if question_id:
        question = get_object_or_404(SurveyQuestion, id=question_id, survey=survey)

    if request.method == "POST":
        form = SurveyQuestionModalForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                if question is None:
                    question = SurveyQuestion.objects.create(
                        survey=survey,
                        text=form.cleaned_data["text"],
                        question_type=form.cleaned_data["question_type"],
                        order=SurveyService.next_question_order(survey),
                    )
                else:
                    question.text = form.cleaned_data["text"]
                    question.question_type = form.cleaned_data["question_type"]
                    question.save()
                    question.options.all().delete()

                SurveyOption.objects.bulk_create(
                    [
                        SurveyOption(question=question, text=text, order=index + 1)
                        for index, text in enumerate(form.cleaned_data["options"])
                    ]
                )

            survey = Survey.objects.prefetch_related("questions__options").get(id=survey.id)
            if is_ajax(request):
                return ajax_success(
                    "Вопрос сохранён.",
                    html_questions=_questions_html(request, survey),
                )
            messages.success(request, "Вопрос сохранён.")
            return redirect("students:survey-admin-detail", survey_id=survey.id)

        if is_ajax(request):
            html = render_modal(
                request,
                "students/survey_admin/modals/question_form.html",
                {
                    "form": form,
                    "survey": survey,
                    "question": question,
                    "action_url": request.path,
                },
            )
            return ajax_error("Проверьте данные формы.", html)

    elif is_ajax(request):
        form = SurveyQuestionModalForm.from_question(question) if question else SurveyQuestionModalForm()
        action_url = (
            reverse("students:survey-question-edit", kwargs={"survey_id": survey.id, "question_id": question.id})
            if question
            else reverse("students:survey-question-create", kwargs={"survey_id": survey.id})
        )
        html = render_modal(
            request,
            "students/survey_admin/modals/question_form.html",
            {"form": form, "survey": survey, "question": question, "action_url": action_url},
        )
        return ajax_modal(html)

    return redirect("students:survey-admin-detail", survey_id=survey.id)


@with_stepper
@survey_admin_required
def survey_question_delete(request, question_id):
    question = get_object_or_404(SurveyQuestion, id=question_id)
    survey = question.survey

    if request.method == "POST":
        question.delete()
        survey = Survey.objects.prefetch_related("questions__options").get(id=survey.id)
        if is_ajax(request):
            return ajax_success(
                "Вопрос удалён.",
                html_questions=_questions_html(request, survey),
            )
        messages.success(request, "Вопрос удалён.")
        return redirect("students:survey-admin-detail", survey_id=survey.id)

    if is_ajax(request):
        html = render_modal(
            request,
            "students/survey_admin/modals/question_delete.html",
            {"question": question, "action_url": request.path},
        )
        return ajax_modal(html)

    return redirect("students:survey-admin-detail", survey_id=survey.id)


@with_stepper
@survey_admin_required
def survey_question_move(request, question_id, direction):
    question = get_object_or_404(SurveyQuestion, id=question_id)
    SurveyService.swap_question_order(question, direction)
    survey = Survey.objects.prefetch_related("questions__options").get(id=question.survey_id)

    if is_ajax(request):
        return ajax_success(
            "Порядок обновлён.",
            html_questions=_questions_html(request, survey),
        )

    return redirect("students:survey-admin-detail", survey_id=survey.id)


@with_stepper
@survey_admin_required
def survey_completions(request, survey_id):
    is_pdf = request.GET.get("export") == "pdf"
    include_answers = request.GET.get("include_answers") == "1"

    survey_qs = Survey.objects.filter(pk=survey_id)
    if is_pdf and include_answers:
        from student.models import SurveyQuestion

        survey_qs = survey_qs.prefetch_related(
            Prefetch(
                "questions",
                queryset=SurveyQuestion.objects.order_by("order", "id"),
            )
        )
    else:
        survey_qs = survey_qs.only("id", "title")

    survey = get_object_or_404(survey_qs, pk=survey_id)

    filter_meta = SurveyExportService.completions_filter_meta(survey)
    filter_params = {
        k: v
        for k, v in request.GET.items()
        if k not in ("export", "include_answers", "page")
    }
    filter_form = SurveySubmissionFilterForm(
        survey,
        data=filter_params or None,
        edu_years=filter_meta["edu_years"],
    )

    cleaned = filter_form.cleaned_data if filter_form.is_bound and filter_form.is_valid() else {}
    if filter_form.is_bound and not filter_form.is_valid():
        messages.error(request, "Проверьте параметры фильтра.")

    submissions_qs = SurveyExportService.filtered_submissions(
        survey,
        cleaned,
        prefetch_answers=is_pdf and include_answers,
        for_list=not is_pdf,
    )

    if is_pdf:
        if filter_form.is_bound and not filter_form.is_valid():
            messages.error(request, "Исправьте фильтр перед экспортом.")
            return redirect("students:survey-admin-completions", survey_id=survey.id)

        submissions = list(submissions_qs)
        try:
            pdf_bytes = SurveyExportService.build_pdf(
                survey,
                submissions,
                cleaned,
                include_answers=include_answers,
                submissions_count=len(submissions),
            )
        except RuntimeError as exc:
            messages.error(request, str(exc))
            return redirect("students:survey-admin-completions", survey_id=survey.id)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        filename = SurveyExportService.pdf_filename(survey, include_answers=include_answers)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    paginator = Paginator(submissions_qs, SURVEY_COMPLETIONS_PAGE_SIZE)
    page_number = request.GET.get("page", 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)

    filters_active = any(
        cleaned.get(field)
        for field in ("edu_year", "date_from", "date_to", "group", "search")
    )

    return render(
        request,
        "students/survey_admin/completions.html",
        {
            "survey": survey,
            "page_obj": page_obj,
            "filter_form": filter_form,
            "group_suggestions": filter_meta["groups"],
            "submissions_count": paginator.count,
            "filters_active": filters_active,
            "navbar": "survey-admin",
            "title": f"Прошедшие студенты — {survey.title}",
        },
    )


@with_stepper
@survey_admin_required
def survey_submission_answers(request, survey_id, submission_id):
    get_object_or_404(Survey.objects.only("id"), pk=survey_id)
    submission = get_object_or_404(
        SurveyExportService.submission_with_answers_queryset(survey_id),
        pk=submission_id,
    )
    html = render_to_string(
        "students/survey_admin/_submission_answers_panel.html",
        {"submission": submission},
        request=request,
    )
    return HttpResponse(html)
