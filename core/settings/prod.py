from core.settings.base import *

DEBUG = False
# Без этой строки Django игнорирует заголовок от Nginx и думает, что запрос пришел по HTTP
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Чтобы куки сессии и CSRF не летали по обычному HTTP
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Если вы хотите, чтобы Django сам перекидывал с http на https
SECURE_SSL_REDIRECT = True
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USERNAME'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'PORT': config('PORT'),
#         'HOST': config('HOST'),
#         'CONN_MAX_AGE': 60,
#     }
# }

CSRF_TRUSTED_ORIGINS = [
    'https://next.oshsu.kg',
    'https://www.next.oshsu.kg',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USERNAME'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': '127.0.0.1',
        'PORT': '6432',
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 5,
        }
    }
}
