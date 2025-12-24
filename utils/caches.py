from django.core.cache import cache

CACHE_TIMEOUT = 5 * 60 * 60


def get_student_from_cache(student_id):
    """
    Достает студента из Redis по student_id.
    Возвращает словарь данных или None, если нет в кеше.
    """
    cache_key = f"student:{student_id}"
    return cache.get(cache_key)


def set_student_to_cache(student):
    """
    Сохраняет данные студента в Redis на 5 часов.
    Не сохраняет, если student == None.
    """
    if not student or student == "":
        return

    student_id = student.get("student_id")
    if not student_id:
        return

    cache_key = f"student:{student_id}"
    cache.set(cache_key, student, timeout=CACHE_TIMEOUT)
