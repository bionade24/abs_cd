"""
Django settings for abs_cd project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from django.core.management import utils
from urllib.parse import urlparse

from .confighelper import Confighelper

helper = Confighelper()


def get_secret_key():
    key = helper.get_setting('SECRET_KEY')
    if key == '':
        key = utils.get_random_secret_key()
        helper.write_setting('SECRET_KEY', key)
    return key


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret_key()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (helper.get_setting('DEBUG') == 'True')

APPLICATION_URL = helper.get_setting('APPLICATION_URL', "http://localhost")
ALLOWED_HOSTS = ['127.0.0.1', urlparse(APPLICATION_URL).hostname]
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1", "https://127.0.0.1", APPLICATION_URL]

# Application definition
INSTALLED_APPS = [
    'cd_manager.apps.Abs_cd_AdminSite',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_crontab',
    'sortable_listview',
    'cd_manager.apps.CdManagerConfig']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'abs_cd.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates"), ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'abs_cd.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'data', 'db.sqlite3'),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
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

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

CRONJOBS = [
    ('0 0 * * *', 'cd_manager.cron.update_pacmandbs'),
    ('30 0 * * *', 'cd_manager.cron.check_for_new_pkgversions'),
    ('0 12 1 * *', 'cd_manager.cron.clean_pacman_cache'),
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = False

USE_L10N = False

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# The absolute path to the directory where collectstatic will collect static files for deployment.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATIC_URL = '/static/'

# Paths for abs_cd (cd_manager & makepkg module)
# Paths set here and not in settings.ini need more manual intervention
ABS_CD_PROJECT_DIR = "/opt/abs_cd"
PKGBUILDREPOS_PATH = "/var/packages"
PKGBUILDREPOS_HOST_PATH = helper.get_setting('PKGBUILDREPOS_HOST_PATH', '/var/local/abs_cd/packages')
PACMAN_CONFIG_PATH = "/etc/pacman.conf"
PACMANREPO_PATH = "/repo"
PACMANREPO_HOST_PATH = helper.get_setting('PACMANREPO_HOST_PATH', 'Docker-volume')
PACMANDB_FILENAME = helper.get_setting('PACMANREPO_NAME', "abs_cd-local") + ".db.tar.zst"
PACMAN_FILESDB_FILENAME = helper.get_setting('PACMANREPO_NAME', "abs_cd-local") + ".files.tar.zst"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'style': '{',
            'format': '[{asctime}] {message}',
            'datefmt': '%d/%b/%Y %H:%M:%S',
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': 'ext://sys.stdout',
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG' if DEBUG else 'INFO',
    },
    'loggers': {
        'cd_manager': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'makepkg': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'level': 'ERROR',
            'propagate': False,
        },
    }
}
