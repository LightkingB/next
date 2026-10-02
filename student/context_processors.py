from student.myedu_student import get_student


def portal_user(request):
    """ФИО и инициалы для шапки портала. MyEDU вызывается один раз на запрос и кэшируется."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    match = getattr(request, "resolver_match", None)
    if not match or match.app_name != "students":
        return {}

    data, _ = get_student(request)
    fio = (data or {}).get("student_fio") or user.full_name or user.email
    parts = fio.split()
    return {
        "portal_user_fio": fio,
        "portal_user_email": user.email,
        "portal_user_initials": "".join(p[0] for p in parts[:2]).upper() if parts else "?",
    }
