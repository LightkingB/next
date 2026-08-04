from stepper.consts import STUDENT_STEPPER_URL
from utils.caches import EntityCache
from utils.myedu import MyEduService


def portal_user(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    match = getattr(request, "resolver_match", None)
    if not match or match.app_name != "students":
        return {}

    fio = user.full_name or user.email
    student_data = EntityCache.get_or_set(
        entity_id=user.myedu_id,
        fetch_func=MyEduService.get_stepper_data_from_api,
        fetch_kwargs={
            "url": STUDENT_STEPPER_URL,
            "search": user.myedu_id,
        },
    )
    if student_data and student_data.get("student_fio"):
        fio = student_data["student_fio"]

    return {
        "portal_user_fio": fio,
        "portal_user_email": user.email,
    }
