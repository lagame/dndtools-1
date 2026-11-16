# -*- coding: utf-8 -*-
from django.shortcuts import render_to_response
from django.template import RequestContext
from dnd.menu import menu_item
from dnd.models import NewsEntry


@menu_item("home")
def index_mobile(request):
    news_entries = NewsEntry.objects.filter(enabled=True).exclude(
        body__icontains='dndtools.eu').order_by('-published')[:15]

    response = render_to_response('dnd/mobile/index/index.html',
                                  {
                                      'request': request, 'newsEntries': news_entries,
                                  },
                                  context_instance=RequestContext(request), )

    return response
