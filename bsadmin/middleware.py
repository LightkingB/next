# import logging
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404

# Получаем логгер. Имя 'bsheet.auth_access' будет использоваться в settings.py
# logger = logging.getLogger('bsheet.auth_access')


class AuthRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Список ИМЕН URL-адресов, которые являются публичными.
        # Эти URL-адреса доступны без аутентификации.
        self.public_urls = [
            'auth_required',  # Наша страница "Доступ ограничен"
            'students:next-student-login',  # Страница входа для студентов
            'integrator:next-teacher-login',  # Страница входа для преподавателей
            'stepper:qr-code-status',  # Страница статуса QR-кода
            # Добавьте сюда любые другие URL-адреса, которые должны быть публичными,
            # например, главная страница, страницы "О нас", "Контакты" и т.д.
            # Если у вас есть URL-ы для сброса пароля, их тоже нужно добавить:
            # 'password_reset', 'password_reset_done', 'password_reset_confirm', 'password_reset_complete'
        ]

    def __call__(self, request):
        # 1. Пропускаем, если пользователь уже авторизован
        if request.user.is_authenticated:
            return self.get_response(request)

        # 2. Определяем имя текущего URL для проверки
        url_name = None
        try:
            match = resolve(request.path_info)
            url_name = match.url_name
            # Для имен URL с namespace (например, 'students:next-student-login')
            if match.app_names:
                url_name = f"{match.app_names[0]}:{url_name}"
        except Resolver404:
            # Если URL не найден, это не наша забота, пусть Django обрабатывает 404
            pass

        # 3. Пропускаем, если URL находится в нашем "белом списке" публичных URL
        if url_name in self.public_urls:
            return self.get_response(request)

        # --- ЛОГИКА ПЕРЕХВАТА И РАСШИРЕННОГО ЛОГИРОВАНИЯ ---
        # Сюда попадают только неавторизованные пользователи,
        # которые пытаются зайти на закрытую страницу.

        # Собираем всю возможную информацию о запросе в словарь
        # log_details = {
        #     'user_status': 'AnonymousUser',  # Явно указываем, что пользователь не авторизован
        #     'ip_address': request.META.get('REMOTE_ADDR', 'N/A'),
        #     'full_url': request.build_absolute_uri(),  # Полный URL с http/https и параметрами
        #     'scheme': request.scheme,  # http или https
        #     'method': request.method,  # GET, POST и т.д.
        #     'user_agent': request.META.get('HTTP_USER_AGENT', 'N/A'),
        #     'requested_path': request.path,  # Только путь
        #     'requested_url_name': url_name,  # Имя URL-паттерна
        # }

        # Записываем в лог структурированное сообщение
        # Мы используем параметр `extra`, чтобы передать наш словарь.
        # Это позволяет настроить форматтер логов для вывода этих данных в JSON или другой формат.
        # logger.warning(
        #     f"Попытка неавторизованного доступа к '{request.path}'",
        #     extra=log_details
        # )

        # Перенаправляем пользователя на единую страницу "Доступ ограничен"
        return redirect(reverse('auth_required'))
