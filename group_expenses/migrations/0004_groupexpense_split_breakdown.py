from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group_expenses', '0003_groupmember_name_alter_groupmember_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupexpense',
            name='split_breakdown',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
