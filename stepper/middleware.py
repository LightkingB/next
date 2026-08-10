from .tasks import save_user_log

SENSITIVE_FIELDS = frozenset({'password', 'token', 'secret', 'csrfmiddlewaretoken'})
OMIT_POST_BODY_FIELDS = frozenset({'signature', 'profile'})
MAX_POST_VALUE_LENGTH = 500
SKIP_PATHS = ('/static/', '/media/', '/health/', '/favicon.ico', '/admin/', '/silk/')
LOG_BODY_METHODS = frozenset({'POST', 'PUT', 'PATCH'})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def sanitize_post_for_log(post):
    """Краткая история POST без тяжёлых base64 и секретов."""
    sanitized = {}
    for key in post:
        if key in SENSITIVE_FIELDS:
            continue
        values = post.getlist(key)
        sanitized[key] = [_sanitize_post_value(key, value) for value in values]
        if len(sanitized[key]) == 1:
            sanitized[key] = sanitized[key][0]
    return sanitized


def _sanitize_post_value(key, value):
    if key in OMIT_POST_BODY_FIELDS:
        if not value:
            return '<empty>'
        if value.startswith('data:image/'):
            return f'<image {len(value)} chars>'
        return f'<omitted {len(value)} chars>'

    if len(value) <= MAX_POST_VALUE_LENGTH:
        return value

    trimmed = value[:MAX_POST_VALUE_LENGTH]
    return f'{trimmed}… (+{len(value) - MAX_POST_VALUE_LENGTH} chars)'


class UserActionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith(SKIP_PATHS):
            return response

        if not request.user.is_authenticated:
            return response

        extra_info = {'status_code': response.status_code}
        if request.GET:
            extra_info['GET'] = request.GET.dict()
        if request.method in LOG_BODY_METHODS and request.POST:
            extra_info['POST'] = sanitize_post_for_log(request.POST)

        log_data = {
            'user_id': request.user.id,
            'username': request.user.email,
            'method': request.method,
            'path': request.get_full_path(),
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'success': 200 <= response.status_code < 300,
            'extra_info': extra_info,
        }

        save_user_log.delay(log_data)

        return response
