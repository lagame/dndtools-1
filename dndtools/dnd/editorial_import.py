"""Validated catalog imports for explicitly trusted editors."""

import csv
import hashlib
import json
from decimal import Decimal
from io import StringIO

from django import forms
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from dnd.editorial import (RESOURCE_LABELS, can_import, detect_duplicate, editable_form, lock_creation_books,
                           save_catalog_entry, serialize_form, validate_new_edition)
from dnd.models import EditorialProposal
from dnd.supplemental.forms import parse_class_levels


MAX_MIB = 40
MAX_BYTES = MAX_MIB * 1024 ** 2
MAX_ROWS = 5000
INLINE_BYTES = 1024 ** 2
INLINE_ROWS = 250


class ImportRowLimitError(forms.ValidationError):
    pass


def _row_limit_error(max_rows):
    return ImportRowLimitError(_('Import at most %(rows)s records per file.') % {'rows': max_rows})
REQUIRED_COLUMNS = frozenset(('source_reference', 'name', 'rulebook'))
DOWNLOAD_FORMATS = {'csv': ',', 'csv-semicolon': ';', 'json': None}

# Illustrative data only. Downloads never read records from the catalog.
EXAMPLE_FIELDS = {
    'Spell': {'school': 'Example school', 'description': 'Replace with the spell effect.',
              'casting_time': '1 standard action', 'verbal_component': True, 'somatic_component': False},
    'Feat': {'feat_categories': ['Example feat category'], 'description': 'Replace with a short description.',
             'benefit': 'Replace with the verified benefit.'},
    'Monster': {'size': 'Example size', 'type': 'Example creature type', 'hit_dice': '2d8+2 (11 hp)',
                'initiative': 2, 'armor_class': '14', 'base_attack': 2, 'grapple': 3,
                'attack': 'Claw +3 melee (1d4+1)', 'full_attack': '2 claws +3 melee (1d4+1)',
                'space': 5, 'reach': 5, 'fort_save': 4, 'reflex_save': 2, 'will_save': 0,
                'str': 12, 'dex': 14, 'con': 12, 'int': 10, 'wis': 10, 'cha': 10, 'challenge_rating': 1},
    'Item': {'type': 'MAG', 'description': 'Replace with the verified item effect.'},
    'CreatureTemplate': {'kind': 'acquired', 'applicable_creatures': 'Replace with eligible creatures.',
                         'mechanical_changes': 'Replace with the verified template changes.'},
    'mysteries': {'detail_path': 'Example path', 'detail_grade': 'apprentice', 'detail_mystery_level': 1},
    'invocations': {'detail_grade': 'least', 'detail_invocation_type': 'other', 'detail_equivalent_level': 1},
    'psionics': {'detail_discipline': 'Clairsentience', 'detail_power_points': 1,
                 'detail_class_levels': 'Example class | 1'},
    'auras': {'detail_character_class': 'Example class', 'detail_radius': '30 ft.'},
    'maneuvers': {'detail_discipline': 'Desert Wind', 'detail_maneuver_type': 'strike', 'detail_maneuver_level': 1},
    'monstrous-traits': {'detail_ability_type': 'Ex', 'detail_role': 'attack',
                        'detail_monsters': ['Example monster']},
}


def example_file(resource, kind, file_format):
    fields = ['resource', 'source_reference', *editable_form(resource, kind=kind or None).base_fields]
    example = {'resource': resource, 'name': 'Example record', 'rulebook': 'Example D&D 3.5 rulebook',
               'source_reference': 'Example D&D 3.5 rulebook, p. 12'}
    if 'page' in fields:
        example['page'] = 12
    if kind:
        example.update(kind=kind, mechanics='Replace with the verified rule.')
    example.update(EXAMPLE_FIELDS[kind or resource])
    if file_format == 'json':
        return json.dumps([example], indent=2) + '\n'
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, delimiter=DOWNLOAD_FORMATS[file_format])
    writer.writeheader()
    csv_values = {name: '|'.join(value) if isinstance(value, list) else value
                  for name, value in example.items()}
    writer.writerow(csv_values)
    return '\ufeff' + output.getvalue()


def _unique_fields(pairs):
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError('Duplicate JSON field')
    return fields


def _invalid_constant(value):
    raise ValueError('Invalid JSON number: ' + value)


def _source_rows(content, json_file, allowed, max_rows):
    if json_file:
        try:
            rows = json.loads(content, object_pairs_hook=_unique_fields,
                              parse_float=Decimal, parse_constant=_invalid_constant)
            json.dumps(rows, default=str, ensure_ascii=False).encode('utf-8')
        except (ValueError, ArithmeticError, RecursionError) as error:
            raise forms.ValidationError(_('Invalid JSON or repeated field name.')) from error
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise forms.ValidationError(_('JSON must be an array of record objects.'))
        if len(rows) > max_rows:
            raise _row_limit_error(max_rows)
        for number, row in enumerate(rows, 1):
            yield number, row
    else:
        # Header names are fixed identifiers, so a semicolon in the header
        # unambiguously identifies the separator of a supported CSV.
        header = next(iter(StringIO(content, newline='')), '')
        delimiter = ';' if ';' in header else ','
        reader = csv.DictReader(StringIO(content, newline=''), delimiter=delimiter, strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not REQUIRED_COLUMNS <= set(headers):
            raise forms.ValidationError(_('CSV needs unique headers including source_reference, name and rulebook.'))
        _check_columns(headers, allowed)
        for number, row in enumerate(reader, 2):
            if None in row or None in row.values():
                raise forms.ValidationError(_('Row %(row)s does not match the CSV header.') % {'row': number})
            yield number, row


def _check_columns(fields, allowed):
    unknown = set(fields) - allowed
    if unknown:
        raise forms.ValidationError(_('The file contains fields that cannot be imported: %(fields)s') % {
            'fields': ', '.join(sorted(unknown))})


def _relation_value(field, value):
    if isinstance(field, forms.ModelMultipleChoiceField):
        values = value if isinstance(value, list) else value.split('|')
        parts = [part.strip() for part in values if part.strip()]
    else:
        parts = [value]
    resolved = []
    for part in parts:
        if part.isascii() and part.isdigit() and len(part) <= 19:
            queryset = field.queryset.filter(pk=part)
        else:
            queryset = field.queryset.filter(name__iexact=part)
        matches = list(queryset[:2])
        if len(matches) != 1:
            raise forms.ValidationError(_('Related record “%(value)s” must have one exact match; use its ID if the name is ambiguous.') % {'value': part})
        resolved.append(str(matches[0].pk))
    return resolved if isinstance(field, forms.ModelMultipleChoiceField) else (resolved[0] if resolved else '')


def _field_value(field, value):
    if value is None:
        return ''
    if isinstance(field, forms.BooleanField):
        values = {'': False, 'false': False, '0': False, 'true': True, '1': True}
        normalized = str(value).strip().lower()
        if normalized not in values:
            raise forms.ValidationError(_('Use true or false for yes/no fields.'))
        return values[normalized]
    related_multiple = isinstance(field, forms.ModelMultipleChoiceField)
    if isinstance(value, list) and related_multiple and all(type(part) in (str, int) for part in value):
        return _relation_value(field, [str(part) for part in value])
    if type(value) not in (str, int, Decimal):
        raise forms.ValidationError(_('Use text or a number, or a list for multiple related records.'))
    value = str(value).strip()
    if value and isinstance(field, forms.ModelChoiceField):
        return _relation_value(field, value)
    return value


def validated_rows(content, resource, kind, *, json_file=False, max_rows=None, progress=None):
    max_rows = MAX_ROWS if max_rows is None else max_rows
    if len(content.encode('utf-8')) > MAX_BYTES:
        raise forms.ValidationError(_('The file exceeds the %(mib)s MiB limit.') % {'mib': MAX_MIB})
    Form = editable_form(resource, kind=kind or None)
    allowed = {'resource', 'source_reference', *Form.base_fields}
    rows = []
    seen = set()
    try:
        for number, row in _source_rows(content.lstrip('\ufeff'), json_file, allowed, max_rows):
            if len(rows) >= max_rows:
                raise _row_limit_error(max_rows)
            try:
                declared = row.get('resource')
                if json_file and not declared:
                    raise forms.ValidationError(_(
                        'JSON records must declare resource. Download the current example for this importer.'))
                if declared and declared != resource:
                    raise forms.ValidationError(_(
                        'This file declares %(actual)s, but this form imports %(expected)s. Use the correct importer.') % {
                            'actual': RESOURCE_LABELS.get(declared, declared) if isinstance(declared, str) else declared,
                            'expected': RESOURCE_LABELS[resource],
                        })
                _check_columns(row, allowed)
                source = row.get('source_reference')
                if not isinstance(source, str) or not source.strip():
                    raise forms.ValidationError(_('Enter the official source and page.'))
                if len(source.strip()) > 2000:
                    raise forms.ValidationError(_('The source reference may contain up to 2000 characters.'))
                data = {}
                for name, field in Form.base_fields.items():
                    if name in row:
                        try:
                            data[name] = _field_value(field, row[name])
                        except forms.ValidationError as error:
                            raise forms.ValidationError('%s: %s' % (
                                field.label or name, '; '.join(error.messages))) from error
                if kind:
                    if data.get('kind') not in (None, '', kind):
                        raise forms.ValidationError(_('This record has a different catalog type.'))
                    data['kind'] = kind
                form = Form(data)
                if not form.is_valid():
                    problems = [
                        '%s: %s' % (form[name].label, '; '.join(errors)) if name in form.fields
                        else '; '.join(errors)
                        for name, errors in form.errors.items()
                    ]
                    raise forms.ValidationError(problems)
                validate_new_edition(resource, form)
                detect_duplicate(resource, form)
                key = (form.cleaned_data['name'].casefold(), form.cleaned_data['rulebook'].pk)
                if key in seen:
                    raise forms.ValidationError(_('This record duplicates another entry in the file.'))
                seen.add(key)
            except forms.ValidationError as error:
                raise forms.ValidationError(_('Row %(row)s: %(error)s') % {
                    'row': number, 'error': '; '.join(error.messages)}) from error
            rows.append((number, row, form))
            if progress and len(rows) % INLINE_ROWS == 0:
                progress(len(rows))
    except csv.Error as error:
        raise forms.ValidationError(_('Invalid CSV format.')) from error
    if not rows:
        raise forms.ValidationError(_('The file has no records.'))
    return rows


def preview_digest(rows):
    values = []
    for _, _, form in rows:
        payload = serialize_form(form)
        if payload.get('detail_class_levels'):
            payload['detail_class_levels'] = [(cls.pk, level) for cls, level in
                                               parse_class_levels(payload['detail_class_levels'])]
        values.append(payload)
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


@transaction.atomic
def publish_rows(content, resource, kind, user, *, json_file=False, expected_digest, wait=True):
    if not can_import(user, resource, kind=kind or None):
        raise PermissionDenied
    rows = validated_rows(content, resource, kind, json_file=json_file)
    if preview_digest(rows) != expected_digest:
        raise forms.ValidationError(_('Catalog values changed after the preview. Upload the file again.'))
    lock_creation_books({form.cleaned_data['rulebook'].pk for number, raw, form in rows}, wait=wait)
    user.refresh_from_db(fields=('is_active', 'is_staff', 'is_superuser', 'email'))
    if not can_import(user, resource, kind=kind or None):
        raise PermissionDenied
    for number, raw, form in rows:
        entry = save_catalog_entry(resource, form, user, creating=True)
        EditorialProposal.objects.create(
            resource=resource, action='create', target_pk=entry.pk,
            payload=serialize_form(form), source_reference=raw['source_reference'].strip(),
            status='approved', author=user, reviewer=user,
            review_note='Direct file import', reviewed_at=timezone.now(),
        )
    user.refresh_from_db(fields=('is_active', 'is_staff', 'is_superuser', 'email'))
    if not can_import(user, resource, kind=kind or None):
        raise PermissionDenied
    return len(rows)
