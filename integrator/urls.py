from django.urls import path

from integrator.auth import sign_in_view, sign_out_view
from integrator.views import *

app_name = 'integrator'
urlpatterns = [
    path('', integrator_index, name='index'),

    path('login/', sign_in_view, name='next-teacher-login'),
    path('logout/', sign_out_view, name='next-teacher-logout'),
]
