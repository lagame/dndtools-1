from django.db.models import F, Q
from django.db.models.functions import Collate
import django_filters2

from dnd.search import COLLATION


class CatalogCharFilter(django_filters2.CharFilter):
    def filter(self, qs, value):
        if not value or self.lookup_type != 'icontains':
            return super().filter(qs, value)
        alias = f'_catalog_ci_{self.creation_counter}'
        return qs.alias(**{alias: Collate(F(self.name), COLLATION)}).filter(
            **{f'{alias}__contains': value})


class FeatMultiPrerequisiteFieldFilter(CatalogCharFilter):
    def filter(self, qs, value):
        if value:
            fields = (
                'special_feat_prerequisites__print_format', 'textfeatprerequisite__text',
                'required_skills__skill__name', 'required_feats__required_feat__name',
            )
            aliases = {f'_prerequisite_ci_{index}': Collate(F(field), COLLATION)
                       for index, field in enumerate(fields)}
            matches = Q()
            for alias in aliases:
                matches |= Q(**{f'{alias}__contains': value})
            return qs.alias(**aliases).filter(matches)
        return qs
