from django.urls import path

from stepper.views import *

app_name = 'stepper'
urlpatterns = [
    path('', route, name='route'),
    path('students/', cs_index, name='index'),
    path('student/<int:myedu_id>/detail/', cs_detail, name='cs-detail'),
    path('student/<int:myedu_id>/force/', cs_force, name='cs-force'),
    path('student/<int:myedu_id>/order/done/', order_done, name='order-done'),
    path('student/<int:myedu_id>/request/', request_cs, name='request-cs'),
    path('student/<int:id>/step/remove/', step_remove, name='step-remove'),
    path('student/<int:id>/step/<int:trajectory_id>/rating/', step_rating, name='step-rating'),

    path('stage/employee/', stage_employee, name='stage-employee'),
    path('stage/employee/create/', stage_employee_create, name='stage-employee-create'),
    path('stage/employee/<int:pk>/update/', stage_employee_update, name='stage-employee-update'),

    path('cs/', cs, name='cs'),
    path('cs/done/', cs_done, name='cs-done'),
    path('cs/issuance/', cs_issuance, name='cs-issuance'),
    path('cs/<int:stage>/stage/', cs_debt_stage, name='cs-stage'),
    path('cs/<int:cs_id>/report/', cs_report, name='cs-report'),
    path('cs/<int:cs_id>/step/undo/', cs_step_undo, name='cs-step-undo'),
    path('cs/<int:myedu_id>/history/', cs_history, name='cs-history'),
    path('cs/<int:cs_id>/history/detail/', cs_history_detail, name='cs-history-detail'),

    path('spec/', spec, name='spec'),
    path('spec/students/', spec_students, name='spec-students'),
    path('spec/diploma/', spec_diploma, name='spec-diploma'),
    path('spec/history/', spec_history, name='spec-history'),
    path('spec/avn/', spec_avn, name='spec-avn'),
    path('spec/<int:id>/<int:myedu_id>/student/', spec_part, name='spec-part'),
    path('spec/<int:id>/<int:myedu_id>/sync/', spec_sync, name='spec-sync'),
    path('spec/<int:id>/<int:myedu_id>/student/double', spec_part_double, name='spec-part-double'),
    path('spec/<int:id>/<int:myedu_id>/student/remove/', spec_part_remove, name='spec-part-remove'),

    path('archive/', archive, name='archive'),
    path('archive/history/', archive_history, name='archive-history'),
    path('archive/avn/', archive_avn, name='archive-avn'),
    path('archive/<int:id>/<int:myedu_id>/student/', archive_part, name='archive-part'),
    path('archive/<int:id>/<int:myedu_id>/student/remove/', archive_part_remove, name='archive-part-remove'),

    path('debts/', debts, name='debts'),
    path('debts/<int:id>/comment/', debts_comment, name='debts-comment'),

    path("api/check_clearance_sheet/", check_clearance_sheet, name="check_clearance_sheet"),
    path("api/create_clearance_sheet/", create_clearance_sheet, name="create_clearance_sheet"),

    path("api/specailities/", load_specialities, name="load-specialities"),
    path("api/create-diploma/", diploma_create_ajax, name="create-diploma"),

    path('api/issuance-delete/', cs_issuance_delete, name='issuance-delete'),

    path("teachers/", teachers, name="teachers"),
    path("teacher/<str:myedu_id>/cs/", teacher_cs_detail, name="teacher-cs-detail"),
    path('teachers/cs/', teachers_cs, name='teachers-cs'),
    path('teachers/debts/', teacher_debts, name='teacher-debts'),
    path('teachers/debts/<int:id>/comment/', teacher_debt_comments, name='teacher-debt-comments'),
]
