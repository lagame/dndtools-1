# -*- coding: utf-8 -*-
from dnd.menu import MenuItem
from dnd.navigation import catalog_navigation


def privacy_language(request):
    if request.path == '/privacy/':
        requested = request.GET.get('lang', '').lower()
        if requested in ('pt', 'en'):
            return {'privacy_language': requested}
    preferred = request.META.get('HTTP_ACCEPT_LANGUAGE', '').split(',', 1)[0].lower()
    return {'privacy_language': 'pt' if preferred.startswith('pt') else 'en'}


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
