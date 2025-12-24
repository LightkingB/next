from .tasks import save_user_log

SENSITIVE_FIELDS = {'password', 'token', 'secret', 'csrfmiddlewaretoken'}
SKIP_PATHS = ['/static/', '/media/', '/health/', '/favicon.ico', '/admin/']


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


class UserActionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if any(request.path.startswith(p) for p in SKIP_PATHS):
            return response

        if request.user.is_authenticated:
            post_data = {k: v for k, v in request.POST.items() if k not in SENSITIVE_FIELDS}

            log_data = {
                'user_id': request.user.id,
                'username': request.user.email,
                'method': request.method,
                'path': request.get_full_path(),
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'success': 200 <= response.status_code < 300,
                'extra_info': {'GET': request.GET.dict(), 'POST': post_data, 'status_code': response.status_code}
            }

            save_user_log.delay(log_data)

        return response
