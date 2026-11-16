from django.core.paginator import Paginator
from django.db.models import F
from django.db.models.functions import Collate
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from dnd.models import SupplementalEntry


def _label(kind):
    try:
        return dict(SupplementalEntry.KINDS)[kind]
    except KeyError:
        raise Http404


def index(request, kind):
    label = _label(kind)
    query = request.GET.get('q', '').strip()[:100]
    entries = SupplementalEntry.objects.filter(kind=kind).select_related('rulebook').order_by('name', 'pk')
    if query:
        entries = entries.alias(search_name=Collate(F('name'), 'utf8mb4_0900_ai_ci')).filter(
            search_name__contains=query)
    return render(request, 'dnd/supplemental/index.html', {
        'kind': kind, 'label': label, 'query': query,
        'entries': Paginator(entries, 30).get_page(request.GET.get('page')),
    })


def detail(request, kind, slug, entry_id):
    label = _label(kind)
    entry = get_object_or_404(SupplementalEntry.objects.select_related('rulebook'), pk=entry_id, kind=kind)
    if slug != entry.slug:
        return redirect(entry.get_absolute_url(), permanent=True)
    from dnd.localization import localize_record
    return render(request, 'dnd/supplemental/detail.html', {
        'entry': entry, 'label': label,
        'translation_fallback': localize_record(request, entry)})
