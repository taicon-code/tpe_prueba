# Generated migration to fix CASCADE → PROTECT relationships
# This prevents accidental data loss when deleting parent records

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0006_memorandum_add_resolucion_fk'),
    ]

    operations = [
        # ============================================================
        # DocumentoAdjunto: Cambiar CASCADE → PROTECT
        # ============================================================
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='sim',
            field=models.ForeignKey('SIM', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Sumario SIM'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='resolucion',
            field=models.ForeignKey('Resolucion', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Resolución'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='autotpe',
            field=models.ForeignKey('AUTOTPE', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Auto TPE'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='autotsp',
            field=models.ForeignKey('AUTOTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Auto TSP'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='recurso_tsp',
            field=models.ForeignKey('RecursoTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Recurso TSP'),
        ),

        # ============================================================
        # Memorandum: Cambiar CASCADE → PROTECT
        # ============================================================
        migrations.AlterField(
            model_name='Memorandum',
            name='resolucion',
            field=models.ForeignKey('Resolucion', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='memorandums', verbose_name='Resolución vinculada'),
        ),
        migrations.AlterField(
            model_name='Memorandum',
            name='autotpe',
            field=models.ForeignKey('AUTOTPE', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='memorandums', verbose_name='Auto TPE vinculado'),
        ),

        # ============================================================
        # Notificacion: Cambiar CASCADE → PROTECT
        # ============================================================
        migrations.AlterField(
            model_name='Notificacion',
            name='resolucion',
            field=models.OneToOneField('Resolucion', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Resolución'),
        ),
        migrations.AlterField(
            model_name='Notificacion',
            name='autotpe',
            field=models.OneToOneField('AUTOTPE', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Auto TPE'),
        ),
        migrations.AlterField(
            model_name='Notificacion',
            name='autotsp',
            field=models.OneToOneField('AUTOTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Auto TSP'),
        ),
        migrations.AlterField(
            model_name='Notificacion',
            name='recurso_tsp',
            field=models.OneToOneField('RecursoTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Recurso TSP'),
        ),

        # ============================================================
        # RecursoTSP: Cambiar CASCADE → PROTECT
        # ============================================================
        migrations.AlterField(
            model_name='RecursoTSP',
            name='recurso_origen',
            field=models.ForeignKey('self', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='aclaraciones', verbose_name='Recurso origen (solo ACLARACION_ENMIENDA)'),
        ),
    ]
