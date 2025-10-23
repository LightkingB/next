import os
from pathlib import Path
from django.contrib import messages
from decouple import config

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
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
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
