import logging

import httpx
from django.contrib import messages

from bsadmin.consts import MYEDU_LOGIN, MYEDU_PASSWORD, API_URL

logger = logging.getLogger(__name__)
limits = httpx.Limits(
    max_connections=50,
    max_keepalive_connections=20
)

timeouts = httpx.Timeout(7.0, connect=2.0, read=5.0)

client = httpx.Client(
    limits=limits,
    timeout=timeouts,
    http2=False
)


class MyEduService:
    """Единый сервис для работы с внешним API MyEdu"""

    @staticmethod
    def _safe_request(method, url, **kwargs):
        """Внутренний вспомогательный метод для выполнения запросов"""
        try:
            response = client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectTimeout:
            logger.error(f"Connect Timeout: Не удалось подключиться к {url} за 2 сек.")
        except httpx.ReadTimeout:
            logger.warning(f"Read Timeout: API {url} не прислало данные за 5 сек.")
        except httpx.HTTPStatusError as exc:
            logger.error(f"API Error: Код {exc.response.status_code} для {url}")
        except Exception as e:
            logger.error(f"Unexpected API error: {e}")
        return None

    @classmethod
    def handle_student_search(cls, request):
        """Метод поиска студента (был в отдельной функции)"""
        student_query = request.POST.get("student")
        if not student_query:
            return None

        url = f"{API_URL}/obhadnoi/searchstudent"
        return cls._safe_request("POST", url, data={"search": student_query})

    @classmethod
    def fetch_students(cls, request, api_url, search_query=None):
        method = "POST" if search_query else "GET"
        data = {"search": search_query} if search_query else None

        result = cls._safe_request(method, api_url, data=data)
        if result is None:
            messages.error(request, "Не удалось получить список студентов.")
            return []
        return result

    @classmethod
    def get_stepper_data_from_api(cls, url, search=None, faculty_id=0, specialty_id=0):
        payload = {
            "login": MYEDU_LOGIN,
            "password": MYEDU_PASSWORD,
            "faculty_id": faculty_id,
            "speciality_id": specialty_id
        }
        if search:
            payload["search"] = search

        result = cls._safe_request("POST", url, data=payload)
        return result if isinstance(result, list) else []

    @classmethod
    def get_user_auth(cls, email, password):
        payload = {"email": email, "password": password}
        url = f"{API_URL}/checkuser"
        result = cls._safe_request("POST", url, data=payload)

        if result and isinstance(result, dict):
            return result, result.get('success', False)
        return None, False

    @classmethod
    def fetch_faculties(cls):
        url = f"{API_URL}/open/faculty"
        return cls._safe_request("GET", url) or []

    @classmethod
    def fetch_specialities(cls, faculty_id):
        url = f"{API_URL}/open/getspecialitywithidfaculty"
        params = {"id_faculty": faculty_id}
        return cls._safe_request("GET", url, params=params) or []
