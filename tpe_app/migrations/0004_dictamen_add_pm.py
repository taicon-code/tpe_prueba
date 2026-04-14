# Generated migration for adding PM field to DICTAMEN

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0003_alter_pm_pm_arma_alter_pm_pm_escalafon_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dictamen',
            name='pm',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='tpe_app.pm',
                verbose_name='Militar',
            ),
        ),
    ]
