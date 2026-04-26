from django.db import migrations, models
import django.db.models.deletion


def poblar_fks(apps, schema_editor):
    """Migra tabla+registro_id a FKs específicas."""
    DocumentoAdjunto = apps.get_model('tpe_app', 'DocumentoAdjunto')
    for doc in DocumentoAdjunto.objects.all():
        tabla = doc.tabla
        rid   = doc.registro_id
        if tabla == 'sim':
            doc.sim_id = rid
        elif tabla == 'resolucion':
            doc.resolucion_id = rid
        elif tabla == 'autotpe':
            doc.autotpe_id = rid
        elif tabla == 'autotsp':
            doc.autotsp_id = rid
        elif tabla == 'recurso_tsp':
            doc.recurso_tsp_id = rid
        doc.save()


def revertir_fks(apps, schema_editor):
    """Repuebla tabla+registro_id desde FKs (rollback)."""
    DocumentoAdjunto = apps.get_model('tpe_app', 'DocumentoAdjunto')
    MAPPING = [
        ('sim_id',         'sim'),
        ('resolucion_id',  'resolucion'),
        ('autotpe_id',     'autotpe'),
        ('autotsp_id',     'autotsp'),
        ('recurso_tsp_id', 'recurso_tsp'),
    ]
    for doc in DocumentoAdjunto.objects.all():
        for field, tabla in MAPPING:
            val = getattr(doc, field, None)
            if val:
                doc.tabla = tabla
                doc.registro_id = val
                break
        doc.save()


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0004_notificacion_memorandum'),
    ]

    operations = [
        # 1. Agregar columnas FK (nullable)
        migrations.AddField(
            model_name='documentoadjunto',
            name='sim',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='documentos', to='tpe_app.sim', verbose_name='Sumario SIM',
            ),
        ),
        migrations.AddField(
            model_name='documentoadjunto',
            name='resolucion',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='documentos', to='tpe_app.resolucion', verbose_name='Resolución',
            ),
        ),
        migrations.AddField(
            model_name='documentoadjunto',
            name='autotpe',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='documentos', to='tpe_app.autotpe', verbose_name='Auto TPE',
            ),
        ),
        migrations.AddField(
            model_name='documentoadjunto',
            name='autotsp',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='documentos', to='tpe_app.autotsp', verbose_name='Auto TSP',
            ),
        ),
        migrations.AddField(
            model_name='documentoadjunto',
            name='recurso_tsp',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='documentos', to='tpe_app.recursotsp', verbose_name='Recurso TSP',
            ),
        ),
        # 2. Copiar datos: tabla+registro_id → FK
        migrations.RunPython(poblar_fks, revertir_fks),
        # 3. Eliminar índice y campos obsoletos
        migrations.RemoveIndex(
            model_name='documentoadjunto',
            name='DOC_TABLA_ID',
        ),
        migrations.RemoveField(
            model_name='documentoadjunto',
            name='tabla',
        ),
        migrations.RemoveField(
            model_name='documentoadjunto',
            name='registro_id',
        ),
    ]
