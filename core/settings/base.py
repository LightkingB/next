import os
from pathlib import Path

from decouple import config
from django.contrib import messages

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = ['*']

FIRST_APPS = [
    'modeltranslation',
]

SYSTEM_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_APPS = [
    'django_filters',
    'debug_toolbar',
    'crispy_forms',
    'ckeditor',
    'ckeditor_uploader',
    'silk',
]

CUSTOM_APPS = [
    'cms.apps.CmsConfig',
    'bsadmin.apps.BsadminConfig',
    'stepper.apps.StepperConfig',
    'integrator.apps.IntegratorConfig',
    'student.apps.StudentConfig',
    'archives.apps.ArchivesConfig',
]

INSTALLED_APPS = FIRST_APPS + SYSTEM_APPS + CUSTOM_APPS + THIRD_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'silk.middleware.SilkyMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'stepper.middleware.UserActionLoggingMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'bsadmin.context_processors.roles_constants'
            ],
        },
    },
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

WSGI_APPLICATION = 'core.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Asia/Bishkek'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "static", "static_root")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static", "static_dirs"),
]
MEDIA_ROOT = os.path.join(BASE_DIR, "static", "media")
MEDIA_URL = '/media/'

INTERNAL_IPS = [
    '127.0.0.1',
]

CSRF_TRUSTED_ORIGINS = [
    'https://next.oshsu.kg',
    'http://next.oshsu.kg',
    'https://www.next.oshsu.kg',
]

AUTH_USER_MODEL = "bsadmin.CustomUser"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    'full_ckeditor': {
        'toolbar': 'full',
        'height': 250,
        'width': '99.9%'
    },
    'awesome_ckeditor': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'JustifyLeft', 'JustifyCenter',
             'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source']
        ],
        'height': 150,
        'width': '99.9%'
    },
    'default': {
        'height': 150,
        'width': '99.9%',
        'toolbar_Full': [
            ['Styles', 'Format', 'Bold', 'Italic', 'Underline', 'Strike', 'SpellChecker', 'Undo', 'Redo'],
            ['Link', 'Unlink', 'Anchor'],
            ['Image', 'Flash', 'Table', 'HorizontalRule'],
            ['TextColor', 'BGColor'],
            ['Smiley', 'SpecialChar'], ['Source'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['NumberedList', 'BulletedList'],
            ['Indent', 'Outdent'],
            ['Maximize'],
        ],
        'extraPlugins': 'justify,liststyle,indent',
    },
}

gettext = lambda s: s
LANGUAGES = (
    ('en', gettext('English')),
    ('ru', gettext('Russia')),
    ('ky', gettext('Kyrgyz')),

)
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}
CRISPY_TEMPLATE_PACK = 'bootstrap4'

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

# ---------------- Celery ----------------
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/2'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/3'

CELERY_IGNORE_RESULT = True
CELERY_RESULT_EXPIRES = 3600

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

CELERY_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

CELERY_TASK_SOFT_TIME_LIMIT = 180
CELERY_TASK_TIME_LIMIT = 240


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', ],
            'level': 'INFO',
            'propagate': True,
        },
        'celery': {
            'handlers': ['console', ],
            'level': 'INFO',
            'propagate': True,
        },
        'stepper': {
            'handlers': ['console', ],
            'level': 'INFO',
            'propagate': True,
        },
    }
}


# --- Конфигурация Silk ---
def silk_intercept_func(request):
    ignored_paths = ['/admin/', '/silk/', '/static/', '/media/', '/health/']
    if any(request.path.startswith(p) for p in ignored_paths):
        return False
    return True


SILKY_INTERCEPT_FUNC = silk_intercept_func

# 2. Ограничиваем объемы данных
SILKY_MAX_RECORDED_REQUESTS = 500
SILKY_MAX_RECORDED_REQUESTS_CHECK_STEP = 50
SILKY_MAX_RESPONSE_BODY_SIZE = 1024
SILKY_MAX_REQUEST_BODY_SIZE = 1024

# 3. Производительность
SILKY_PYTHON_PROFILER = False
SILKY_ANALYZE_QUERIES = True
SILKY_SAVE_IDS_ONLY = False

# 4. Безопасность
SILKY_AUTHENTICATION = True
SILKY_AUTHORISATION = True
