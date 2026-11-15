"""Give first-party assets a new URL when their content changes."""

from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from django import template
from django.conf import settings
from django.templatetags.static import static


register = template.Library()


@lru_cache(maxsize=64)
def _digest(path):
    return sha256((Path(settings.STATIC_DIR) / path).read_bytes()).hexdigest()[:12]


@register.simple_tag
def versioned_static(path):
    if settings.DEBUG:
        _digest.cache_clear()
    return '%s?v=%s' % (static(path), _digest(path))
