from django.conf import settings


class DisableStaticCacheMiddleware:
    """В DEBUG отключает кэш браузера для /static/ — запасной вариант к ?v=mtime."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and request.path.startswith(settings.STATIC_URL):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
