from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('dnd', '0004_supplementalentry')]

    operations = [
        migrations.AddField(
            model_name='editorialgrant',
            name='can_delete',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='editorialproposal',
            name='action',
            field=models.CharField(
                choices=[('create', 'Create'), ('correct', 'Correct'),
                         ('translate', 'Translate'), ('delete', 'Remove')],
                max_length=16,
            ),
        ),
    ]
