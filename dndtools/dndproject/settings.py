# -*- coding: utf-8 -*-
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

ADMINS = (
    ('DnDtools', 'dndtools.eu@gmail.com'),
)

MANAGERS = ADMINS
TIME_ZONE = 'Europe/Prague'
LANGUAGE_CODE = 'en-us'
MEDIA_URL = '/media/'
STATIC_URL = '/static/'
USE_I18N = False
USE_L10N = False
ADMIN_MEDIA_PREFIX = '/media/'

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'dndproject.urls'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dnd',
    'django.contrib.sitemaps',
)

SERVER_EMAIL = 'error@dndtools.eu'
USE_TZ = False

# LOCAL PY

MEDIA_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = (STATIC_DIR, )
SITE_ID = 1

TEMPLATES = (
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': (os.path.join(BASE_DIR, 'templates'),),
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                'dnd.context_processors.unread_news',
                'dnd.context_processors.disable_social',
                'dnd.context_processors.is_mobile',
                'dnd.context_processors.is_admin',
                'dnd.context_processors.menu_constants',
            ),
        },
    },
)

RECAPTCHA_PUBLIC = ''
WSGI_APPLICATION = 'dndproject.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

from dndproject.local import *
