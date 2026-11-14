"""Runtime compatibility shims for the original Django application."""

import builtins
import sys
import types

from django import shortcuts
from django.db import models as django_models
from django.shortcuts import render
from django.urls import reverse

from dnd.compat.urls import include, patterns, url


if not hasattr(builtins, 'unicode'):
    builtins.unicode = str


if getattr(django_models.ForeignKey.__init__, '__name__', '') != 'legacy_foreign_key_init':
    _ForeignKey = django_models.ForeignKey

    class LegacyForeignKey(_ForeignKey):
        def __init__(self, *args, **kwargs):
            if len(args) < 2:
                kwargs.setdefault('on_delete', django_models.CASCADE)
            super(LegacyForeignKey, self).__init__(*args, **kwargs)

    LegacyForeignKey.__init__.__name__ = 'legacy_foreign_key_init'
    django_models.ForeignKey = LegacyForeignKey


if not hasattr(django_models, 'NullBooleanField'):
    django_models.NullBooleanField = django_models.BooleanField


if not hasattr(shortcuts, 'render_to_response'):
    def render_to_response(template_name, context=None, context_instance=None,
                           content_type=None, status=None, using=None):
        request = getattr(context_instance, 'request', None)
        return render(
            request,
            template_name,
            context or {},
            content_type=content_type,
            status=status,
            using=using,
        )

    shortcuts.render_to_response = render_to_response


if not hasattr(django_models, 'permalink'):
    def permalink(function):
        def wrapper(self):
            view_name, args, kwargs = function(self)
            return reverse(view_name, args=args, kwargs=kwargs)

        wrapper.__name__ = function.__name__
        wrapper.__doc__ = function.__doc__
        return wrapper

    django_models.permalink = permalink


try:
    import django.conf.urls as django_conf_urls
    django_conf_urls.include = include
    django_conf_urls.patterns = patterns
    django_conf_urls.url = url
except ImportError:
    pass


urlresolvers = types.ModuleType('django.core.urlresolvers')
urlresolvers.reverse = reverse
sys.modules.setdefault('django.core.urlresolvers', urlresolvers)
