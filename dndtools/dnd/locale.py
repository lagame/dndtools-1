"""Public URL language selection, independent of the catalog theme."""

from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import translation
from django.views.decorators.http import require_GET


class PublicLocaleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path == '/':
            stored = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
            preferred = request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(',', 1)[0].lower()
            if stored == 'pt-br' or (stored not in ('en-us', 'pt-br') and preferred.startswith('pt')):
                return HttpResponseRedirect('/pt-br/' + ('?' + request.META['QUERY_STRING'] if request.META.get('QUERY_STRING') else ''))
        if path == '/privacy/' and request.GET.get('lang', '').lower() == 'pt':
            return HttpResponseRedirect('/pt-br/privacy/')
        if path.startswith('/' + settings.ADMIN_URL):
            language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, 'en-us')
            if language not in ('en-us', 'pt-br'):
                language = 'en-us'
        else:
            language = 'pt-br' if path.startswith('/pt-br/') else 'en-us'
        translation.activate(language)
        request.LANGUAGE_CODE = language
        try:
            response = self.get_response(request)
            response['Content-Language'] = language
            return response
        finally:
            translation.deactivate()


@require_GET
def switch_language(request):
    language = request.GET.get('language')
    if language not in ('en-us', 'pt-br'):
        language = 'en-us'
    next_url = request.GET.get('next', '/')
    parsed = urlsplit(next_url)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/') or parsed.path.startswith('//'):
        parsed = urlsplit('/')
    path = parsed.path
    if path.startswith('/pt-br/'):
        path = path[len('/pt-br'):]
    elif path == '/pt-br':
        path = '/'
    is_admin = path.startswith('/' + settings.ADMIN_URL)
    is_forum = path == '/forum' or path.startswith('/forum/')
    if path.startswith('/language/'):
        path = '/'
    if language == 'pt-br' and not is_admin and not is_forum:
        path = '/pt-br' + path
    response = HttpResponseRedirect(urlunsplit(('', '', path, parsed.query, '')))
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language, max_age=31536000,
                        secure=not settings.DEBUG, httponly=True, samesite='Lax')
    return response
