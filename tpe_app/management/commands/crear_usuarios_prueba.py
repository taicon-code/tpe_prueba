# tpe_app/management/commands/crear_usuarios_prueba.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tpe_app.models import PerfilUsuario, PM

class Command(BaseCommand):
    help = 'Crea usuarios de prueba para cada rol'

    def handle(self, *args, **kwargs):
        # 1. Crear ADMINISTRADOR
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@tpe.bo',
                password='admin123',
                first_name='Administrador',
                last_name='Sistema'
            )
            PerfilUsuario.objects.create(
                user=admin,
                rol='ADMINISTRADOR',
                activo=True
            )
            self.stdout.write(self.style.SUCCESS('✅ Usuario ADMINISTRADOR creado'))
            self.stdout.write(f'   Usuario: admin | Contraseña: admin123')
        
        # 2. Crear ABOGADO (PM con rol ABOG1_ASESOR)
        if not User.objects.filter(username='abogado1').exists():
            pm_abog = PM.objects.filter(perfilusuario__isnull=True).first()
            abogado_user = User.objects.create_user(
                username='abogado1',
                email='abogado@tpe.bo',
                password='abogado123',
                first_name='Juan',
                last_name='Perez'
            )
            PerfilUsuario.objects.create(
                user=abogado_user,
                rol='ABOG1_ASESOR',
                pm=pm_abog,
                activo=True
            )
            self.stdout.write(self.style.SUCCESS('✅ Usuario ABOG1_ASESOR creado'))
            self.stdout.write(f'   Usuario: abogado1 | Contrasena: abogado123')
        
        # 3. Crear BUSCADOR
        if not User.objects.filter(username='buscador1').exists():
            buscador = User.objects.create_user(
                username='buscador1',
                email='buscador@tpe.bo',
                password='buscador123',
                first_name='María',
                last_name='González'
            )
            PerfilUsuario.objects.create(
                user=buscador,
                rol='BUSCADOR',
                activo=True
            )
            self.stdout.write(self.style.SUCCESS('✅ Usuario BUSCADOR creado'))
            self.stdout.write(f'   Usuario: buscador1 | Contraseña: buscador123')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 ¡Usuarios de prueba creados exitosamente!'))
        self.stdout.write('\n📋 Resumen de usuarios:')
        self.stdout.write('   ADMINISTRADOR  → admin / admin123')
        self.stdout.write('   ABOGADO        → abogado1 / abogado123')
        self.stdout.write('   BUSCADOR       → buscador1 / buscador123')