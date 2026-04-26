from datetime import date
from django.db import migrations, models


def cargar_feriados_2026(apps, schema_editor):
    FeriadoBolivia = apps.get_model('tpe_app', 'FeriadoBolivia')
    feriados = [
        (date(2026, 1, 23), 'Día Plurinacional de Bolivia'),
        (date(2026, 2, 16), 'Carnaval (lunes)'),
        (date(2026, 2, 17), 'Carnaval (martes)'),
        (date(2026, 4, 3),  'Viernes Santo'),
        (date(2026, 5, 1),  'Día del Trabajo'),
        (date(2026, 6, 4),  'Corpus Christi'),
        (date(2026, 6, 5),  'Día del Maestro Rural'),
        (date(2026, 6, 22), 'Año Nuevo Andino Amazónico (Willkakuti)'),
        (date(2026, 8, 6),  'Día de la Independencia'),
        (date(2026, 8, 7),  'Batalla de Junín'),
        (date(2026, 11, 2), 'Día de los Difuntos'),
        (date(2026, 12, 25), 'Navidad'),
    ]
    for fecha, descripcion in feriados:
        FeriadoBolivia.objects.create(
            fecha=fecha,
            descripcion=descripcion,
            anio=fecha.year,
        )


def revertir_feriados_2026(apps, schema_editor):
    FeriadoBolivia = apps.get_model('tpe_app', 'FeriadoBolivia')
    FeriadoBolivia.objects.filter(anio=2026).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0002_alter_abog_ci_alter_abog_especialidad_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeriadoBolivia',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha',       models.DateField(unique=True, verbose_name='Fecha')),
                ('descripcion', models.CharField(max_length=100, verbose_name='Descripción')),
                ('anio',        models.IntegerField(db_index=True, verbose_name='Año')),
            ],
            options={
                'verbose_name':        'Feriado Bolivia',
                'verbose_name_plural': 'Feriados Bolivia',
                'db_table':            'feriado_bolivia',
                'ordering':            ['fecha'],
            },
        ),
        migrations.RunPython(cargar_feriados_2026, revertir_feriados_2026),
    ]
