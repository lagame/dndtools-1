"""Use the catalog domain for absolute sitemap URLs."""

from django.db import migrations


def set_site_domain(apps, schema_editor):
    Site = apps.get_model('sites', 'Site')
    Site.objects.using(schema_editor.connection.alias).update_or_create(
        pk=1, defaults={'domain': 'dndtools.quest', 'name': 'D&D Tools'})


class Migration(migrations.Migration):
    dependencies = [
        ('dnd', '0007_auradetail_invocationdetail_maneuverdetail_and_more'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [migrations.RunPython(set_site_domain, migrations.RunPython.noop)]
