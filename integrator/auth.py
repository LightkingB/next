"""
Единый вход для студентов и сотрудников (логин и пароль MyEDU).

После входа пользователь попадает:
  1) на страницу, которую открывал до входа (?next=, только внутри сайта);
  2) иначе сотрудник (признак MyEDU или любая роль в системе) — в «Модули», студент — в личный кабинет.
"""
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from bsadmin.forms import LoginForm
from bsadmin.services import UserService
from utils.myedu import MyEduService

LOGIN_TEMPLATE = "auth/login.html"


def _safe_next(request):
    url = request.POST.get("next") or request.GET.get("next") or ""
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
        return url
    return ""


def _home_for(user):
    if user.is_worker or user.roles.exists():
        return reverse("integrator:index")
    return reverse("students:index")


def sign_in_view(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        return redirect(next_url or _home_for(request.user))

    form = LoginForm(request.POST or None)
    error = None
    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data["email"].strip()
            password = form.cleaned_data["password"]
            user = authenticate(email=email, password=password)
            if user is None:
                myedu_data, success = MyEduService.get_user_auth(email, password)
                if success:
                    user = UserService().update_or_create_user(email, password, myedu_data)
                elif myedu_data is None:
                    error = "Не удалось связаться с MyEDU. Повторите попытку через минуту."
                else:
                    error = "Неверный логин или пароль. Используйте данные от MyEDU."
            if user is not None:
                login(request, user)
                return redirect(next_url or _home_for(user))
        else:
            error = "Введите логин и пароль."

    return render(request, LOGIN_TEMPLATE, {
        "form": form,
        "error": error,
        "next": next_url,
    }, status=401 if error else 200)


def sign_out_view(request):
    for key in ("user_data", "access"):
        request.session.pop(key, None)
    logout(request)
    return redirect("students:next-student-login")
