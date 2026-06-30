from collections import defaultdict

from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, Max, OuterRef, Prefetch

from stepper.models import EduYear
from student.choices import QuestionType
from student.models import StudentProfile, Survey, SurveyAnswerItem, SurveyQuestion, SurveySubmission

QUESTIONS_WITH_OPTIONS_PREFETCH = Prefetch(
    "questions",
    queryset=SurveyQuestion.objects.order_by("order", "id").prefetch_related("options"),
)


class SurveyService:
    @staticmethod
    def commission_edu_year():
        return EduYear.objects.filter(commission_active=True).first()

    @staticmethod
    def active_surveys():
        return (
            Survey.objects.filter(is_active=True)
            .annotate(question_count=Count("questions", distinct=True))
            .order_by("-created_at")
        )

    @staticmethod
    def active_surveys_with_questions():
        return (
            Survey.objects.filter(is_active=True)
            .annotate(question_count=Count("questions", distinct=True))
            .prefetch_related(QUESTIONS_WITH_OPTIONS_PREFETCH)
            .order_by("-created_at")
        )

    @staticmethod
    def survey_for_take(survey_id, user, edu_year):
        submission_exists = SurveySubmission.objects.filter(
            survey_id=OuterRef("pk"),
            user_id=user.pk,
            edu_year_id=edu_year.pk,
        )
        return (
            Survey.objects.filter(is_active=True, id=survey_id)
            .annotate(
                question_count=Count("questions", distinct=True),
                already_submitted=Exists(submission_exists),
            )
            .prefetch_related(QUESTIONS_WITH_OPTIONS_PREFETCH)
        )

    @staticmethod
    def user_has_profile(user):
        return StudentProfile.objects.filter(user_id=user.pk).values("id").exists()

    @staticmethod
    def dashboard_for_user(user):
        """Данные для списка анкет студента — без N+1."""
        edu_year = SurveyService.commission_edu_year()
        history = list(
            SurveySubmission.objects.filter(user=user)
            .select_related("survey", "edu_year")
            .order_by("-submitted_at")
        )

        if not edu_year:
            return edu_year, history, []

        submissions_by_survey = {
            item.survey_id: item for item in history if item.edu_year_id == edu_year.pk
        }
        active_surveys = list(SurveyService.active_surveys())

        active_items = []
        for survey in active_surveys:
            submission = submissions_by_survey.get(survey.id)
            active_items.append(
                {
                    "survey": survey,
                    "is_completed": survey.id in submissions_by_survey,
                    "submission": submission,
                    "can_take": survey.id not in submissions_by_survey and survey.question_count > 0,
                }
            )
        return edu_year, history, active_items

    @staticmethod
    def submission_counts_by_myedu_ids(myedu_ids, edu_year=None):
        """Bulk: myedu_id -> число прохождений (за учебный год комиссии или за всё время)."""
        normalized = [str(item) for item in myedu_ids if item]
        if not normalized:
            return {}

        qs = SurveySubmission.objects.filter(user__myedu_id__in=normalized)
        if edu_year:
            qs = qs.filter(edu_year=edu_year)

        counts = defaultdict(int)
        for row in qs.values("user__myedu_id").annotate(total=Count("id")):
            counts[str(row["user__myedu_id"])] = row["total"]
        return dict(counts)

    @staticmethod
    def submissions_for_myedu_id(myedu_id):
        if not myedu_id:
            return SurveySubmission.objects.none()
        return (
            SurveySubmission.objects.filter(user__myedu_id=str(myedu_id))
            .select_related("survey", "edu_year", "user")
            .prefetch_related(
                Prefetch(
                    "answers",
                    queryset=SurveyAnswerItem.objects.select_related("question", "option").order_by(
                        "question__order", "option__order"
                    ),
                )
            )
            .order_by("-submitted_at")
        )

    @staticmethod
    def active_survey():
        return SurveyService.active_surveys().first()

    @staticmethod
    def user_submissions(user):
        return (
            SurveySubmission.objects.filter(user=user)
            .select_related("survey", "edu_year")
            .order_by("-submitted_at")
        )

    @staticmethod
    def completed_survey_ids(user, edu_year):
        if not edu_year:
            return set()
        return set(
            SurveySubmission.objects.filter(user=user, edu_year=edu_year).values_list(
                "survey_id", flat=True
            )
        )

    @staticmethod
    def has_submission(user, survey, edu_year):
        if not survey or not edu_year:
            return False
        return SurveySubmission.objects.filter(
            user=user,
            survey=survey,
            edu_year=edu_year,
        ).exists()

    @staticmethod
    def get_submission(user, survey, edu_year):
        return SurveySubmission.objects.filter(
            user=user,
            survey=survey,
            edu_year=edu_year,
        ).first()

    @staticmethod
    def validate_answers(survey, cleaned_data):
        errors = {}
        questions = list(survey.questions.all())
        option_ids_by_question = {
            question.id: {option.id for option in question.options.all()}
            for question in questions
        }

        for question in questions:
            field_name = f"q_{question.id}"
            value = cleaned_data.get(field_name)

            if question.question_type == QuestionType.RADIO:
                if not value:
                    errors[field_name] = "Выберите вариант ответа."
                    continue
                try:
                    option_id = int(value)
                except (TypeError, ValueError):
                    errors[field_name] = "Некорректный вариант ответа."
                    continue
                if option_id not in option_ids_by_question[question.id]:
                    errors[field_name] = "Некорректный вариант ответа."
            else:
                if not value:
                    errors[field_name] = "Выберите хотя бы один вариант ответа."
                    continue
                for raw_option_id in value:
                    try:
                        option_id = int(raw_option_id)
                    except (TypeError, ValueError):
                        errors[field_name] = "Некорректный вариант ответа."
                        break
                    if option_id not in option_ids_by_question[question.id]:
                        errors[field_name] = "Некорректный вариант ответа."
                        break

        return errors

    @classmethod
    @transaction.atomic
    def save_submission(cls, user, survey, edu_year, cleaned_data, student_data):
        validation_errors = cls.validate_answers(survey, cleaned_data)
        if validation_errors:
            return None, validation_errors

        submission = SurveySubmission(
            user=user,
            survey=survey,
            edu_year=edu_year,
            student_fio=student_data.get("student_fio", user.full_name),
            student_login=user.email,
            student_group=student_data.get("group", ""),
        )
        try:
            submission.save()
        except IntegrityError:
            return None, "Анкета уже заполнена."

        answer_items = []
        for question in survey.questions.all():
            field_name = f"q_{question.id}"
            value = cleaned_data.get(field_name)
            if question.question_type == QuestionType.RADIO:
                option_ids = [int(value)]
            else:
                option_ids = [int(option_id) for option_id in value]

            for option_id in option_ids:
                answer_items.append(
                    SurveyAnswerItem(
                        submission=submission,
                        question_id=question.id,
                        option_id=option_id,
                    )
                )

        SurveyAnswerItem.objects.bulk_create(answer_items)
        return submission, None

    @staticmethod
    def next_question_order(survey):
        current_max = survey.questions.aggregate(max_order=Max("order"))["max_order"]
        return (current_max or 0) + 1

    @staticmethod
    def next_option_order(question):
        current_max = question.options.aggregate(max_order=Max("order"))["max_order"]
        return (current_max or 0) + 1

    @staticmethod
    def swap_question_order(question, direction):
        if direction == "up":
            sibling = question.survey.questions.filter(order__lt=question.order).order_by("-order").first()
        else:
            sibling = question.survey.questions.filter(order__gt=question.order).order_by("order").first()

        if not sibling:
            return False

        question.order, sibling.order = sibling.order, question.order
        question.save(update_fields=["order"])
        sibling.save(update_fields=["order"])
        return True

    @staticmethod
    def swap_option_order(option, direction):
        if direction == "up":
            sibling = option.question.options.filter(order__lt=option.order).order_by("-order").first()
        else:
            sibling = option.question.options.filter(order__gt=option.order).order_by("order").first()

        if not sibling:
            return False

        option.order, sibling.order = sibling.order, option.order
        option.save(update_fields=["order"])
        sibling.save(update_fields=["order"])
        return True
