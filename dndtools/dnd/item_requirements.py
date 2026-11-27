"""Validate and present reviewed creation requirements without rewriting the source."""

from collections import defaultdict
from hashlib import sha256
import json
from unicodedata import normalize

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from dnd.models import Feat, Item, ItemCreationRequirements, PublishedTranslation, Rulebook, Spell, SupplementalEntry

RESOURCE = 'ItemCreationRequirements'
MAX_ROWS = 250
MAX_BYTES = 1024 * 1024
TARGETS = {'feat': Feat, 'spell': Spell, 'psionic_power': SupplementalEntry}


def decode_submission(content):
    def unique_keys(pairs):
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValidationError(_('JSON objects must not contain duplicate keys.'))
        return result

    def invalid_constant(_value):
        raise ValueError('Non-finite numbers are not valid JSON.')

    try:
        content = content if isinstance(content, bytes) else content.encode('utf-8')
        if len(content) > MAX_BYTES:
            raise ValidationError(_('Use a JSON file of at most 1 MiB.'))
        return json.loads(content.decode('utf-8-sig'), object_pairs_hook=unique_keys, parse_constant=invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValidationError(_('Use a valid UTF-8 JSON file.')) from error


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() <= set(required) | set(optional):
        raise ValidationError(_('Invalid fields in the prerequisite data.'))


def _number(value):
    if type(value) is not int or not 1 <= value <= 2_147_483_647:
        raise ValidationError(_('IDs and printed pages must be positive integers.'))
    return value


def _text(value, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
        raise ValidationError(_('A required text field is empty or invalid.'))
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValidationError(_('A required text field is empty or invalid.')) from error
    return value.strip()


def _node(value, *, depth=0, budget):
    budget[0] -= 1
    if budget[0] < 0 or depth > 8 or not isinstance(value, dict):
        raise ValidationError(_('Invalid or excessively nested prerequisite expression.'))
    if value.get('op') == 'none' and depth == 0:
        _fields(value, ('op',))
        return value
    if value.get('op') in ('all', 'any'):
        _fields(value, ('op', 'children'))
        children = value['children']
        if not isinstance(children, list) or len(children) < 2:
            raise ValidationError(_('Each group must contain at least two requirements.'))
        return {'op': value['op'], 'children': [_node(child, depth=depth + 1, budget=budget) for child in children]}
    kind = value.get('kind')
    if kind == 'condition':
        _fields(value, ('kind', 'en', 'pt_br'))
        return {'kind': kind, 'en': _text(value['en'], 2000), 'pt_br': _text(value['pt_br'], 2000)}
    if not isinstance(kind, str) or kind not in TARGETS:
        raise ValidationError(_('Unknown prerequisite type or group.'))
    _fields(value, ('kind', 'original_name'), ('target_id', 'reference'))
    leaf = {'kind': kind, 'original_name': _text(value['original_name'], 128)}
    if 'reference' in value:
        reference = value['reference']
        _fields(reference, ('rulebook_id', 'page'))
        leaf['reference'] = {key: _number(reference[key]) for key in ('rulebook_id', 'page')}
    if 'target_id' in value:
        if 'reference' not in leaf:
            raise ValidationError(_('A catalog link requires a confirmed book and page.'))
        leaf['target_id'] = _number(value['target_id'])
    return leaf


def _row(row):
    _fields(row, ('item_id', 'original_name', 'rulebook_id', 'page', 'source', 'requirements'))
    source = row['source']
    _fields(source, ('rulebook_id', 'pages'))
    pages = source['pages']
    if not isinstance(pages, list) or not 1 <= len(pages) <= 20:
        raise ValidationError(_('List the printed pages that were reviewed.'))
    return {
        'item_id': _number(row['item_id']), 'original_name': _text(row['original_name'], 64),
        'rulebook_id': _number(row['rulebook_id']), 'page': None if row['page'] is None else _number(row['page']),
        'source': {'rulebook_id': _number(source['rulebook_id']), 'pages': sorted({_number(page) for page in pages})},
        'requirements': _node(row['requirements'], budget=[64]),
    }


def _leaves(node):
    if 'kind' in node:
        yield node
    for child in node.get('children', ()):
        yield from _leaves(child)


def _related(rows):
    book_ids = set()
    ids = defaultdict(set)
    for row in rows:
        book_ids.add(row['source']['rulebook_id'])
        if 'rulebook_id' in row:
            book_ids.add(row['rulebook_id'])
        for leaf in _leaves(row['requirements']):
            if 'reference' in leaf:
                book_ids.add(leaf['reference']['rulebook_id'])
            if 'target_id' in leaf:
                ids[leaf['kind']].add(leaf['target_id'])
    books = Rulebook.objects.select_related('dnd_edition').in_bulk(book_ids)
    targets = {}
    for kind, pks in ids.items():
        queryset = TARGETS[kind].objects.select_related('rulebook__dnd_edition')
        if kind == 'psionic_power':
            queryset = queryset.select_related('psionic_detail')
        targets[kind] = queryset.in_bulk(pks)
    return books, targets


def _name(value):
    return ' '.join(normalize('NFC', value).casefold().split())


def _matching_target(leaf, targets, book):
    obj = targets.get(leaf['kind'], {}).get(leaf.get('target_id'))
    if obj is None or book is None or (leaf['kind'] == 'psionic_power' and obj.kind != 'psionics'):
        return None
    if (obj.rulebook_id != book.pk or obj.page != leaf['reference']['page']
            or _name(obj.name) != _name(leaf['original_name'])):
        return None
    return obj


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def item_source_digest(item):
    return _digest((item.name, item.type, item.rulebook_id, item.rulebook.dnd_edition_id, item.page, item.description,
                    item.required_extra, sorted(feat.pk for feat in item.required_feats.all()),
                    sorted(spell.pk for spell in item.required_spells.all())))


def _items(ids, *, lock=False):
    qs = Item.objects.filter(pk__in=ids).order_by('pk').prefetch_related('rulebook', 'required_feats', 'required_spells')
    return {item.pk: item for item in (qs.select_for_update() if lock else qs)}


def validate_submission(raw, *, lock=False):
    """Normalize both authoring paths and snapshot source and review state for approval."""
    _fields(raw, ('resource', 'version', 'items'))
    if raw['resource'] != RESOURCE or type(raw['version']) is not int or raw['version'] != 1:
        raise ValidationError(_('This file is not a supported item creation prerequisites file.'))
    if not isinstance(raw['items'], list) or not 1 <= len(raw['items']) <= MAX_ROWS:
        raise ValidationError(_('Include between 1 and 250 items in the file.'))
    rows, errors = [], []
    for line, value in enumerate(raw['items'], 1):
        try:
            rows.append(_row(value))
        except ValidationError as error:
            errors.append(_('Row %(row)s · %(error)s') % {'row': line, 'error': ' '.join(error.messages)})
    if errors:
        raise ValidationError(errors)
    ids = {row['item_id'] for row in rows}
    if len(ids) != len(rows):
        raise ValidationError(_('Each item may only appear once in the file.'))
    items = _items(ids, lock=lock)
    revisions = dict(ItemCreationRequirements.objects.filter(item_id__in=ids).values_list('item_id', 'proposal_id'))
    books, targets = _related(rows)
    snapshots = {}
    for line, row in enumerate(rows, 1):
        pk = row['item_id']
        item = items.get(pk)
        source = row['source']
        if item is None or (item.name, item.rulebook_id, item.page) != (row['original_name'], row['rulebook_id'], row['page']):
            errors.append(_('Row %(row)s · Item name, book or page does not match item #%(item)s.') % {'row': line, 'item': pk})
            continue
        source_book = books.get(source['rulebook_id'])
        item_system = books[item.rulebook_id].dnd_edition.system
        if source_book is None:
            errors.append(_('Row %(row)s · The reviewed source book does not exist.') % {'row': line})
        elif source_book.dnd_edition.system != item_system:
            errors.append(_('Row %(row)s · The reviewed source is from a different rules edition.') % {'row': line})
        elif source_book.pk == item.rulebook_id and item.page and item.page not in source['pages']:
            errors.append(_('Row %(row)s · Include the item’s printed page in the reviewed source.') % {'row': line})
        for leaf in _leaves(row['requirements']):
            reference = leaf.get('reference')
            book = books.get(reference['rulebook_id']) if reference else None
            target = _matching_target(leaf, targets, book) if 'target_id' in leaf else None
            if (reference and not book) or ('target_id' in leaf and (
                    target is None or book.dnd_edition.system != item_system)):
                errors.append(_('Row %(row)s · Check the confirmed reference for %(name)s.') %
                              {'row': line, 'name': leaf['original_name']})
            elif target is not None:
                leaf['original_name'] = target.name
        snapshots[str(pk)] = _digest((item_source_digest(item), revisions.get(pk)))
    if errors:
        raise ValidationError(errors)
    return {'resource': RESOURCE, 'version': 1, 'items': rows}, snapshots


def publish_requirements(envelope, proposal):
    """Called after the entire envelope is validated under the item locks."""
    rows = envelope['items']
    ids = [row['item_id'] for row in rows]
    items = _items(ids)
    previous = ItemCreationRequirements.objects.in_bulk(ids, field_name='item_id')
    create, update = [], []
    for row in rows:
        item = items[row['item_id']]
        entry = previous.get(item.pk)
        if entry is None:
            entry = ItemCreationRequirements(item=item)
            create.append(entry)
        else:
            update.append(entry)
        entry.requirements = row['requirements']
        entry.source = row['source']
        entry.source_digest = item_source_digest(item)
        entry.proposal = proposal
    ItemCreationRequirements.objects.bulk_create(create)
    ItemCreationRequirements.objects.bulk_update(update, ('requirements', 'source', 'source_digest', 'proposal'))


def active_row(item):
    entry = getattr(item, 'creation_requirements', None)
    if entry is None or item_source_digest(item) != entry.source_digest:
        return None
    source_id = entry.source['rulebook_id']
    if source_id != item.rulebook_id:
        if not Rulebook.objects.filter(pk=source_id, dnd_edition__system=item.rulebook.dnd_edition.system).exists():
            return None
    return {'source': entry.source, 'requirements': entry.requirements}


def current_state(item):
    if getattr(item, 'creation_requirements', None) is None:
        return 'legacy'
    return 'published' if active_row(item) else 'stale'


def present_rows(rows, *, include_portuguese=True):
    """Resolve verified links in batches and gracefully display citations without a link."""
    from dnd.editorial import source_digest

    books, targets = _related(rows)
    translations = {}
    if include_portuguese:
        for kind, entries in targets.items():
            resource = TARGETS[kind]._meta.object_name
            translated = PublishedTranslation.objects.filter(resource=resource, target_pk__in=entries, locale='pt-br')
            for row in translated:
                if row.source_digest == source_digest(entries[row.target_pk], translation=True):
                    translations[(kind, row.target_pk)] = row.payload.get('name')

    def present(node, system):
        if 'children' in node:
            return {'op': node['op'], 'children': [present(child, system) for child in node['children']]}
        if node.get('kind') not in TARGETS:
            return node
        reference = node.get('reference')
        book = books.get(reference['rulebook_id']) if reference else None
        target = _matching_target(node, targets, book) if 'target_id' in node else None
        if target and book.dnd_edition.system != system:
            target = None
        return {**node, 'book': book, 'target': target,
                'pt_br_name': translations.get((node['kind'], target.pk)) if target else None}

    presented = []
    for row in rows:
        book = books.get(row['source']['rulebook_id'])
        presented.append({'source': {'book': book, 'pages': row['source']['pages']},
                          'tree': present(row['requirements'], book.dnd_edition.system if book else None)})
    return presented


def presentation(row, *, include_portuguese=True):
    return present_rows([row], include_portuguese=include_portuguese)[0]
