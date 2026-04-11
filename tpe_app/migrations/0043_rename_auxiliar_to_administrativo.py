# Generated migration — rename rol AUXILIAR → ADMINISTRATIVO

from django.db import migrations, models


def rename_auxiliar_to_administrativo(apps, schema_editor):
    PerfilUsuario = apps.get_model('tpe_app', 'PerfilUsuario')
    PerfilUsuario.objects.filter(rol='AUXILIAR').update(rol='ADMINISTRATIVO')


def rename_administrativo_to_auxiliar(apps, schema_editor):
    PerfilUsuario = apps.get_model('tpe_app', 'PerfilUsuario')
    PerfilUsuario.objects.filter(rol='ADMINISTRATIVO').update(rol='AUXILIAR')


class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0042_add_pm_foto'),
    ]

    operations = [
        # 1. Actualizar el valor en la base de datos (AUXILIAR → ADMINISTRATIVO)
        migrations.RunPython(
            rename_auxiliar_to_administrativo,
            reverse_code=rename_administrativo_to_auxiliar,
        ),
        # 2. Actualizar la definición de choices en el campo
        migrations.AlterField(
            model_name='perfilusuario',
            name='rol',
            field=models.CharField(
                choices=[
                    ('ADMINISTRADOR', 'Administrador'),
                    ('ABOGADO', 'Abogado'),
                    ('BUSCADOR', 'Buscador'),
                    ('ADMINISTRATIVO', 'Administrativo'),
                ],
                max_length=20,
                verbose_name='Rol/Perfil',
            ),
        ),
    ]
