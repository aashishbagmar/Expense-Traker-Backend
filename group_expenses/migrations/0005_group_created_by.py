from django.db import migrations, models
import django.conf


class Migration(migrations.Migration):

    dependencies = [
        ('group_expenses', '0004_groupexpense_split_breakdown'),
        migrations.swappable_dependency(django.conf.settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='groups_created', to=django.conf.settings.AUTH_USER_MODEL),
        ),
    ]
