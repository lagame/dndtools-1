from django.core.paginator import Paginator
from django.db import models
from django.db.models import F
from django.db.models.functions import Collate
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from dnd.models import SupplementalEntry
from dnd.catalog_ordering import order_catalog
from dnd.supplemental.catalog import DETAILS, DISPLAY, FACETS, displayed_details, detail_for


def _label(kind):
    try:
        return dict(SupplementalEntry.KINDS)[kind]
    except KeyError:
        raise Http404


def index(request, kind):
    label = _label(kind)
    query = request.GET.get('q', '').strip()[:100]
    relation, model = DETAILS[kind]
    related = ['rulebook', relation]
    if kind == 'invocations':
        related.append(relation + '__character_class')
    elif kind == 'auras':
        related.extend((relation + '__character_class', relation + '__monster'))
    entries = (SupplementalEntry.objects.filter(kind=kind)
               .select_related(*related).order_by('name', 'pk'))
    if kind == 'psionics':
        entries = entries.prefetch_related(relation + '__class_levels__character_class')
    elif kind == 'monstrous-traits':
        entries = entries.prefetch_related(relation + '__monsters')
    if query:
        entries = entries.alias(search_name=Collate(F('name'), 'utf8mb4_0900_ai_ci')).filter(
            search_name__contains=query)
    book_ids = SupplementalEntry.objects.filter(kind=kind).values_list('rulebook_id', flat=True).distinct()
    from dnd.models import Rulebook
    books = Rulebook.objects.filter(pk__in=book_ids).order_by('name')
    book = request.GET.get('book', '')
    if book.isdigit():
        entries = entries.filter(rulebook_id=int(book))
    facets = []
    labels = dict(DISPLAY[kind])
    for name in FACETS[kind]:
        field = None if name in ('class_levels', 'monsters') else model._meta.get_field(name)
        if field and field.choices:
            options = [(str(value), label) for value, label in field.choices]
        elif field and isinstance(field, models.ForeignKey):
            ids = model.objects.values_list(name + '_id', flat=True).distinct()
            options = [(str(obj.pk), str(obj)) for obj in field.related_model.objects.filter(pk__in=ids).order_by('name')]
        elif field:
            options = [(str(value), str(value)) for value in model.objects.values_list(name, flat=True).distinct().order_by(name) if value is not None]
        elif name == 'class_levels':
            from dnd.models import CharacterClass
            ids = model.objects.values_list('class_levels__character_class_id', flat=True).distinct()
            options = [(str(obj.pk), str(obj)) for obj in CharacterClass.objects.filter(pk__in=ids).order_by('name')]
        else:
            from dnd.models import Monster
            ids = model.objects.values_list('monsters__pk', flat=True).distinct()
            options = [(str(obj.pk), str(obj)) for obj in Monster.objects.filter(pk__in=ids).order_by('name')]
        selected = request.GET.get(name, '')
        if selected and selected in {str(value) for value, _ in options}:
            lookup = '%s__%s' % (relation, name)
            if name == 'class_levels':
                lookup += '__character_class_id'
            elif name in ('monsters',) or (field and isinstance(field, models.ForeignKey)):
                lookup += '__pk'
            entries = entries.filter(**{lookup: selected}).distinct()
        facets.append({'name': name, 'label': labels.get(name, _('Class')),
                       'options': options, 'selected': selected})
    order = request.GET.get('order', '')
    if order in ('details', '-details'):
        detail_field = {
            'mysteries': 'path', 'invocations': 'grade', 'psionics': 'discipline',
            'auras': 'character_class__name', 'maneuvers': 'discipline',
            'monstrous-traits': 'ability_type',
        }[kind]
        entries = entries.order_by(F(relation + '__' + detail_field).desc(nulls_last=True)
                                   if order.startswith('-') else
                                   F(relation + '__' + detail_field).asc(nulls_last=True), 'pk')
    else:
        entries, order = order_catalog(entries, request)
    requested_size = request.GET.get('page_size', '50')
    page_size = int(requested_size) if requested_size in ('20', '50', '100', '1000', '5000') else 50
    params = request.GET.copy()
    params.pop('page', None)
    querystring = params.urlencode()
    page = Paginator(entries, page_size).get_page(request.GET.get('page'))
    for entry in page.object_list:
        entry.summary = displayed_details(entry)[:2] if detail_for(entry) else []
    return render(request, 'dnd/supplemental/index.html', {
        'kind': kind, 'label': label, 'query': query,
        'order': order,
        'entries': page, 'books': books, 'selected_book': book,
        'facets': facets, 'page_size': page_size, 'querystring': querystring,
    })


def detail(request, kind, slug, entry_id):
    label = _label(kind)
    entry = get_object_or_404(SupplementalEntry.objects.select_related('rulebook', DETAILS[kind][0]), pk=entry_id, kind=kind)
    if slug != entry.slug:
        return redirect(entry.get_absolute_url(), permanent=True)
    from dnd.localization import localize_record
    fallback = localize_record(request, entry)
    return render(request, 'dnd/supplemental/detail.html', {
        'entry': entry, 'label': label,
        'typed_details': displayed_details(entry),
        'translation_fallback': fallback})
