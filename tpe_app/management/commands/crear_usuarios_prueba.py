# tpe_app/management/commands/crear_usuarios_prueba.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tpe_app.models import PerfilUsuario, ABOG

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
        
        # 2. Crear ABOGADO (necesita registro en tabla ABOG)
        if not User.objects.filter(username='abogado1').exists():
            # Verificar si existe un abogado en la tabla ABOG
            abogado_obj = ABOG.objects.first()
            
            if abogado_obj:
                abogado_user = User.objects.create_user(
                    username='abogado1',
                    email='abogado@tpe.bo',
                    password='abogado123',
                    first_name='Juan',
                    last_name='Pérez'
                )
                PerfilUsuario.objects.create(
                    user=abogado_user,
                    rol='ABOGADO',
                    abogado=abogado_obj,
                    activo=True
                )
                self.stdout.write(self.style.SUCCESS('✅ Usuario ABOGADO creado'))
                self.stdout.write(f'   Usuario: abogado1 | Contraseña: abogado123')
                self.stdout.write(f'   Vinculado a: {abogado_obj}')
            else:
                self.stdout.write(self.style.WARNING('⚠️  No hay abogados en la tabla ABOG. Crea uno primero en /admin/'))
        
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
        
        # 4. Crear ADMINISTRATIVO
        if not User.objects.filter(username='administrativo1').exists():
            administrativo = User.objects.create_user(
                username='administrativo1',
                email='administrativo@tpe.bo',
                password='administrativo123',
                first_name='Carlos',
                last_name='Mamani'
            )
            PerfilUsuario.objects.create(
                user=administrativo,
                rol='ADMINISTRATIVO',
                activo=True
            )
            self.stdout.write(self.style.SUCCESS('✅ Usuario ADMINISTRATIVO creado'))
            self.stdout.write(f'   Usuario: administrativo1 | Contraseña: administrativo123')

        self.stdout.write(self.style.SUCCESS('\n🎉 ¡Usuarios de prueba creados exitosamente!'))
        self.stdout.write('\n📋 Resumen de usuarios:')
        self.stdout.write('   ADMINISTRADOR  → admin / admin123')
        self.stdout.write('   ABOGADO        → abogado1 / abogado123')
        self.stdout.write('   BUSCADOR       → buscador1 / buscador123')
        self.stdout.write('   ADMINISTRATIVO → administrativo1 / administrativo123')