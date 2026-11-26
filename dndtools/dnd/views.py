# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.urls import Resolver404, resolve
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.views.decorators.http import require_GET
from dnd.menu import menu_item, submenu_item, MenuItem
from dnd.models import NewsEntry


def legacy_mobile_redirect(request, path=''):
    language_prefix = request.path.partition('/m/')[0]
    candidate = language_prefix + '/' + path
    try:
        resolve(candidate)
    except Resolver404:
        section = path.split('/', 1)[0]
        candidate = language_prefix + '/' + section + '/' if section in {
            'rulebooks', 'classes', 'feats', 'spells', 'skills', 'races',
            'monsters', 'items', 'languages', 'deities', 'rules',
        } else language_prefix + '/'
    if request.GET:
        candidate += '?' + request.GET.urlencode()
    return HttpResponsePermanentRedirect(candidate)


def permanent_redirect_view(request, view_name, args=None, kwargs=None):
    url = reverse(view_name, args=args, kwargs=kwargs)
    # get parameters
    if len(request.GET) > 0:
        #noinspection PyUnresolvedReferences
        url += "?" + request.GET.urlencode()

    return HttpResponsePermanentRedirect(url)


# noinspection PyShadowingBuiltins
def permanent_redirect_object(request, object):
    url = object.get_absolute_url()
    # get parameters
    if len(request.GET) > 0:
        #noinspection PyUnresolvedReferences
        url += "?" + request.GET.urlencode()

    return HttpResponsePermanentRedirect(url)


def is_3e_edition(edition):
    return edition.system == 'DnD 3.0'


def is_admin(request):
    return request.user.is_staff and request.user.is_active


@menu_item(MenuItem.CONTACTS)
@submenu_item(MenuItem.Contacts.NEWS)
def index(request):
    news_entries = NewsEntry.objects.filter(enabled=True).exclude(
        body__icontains='dndtools.eu').order_by('-published')[:15]

    response = render_to_response('dnd/index.html',
                                  {
                                      'request': request, 'news_entries': news_entries,
                                  },
                                  context_instance=RequestContext(request), )

    return response


@require_GET
def inaccurate_content(request):
    return render_to_response('dnd/inaccurate_content.html',
                              {'request': request, 'reported_url': request.GET.get('url', '')},
                              context_instance=RequestContext(request))

def inaccurate_content_sent(request):
    return HttpResponseRedirect(reverse('inaccurate_content'))
