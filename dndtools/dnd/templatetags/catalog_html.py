"""Sanitize untrusted, legacy HTML fragments at their rendering boundary."""

import nh3
from django import template
from django.utils.safestring import mark_safe


register = template.Library()


def _internal_link(url):
    return url if url.startswith('/') and not url.startswith('//') and '\\' not in url else None


_cleaner = nh3.Cleaner(
    tags={'a', 'b', 'blockquote', 'br', 'caption', 'code', 'dd', 'del', 'div', 'dl', 'dt',
          'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'ins', 'li', 'ol', 'p', 'pre', 's',
          'small', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot',
          'th', 'thead', 'tr', 'u', 'ul'},
    attributes={'a': {'href', 'title'}, 'p': {'style'}, 'span': {'style'},
                'td': {'colspan', 'rowspan', 'style'},
                'th': {'colspan', 'rowspan', 'scope', 'style'}},
    allowed_classes={'span': {'caps', 'errata-old', 'errata-new'},
                     'p': {'gray-box', 'footnote'}},
    filter_style_properties={'text-align', 'vertical-align', 'white-space',
                             'padding-left', 'padding-right', 'color'},
    url_schemes=set(),
    url_relative=_internal_link,
    clean_content_tags={'script', 'style', 'iframe', 'object', 'svg', 'math'},
    link_rel='noopener noreferrer',
)


@register.filter
def safe_catalog_html(value):
    return mark_safe(_cleaner.clean(str(value or '')))
