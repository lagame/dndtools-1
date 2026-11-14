"""Small compatibility layer for the pre-Django-1.10 URL declarations."""

from importlib import import_module

from django.urls import include, re_path, reverse
from django.urls.resolvers import URLPattern


class LegacyURL:
    def __init__(self, regex, view, kwargs=None, name=None):
        self.regex = regex
        self.view = view
        self.kwargs = kwargs
        self.name = name


def url(regex, view, kwargs=None, name=None):
    return LegacyURL(regex, view, kwargs, name)


def patterns(prefix, *url_patterns):
    result = []
    for pattern in url_patterns:
        if isinstance(pattern, LegacyURL):
            callback = pattern.view
            if isinstance(callback, str):
                callback = getattr(import_module(prefix), callback)
            pattern = re_path(pattern.regex, callback, pattern.kwargs, pattern.name)
        elif isinstance(pattern, tuple):
            pattern = re_path(*pattern)

        callback = getattr(pattern, '_callback', None)
        result.append(pattern)
    return result


__all__ = ['include', 'patterns', 'reverse', 'url']
