from core.settings.base import *

DEBUG = False
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USERNAME'),
        'PASSWORD': config('DB_PASSWORD'),
        'PORT': config('PORT'),
        'HOST': config('HOST'),
        'CONN_MAX_AGE': 60,
    }
}
