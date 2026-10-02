from django.contrib import messages
from django.db.models import Count, Prefetch, Q
from django.shortcuts import render, redirect, get_object_or_404

from stepper.decorators import with_stepper
from stepper.models import ClearanceSheet, Trajectory, StageStatus
from student.dashboard import dashboard_context
from student.myedu_student import get_student


@with_stepper
def student_index(request):
    # if not request.user.is_authenticated:
    #     return redirect("students:next-student-login")

    myedu_id = request.user.myedu_id
    student, _ = get_student(request)

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
        messages.success(request, "Заявка на обходной лист отправлена. Этапы появятся ниже.")
        # Post/Redirect/Get: обновление страницы не отправит заявку повторно.
        return redirect("students:index")

    trajectory_prefetch = Prefetch(
        'trajectory_set',
        queryset=Trajectory.objects.select_related(
            'template_stage',
            'template_stage__stage',
            'assigned_by'
        ).prefetch_related(
            Prefetch(
                'stagestatus_set',
                queryset=StageStatus.objects.select_related('processed_by').order_by('-created_at')
            )
        ).order_by('template_stage__order')
    )

    cs_list = (
        ClearanceSheet.objects.filter(myedu_id=myedu_id)
        .annotate(
            trajectory_total=Count('trajectory', distinct=True),
            trajectory_done=Count(
                'trajectory',
                filter=Q(trajectory__completed_at__isnull=False),
                distinct=True,
            ),
        )
        .prefetch_related(trajectory_prefetch)
        .order_by('-issued_at')
    )

    cs_list = list(cs_list)
    for cs in cs_list:
        steps = list(cs.trajectory_set.all())
        cs.current_step = next((t for t in steps if t.completed_at is None), None)
        cs.current_index = steps.index(cs.current_step) + 1 if cs.current_step else None
    active_cs = next((cs for cs in cs_list if not cs.completed_at), None)

    context = {
        "cs_list": cs_list,
        "has_cs": has_cs,
        "active_cs": active_cs,
        **dashboard_context(request, cs_list[0] if cs_list else None, tab="overview"),
    }
    return render(request, "students/index.html", context)


def student_cs_history_detail(request, cs_id):
    student = get_object_or_404(ClearanceSheet, id=cs_id, myedu_id=request.user.myedu_id)
    trajectories = (
        Trajectory.objects.filter(clearance_sheet=student)
        .select_related("template_stage", "template_stage__stage")
        .prefetch_related("stagestatus_set", "stagestatus_set__processed_by")
        .order_by("template_stage__order")
    )

    context = {
        "student": student,
        "trajectories": trajectories,
    }
    return render(request, "students/cs-history.html", context)


