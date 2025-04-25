from django.urls import path

from integrator.views import *

app_name = 'integrator'
urlpatterns = [
    path('', integrator_index, name='index'),

    path('login/', sign_in_teacher_view, name='next-teacher-login'),
    path('logout/', sign_out_teacher_view, name='next-teacher-logout'),
]
