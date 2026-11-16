# -*- coding: utf-8 -*-
from django.conf import settings
from dnd.menu import MenuItem
from dnd.navigation import catalog_navigation


def privacy_language(request):
    if request.path in ('/privacy/', '/pt-br/privacy/'):
        requested = request.GET.get('lang', '').lower()
        if requested in ('pt', 'en'):
            return {'privacy_language': requested}
    return {'privacy_language': 'pt' if request.LANGUAGE_CODE == 'pt-br' else 'en'}


def is_mobile(request):
    mobile = False
    if hasattr(request, 'is_mobile') and request.is_mobile:
        mobile = True

    return {
        'is_mobile': mobile,
    }


def is_admin(request):
    return {
        'is_admin': request.user.is_staff and request.user.is_active,
    }


def menu_constants(request):
    return {
        'MenuItem': MenuItem,
        'catalog_navigation': catalog_navigation(request),
    }


def editorial_queue(request):
    """Show the owner a count of every submitted, unreviewed collaboration."""
    if not request.path.startswith('/' + settings.ADMIN_URL):
        return {}
    from dnd.editorial import owner
    from dnd.models import EditorialProposal
    if not owner(request.user):
        return {'editorial_queue_count': 0}
    return {'editorial_queue_count': EditorialProposal.objects.filter(status='pending').count()}
