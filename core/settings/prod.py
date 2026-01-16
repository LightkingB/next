from core.settings.base import *

DEBUG = False
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
