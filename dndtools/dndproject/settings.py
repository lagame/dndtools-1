# -*- coding: utf-8 -*-
import os
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DEBUG = os.environ.get('DND_DEBUG') == '1'

ADMINS = (
    ('Ronassic', 'ronassic@gmail.com'),
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
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'dnd.privacy.LegacyCookieCleanupMiddleware',
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

SERVER_EMAIL = 'ronassic@gmail.com'
USE_TZ = False

# LOCAL PY

MEDIA_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = (STATIC_DIR, )
STATIC_ROOT = os.environ.get('DND_STATIC_ROOT', os.path.join(BASE_DIR, 'collected_static'))
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
                'dnd.context_processors.privacy_language',
                'dnd.context_processors.is_mobile',
                'dnd.context_processors.is_admin',
                'dnd.context_processors.menu_constants',
            ),
        },
    },
)

WSGI_APPLICATION = 'dndproject.wsgi.application'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

MIGRATION_MODULES = {'dnd': 'dnd.migrations_modern'}

required = ('DND_DB_HOST', 'DND_DB_NAME', 'DND_DB_USER', 'DND_DB_PASSWORD', 'DND_SECRET_KEY')
missing = [name for name in required if not os.environ.get(name)]
if missing:
    raise ImproperlyConfigured('Missing environment variables: %s' % ', '.join(missing))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DND_DB_NAME'],
        'USER': os.environ['DND_DB_USER'],
        'PASSWORD': os.environ['DND_DB_PASSWORD'],
        'HOST': os.environ['DND_DB_HOST'],
        'PORT': os.environ.get('DND_DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
    }
}
SECRET_KEY = os.environ['DND_SECRET_KEY']
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('DND_ALLOWED_HOSTS', '').split(',') if host.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('DND_CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()]
MEDIA_ROOT = os.environ.get('DND_MEDIA_ROOT', MEDIA_ROOT)
PUBLIC_HOST = os.environ.get('DND_PUBLIC_HOST', 'localhost')
FORCE_HTTPS = not DEBUG and os.environ.get('DND_FORCE_HTTPS', '1') == '1'
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('DND_ALLOWED_HOSTS is required in production.')

if not DEBUG:
    SESSION_COOKIE_SECURE = FORCE_HTTPS
    CSRF_COOKIE_SECURE = FORCE_HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = FORCE_HTTPS
    SECURE_HSTS_SECONDS = 31536000 if FORCE_HTTPS else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = FORCE_HTTPS
    SECURE_HSTS_PRELOAD = FORCE_HTTPS
    SECURE_CONTENT_TYPE_NOSNIFF = True
