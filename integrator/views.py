from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect

from bsadmin.forms import LoginForm
from bsadmin.services import HttpMyEduServiceAPI, UserService
from utils.errors import handle_error


def sign_in_teacher_view(request):
    user_service = UserService()
    if request.user.is_authenticated:
        return redirect("integrator:index")

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
                    return handle_error(
                        request,
                        {"form": form},
                        template_name="teachers/profile/login.html",
                        message="Проверьте правильность данных и повторите попытку."
                    )

            request.session['user_id'] = user.id
            login(request, user)
            return redirect("integrator:index")
    context = {
        "navbar": "teacher-next-login",
        "form": LoginForm()
    }
    return render(request, "teachers/profile/login.html", context)


def sign_out_teacher_view(request):
    if request.session.get('user_data', None):
        del request.session['user_data']
    if request.session.get('access', None):
        del request.session['access']
    logout(request)
    return redirect("integrator:next-teacher-login")


def integrator_index(request):
    if not request.user.is_authenticated:
        return redirect("integrator:next-teacher-login")
    context = {
        "navbar": "integrator"
    }
    return render(request, "teachers/integrator.html", context)
