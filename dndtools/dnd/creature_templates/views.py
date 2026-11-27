from django.core.paginator import Paginator
from django.db.models import F
from django.db.models.functions import Collate
from django.shortcuts import get_object_or_404, redirect, render

from dnd.models import CreatureTemplate
from dnd.catalog_ordering import order_catalog


def index(request):
    entries = CreatureTemplate.objects.select_related('rulebook').order_by('name', 'pk')
    query = request.GET.get('q', '').strip()[:100]
    if query:
        entries = entries.alias(search_name=Collate(F('name'), 'utf8mb4_0900_ai_ci')).filter(
            search_name__contains=query)
    entries, order = order_catalog(entries, request)
    return render(request, 'dnd/creature_templates/index.html', {
        'entries': Paginator(entries, 30).get_page(request.GET.get('page')),
        'query': query,
        'order': order,
    })


def detail(request, slug, template_id):
    entry = get_object_or_404(CreatureTemplate.objects.select_related('rulebook'), pk=template_id)
    if slug != entry.slug:
        return redirect(entry.get_absolute_url(), permanent=True)
    from dnd.localization import localize_record
    return render(request, 'dnd/creature_templates/detail.html', {
        'entry': entry, 'translation_fallback': localize_record(request, entry)})
