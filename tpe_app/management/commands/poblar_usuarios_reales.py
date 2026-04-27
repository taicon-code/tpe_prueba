"""
Comando: poblar_usuarios_reales
Crea los registros PM, ABOG (cuando aplica) y cuentas de usuario del sistema TPE.

Uso:
    python manage.py poblar_usuarios_reales
    python manage.py poblar_usuarios_reales --forzar   (actualiza emails y datos existentes)
"""
import secrets
import string
from datetime import date
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from tpe_app.models import PM, PerfilUsuario


# ─────────────────────────────────────────────────────────────────────────────
# LISTA DE USUARIOS DEL SISTEMA — Gestion 2026
# Columnas: (grado, escalafon, arma, especialidad, nombre, paterno, materno,
#            email, username, rol)
# ─────────────────────────────────────────────────────────────────────────────
ROLES_ABOG = {'ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR', 'ABOGADO'}

USUARIOS = [
    # ── Asesor Jefe (ya existe en tribunal, solo actualiza email) ─────────────
    ('CNL.',       'OFICIAL SUPERIOR',  None,      'DAEN',
     'RUBEN NICOLAS', 'VARGAS', 'VILLA',
     'vargas@tpe.bo', 'vargas', 'ASESOR_JEFE'),

    # ── Abogados Asesores (ABOG1) ─────────────────────────────────────────────
    ('CAP.',       'OFICIAL SUBALTERNO', 'INF.',   None,
     'MARCELO',       'MEDINA',   'NUNEZ DEL PRADO',
     'medina@tpe.bo',   'medina',   'ABOG1_ASESOR'),

    ('CAP.',       'OFICIAL SUBALTERNO', 'INF.',   None,
     'GROVER EFRAIN',  'CHIPANA',  'FERNANDEZ',
     'chipana@tpe.bo',  'chipana',  'ABOG1_ASESOR'),

    ('SOF. 1RO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'GONZALO',        'SOLIZ',    'TRUJILLO',
     'soliz@tpe.bo',    'soliz',    'ABOG1_ASESOR'),

    ('SOF. 2DO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'FREDDY JAIME',   'URQUIETA', 'VILLARROEL',
     'urquieta@tpe.bo', 'urquieta', 'ABOG1_ASESOR'),

    ('SOF. 2DO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'ROSALY',         'TROCHE',   'RIOS',
     'troche@tpe.bo',   'troche',   'ABOG1_ASESOR'),

    ('PROF. V',    'EMPLEADO CIVIL',     None,     'ABOG.',
     'DANIELA TANIA',  'ROMERO',   'CARVAJAL',
     'romero@tpe.bo',   'romero',   'ABOG1_ASESOR'),

    ('PROF. V',    'EMPLEADO CIVIL',     None,     'ABOG.',
     'JHONATAN KEVIN', 'ANDIA',    'CORTEZ',
     'andia@tpe.bo',    'andia',    'ABOG1_ASESOR'),

    # ── Abogados de Autos (ABOG2) ─────────────────────────────────────────────
    ('SOF. MY.',   'SUBOFICIAL',         None,     'DEPSS.',
     'JULIO CESAR',    'CHOQUE',   'MAMANI',
     'choque@tpe.bo',   'choque',   'ABOG2_AUTOS'),

    ('SOF. 1RO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'JOSE LUIS',      'QUISPE',   'TICONA',
     'quispe@tpe.bo',   'quispe',   'ABOG2_AUTOS'),

    ('SOF. 1RO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'EFRAIN',         'VELA',     'CALLE',
     'vela@tpe.bo',     'vela',     'ABOG2_AUTOS'),

    ('SOF. 2DO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'JHON',           'SANTALLA', 'TARQUINO',
     'santalla@tpe.bo', 'santalla', 'ABOG2_AUTOS'),

    # ── Administrativos ───────────────────────────────────────────────────────
    ('SOF. 2DO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'ALI EDIL',       'CRUZ',     'RIVAS',
     'cruz@tpe.bo',     'cruz',     'ADMIN1_AGENDADOR'),

    ('SOF. INCL.', 'SUBOFICIAL',        'MUS.',    None,
     'VICTOR MARCELO', 'MAMANI',   'FLORES',
     'mamani@tpe.bo',   'mamani',   'ADMIN1_AGENDADOR'),

    ('SOF. INCL.', 'SUBOFICIAL',        'COM.',    None,
     'HARUZI ANDREA',  'MERCADO',  'MAMANI',
     'mercado@tpe.bo',  'mercado',  'ADMIN2_ARCHIVO'),

    # ── Ayudante ──────────────────────────────────────────────────────────────
    ('SGTO. 1RO.', 'SARGENTO',          'TGRAFO.', None,
     'REYNALDO FELIX',  'PAREDES',  'ALIAGA',
     'paredes@tpe.bo',  'paredes',  'AYUDANTE'),

    # ── Master ────────────────────────────────────────────────────────────────
    ('SOF. 2DO.',  'SUBOFICIAL',         None,     'DEPSS.',
     'EDGAR',          'TICONA',   'COLQUEHUANCA',
     'ticona@tpe.bo',   'ticona',   'MASTER'),

    # ── Buscador ──────────────────────────────────────────────────────────────
    ('ADM. IV',    'EMPLEADO CIVIL',     None,     'STRIA.',
     'GRACIELA',       'MARTINEZ', 'QUISPE',
     'martinez@tpe.bo', 'martinez', 'BUSCADOR'),
]


def _generar_password(longitud=12):
    alfabeto = string.ascii_letters + string.digits + '!@#$%'
    while True:
        pwd = ''.join(secrets.choice(alfabeto) for _ in range(longitud))
        if (any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in '!@#$%' for c in pwd)):
            return pwd


class Command(BaseCommand):
    help = 'Crea cuentas de usuario y registros PM/ABOG para el personal del sistema TPE'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forzar', action='store_true',
            help='Actualiza email y datos de registros existentes',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        forzar = options['forzar']
        credenciales = []
        omitidos     = []

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n======================================================'
            '\n  USUARIOS DEL SISTEMA TPE - Gestion 2026'
            '\n======================================================'
        ))

        for (grado, escalafon, arma, especialidad,
             nombre, paterno, materno,
             email, username, rol) in USUARIOS:

            # ── 1. PM ────────────────────────────────────────────────────────
            lookup_pm   = {'paterno': paterno, 'nombre': nombre}
            defaults_pm = {
                'grado':       grado,
                'escalafon':   escalafon,
                'arma':        arma,
                'especialidad': especialidad,
                'materno':     materno,
                'estado':      'ACTIVO',
            }
            if forzar:
                pm, _ = PM.objects.update_or_create(**lookup_pm, defaults=defaults_pm)
            else:
                pm, _ = PM.objects.get_or_create(**lookup_pm, defaults=defaults_pm)

            # ── 2. USUARIO ───────────────────────────────────────────────────
            # Caso especial: CNL. Vargas ya fue creado por poblar_tribunal_real
            perfil_existente = PerfilUsuario.objects.filter(
                rol=rol, pm=pm
            ).select_related('user').first()

            if not perfil_existente and rol == 'ASESOR_JEFE':
                # Buscar por vocal vinculado al mismo PM
                perfil_existente = PerfilUsuario.objects.filter(
                    vocal__pm=pm
                ).select_related('user').first()

            if perfil_existente:
                if forzar:
                    perfil_existente.user.email = email
                    perfil_existente.user.save(update_fields=['email'])
                    perfil_existente.pm = pm
                    perfil_existente.save()
                    omitidos.append(
                        f'  [actualizado] {grado} {nombre} {paterno}'
                        f' -> "{perfil_existente.user.username}"'
                    )
                else:
                    omitidos.append(
                        f'  [ya existe]   {grado} {nombre} {paterno}'
                        f' -> "{perfil_existente.user.username}"'
                    )
                continue

            if User.objects.filter(username=username).exists():
                omitidos.append(
                    f'  [username ocupado] {username} ({grado} {paterno})'
                )
                continue

            password = _generar_password()
            usuario  = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=nombre.title(),
                last_name=paterno.title(),
            )
            PerfilUsuario.objects.create(
                user=usuario,
                rol=rol,
                pm=pm,
                activo=True,
            )
            credenciales.append((grado, nombre, paterno, username, password, rol))
            self.stdout.write(self.style.SUCCESS(
                f'  + {grado:<12} {nombre} {paterno:<18} -> "{username}" [{rol}]'
            ))

        # ── Omitidos ─────────────────────────────────────────────────────────
        if omitidos:
            self.stdout.write(self.style.WARNING('\n[Omitidos / Ya existentes]'))
            for msg in omitidos:
                self.stdout.write(msg)

        # ── Tabla de credenciales → archivo en D:\ ───────────────────────────
        if credenciales:
            archivo = Path(f'D:/tpe_credenciales_{date.today().strftime("%Y-%m-%d")}.txt')
            try:
                lineas = [
                    'CREDENCIALES SISTEMA TPE — Gestión 2026\n',
                    f'Generado: {date.today()}\n',
                    '=' * 62 + '\n',
                    f'{"USUARIO":<12} {"CONTRASENA":<14} {"ROL":<20} NOMBRE\n',
                    f'{"-"*12} {"-"*14} {"-"*20} {"-"*35}\n',
                ]
                for grado, nombre, paterno, usr, pwd, rol in credenciales:
                    lineas.append(f'{usr:<12} {pwd:<14} {rol:<20} {grado} {nombre} {paterno}\n')
                archivo.write_text(''.join(lineas), encoding='utf-8')
                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Credenciales guardadas en: {archivo}'
                ))
                self.stdout.write(self.style.WARNING(
                    '   ⚠️  Proteger ese archivo. No compartir por correo ni mensajería.'
                ))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'❌ No se pudo escribir en D:\\: {exc}'))
                self.stdout.write(self.style.WARNING(
                    '   Los usuarios fueron creados. Anota las credenciales desde el panel admin.'
                ))

        total = len(credenciales)
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Proceso completado: {total} usuario(s) nuevo(s) creado(s) ===\n'
        ))
