# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from dnd.models import (FeatCategory, Skill, SpecialFeatPrerequisite, TextFeatPrerequisite,
                        FeatSpecialFeatPrerequisite, FeatRequiresFeat, Feat, FeatRequiresSkill,
                        CharacterClassVariant, RaceFavoredCharacterClass, Race, RaceSize, RaceSpeed,
                        RaceSpeedType, SkillVariant, NewsEntry, StaticPage, CharacterClassVariantRequiresFeat,
                        CharacterClassVariantRequiresRace, CharacterClassVariantRequiresSkill, MonsterHasFeat,
                        MonsterHasSkill, MonsterSpeed, Monster, MonsterSubtype, MonsterType, Rule, Item,
                        ItemSlot, ItemAuraType, ItemActivationType, ItemProperty, Language, RaceType, Deity,
                        DndEdition, Rulebook, CharacterClass, SpellDescriptor,
                        SpellSchool, SpellSubSchool, Spell, SpellClassLevel,
                        Domain, SpellDomainLevel, DomainVariant, RuleCondition,
                        EditorialGrant, CreatureTemplate, SupplementalEntry)
from dnd.editorial import FIELD_LABELS, GRANT_CHOICES, RESOURCE_LABELS, owner


class OwnerOnlyAdminMixin:
    def has_module_permission(self, request):
        return owner(request.user) or super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return owner(request.user) or super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return owner(request.user)

    def has_change_permission(self, request, obj=None):
        return owner(request.user)

    def has_delete_permission(self, request, obj=None):
        return owner(request.user)


class LocalizedCatalogFields:
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if field is not None:
            if db_field.name in FIELD_LABELS:
                field.label = FIELD_LABELS[db_field.name]
            if field.help_text == 'Textile enabled!':
                field.help_text = _('Textile formatting is supported.')
        return field


class CatalogModelAdmin(OwnerOnlyAdminMixin, LocalizedCatalogFields, admin.ModelAdmin):
    def get_changelist_instance(self, request):
        changelist = super().get_changelist_instance(request)
        for filter_spec in changelist.filter_specs:
            label = FIELD_LABELS.get(getattr(filter_spec, 'field_path', None))
            if label:
                filter_spec.title = label
        return changelist

    def changelist_view(self, request, extra_context=None):
        label = RESOURCE_LABELS.get(self.model.__name__, self.model._meta.verbose_name_plural)
        context = {'title': _('Manage %(model)s') % {'model': label}, **(extra_context or {})}
        return super().changelist_view(request, extra_context=context)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        label = RESOURCE_LABELS.get(self.model.__name__, self.model._meta.verbose_name_plural)
        title = _('Edit record — %(model)s') if object_id else _('Add record — %(model)s')
        context = {'title': title % {'model': label}, **(extra_context or {})}
        return super().changeform_view(request, object_id, form_url, extra_context=context)


class CatalogTabularInline(LocalizedCatalogFields, admin.TabularInline):
    def __init__(self, parent_model, admin_site):
        super().__init__(parent_model, admin_site)
        if self.model.__name__ in RESOURCE_LABELS:
            self.verbose_name = _('record')
            self.verbose_name_plural = RESOURCE_LABELS[self.model.__name__]


class ModifiedUserAdmin(OwnerOnlyAdminMixin, UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'last_login')


class OwnerOnlyGroupAdmin(OwnerOnlyAdminMixin, GroupAdmin):
    list_display = ('name',)


class NamedCatalogAdmin(CatalogModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('name',)


class EditorialGrantAdmin(admin.ModelAdmin):
    list_display = ('user', 'resource', 'can_create', 'can_correct', 'can_translate', 'can_delete')
    exclude = ('can_import',)
    list_filter = ('resource',)
    search_fields = ('user__username', 'user__email')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['resource'].widget = forms.Select(
            choices=GRANT_CHOICES)
        return form

    def has_module_permission(self, request):
        return owner(request.user)

    def has_view_permission(self, request, obj=None):
        return owner(request.user)

    def has_add_permission(self, request):
        return owner(request.user)

    def has_change_permission(self, request, obj=None):
        return owner(request.user)

    def has_delete_permission(self, request, obj=None):
        return owner(request.user)


class DndEditionAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', 'system', )
    list_display_links = ('name', )
    list_filter = ('system', )
    search_fields = ('name', )


class RulebookAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', 'dnd_edition', 'publication_type', 'isbn')
    list_display_links = ('name', )
    list_filter = ('dnd_edition', 'publication_type')
    search_fields = ('name', 'isbn', 'authors')


class CharacterClassAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', 'prestige')
    list_display_links = ('name', )
    list_filter = ('prestige', )
    search_fields = ('name', )


class CharacterClassVariantRequiresRaceInline(CatalogTabularInline):
    model = CharacterClassVariantRequiresRace
    extra = 3


class CharacterClassVariantRequiresFeatInline(CatalogTabularInline):
    model = CharacterClassVariantRequiresFeat
    extra = 3


class CharacterClassVariantRequiresSkillInline(CatalogTabularInline):
    model = CharacterClassVariantRequiresSkill
    extra = 3


class CharacterClassVariantAdmin(CatalogModelAdmin):
    list_display = ('id', 'character_class', 'rulebook', )
    list_filter = ('character_class', 'rulebook', )
    search_fields = ('character_class__name', )
    filter_horizontal = ('class_skills', )
    inlines = (
        CharacterClassVariantRequiresRaceInline, CharacterClassVariantRequiresFeatInline,
        CharacterClassVariantRequiresSkillInline,
    )


class ItemAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', 'price_gp', 'price_bonus')
    list_display_links = ('name', )
    search_fields = ('name', )
    filter_horizontal = ('required_spells', 'aura_schools', 'required_feats', )


class ItemSlotAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name')
    list_display_links = ('name', )
    search_fields = ('name', )


class ItemAuraTypeAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name')
    list_display_links = ('name', )
    search_fields = ('name', )


class ItemPropertyAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name')
    list_display_links = ('name', )
    search_fields = ('name', )


class ItemActivationTypeAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name')
    list_display_links = ('name', )
    search_fields = ('name', )


class DomainAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name',)
    list_display_links = ('name', )
    search_fields = ('name', )


class DomainVariantAdmin(CatalogModelAdmin):
    list_display = ('id', 'domain', 'rulebook', )
    list_display_links = ('domain', )
    list_filter = ('domain', 'rulebook', )
    search_fields = ('domain__name', )
    filter_horizontal = ('deities', 'other_deities', )


class SpellDescriptorAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', )
    list_display_links = ('name', )
    search_fields = ('name', )


class SpellSchoolAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', )
    list_display_links = ('name', )
    search_fields = ('name', )


class SpellSubSchoolAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', )
    list_display_links = ('name', )
    search_fields = ('name', )


class SpellClassLevelInline(CatalogTabularInline):
    model = SpellClassLevel
    extra = 3


class SpellDomainLevelInline(CatalogTabularInline):
    model = SpellDomainLevel
    extra = 3


class SpellAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = (
        'id', 'name', 'verified', 'verified_author', 'verified_time',
        'rulebook', 'page', 'school', 'sub_school',
    )
    list_display_links = ('name', )
    list_filter = ('verified', 'verified_author', 'rulebook',)
    date_hierarchy = 'verified_time'
    readonly_fields = ('verified', 'verified_author', 'verified_time', )
    search_fields = ('name', )
    inlines = (SpellClassLevelInline, SpellDomainLevelInline, )
    filter_horizontal = ('descriptors', )


class FeatCategoryAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', )
    list_display_links = ('name', )
    search_fields = ('name', )


class SkillAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = (
        'id', 'name', 'base_skill', 'trained_only', 'armor_check_penalty',
    )
    list_display_links = ('name', )
    search_fields = ('name', )
    list_filter = ('base_skill', 'trained_only', 'armor_check_penalty',)


class SkillVariantAdmin(CatalogModelAdmin):
    list_display = ('id', 'skill', 'rulebook', )
    list_filter = ('skill', 'rulebook', )


class SpecialFeatPrerequisiteAdmin(CatalogModelAdmin):
    list_display = (
        'name', 'print_format',
    )
    list_display_links = ('name', )
    search_fields = ('name', )


class TextFeatPrerequisiteInline(CatalogTabularInline):
    model = TextFeatPrerequisite
    extra = 3


class FeatSpecialFeatPrerequisiteInline(CatalogTabularInline):
    model = FeatSpecialFeatPrerequisite
    extra = 3


class FeatRequiresFeatInline(CatalogTabularInline):
    model = FeatRequiresFeat
    extra = 3
    fk_name = 'source_feat'


class FeatRequiresSkillInline(CatalogTabularInline):
    model = FeatRequiresSkill
    extra = 3


class FeatAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = (
        'id', 'name', 'rulebook',
    )
    list_display_links = ('name', )
    list_filter = (
        'rulebook',
    )
    search_fields = ('name', )
    inlines = (
        TextFeatPrerequisiteInline, FeatSpecialFeatPrerequisiteInline,
        FeatRequiresSkillInline,
        FeatRequiresFeatInline,
    )


class MonsterTypeAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', )
    list_display_links = ('name', )
    search_fields = ('name', )


class MonsterSubtypeAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', )
    list_display_links = ('name', )
    search_fields = ('name', )


class MonsterSpeedInline(CatalogTabularInline):
    model = MonsterSpeed
    extra = 1


class MonsterHasFeatInline(CatalogTabularInline):
    model = MonsterHasFeat
    extra = 3


class MonsterHasSkillInline(CatalogTabularInline):
    model = MonsterHasSkill
    extra = 3


class MonsterSubtypeInline(CatalogTabularInline):
    model = MonsterHasSkill
    extra = 3


class MonsterForm(forms.ModelForm):
    special_qualities = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = Monster
        fields = '__all__'


class MonsterAdmin(CatalogModelAdmin):
    form = MonsterForm
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('id', 'name', 'rulebook', )
    list_display_links = ('name', )
    list_filter = ('rulebook', )
    search_fields = ('name', )
    inlines = (
        MonsterSpeedInline, MonsterHasSkillInline, MonsterHasFeatInline,
    )


class RaceFavoredCharacterClassInline(CatalogTabularInline):
    model = RaceFavoredCharacterClass
    extra = 1


class RaceSpeedInline(CatalogTabularInline):
    model = RaceSpeed
    extra = 1


class RaceAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = (
        'id', 'name', 'rulebook', 'str', 'dex', 'con', 'int', 'wis', 'cha', 'level_adjustment',
    )
    list_display_links = ('name', )
    list_filter = (
        'rulebook',
    )
    search_fields = ('name', )
    inlines = (
        RaceFavoredCharacterClassInline, RaceSpeedInline
    )
    filter_horizontal = ('automatic_languages', 'bonus_languages', )


class RaceSizeAdmin(CatalogModelAdmin):
    list_display = (
        'name',
    )
    list_display_links = ('name', )


class RaceSpeedTypeAdmin(CatalogModelAdmin):
    list_display = (
        'name', 'extra'
    )
    list_display_links = ('name', )


class NewsEntryAdmin(CatalogModelAdmin):
    list_display = (
        'title', 'published', 'enabled',
    )
    date_hierarchy = 'published'


class StaticPageAdmin(CatalogModelAdmin):
    list_display = (
        'name',
    )


class RuleAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ('name', )
    list_display = (
        'name',
    )


class LanguageAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = (
        'name',
    )
    list_display_links = ('name', )
    search_fields = ('name', )


class RaceTypeAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = (
        'name',
    )
    list_display_links = ('name', )
    search_fields = ('name', )


class DeityAdmin(CatalogModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = (
        'name',
    )
    list_display_links = ('name', )
    search_fields = ('name', )


admin.site.register(DndEdition, DndEditionAdmin)
admin.site.register(Rulebook, RulebookAdmin)
admin.site.register(CharacterClass, CharacterClassAdmin)
admin.site.register(CharacterClassVariant, CharacterClassVariantAdmin)
admin.site.register(SpellDescriptor, SpellDescriptorAdmin)
admin.site.register(SpellSchool, SpellSchoolAdmin)
admin.site.register(SpellSubSchool, SpellSubSchoolAdmin)
admin.site.register(Spell, SpellAdmin)
admin.site.register(Domain, DomainAdmin)
admin.site.register(FeatCategory, FeatCategoryAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(SkillVariant, SkillVariantAdmin)
admin.site.register(SpecialFeatPrerequisite, SpecialFeatPrerequisiteAdmin)
admin.site.register(Feat, FeatAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(MonsterType, MonsterTypeAdmin)
admin.site.register(MonsterSubtype, MonsterSubtypeAdmin)
admin.site.register(Monster, MonsterAdmin)
admin.site.register(Race, RaceAdmin)
admin.site.register(RaceSize, RaceSizeAdmin)
admin.site.register(RaceSpeedType, RaceSpeedTypeAdmin)
admin.site.register(RaceType, RaceTypeAdmin)
admin.site.register(NewsEntry, NewsEntryAdmin)
admin.site.register(StaticPage, StaticPageAdmin)
admin.site.register(Rule, RuleAdmin)
admin.site.register(RuleCondition, NamedCatalogAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(ItemSlot, ItemSlotAdmin)
admin.site.register(ItemProperty, ItemPropertyAdmin)
admin.site.register(ItemAuraType, ItemAuraTypeAdmin)
admin.site.register(ItemActivationType, ItemActivationTypeAdmin)
admin.site.register(Deity, DeityAdmin)
admin.site.register(DomainVariant, DomainVariantAdmin)
admin.site.register(EditorialGrant, EditorialGrantAdmin)
admin.site.register(CreatureTemplate, NamedCatalogAdmin)
admin.site.register(SupplementalEntry, NamedCatalogAdmin)
admin.site.unregister(User)
admin.site.register(User, ModifiedUserAdmin)
admin.site.unregister(Group)
admin.site.register(Group, OwnerOnlyGroupAdmin)
