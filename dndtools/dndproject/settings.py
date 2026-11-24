# -*- coding: utf-8 -*-
import os
import re
from datetime import timedelta
from csp.constants import NONE, SELF
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
USE_I18N = True
LANGUAGES = (('en-us', 'English'), ('pt-br', 'Português (Brasil)'))
LOCALE_PATHS = (os.path.join(BASE_DIR, 'locale'),)
USE_L10N = False
ADMIN_MEDIA_PREFIX = '/media/'

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'dnd.locale.PublicLocaleMiddleware',
    'dnd.privacy.LegacyCookieCleanupMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'dnd.access.AccessIdentityMiddleware',
    'dnd.cache.HtmlCachePolicyMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'csp.middleware.CSPMiddleware',
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
    'axes',
    'csp',
    'dnd',
    'django.contrib.sitemaps',
)

AUTHENTICATION_BACKENDS = (
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
)
AUTH_PASSWORD_VALIDATORS = (
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
)

# Only an explicitly trusted reverse proxy may supply the visitor IP.
AXES_ONLY_ADMIN_SITE = True
AXES_LOCKOUT_PARAMETERS = 'dnd.security.axes_lockout_parameters'
AXES_CLIENT_IP_CALLABLE = 'dnd.security.axes_client_ip'
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_USE_ATTEMPT_EXPIRATION = True
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
AXES_NEVER_LOCKOUT_GET = True
AXES_ENABLE_RETRY_AFTER_HEADER = True
AXES_DISABLE_ACCESS_LOG = True
AXES_VERBOSE = False
AXES_LOCKOUT_TEMPLATE = 'admin/locked_out.html'

SERVER_EMAIL = 'ronassic@gmail.com'
DEFAULT_FROM_EMAIL = os.environ.get('DND_EMAIL_FROM') or SERVER_EMAIL
EMAIL_HOST = os.environ.get('DND_EMAIL_HOST') or 'localhost'
EMAIL_PORT = int(os.environ.get('DND_EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('DND_EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DND_EMAIL_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('DND_EMAIL_USE_TLS', '1') == '1'
EDITORIAL_NOTIFY_EMAIL = os.environ.get('DND_EDITORIAL_NOTIFY_EMAIL', '')
if not DEBUG and (not EDITORIAL_NOTIFY_EMAIL or not os.environ.get('DND_EMAIL_HOST')
                  or not os.environ.get('DND_EMAIL_FROM')):
    raise ImproperlyConfigured('Configure DND_EDITORIAL_NOTIFY_EMAIL, DND_EMAIL_HOST and '
                               'DND_EMAIL_FROM before enabling editorial access in production.')
if not DEBUG and EMAIL_HOST == 'smtp.gmail.com' and (not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD):
    raise ImproperlyConfigured('Configure Gmail SMTP user and app password before production.')
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
                'dnd.context_processors.public_seo',
                'dnd.context_processors.is_mobile',
                'dnd.context_processors.is_admin',
                'dnd.context_processors.menu_constants',
                'dnd.context_processors.editorial_queue',
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
FORUM_ENABLED = os.environ.get('DND_FORUM_ENABLED') == '1'
FORCE_HTTPS = not DEBUG and os.environ.get('DND_FORCE_HTTPS', '1') == '1'
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('DND_ALLOWED_HOSTS is required in production.')

ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', '').strip()
if not ADMIN_URL and DEBUG:
    ADMIN_URL = 'admin'
if not ADMIN_URL or (not DEBUG and not re.fullmatch(r'[a-zA-Z0-9_-]{16,64}', ADMIN_URL)):
    raise ImproperlyConfigured('Set DJANGO_ADMIN_URL to a private 16-64 character path in production.')
if not re.fullmatch(r'[a-zA-Z0-9_-]+', ADMIN_URL):
    raise ImproperlyConfigured('DJANGO_ADMIN_URL must be one path segment.')
ADMIN_URL += '/'
ACCESS_TEAM_DOMAIN = os.environ.get('DND_ACCESS_TEAM_DOMAIN', '').strip().rstrip('/')
ACCESS_AUD = [value.strip() for value in os.environ.get('DND_ACCESS_AUD', '').split(',')
              if value.strip()]
ACCESS_REQUIRED = not DEBUG
if ACCESS_REQUIRED and (not ACCESS_TEAM_DOMAIN or not ACCESS_AUD):
    raise ImproperlyConfigured('Set DND_ACCESS_TEAM_DOMAIN and DND_ACCESS_AUD for admin identity binding.')
CONTENT_SECURITY_POLICY_REPORT_ONLY = {
    'DIRECTIVES': {
        'default-src': [SELF], 'script-src': [SELF], 'style-src': [SELF],
        'img-src': [SELF, 'data:'], 'font-src': [SELF], 'connect-src': [SELF],
        'object-src': [NONE], 'base-uri': [SELF], 'form-action': [SELF],
        'frame-ancestors': [NONE],
    },
}

if not DEBUG:
    SESSION_COOKIE_SECURE = FORCE_HTTPS
    CSRF_COOKIE_SECURE = FORCE_HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = FORCE_HTTPS
    SECURE_HSTS_SECONDS = 31536000 if FORCE_HTTPS else 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = FORCE_HTTPS
    SECURE_HSTS_PRELOAD = FORCE_HTTPS
    SECURE_CONTENT_TYPE_NOSNIFF = True
