from django.db import migrations, models


def copiar_resumen_a_tipo(apps, schema_editor):
    """Migra datos: copia resumen → tipo para resoluciones RECONSIDERACION."""
    Resolucion = apps.get_model('tpe_app', 'Resolucion')
    for rr in Resolucion.objects.filter(
        instancia='RECONSIDERACION',
        resumen__isnull=False,
        tipo__isnull=True,
    ):
        rr.tipo = rr.resumen
        rr.save(update_fields=['tipo'])


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0003_aumentar_numero_oficio_max_length'),
    ]

    operations = [
        migrations.RunPython(copiar_resumen_a_tipo, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='resolucion',
            name='resumen',
        ),
        migrations.AlterField(
            model_name='resolucion',
            name='tipo',
            field=models.CharField(
                max_length=100,
                choices=[
                    ('ARCHIVO_OBRADOS',                'Archivo de Obrados'),
                    ('ADMINISTRATIVO',                 'Administrativo'),
                    ('SANCIONES_DISCIPLINARIAS',       'Sanciones Disciplinarias'),
                    ('NO_HA_LUGAR_SANCION_DISCIPLINARIA', 'No ha Lugar a la Sanción Disciplinaria'),
                    ('SOLICITUD_DE_RETIRO_VOLUNTARIO', 'Solicitud de Retiro Voluntario'),
                    ('SANCION_ARRESTO',                'Sanción Arresto (Ejecutiva)'),
                    ('SANCION_LETRA_B',                'Sanción Letra B (Pérdida de Antigüedad)'),
                    ('SANCION_RETIRO_OBLIGATORIO',     'Sanción Retiro Obligatorio'),
                    ('SANCION_BAJA',                   'Sanción Baja'),
                    ('SOLICITUD_LETRA_D',              'Solicitud Letra D (Permiso Médico)'),
                    ('SOLICITUD_LICENCIA_MAXIMA',      'Solicitud Licencia Máxima'),
                    ('SOLICITUD_ASCENSO',              'Solicitud de Ascenso'),
                    ('SOLICITUD_RESTITUCION_ANTIGUEDAD', 'Solicitud de Restitución de Antigüedad'),
                    ('SOLICITUD_RESTITUCION_DE_DERECHOS_PROFESIONALES', 'Solicitud de Restitución de Derechos Profesionales'),
                    ('SOLICITUD_ART_114_(Invalidez Instructor)',   'Solicitud Artículo 114 (Invalides Instructor)'),
                    ('SOLICITUD_ART_117_(Fallecimiento)',  'Solicitud Artículo 117 (Fallecimiento)'),
                    ('SOLICITUD_ART_118_(Invalidez Sldo)', 'Solicitud Artículo 118 (Invalidez Sldo)'),
                    ('OTRO', 'Otro'),
                    ('PROCEDENCIA',   'Procedencia a su Recurso de Reconsideración'),
                    ('IMPROCEDENCIA', 'Improcedencia a su Recurso de Reconsideración'),
                ],
                null=True,
                blank=True,
                verbose_name='Tipo',
            ),
        ),
    ]
