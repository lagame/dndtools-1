from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):
    dependencies = [('dnd', '0008_site_domain')]

    operations = [
        migrations.AddField(
            model_name='editorialgrant',
            name='can_import',
            field=models.BooleanField(default=False, verbose_name=_('Can publish imports directly')),
        ),
    ]
