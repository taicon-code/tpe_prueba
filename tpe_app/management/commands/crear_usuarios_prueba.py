# tpe_app/management/commands/crear_usuarios_prueba.py
"""
Crea usuarios de prueba para desarrollo local.

Solo se ejecuta cuando DEBUG=True. En produccion aborta inmediatamente para
evitar la creacion accidental de cuentas con contrasenas debiles.

Las contrasenas se piden interactivamente con getpass (o se generan aleatorias
con --random) en vez de hardcodearse en el codigo.
"""
import getpass
import secrets
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from tpe_app.models import PerfilUsuario, PM


def _generar_password(length=16):
    alfabeto = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alfabeto) for _ in range(length))


class Command(BaseCommand):
    help = 'Crea usuarios de prueba para desarrollo local. SOLO en DEBUG=True.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--random',
            action='store_true',
            help='Genera contrasenas aleatorias (16 chars) y las muestra solo una vez al final.',
        )

    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError(
                'Este comando solo puede ejecutarse en desarrollo (DEBUG=True). '
                'Para crear usuarios en produccion use scripts/crear_superuser_django.py '
                'o el panel de administracion.'
            )

        usar_random = opts.get('random', False)
        creados = []

        def _obtener_password(rol_label):
            if usar_random:
                return _generar_password()
            pw = getpass.getpass(f'Contrasena para {rol_label}: ')
            if len(pw) < 8:
                raise CommandError('Contrasena debe tener al menos 8 caracteres.')
            return pw

        # 1. ADMINISTRADOR
        if not User.objects.filter(username='admin').exists():
            pw = _obtener_password('admin (ADMINISTRADOR)')
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@tpe.bo',
                password=pw,
                first_name='Administrador',
                last_name='Sistema',
            )
            PerfilUsuario.objects.create(user=admin, rol='ADMINISTRADOR', activo=True)
            self.stdout.write(self.style.SUCCESS('OK - Usuario ADMINISTRADOR creado (admin)'))
            if usar_random:
                creados.append(('admin', pw))

        # 2. ABOG1_ASESOR
        if not User.objects.filter(username='abogado1').exists():
            pw = _obtener_password('abogado1 (ABOG1_ASESOR)')
            pm_abog = PM.objects.filter(perfilusuario__isnull=True).first()
            abogado_user = User.objects.create_user(
                username='abogado1',
                email='abogado@tpe.bo',
                password=pw,
                first_name='Juan',
                last_name='Perez',
            )
            PerfilUsuario.objects.create(
                user=abogado_user, rol='ABOG1_ASESOR', pm=pm_abog, activo=True
            )
            self.stdout.write(self.style.SUCCESS('OK - Usuario ABOG1_ASESOR creado (abogado1)'))
            if usar_random:
                creados.append(('abogado1', pw))

        # 3. BUSCADOR
        if not User.objects.filter(username='buscador1').exists():
            pw = _obtener_password('buscador1 (BUSCADOR)')
            buscador = User.objects.create_user(
                username='buscador1',
                email='buscador@tpe.bo',
                password=pw,
                first_name='Maria',
                last_name='Gonzalez',
            )
            PerfilUsuario.objects.create(user=buscador, rol='BUSCADOR', activo=True)
            self.stdout.write(self.style.SUCCESS('OK - Usuario BUSCADOR creado (buscador1)'))
            if usar_random:
                creados.append(('buscador1', pw))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Usuarios de prueba procesados.'))

        if usar_random and creados:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'Contrasenas generadas (anotelas AHORA, no se mostraran de nuevo):'
            ))
            for username, pw in creados:
                self.stdout.write(f'  {username}: {pw}')
