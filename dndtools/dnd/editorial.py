"""Validated, permissioned proposals for the existing catalog models."""

import hashlib
import json
from decimal import Decimal
from datetime import date, datetime

from django import forms
from django.apps import apps
from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.db.models.functions import Collate
from django.forms import modelform_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dnd.models import EditorialGrant, EditorialProposal, PublishedTranslation, SupplementalEntry


RESOURCE_GROUPS = {
    _('Rulebooks and rules'): ('DndEdition', 'Rulebook', 'Rule', 'RuleCondition'),
    _('Character options'): ('CharacterClass', 'CharacterClassVariant',
                          'CharacterClassVariantRequiresRace', 'CharacterClassVariantRequiresFeat',
                          'CharacterClassVariantRequiresSkill', 'FeatCategory', 'Feat',
                          'SpecialFeatPrerequisite', 'TextFeatPrerequisite',
                          'FeatSpecialFeatPrerequisite', 'FeatRequiresFeat', 'FeatRequiresSkill',
                          'Skill', 'SkillVariant', 'Deity', 'Language'),
    'Magic': ('Spell', 'SpellClassLevel', 'SpellDomainLevel', 'SpellSchool',
              'SpellSubSchool', 'SpellDescriptor', 'Domain', 'DomainVariant'),
    'Bestiary': ('Race', 'RaceSize', 'RaceSpeedType', 'RaceType', 'RaceSpeed',
                 'RaceFavoredCharacterClass', 'Monster', 'MonsterType',
                 'MonsterSubtype', 'MonsterHasFeat', 'MonsterHasSkill',
                 'MonsterSpeed', 'CreatureTemplate'),
    'Items': ('Item', 'ItemSlot', 'ItemProperty', 'ItemAuraType', 'ItemActivationType'),
    'Additional 3.5 mechanics': ('SupplementalEntry',),
}
RESOURCES = frozenset(name for names in RESOURCE_GROUPS.values() for name in names)
GRANT_CHOICES = ([(name, name) for name in sorted(RESOURCES - {'SupplementalEntry'})] +
                 [('SupplementalEntry', 'All additional mechanics')] +
                 [('SupplementalEntry:' + kind, label) for kind, label in SupplementalEntry.KINDS])
EXCLUDED_FIELDS = {'slug', 'verified', 'verified_author', 'verified_time', 'added'}
UNTRANSLATED_FIELDS = {'slug', 'abbr', 'system', 'kind', 'type', 'year',
                       'url', 'official_url', 'website', 'email', 'code',
                       'icon', 'print_format'}


def model_for(resource):
    if resource not in RESOURCES:
        raise ValueError('Unknown catalog resource.')
    return apps.get_model('dnd', resource)


def owner(user):
    return user.is_authenticated and user.is_active and user.is_superuser and (
        user.email.casefold() == settings.ADMINS[0][1].casefold())


def can_propose(user, resource, action, *, kind=None):
    if not user.is_authenticated or not user.is_active or not user.is_staff or resource not in RESOURCES:
        return False
    if owner(user):
        return True
    field = {'create': 'can_create', 'correct': 'can_correct',
             'translate': 'can_translate'}.get(action)
    if not field:
        return False
    choices = [resource]
    if resource == 'SupplementalEntry':
        choices += (['SupplementalEntry:' + kind] if kind else
                    ['SupplementalEntry:' + name for name, _ in SupplementalEntry.KINDS])
    return EditorialGrant.objects.filter(
        user=user, resource__in=choices, **{field: True}).exists()


def editable_form(resource):
    model = model_for(resource)
    fields = [field.name for field in model._meta.get_fields()
              if field.concrete and field.editable and not field.auto_created
              and not (field.many_to_many and not field.remote_field.through._meta.auto_created)
              and field.name not in EXCLUDED_FIELDS and not field.name.endswith('_html')
              and not isinstance(field, (models.FileField, models.ImageField))]
    return modelform_factory(model, fields=fields)


def translatable_fields(obj):
    result = {}
    for field in obj._meta.concrete_fields:
        if (isinstance(field, (models.CharField, models.TextField))
                and field.name not in UNTRANSLATED_FIELDS
                and not field.name.endswith('_html')):
            value = getattr(obj, field.name)
            if value:
                result[field.name] = value
    return result


def source_digest(obj, *, translation=False):
    if translation:
        values = translatable_fields(obj)
    else:
        fields = editable_form(obj._meta.object_name)().fields
        values = {}
        for name in fields:
            value = getattr(obj, name)
            if isinstance(value, models.Manager):
                value = sorted(value.values_list('pk', flat=True))
            elif isinstance(value, models.Model):
                value = value.pk
            values[name] = value
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str,
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def translation_form(obj):
    fields = {}
    for name, value in translatable_fields(obj).items():
        model_field = obj._meta.get_field(name)
        fields[name] = forms.CharField(
            label=model_field.verbose_name, required=True,
            max_length=getattr(model_field, 'max_length', None),
            widget=forms.Textarea(attrs={'rows': 5}) if isinstance(model_field, models.TextField)
            else forms.TextInput(),
            help_text='Original: ' + str(value)[:300],
        )
    return type('%sTranslationForm' % obj._meta.object_name, (forms.Form,), fields)


def serialize_form(form):
    data = {}
    for name, value in form.cleaned_data.items():
        if isinstance(value, models.Model):
            value = value.pk
        elif isinstance(value, models.QuerySet):
            value = list(value.values_list('pk', flat=True))
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        data[name] = value
    return data


def validate_new_edition(resource, form):
    if resource == 'DndEdition':
        if form.cleaned_data.get('system') != 'DnD 3.5':
            raise forms.ValidationError('New catalog entries must be confirmed D&D 3.5.')
    book = form.cleaned_data.get('rulebook')
    if book and book.dnd_edition.system != 'DnD 3.5':
        raise forms.ValidationError('New catalog entries must use a confirmed D&D 3.5 rulebook.')
    edition = form.cleaned_data.get('dnd_edition')
    if edition and edition.system != 'DnD 3.5':
        raise forms.ValidationError('New catalog entries must use D&D 3.5.')


def detect_duplicate(resource, form):
    model = model_for(resource)
    name = form.cleaned_data.get('name')
    if not name or not any(field.name == 'name' for field in model._meta.concrete_fields):
        return
    matches = model.objects.alias(_name=Collate(F('name'), 'utf8mb4_0900_ai_ci')).filter(_name__exact=name)
    book = form.cleaned_data.get('rulebook')
    if book and any(field.name == 'rulebook' for field in model._meta.concrete_fields):
        matches = matches.filter(rulebook=book)
    edition = form.cleaned_data.get('dnd_edition')
    if edition and any(field.name == 'dnd_edition' for field in model._meta.concrete_fields):
        matches = matches.filter(dnd_edition=edition)
    if resource == 'SupplementalEntry':
        matches = matches.filter(kind=form.cleaned_data.get('kind'))
    if matches.exists():
        raise forms.ValidationError('A catalog record with this original name already exists.')


@transaction.atomic
def approve(proposal, reviewer):
    if not owner(reviewer):
        raise PermissionError('Only the owner may approve proposals.')
    proposal = EditorialProposal.objects.select_for_update().get(pk=proposal.pk)
    if proposal.status != 'pending':
        raise forms.ValidationError('This proposal has already been reviewed.')
    model = model_for(proposal.resource)
    target = None
    if proposal.action != 'create':
        target = model.objects.select_for_update().get(pk=proposal.target_pk)
        if source_digest(target, translation=proposal.action == 'translate') != proposal.source_digest:
            raise forms.ValidationError('The original changed after submission. Request a new proposal.')
    if proposal.action == 'translate':
        form = translation_form(target)(proposal.payload)
        if not form.is_valid():
            raise forms.ValidationError('Translation is incomplete or invalid.')
        PublishedTranslation.objects.update_or_create(
            resource=proposal.resource, target_pk=target.pk, locale='pt-br',
            defaults={'payload': serialize_form(form), 'source_digest': proposal.source_digest,
                      'author': proposal.author, 'reviewer': reviewer},
        )
    else:
        form = editable_form(proposal.resource)(proposal.payload, instance=target)
        if not form.is_valid():
            raise forms.ValidationError('The proposed catalog values are no longer valid: %s' % form.errors)
        if proposal.action == 'create':
            validate_new_edition(proposal.resource, form)
            detect_duplicate(proposal.resource, form)
        entry = form.save(commit=False)
        if proposal.action == 'create' and hasattr(entry, 'slug') and not entry.slug:
            from django.utils.text import slugify
            limit = entry._meta.get_field('slug').max_length
            base = slugify(getattr(entry, 'name', '')) or entry._meta.model_name
            candidate = base[:limit]
            number = 2
            while model.objects.filter(slug=candidate).exists():
                suffix = '-%s' % number
                candidate = base[:limit - len(suffix)] + suffix
                number += 1
            entry.slug = candidate
        if proposal.resource == 'Spell':
            entry.verified = True
            entry.verified_author = reviewer
            entry.verified_time = timezone.now()
        entry.full_clean()
        entry.save()
        form.save_m2m()
        proposal.target_pk = entry.pk
    proposal.status = 'approved'
    proposal.reviewer = reviewer
    proposal.reviewed_at = timezone.now()
    proposal.save(update_fields=('status', 'reviewer', 'reviewed_at', 'target_pk'))
    return proposal
