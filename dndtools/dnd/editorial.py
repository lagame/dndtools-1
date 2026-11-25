"""Validated, permissioned proposals for the existing catalog models."""

import hashlib
import json
from decimal import Decimal
from datetime import date, datetime

from django import forms
from django.apps import apps
from django.conf import settings
from django.db import OperationalError, models, transaction
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django.db.models import F
from django.db.models.functions import Collate
from django.forms import modelform_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from dnd.models import (EditorialGrant, EditorialProposal,
                        PublishedTranslation, Rulebook, SupplementalEntry)


RESOURCE_GROUPS = {
    _('Rulebooks and rules'): ('DndEdition', 'Rulebook', 'Rule', 'RuleCondition'),
    _('Character options'): ('CharacterClass', 'CharacterClassVariant',
                          'CharacterClassVariantRequiresRace', 'CharacterClassVariantRequiresFeat',
                          'CharacterClassVariantRequiresSkill', 'FeatCategory', 'Feat',
                          'SpecialFeatPrerequisite', 'TextFeatPrerequisite',
                          'FeatSpecialFeatPrerequisite', 'FeatRequiresFeat', 'FeatRequiresSkill',
                          'Skill', 'SkillVariant', 'Deity', 'Language'),
    _('Magic'): ('Spell', 'SpellClassLevel', 'SpellDomainLevel', 'SpellSchool',
              'SpellSubSchool', 'SpellDescriptor', 'Domain', 'DomainVariant'),
    _('Bestiary'): ('Race', 'RaceSize', 'RaceSpeedType', 'RaceType', 'RaceSpeed',
                 'RaceFavoredCharacterClass', 'Monster', 'MonsterType',
                 'MonsterSubtype', 'MonsterHasFeat', 'MonsterHasSkill',
                 'MonsterSpeed', 'CreatureTemplate'),
    _('Items'): ('Item', 'ItemSlot', 'ItemProperty', 'ItemAuraType', 'ItemActivationType'),
    _('Additional 3.5 mechanics'): ('SupplementalEntry',),
}
RESOURCES = frozenset(name for names in RESOURCE_GROUPS.values() for name in names)
RESOURCE_LABELS = {
    'DndEdition': _('Editions'), 'Rulebook': _('Rulebooks'), 'Rule': _('Rules'),
    'RuleCondition': _('Rule conditions'), 'CharacterClass': _('Classes'),
    'CharacterClassVariant': _('Class variants'),
    'CharacterClassVariantRequiresRace': _('Class variant race requirements'),
    'CharacterClassVariantRequiresFeat': _('Class variant feat requirements'),
    'CharacterClassVariantRequiresSkill': _('Class variant skill requirements'),
    'FeatCategory': _('Feat categories'), 'Feat': _('Feats'),
    'SpecialFeatPrerequisite': _('Special feat prerequisites'),
    'TextFeatPrerequisite': _('Text feat prerequisites'),
    'FeatSpecialFeatPrerequisite': _('Feat special prerequisites'),
    'FeatRequiresFeat': _('Feat requirements'),
    'FeatRequiresSkill': _('Feat skill requirements'),
    'Skill': _('Skills'), 'SkillVariant': _('Skill variants'),
    'Deity': _('Deities'), 'Language': _('Languages'),
    'Spell': _('Spells'), 'SpellClassLevel': _('Spell class levels'),
    'SpellDomainLevel': _('Spell domain levels'),
    'SpellSchool': _('Spell schools'), 'SpellSubSchool': _('Spell subschools'),
    'SpellDescriptor': _('Spell descriptors'), 'Domain': _('Domains'),
    'DomainVariant': _('Domain variants'), 'Race': _('Races'),
    'RaceSize': _('Race sizes'), 'RaceSpeedType': _('Race speed types'),
    'RaceType': _('Race types'), 'RaceSpeed': _('Race speeds'),
    'RaceFavoredCharacterClass': _('Race favored classes'),
    'Monster': _('Monsters'), 'MonsterType': _('Monster types'),
    'MonsterSubtype': _('Monster subtypes'), 'MonsterHasFeat': _('Monster feats'),
    'MonsterHasSkill': _('Monster skills'), 'MonsterSpeed': _('Monster speeds'),
    'CreatureTemplate': _('Creature templates'), 'Item': _('Items'),
    'ItemSlot': _('Item slots'), 'ItemProperty': _('Item properties'),
    'ItemAuraType': _('Item aura types'), 'ItemActivationType': _('Item activation types'),
    'SupplementalEntry': _('Additional mechanics'),
}
KIND_LABELS = {
    'mysteries': _('Shadow casting mysteries'),
    'invocations': _('Invocations'),
    'psionics': _('Psionic powers'),
    'auras': _('Auras'),
    'maneuvers': _('Martial maneuvers'),
    'monstrous-traits': _('Monstrous traits'),
}
FIELD_LABELS = {
    'name': _('Name'), 'rulebook': _('Rulebook'), 'dnd_edition': _('Edition'),
    'page': _('Page'), 'page_from': _('First page'), 'page_to': _('Last page'),
    'description': _('Description'), 'short_description': _('Short description'),
    'body': _('Rule text'), 'text': _('Text'), 'extra': _('Additional details'),
    'kind': _('Type'), 'type': _('Type'), 'category': _('Category'),
    'level': _('Level'), 'mechanics': _('Rules text'), 'prerequisites': _('Prerequisites'),
    'character_class': _('Class'), 'character_class_variant': _('Class variant'),
    'race': _('Race'), 'feat': _('Feat'), 'spell': _('Spell'), 'skill': _('Skill'),
    'monster': _('Monster'), 'domain': _('Domain'), 'school': _('School'),
    'sub_school': _('Subschool'), 'size': _('Size'), 'system': _('System'),
    'core': _('Core book'), 'prestige': _('Prestige class'),
    'skill_points': _('Skill points'), 'requirements': _('Requirements'),
    'required_bab': _('Required base attack bonus'), 'class_features': _('Class features'),
    'hit_die': _('Hit die'), 'alignment': _('Alignment'),
    'starting_gold': _('Starting gold'), 'advancement': _('Advancement'),
    'class_skills': _('Class skills'), 'ranks': _('Ranks'),
    'text_before': _('Text before'), 'text_after': _('Text after'),
    'remove_comma': _('Remove comma'), 'benefit': _('Benefit'),
    'special': _('Special'), 'normal': _('Normal'),
    'source_feat': _('Source feat'), 'required_feat': _('Required feat'),
    'min_rank': _('Minimum ranks'), 'additional_text': _('Additional text'),
    'special_feat_prerequisite': _('Special prerequisite'),
    'value_1': _('First value'), 'value_2': _('Second value'),
    'base_skill': _('Base skill'), 'trained_only': _('Trained only'),
    'armor_check_penalty': _('Armor check penalty'),
    'check_text': _('Check'), 'action': _('Action'),
    'try_again': _('Try again'), 'synergy': _('Synergy'),
    'restriction': _('Restriction'), 'untrained': _('Untrained'),
    'deities_text': _('Deities'), 'requirement': _('Requirement'),
    'granted_power': _('Granted power'), 'granted_power_type': _('Granted power type'),
    'deities': _('Deities'), 'other_deities': _('Other deities'),
    'favored_weapon': _('Favored weapon'), 'print_format': _('Display format'),
    'applicable_creatures': _('Applicable creatures'),
    'challenge_rating_adjustment': _('Challenge rating adjustment'),
    'level_adjustment': _('Level adjustment'),
    'mechanical_changes': _('Mechanical changes'),
    'publication_type': _('Publication type'), 'isbn': _('ISBN'),
    'authors': _('Authors'), 'cover_artist': _('Cover artist'),
    'publisher': _('Publisher'), 'pages': _('Pages'), 'format': _('Format'),
    'bibliography_url': _('Bibliography URL'), 'year': _('Year'),
    'published': _('Published'), 'official_url': _('Official URL'),
    'abbr': _('Abbreviation'), 'price_gp': _('Price in gp'),
    'price_bonus': _('Enhancement bonus'), 'item_level': _('Item level'),
    'body_slot': _('Body slot'), 'property': _('Property'),
    'caster_level': _('Caster level'), 'aura': _('Aura'), 'aura_dc': _('Aura DC'),
    'activation': _('Activation'), 'weight': _('Weight'),
    'visual_description': _('Appearance'), 'cost_to_create': _('Creation cost'),
    'required_extra': _('Other requirements'),
    'synergy_prerequisite': _('Synergy prerequisite'),
    'aura_schools': _('Aura schools'), 'required_feats': _('Required feats'),
    'required_spells': _('Required spells'), 'feat_categories': _('Feat categories'),
    'descriptors': _('Descriptors'), 'subtypes': _('Subtypes'),
    'automatic_languages': _('Automatic languages'),
    'bonus_languages': _('Bonus languages'), 'race_type': _('Race type'),
    'racial_hit_dice_count': _('Racial hit dice'),
    'hit_die_size': _('Hit die size'),
    'base_attack_type': _('Base attack progression'),
    'base_fort_save_type': _('Fortitude save progression'),
    'base_reflex_save_type': _('Reflex save progression'),
    'base_will_save_type': _('Will save progression'),
    'speed': _('Speed'), 'order': _('Order'),
    'hit_dice': _('Hit dice'), 'initiative': _('Initiative'),
    'armor_class': _('Armor class'), 'touch_armor_class': _('Touch armor class'),
    'flat_footed_armor_class': _('Flat-footed armor class'),
    'base_attack': _('Base attack'), 'grapple': _('Grapple'),
    'attack': _('Attack'), 'full_attack': _('Full attack'),
    'space': _('Space'), 'reach': _('Reach'),
    'special_attacks': _('Special attacks'), 'special_qualities': _('Special qualities'),
    'fort_save': _('Fortitude save'), 'fort_save_extra': _('Fortitude details'),
    'reflex_save': _('Reflex save'), 'reflex_save_extra': _('Reflex details'),
    'will_save': _('Will save'), 'will_save_extra': _('Will details'),
    'str': _('Strength'), 'dex': _('Dexterity'), 'con': _('Constitution'),
    'int': _('Intelligence'), 'wis': _('Wisdom'), 'cha': _('Charisma'),
    'environment': _('Environment'), 'organization': _('Organization'),
    'challenge_rating': _('Challenge rating'), 'treasure': _('Treasure'),
    'combat': _('Combat'), 'racial_traits': _('Racial traits'),
    'natural_armor': _('Natural armor'),
    'verbal_component': _('Verbal component'), 'somatic_component': _('Somatic component'),
    'material_component': _('Material component'),
    'arcane_focus_component': _('Arcane focus component'),
    'divine_focus_component': _('Divine focus component'),
    'xp_component': _('XP component'), 'meta_breath_component': _('Metabreath component'),
    'true_name_component': _('Truename component'),
    'extra_components': _('Other components'), 'casting_time': _('Casting time'),
    'range': _('Range'), 'target': _('Target'), 'effect': _('Effect'),
    'area': _('Area'), 'duration': _('Duration'),
    'saving_throw': _('Saving throw'), 'spell_resistance': _('Spell resistance'),
    'corrupt_component': _('Corrupt component'), 'corrupt_level': _('Corrupt level'),
}
GRANT_CHOICES = ([(name, RESOURCE_LABELS[name]) for name in sorted(RESOURCES - {'SupplementalEntry'})] +
                 [('SupplementalEntry', _('All additional mechanics'))] +
                 [('SupplementalEntry:' + kind, KIND_LABELS[kind]) for kind, _ in SupplementalEntry.KINDS])
EXCLUDED_FIELDS = {'slug', 'verified', 'verified_author', 'verified_time', 'added'}
UNTRANSLATED_FIELDS = {'slug', 'abbr', 'system', 'kind', 'type', 'year',
                       'url', 'official_url', 'website', 'email', 'code',
                       'icon', 'print_format', 'publication_type', 'isbn',
                       'authors', 'cover_artist', 'publisher', 'format',
                       'bibliography_url'}


def model_for(resource):
    if resource not in RESOURCES:
        raise ValueError('Unknown catalog resource.')
    return apps.get_model('dnd', resource)


def owner(user):
    return user.is_authenticated and user.is_active and user.is_superuser and (
        user.username == settings.ADMINS[0][0] and
        user.email.casefold() == settings.ADMINS[0][1].casefold())


def can_propose(user, resource, action, *, kind=None):
    if not user.is_authenticated or not user.is_active or not user.is_staff or resource not in RESOURCES:
        return False
    if owner(user):
        return True
    field = {'create': 'can_create', 'correct': 'can_correct',
             'translate': 'can_translate', 'delete': 'can_delete'}.get(action)
    if not field:
        return False
    choices = [resource]
    if resource == 'SupplementalEntry':
        choices += (['SupplementalEntry:' + kind] if kind else
                    ['SupplementalEntry:' + name for name, _ in SupplementalEntry.KINDS])
    return EditorialGrant.objects.filter(
        user=user, resource__in=choices, **{field: True}).exists()


IMPORT_RESOURCES = frozenset(('Spell', 'Feat', 'Monster', 'Item', 'CreatureTemplate', 'SupplementalEntry'))


def can_import(user, resource, *, kind=None):
    if resource not in IMPORT_RESOURCES or (
            resource == 'SupplementalEntry' and kind not in KIND_LABELS):
        return False
    return owner(user)


def editable_form(resource, *, kind=None, target=None, structured=False):
    if resource == 'SupplementalEntry' and kind:
        from dnd.supplemental.catalog import detail_for
        from dnd.supplemental.forms import typed_form
        if target is None or detail_for(target) is not None or structured:
            return typed_form(kind)
    model = model_for(resource)
    fields = [field.name for field in model._meta.get_fields()
              if field.concrete and field.editable and not field.auto_created
              and not (field.many_to_many and not field.remote_field.through._meta.auto_created)
              and field.name not in EXCLUDED_FIELDS and not field.name.endswith('_html')
              and not isinstance(field, (models.FileField, models.ImageField))]
    form = modelform_factory(model, fields=fields)
    for name, field in form.base_fields.items():
        if name in FIELD_LABELS:
            field.label = FIELD_LABELS[name]
    if resource == 'SupplementalEntry':
        form.base_fields['kind'].choices = [('', '---------')] + list(KIND_LABELS.items())
    return form


def translatable_fields(obj):
    result = {}
    for field in obj._meta.concrete_fields:
        if (isinstance(field, (models.CharField, models.TextField))
                and field.name not in UNTRANSLATED_FIELDS
                and not field.name.endswith('_html')):
            value = getattr(obj, field.name)
            if value:
                result[field.name] = value
    if isinstance(obj, SupplementalEntry):
        from dnd.supplemental.catalog import detail_for
        detail = detail_for(obj)
        if detail:
            for field in detail._meta.concrete_fields:
                if (isinstance(field, (models.CharField, models.TextField))
                        and not field.choices and field.name not in ('id', 'entry')):
                    value = getattr(detail, field.name)
                    if value:
                        result['detail_' + field.name] = value
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
    if isinstance(obj, SupplementalEntry) and not translation:
        from dnd.supplemental.catalog import detail_for
        detail = detail_for(obj)
        if detail:
            for field in detail._meta.concrete_fields:
                if field.name in ('id', 'entry'):
                    continue
                values['detail_' + field.name] = getattr(detail, field.attname)
            if obj.kind == 'monstrous-traits':
                values['detail_monsters'] = sorted(detail.monsters.values_list('pk', flat=True))
            if obj.kind == 'psionics':
                values['detail_class_levels'] = sorted(detail.class_levels.values_list(
                    'character_class_id', 'level'))
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str,
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def translation_form(obj):
    fields = {}
    for name, value in translatable_fields(obj).items():
        if name.startswith('detail_') and isinstance(obj, SupplementalEntry):
            from dnd.supplemental.catalog import detail_for
            model_field = detail_for(obj)._meta.get_field(name[7:])
        else:
            model_field = obj._meta.get_field(name)
        fields[name] = forms.CharField(
            label=FIELD_LABELS.get(name, model_field.verbose_name), required=True,
            max_length=getattr(model_field, 'max_length', None),
            widget=forms.Textarea(attrs={'rows': 5}) if isinstance(model_field, models.TextField)
            else forms.TextInput(),
            help_text=str(_('Original')) + ': ' + str(value)[:300],
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
        raise forms.ValidationError(_('New catalog entries must use a confirmed D&D 3.5 rulebook.'))
    edition = form.cleaned_data.get('dnd_edition')
    if edition and edition.system != 'DnD 3.5':
        raise forms.ValidationError('New catalog entries must use D&D 3.5.')


def duplicate_name_key(resource, name):
    name = name.strip().casefold()
    if resource == 'Item' and name.endswith(' [relic]'):
        name = name[:-len(' [relic]')]
    return name


def detect_duplicate(resource, form):
    model = model_for(resource)
    name = form.cleaned_data.get('name')
    if not name or not any(field.name == 'name' for field in model._meta.concrete_fields):
        return
    matches = model.objects.alias(_name=Collate(F('name'), 'utf8mb4_0900_ai_ci'))
    if resource == 'Item':
        base = duplicate_name_key(resource, name)
        matches = matches.filter(_name__in=(base, '%s [Relic]' % base))
    else:
        matches = matches.filter(_name__exact=name)
    book = form.cleaned_data.get('rulebook')
    if book and any(field.name == 'rulebook' for field in model._meta.concrete_fields):
        matches = matches.filter(rulebook=book)
    edition = form.cleaned_data.get('dnd_edition')
    if edition and any(field.name == 'dnd_edition' for field in model._meta.concrete_fields):
        matches = matches.filter(dnd_edition=edition)
    if resource == 'SupplementalEntry':
        matches = matches.filter(kind=form.cleaned_data.get('kind'))
    if matches.exists():
        raise forms.ValidationError(_('A catalog record with this original name already exists.'))


def delete_without_cascading_catalog(target):
    """Remove a reviewed leaf record without silently removing linked content."""
    collector = Collector(using=target._state.db)
    try:
        collector.collect([target])
    except (ProtectedError, RestrictedError) as error:
        raise forms.ValidationError('Remove dependent records or links before approving removal.') from error
    allowed = {type(target)}
    if isinstance(target, SupplementalEntry):
        from dnd.supplemental.catalog import DETAILS
        from dnd.models import PsionicClassLevel
        allowed.update(model for _, model in DETAILS.values())
        allowed.add(PsionicClassLevel)
    for model, entries in collector.data.items():
        if not model._meta.auto_created and (model not in allowed or
                (model == type(target) and len(entries) != 1)):
            raise forms.ValidationError('Remove dependent records or links before approving removal.')
    for queryset in collector.fast_deletes:
        if not queryset.model._meta.auto_created and queryset.model not in allowed and queryset.exists():
            raise forms.ValidationError('Remove dependent records or links before approving removal.')
    collector.delete()


def lock_creation_books(book_ids, *, wait=True):
    # Both CSV publication and proposal approval lock the same source books
    # before checking duplicates. Batches acquire them in primary key order.
    try:
        list(Rulebook.objects.filter(pk__in=book_ids).order_by('pk')
             .select_for_update(nowait=not wait).values_list('pk', flat=True))
    except OperationalError as error:
        if wait or not error.args or error.args[0] != 3572:
            raise
        raise forms.ValidationError(_(
            'Another batch is publishing records in this rulebook. Try again when it finishes.')) from error


def save_catalog_entry(resource, form, reviewer, *, creating):
    """Save a validated catalog form, including its related and typed fields."""
    if creating:
        validate_new_edition(resource, form)
        detect_duplicate(resource, form)
    entry = form.save(commit=False)
    if creating and hasattr(entry, 'slug') and not entry.slug:
        from django.utils.text import slugify
        model = model_for(resource)
        limit = entry._meta.get_field('slug').max_length
        base = slugify(getattr(entry, 'name', '')) or entry._meta.model_name
        candidate = base[:limit]
        number = 2
        while model.objects.filter(slug=candidate).exists():
            suffix = '-%s' % number
            candidate = base[:limit - len(suffix)] + suffix
            number += 1
        entry.slug = candidate
    if resource == 'Spell':
        entry.verified = True
        entry.verified_author = reviewer
        entry.verified_time = timezone.now()
    entry.full_clean()
    entry.save()
    form.save_m2m()
    if hasattr(form, 'save_details'):
        form.save_details(entry)
    return entry


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
    if proposal.action == 'delete':
        target_pk = target.pk
        delete_without_cascading_catalog(target)
        PublishedTranslation.objects.filter(resource=proposal.resource, target_pk=target_pk).delete()
    elif proposal.action == 'translate':
        form = translation_form(target)(proposal.payload)
        if not form.is_valid():
            raise forms.ValidationError('Translation is incomplete or invalid.')
        PublishedTranslation.objects.update_or_create(
            resource=proposal.resource, target_pk=target.pk, locale='pt-br',
            defaults={'payload': serialize_form(form), 'source_digest': proposal.source_digest,
                      'author': proposal.author, 'reviewer': reviewer},
        )
    else:
        kind = proposal.payload.get('kind') if proposal.resource == 'SupplementalEntry' else None
        typed = any(name.startswith('detail_') for name in proposal.payload)
        form = editable_form(proposal.resource, kind=kind if typed else None,
                             target=target, structured=typed)(proposal.payload, instance=target)
        if not form.is_valid():
            raise forms.ValidationError('The proposed catalog values are no longer valid: %s' % form.errors)
        creating = proposal.action == 'create'
        book = form.cleaned_data.get('rulebook')
        if creating and proposal.resource in IMPORT_RESOURCES and book:
            lock_creation_books([book.pk], wait=False)
        entry = save_catalog_entry(proposal.resource, form, reviewer, creating=creating)
        proposal.target_pk = entry.pk
    proposal.status = 'approved'
    proposal.reviewer = reviewer
    proposal.reviewed_at = timezone.now()
    proposal.save(update_fields=('status', 'reviewer', 'reviewed_at', 'target_pk'))
    return proposal
