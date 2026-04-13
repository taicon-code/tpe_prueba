# Generated migration for adding VOCAL_TPE and vocal_excusado field

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0004_dictamen_add_pm'),
    ]

    operations = [
        migrations.CreateModel(
            name='VOCAL_TPE',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cargo', models.CharField(
                    choices=[
                        ('PRESIDENTE', 'Presidente'),
                        ('VICEPRESIDENTE', 'Vicepresidente'),
                        ('VOCAL', 'Vocal'),
                    ],
                    max_length=20,
                    verbose_name='Cargo'
                )),
                ('activo', models.BooleanField(default=True, verbose_name='Activo')),
                ('pm', models.ForeignKey(
                    on_delete=django.db.models.deletion.RESTRICT,
                    to='tpe_app.pm',
                    verbose_name='Militar'
                )),
            ],
            options={
                'verbose_name': 'Vocal del Tribunal',
                'verbose_name_plural': 'Vocales del Tribunal',
                'db_table': 'vocal_tpe',
                'ordering': ['cargo', 'pm__PM_PATERNO'],
            },
        ),
        migrations.AddField(
            model_name='autotpe',
            name='vocal_excusado',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='tpe_app.vocal_tpe',
                verbose_name='Vocal Excusado'
            ),
        ),
    ]
