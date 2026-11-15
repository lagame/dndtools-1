from dnd.compat.urls import patterns, include, url
from django.urls import path

from django.contrib import admin
from django.conf import settings
admin.autodiscover()

urlpatterns = patterns('',

    path(settings.ADMIN_URL, admin.site.urls),
    # TODO
    # (r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    url(r'^', include('dnd.urls')),
)
