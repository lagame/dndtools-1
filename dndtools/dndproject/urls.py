from dnd.compat.urls import patterns, include, url
from django.urls import path
from django.conf.urls.i18n import i18n_patterns

from django.contrib import admin
from django.conf import settings
from dnd.locale import switch_language
from dnd.discussions import record_metadata
admin.autodiscover()

urlpatterns = patterns('',

    path('forum-record/<slug:kind>/<int:record_id>/', record_metadata, name='forum_record_metadata'),
    path(settings.ADMIN_URL + 'editorial/', include('dnd.editorial_urls')),
    path(settings.ADMIN_URL, admin.site.urls),
    path('language/', switch_language, name='switch_language'),
    # TODO
    # (r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
)

urlpatterns += i18n_patterns(*patterns('', url(r'^', include('dnd.urls'))),
                              prefix_default_language=False)
