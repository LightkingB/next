from django.urls import path

from student.survey_admin_views import (
    survey_admin_delete,
    survey_admin_detail,
    survey_admin_edit,
    survey_admin_list,
    survey_completions,
    survey_question_delete,
    survey_question_modal,
    survey_question_move,
    survey_submission_answers,
)
from student.survey_views import survey_index, survey_phone, survey_take
from student.views import sign_in_student_view, sign_out_student_view, student_cs_history_detail, student_index

app_name = "students"
urlpatterns = [
    path("", student_index, name="index"),
    path("cs/<int:cs_id>/history/", student_cs_history_detail, name="cs-history"),
    path("login/", sign_in_student_view, name="next-student-login"),
    path("logout/", sign_out_student_view, name="next-student-logout"),
    path("survey/", survey_index, name="survey"),
    path("survey/phone/", survey_phone, name="survey-phone"),
    path("survey/<int:survey_id>/take/", survey_take, name="survey-take"),
    path("survey/admin/", survey_admin_list, name="survey-admin-list"),
    path("survey/admin/<int:survey_id>/", survey_admin_detail, name="survey-admin-detail"),
    path("survey/admin/<int:survey_id>/edit/", survey_admin_edit, name="survey-admin-edit"),
    path("survey/admin/<int:survey_id>/delete/", survey_admin_delete, name="survey-admin-delete"),
    path("survey/admin/<int:survey_id>/completions/", survey_completions, name="survey-admin-completions"),
    path(
        "survey/admin/<int:survey_id>/completions/<int:submission_id>/answers/",
        survey_submission_answers,
        name="survey-submission-answers",
    ),
    path(
        "survey/admin/<int:survey_id>/questions/create/",
        survey_question_modal,
        name="survey-question-create",
    ),
    path(
        "survey/admin/<int:survey_id>/questions/<int:question_id>/edit/",
        survey_question_modal,
        name="survey-question-edit",
    ),
    path(
        "survey/admin/questions/<int:question_id>/delete/",
        survey_question_delete,
        name="survey-question-delete",
    ),
    path(
        "survey/admin/questions/<int:question_id>/move/<str:direction>/",
        survey_question_move,
        name="survey-question-move",
    ),
]
