from django.urls import path

from student.views import *

app_name = 'students'
urlpatterns = [
    path('', student_index, name='index'),
    path('cs/<int:cs_id>/history/', student_cs_history_detail, name='cs-history'),
    path('login/', sign_in_student_view, name='next-student-login'),
    path('logout/', sign_out_student_view, name='next-student-logout'),
]
