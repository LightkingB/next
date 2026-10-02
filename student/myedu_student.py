"""
Данные студента из MyEDU для студенческого портала.

Один вызов MyEDU на запрос (результат запоминается на объекте request), плюс кэш в Redis:
  • студент найден      — 5 часов;
  • в MyEDU его нет      — 30 минут (раньше такой ответ не кэшировался, и каждая страница ждала MyEDU);
  • MyEDU не ответил     — 1 минута (не долбим упавший сервис, но быстро пробуем снова).
"""
from django.core.cache import cache

from bsadmin.consts import MYEDU_LOGIN, MYEDU_PASSWORD
from stepper.consts import STUDENT_STEPPER_URL
from utils.myedu import MyEduService

FOUND = "found"
NOT_FOUND = "not_found"
UNAVAILABLE = "unavailable"

_TTL = {FOUND: 5 * 60 * 60, NOT_FOUND: 30 * 60, UNAVAILABLE: 60}


def _fetch(myedu_id):
    result = MyEduService._safe_request("POST", STUDENT_STEPPER_URL, data={
        "login": MYEDU_LOGIN, "password": MYEDU_PASSWORD,
        "faculty_id": 0, "speciality_id": 0, "search": myedu_id,
    })
    if result is None:
        return UNAVAILABLE, None
    if isinstance(result, list):
        result = result[0] if result else None
    if isinstance(result, dict) and result:
        return FOUND, result
    return NOT_FOUND, None


def get_student(request):
    """Возвращает (данные | None, статус: found / not_found / unavailable)."""
    cached = getattr(request, "_portal_student", None)
    if cached is not None:
        return cached

    user = request.user
    if not getattr(user, "is_authenticated", False) or not user.myedu_id:
        request._portal_student = (None, NOT_FOUND)
        return request._portal_student

    key = f"portal-student:{user.myedu_id}"
    try:
        stored = cache.get(key)
    except Exception:
        stored = None
    if stored is None:
        status, data = _fetch(user.myedu_id)
        stored = {"status": status, "data": data}
        try:
            cache.set(key, stored, _TTL[status])
        except Exception:
            pass

    request._portal_student = (stored["data"], stored["status"])
    return request._portal_student
