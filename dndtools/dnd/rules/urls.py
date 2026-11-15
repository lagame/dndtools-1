# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url


urlpatterns = patterns(
    'dnd.rules.views',

    url(r'^conditions/$', 'condition_list', name='rule_condition_list'),
    url(r'^conditions/(?P<condition_id>\d+)/$', 'condition_detail', name='rule_condition_detail'),

    # rules list
    url(
        r'^$',
        'rule_list',
        name='rule_list',
    ),

    # rules
    url(
        r'^(?P<rulebook_slug>[^/]+)--(?P<rulebook_id>\d+)/(?P<rule_slug>[^/]+)--(?P<rule_id>\d+)/$',
        'rule_detail',
        name='rule_detail',
    ),

)
