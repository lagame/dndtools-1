"""Retire visitor cookies left by the original site."""


class LegacyCookieCleanupMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for name in ('top_news', 'disable_social', 'force_desktop'):
            if name in request.COOKIES:
                response.delete_cookie(name)
        return response
