"""Public, single-record metadata for the same-origin forum integration."""

from django.apps import apps
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET


# A closed list keeps the forum from becoming a general catalog export endpoint.
RECORD_MODELS = {
    'spell': 'Spell', 'feat': 'Feat', 'monster': 'Monster',
    'creature_template': 'CreatureTemplate', 'supplemental': 'SupplementalEntry',
    'rulebook': 'Rulebook', 'character_class': 'CharacterClass',
    'character_class_variant': 'CharacterClassVariant',
    'skill': 'Skill', 'skill_variant': 'SkillVariant', 'race': 'Race', 'item': 'Item',
    'rule': 'Rule', 'deity': 'Deity', 'language': 'Language',
}


@require_GET
def record_metadata(request, kind, record_id):
    model_name = RECORD_MODELS.get(kind)
    if not model_name:
        return JsonResponse({'error': 'Unknown record type'}, status=404)
    record = get_object_or_404(apps.get_model('dnd', model_name), pk=record_id)
    name = record.name if hasattr(record, 'name') else str(record)
    response = JsonResponse({
        'name': name,
        'path': record.get_absolute_url(),
    })
    response['Cache-Control'] = 'public, max-age=300'
    return response
