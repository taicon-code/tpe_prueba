from django.db import migrations, models


def convertir_fecha_a_anio(apps, schema_editor):
    """Copia el año de PM_PROMOCION_OLD (DateField) a PM_PROMOCION (IntegerField)."""
    PM = apps.get_model('tpe_app', 'PM')
    for pm in PM.objects.filter(PM_PROMOCION_OLD__isnull=False):
        try:
            pm.PM_PROMOCION = pm.PM_PROMOCION_OLD.year
            pm.save(update_fields=['PM_PROMOCION'])
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0026_dictamen_resultado_tribunal_alter_perfilusuario_rol_and_more'),
    ]

    operations = [
        # 1. Renombrar DateField existente a temporal
        migrations.RenameField(
            model_name='pm',
            old_name='PM_PROMOCION',
            new_name='PM_PROMOCION_OLD',
        ),
        # 2. Agregar nuevo campo IntegerField
        migrations.AddField(
            model_name='pm',
            name='PM_PROMOCION',
            field=models.IntegerField(blank=True, null=True, verbose_name='Año de Egreso'),
        ),
        # 3. Migrar datos: copiar año del DateField al IntegerField
        migrations.RunPython(convertir_fecha_a_anio, migrations.RunPython.noop),
        # 4. Eliminar el campo temporal
        migrations.RemoveField(
            model_name='pm',
            name='PM_PROMOCION_OLD',
        ),
        # 5. Agregar PM_NO_ASCENDIO
        migrations.AddField(
            model_name='pm',
            name='PM_NO_ASCENDIO',
            field=models.BooleanField(default=False, verbose_name='No ascendió al grado correspondiente'),
        ),
        # 6. Agregar PMSIM_GRADO_EN_FECHA a PM_SIM
        migrations.AddField(
            model_name='pm_sim',
            name='PMSIM_GRADO_EN_FECHA',
            field=models.CharField(
                blank=True, null=True, max_length=20,
                verbose_name='Grado al momento del sumario',
            ),
        ),
    ]
