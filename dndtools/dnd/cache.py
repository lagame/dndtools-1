"""Keep HTML fresh while static assets can be cached separately."""
from django.conf import settings


class HtmlCachePolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/' + settings.ADMIN_URL):
            response['Cache-Control'] = 'no-store'
        elif response.get('Content-Type', '').startswith('text/html') and 'Cache-Control' not in response:
            response['Cache-Control'] = 'no-cache, max-age=0, must-revalidate'
        return response
