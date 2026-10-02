"""Общие данные личного кабинета студента: «Мои данные» и сводка по анкетам."""
from bsadmin.role_utils import user_role_names
from student.myedu_student import FOUND, NOT_FOUND, UNAVAILABLE, get_student
from student.services import SurveyService


def build_profile(user, student, latest_cs=None):
    """Личные данные: из MyEDU, а если их нет — из последнего обходного листа."""
    student = student or {}
    fio = student.get("student_fio") or (latest_cs.student_fio if latest_cs else "") or user.full_name
    return {
        "fio": fio,
        "myedu_id": user.myedu_id,
        "email": user.email,
        "faculty": student.get("faculty_name") or (latest_cs.myedu_faculty if latest_cs else ""),
        "speciality": student.get("speciality_name") or (latest_cs.myedu_spec if latest_cs else ""),
        "order_status": student.get("id_movement_info") or (latest_cs.order_status if latest_cs else ""),
        "order": student.get("info") or (latest_cs.order if latest_cs else ""),
        "order_date": student.get("date_movement") or (latest_cs.order_date if latest_cs else ""),
    }


def survey_summary(user):
    edu_year, _, items = SurveyService.dashboard_for_user(user)
    takeable = [item for item in items if item["can_take"] or item["is_completed"]]
    done = sum(1 for item in takeable if item["is_completed"])
    first_todo = next((item["survey"] for item in items if item["can_take"]), None)
    return {"edu_year": edu_year, "total": len(takeable), "done": done,
            "left": len(takeable) - done, "first_todo": first_todo}


def is_employee(request, student=None):
    """Сотрудник/преподаватель: флаг из MyEDU или любая роль сотрудника в системе.
    Если MyEDU нашёл данные студента, человек считается студентом."""
    if student:
        return False
    return bool(request.user.is_worker or user_role_names(request))


def dashboard_context(request, latest_cs=None, tab="overview", with_surveys=True):
    student, status = get_student(request)
    return {
        "is_employee": is_employee(request, student),
        "student": student,
        "myedu_status": status,
        "profile": build_profile(request.user, student, latest_cs),
        "survey_kpi": survey_summary(request.user) if with_surveys else None,
        "dash_tab": tab,
        "MYEDU_FOUND": FOUND, "MYEDU_NOT_FOUND": NOT_FOUND, "MYEDU_UNAVAILABLE": UNAVAILABLE,
    }
