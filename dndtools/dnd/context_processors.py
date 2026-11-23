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


def public_seo(request):
    """Keep search URLs on the configured public host, independent of Host headers."""
    path = request.path_info
    english_path = path[6:] if path.startswith('/pt-br/') else path
    origin = 'https://' + settings.PUBLIC_HOST
    route = getattr(request.resolver_match, 'url_name', None)
    bilingual_routes = {
        'index', 'rulebook_list', 'spell_index', 'feat_index',
        'character_class_list', 'skill_list', 'race_index', 'monster_index',
        'item_index', 'rule_list', 'privacy', 'help',
    }
    return {
        'seo_origin': origin,
        'seo_canonical_url': origin + path,
        'seo_english_url': origin + english_path,
        'seo_portuguese_url': origin + '/pt-br' + english_path,
        'seo_bilingual': route in bilingual_routes,
    }


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
        'forum_enabled': settings.FORUM_ENABLED,
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
