from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Prefetch
from django.shortcuts import render, redirect, get_object_or_404

from bsadmin.forms import LoginForm
from bsadmin.services import UserService
from stepper.consts import STUDENT_STEPPER_URL
from stepper.decorators import with_stepper
from stepper.models import ClearanceSheet, Trajectory
from utils.caches import EntityCache
from utils.errors import handle_error
from utils.myedu import MyEduService


@with_stepper
def student_index(request):
    # if not request.user.is_authenticated:
    #     return redirect("students:next-student-login")

    myedu_id = request.user.myedu_id

    student = EntityCache.get_or_set(
        entity_id=myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": myedu_id,
        },
    )

    active_cs_qs = ClearanceSheet.objects.filter(myedu_id=myedu_id, completed_at__isnull=True)
    has_cs = active_cs_qs.exists()

    if request.method == "POST" and student and not has_cs:
        ClearanceSheet.objects.create(
            myedu_id=myedu_id,
            student_fio=student.get('student_fio', ''),
            myedu_faculty_id=student.get('faculty_id', 0),
            myedu_faculty=student.get('faculty_name', ''),
            myedu_spec_id=student.get('speciality_id', 0),
            myedu_spec=student.get('speciality_name', ''),
            order_status=student.get('id_movement_info', ''),
            order=student.get('info', ''),
            order_date=student.get('date_movement', ''),
            edu_year=request.stepper.active_edu_year()
        )
        messages.success(request, "Заявка успешно отправлена")
        has_cs = True

    trajectory_prefetch = Prefetch(
        'trajectory_set',
        queryset=Trajectory.objects.select_related(
            'template_stage',
            'template_stage__stage',
            'assigned_by'
        )
    )

    cs_list = ClearanceSheet.objects.filter(myedu_id=myedu_id).prefetch_related(trajectory_prefetch)

    return render(request, "students/index.html", {
        "cs_list": cs_list,
        "has_cs": has_cs,
        "student": student
    })


def student_cs_history_detail(request, cs_id):
    student = get_object_or_404(ClearanceSheet, id=cs_id)
    trajectories = (
        Trajectory.objects.filter(clearance_sheet=student)
        .select_related("template_stage", "template_stage__stage")
        .prefetch_related("stagestatus_set", "stagestatus_set__processed_by")
    )

    context = {
        "student": student,
        "trajectories": trajectories,
    }
    return render(request, "students/cs-history.html", context)


@with_stepper
def sign_in_student_view(request):
    # if request.user.is_authenticated:
    #     return redirect("students:index")

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email', None)
            password = form.cleaned_data.get('password', None)
            user = authenticate(email=email, password=password)

            if user is None:
                myedu_data, success = MyEduService.get_user_auth(email, password)
                if success:
                    user = request.bs.update_or_create_user(email, password, myedu_data)
                else:
                    return handle_error(
                        request,
                        {"form": form},
                        template_name="students/login.html",
                        message="Проверьте правильность данных и повторите попытку."
                    )

            login(request, user)
            return redirect("students:index")
    context = {
        "navbar": "student-next-login",
        "form": LoginForm()
    }
    return render(request, "students/login.html", context)


def sign_out_student_view(request):
    if request.session.get('user_data', None):
        del request.session['user_data']
    if request.session.get('access', None):
        del request.session['access']
    logout(request)
    return redirect("students:next-student-login")
