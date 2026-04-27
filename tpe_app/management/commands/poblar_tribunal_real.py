"""
Comando: poblar_tribunal_real
Pobla la BD con los miembros reales del Tribunal de Personal del Ejército (gestión 2026).

Uso:
    python manage.py poblar_tribunal_real
    python manage.py poblar_tribunal_real --solo-vocales   (no crea usuarios del sistema)
    python manage.py poblar_tribunal_real --forzar         (actualiza registros existentes)
"""
import secrets
import string
from datetime import date
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from tpe_app.models import PM, VOCAL_TPE, PerfilUsuario


# ─────────────────────────────────────────────────────────────────────────────
# DATOS REALES DEL TRIBUNAL TPE — Gestión 2026
# ─────────────────────────────────────────────────────────────────────────────

MIEMBROS_TRIBUNAL = [
    # (grado, escalafon, especialidad, nombre, paterno, materno, cargo_tpe, cargo_em)
    (
        'GRAL. BRIG.', 'GENERAL', None,
        'HÉCTOR ALEJANDRO', 'ALARCÓN', 'ANTEZANA',
        'PRESIDENTE',
        'COMANDANTE GENERAL DEL EJÉRCITO',
    ),
    (
        'GRAL. BRIG.', 'GENERAL', None,
        'ROSSMER FRANCISCO', 'GUTIÉRREZ', 'LÓPEZ',
        'VICEPRESIDENTE',
        'JEFE DE ESTADO MAYOR GENERAL DEL EJÉRCITO',
    ),
    (
        'GRAL. BRIG.', 'GENERAL', None,
        'JAVIER ERWIN', 'FERNÁNDEZ', 'REVOLLO',
        'VOCAL',
        'INSPECTOR GENERAL DEL EJÉRCITO',
    ),
    (
        'GRAL. BRIG.', 'GENERAL', None,
        'CARMELO EDUARDO', 'ARDAYA', 'FARIA',
        'VOCAL',
        'DECANO DE LA FCAMT',
    ),
    (
        'GRAL. BRIG.', 'GENERAL', None,
        'VICTOR HUGO', 'SORIA GALVARRO', 'CHAVARRÍA',
        'VOCAL',
        'JEFE DEL DPTO. III OPS.',
    ),
    (
        'GRAL. BRIG.', 'GENERAL', None,
        'ESTEBAN EDWIN', 'TAPIA', 'ENCINAS',
        'VOCAL',
        'JEFE DEL DPTO. II ICIA.',
    ),
    (
        'CNL.', 'OFICIAL SUPERIOR', 'DAEN',
        'AMÍLCAR', 'ÁLVAREZ', 'VACA',
        'VOCAL',
        'JEFE DEL DPTO. VI - TRANS. FZA.',
    ),
    (
        'CNL.', 'OFICIAL SUPERIOR', 'DAEN',
        'EDMUNDO GUERY', 'SORIA', 'RODRIGO',
        'VOCAL',
        'JEFE DEL DPTO. IV - LOG.',
    ),
    (
        'CNL.', 'OFICIAL SUPERIOR', 'DAEN',
        'AIBEN VLADIMIR', 'BALDIVIEZO', 'BALDIVIEZO',
        'VOCAL',
        'JEFE DEL DPTO. V AC/OC',
    ),
    (
        'CNL.', 'OFICIAL SUPERIOR', 'DAEN',
        'FÉLIX MARCELO', 'VILLARROEL', 'SANJINÉS',
        'RELATOR',
        'JEFE DEL DPTO. I - PERS.',
    ),
    (
        'SOF. MTRE.', 'SUBOFICIAL', None,
        'ELÍAS', 'FLORES', 'LEÓN',
        'VOCAL',
        'SUBOFICIAL DE COMANDO GENERAL DEL EJÉRCITO',
    ),
    (
        'CNL.', 'OFICIAL SUPERIOR', 'DAEN',
        'ERICK VLADIMIR', 'MENDOZA', 'LLAMPA',
        'ASESOR_JURIDICO',
        'DIRECTOR GENERAL DE JURÍDICA DEL EJÉRCITO',
    ),
    # ── Miembros con acceso al sistema ───────────────────────────────────────
    (
        'CNL.', 'OFICIAL SUPERIOR', 'DAEN',
        'RUBÉN NICOLAS', 'VARGAS', 'VILLA',
        'ASESOR_JEFE',
        'ASESOR JURÍDICO DEL DPTO. I - PERS.',
    ),
    (
        'MY.', 'OFICIAL SUPERIOR', 'DEM',
        'LUIS FERNANDO', 'ESTEN', 'ZABALA',
        'SECRETARIO_ACTAS',
        'AYUDANTE DE ORDENES DEL DPTO. I - PERS.',
    ),
]

# Miembros que tienen acceso al sistema: (paterno, rol_sistema, username)
USUARIOS_SISTEMA = [
    ('VARGAS',  'ASESOR_JEFE',       'vargas.villa'),
    ('ESTEN',   'SECRETARIO_ACTAS',  'esten.zabala'),
]


def _generar_password(longitud=12):
    alfabeto = string.ascii_letters + string.digits + '!@#$%'
    while True:
        pwd = ''.join(secrets.choice(alfabeto) for _ in range(longitud))
        # Garantizar al menos una mayúscula, minúscula, dígito y símbolo
        if (any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in '!@#$%' for c in pwd)):
            return pwd


class Command(BaseCommand):
    help = 'Pobla la BD con los miembros reales del Tribunal de Personal del Ejército (2026)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-vocales', action='store_true',
            help='Solo crea registros PM y VOCAL_TPE, sin crear usuarios del sistema',
        )
        parser.add_argument(
            '--forzar', action='store_true',
            help='Actualiza datos si el registro ya existe (por defecto omite duplicados)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        solo_vocales = options['solo_vocales']
        forzar       = options['forzar']

        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n======================================================\n'
            '  TRIBUNAL DE PERSONAL DEL EJERCITO - Gestion 2026\n'
            '======================================================'
        ))

        # ── 1. CREAR PM Y VOCAL_TPE ───────────────────────────────────────────
        self.stdout.write('\n[1] Registrando miembros del tribunal...\n')
        vocal_map = {}  # paterno → instancia VOCAL_TPE

        for (grado, escalafon, especialidad,
             nombre, paterno, materno,
             cargo_tpe, cargo_em) in MIEMBROS_TRIBUNAL:

            # PM
            lookup_pm = {'paterno': paterno.upper(), 'nombre': nombre.upper()}
            defaults_pm = {
                'grado':      grado,
                'escalafon':  escalafon,
                'especialidad': especialidad.upper() if especialidad else None,
                'materno':    materno.upper() if materno else None,
                'estado':     'ACTIVO',
            }

            if forzar:
                pm, creado = PM.objects.update_or_create(
                    **lookup_pm, defaults=defaults_pm)
            else:
                pm, creado = PM.objects.get_or_create(
                    **lookup_pm, defaults=defaults_pm)

            marca_pm = '+ CREADO' if creado else '  existe'

            # VOCAL_TPE
            defaults_voc = {'cargo_em': cargo_em, 'activo': True}
            if forzar:
                vocal, creado_v = VOCAL_TPE.objects.update_or_create(
                    pm=pm, cargo=cargo_tpe, defaults=defaults_voc)
            else:
                vocal, creado_v = VOCAL_TPE.objects.get_or_create(
                    pm=pm, cargo=cargo_tpe, defaults=defaults_voc)

            marca_voc = '+ CREADO' if creado_v else '  existe'
            vocal_map[paterno.upper()] = vocal

            self.stdout.write(
                f'  {grado:<12} {nombre} {paterno:<18}'
                f'  PM:{marca_pm}  VOCAL:{marca_voc}'
                f'  [{vocal.get_cargo_display()}]'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n  OK: {len(MIEMBROS_TRIBUNAL)} miembros procesados.\n'))

        # ── 2. CREAR USUARIOS DEL SISTEMA ─────────────────────────────────────
        if solo_vocales:
            self.stdout.write('  Omitiendo creacion de usuarios (--solo-vocales).')
            return

        self.stdout.write('[2] Creando usuarios del sistema...\n')
        credenciales = []

        for paterno_key, rol, username in USUARIOS_SISTEMA:
            vocal = vocal_map.get(paterno_key.upper())
            if not vocal:
                self.stdout.write(self.style.WARNING(
                    f'  [!] No se encontro VOCAL_TPE para {paterno_key}, omitido.'))
                continue

            pm = vocal.pm

            if User.objects.filter(username=username).exists():
                self.stdout.write(f'  · Usuario "{username}" ya existe, omitido.')
                continue

            password = _generar_password()
            usuario = User.objects.create_user(
                username=username,
                password=password,
                first_name=pm.nombre.title(),
                last_name=pm.paterno.title(),
                email='',
            )
            PerfilUsuario.objects.create(
                user=usuario,
                rol=rol,
                vocal=vocal,
                activo=True,
            )
            credenciales.append((pm.grado, pm.nombre, pm.paterno, username, password, rol))
            self.stdout.write(self.style.SUCCESS(
                f'  + {pm.grado} {pm.nombre} {pm.paterno} -> usuario "{username}" creado'))

        # ── 3. CREDENCIALES → archivo en D:\ ─────────────────────────────────
        if credenciales:
            archivo = Path(f'D:/tpe_credenciales_tribunal_{date.today().strftime("%Y-%m-%d")}.txt')
            try:
                lineas = [
                    'CREDENCIALES TRIBUNAL TPE — Gestión 2026\n',
                    f'Generado: {date.today()}\n',
                    '=' * 62 + '\n',
                    f'{"USUARIO":<20} {"CONTRASENA":<16} {"ROL":<22} NOMBRE\n',
                    f'{"-"*20} {"-"*16} {"-"*22} {"-"*30}\n',
                ]
                for grado, nombre, paterno, usr, pwd, rol in credenciales:
                    lineas.append(f'{usr:<20} {pwd:<16} {rol:<22} {grado} {nombre} {paterno}\n')
                archivo.write_text(''.join(lineas), encoding='utf-8')
                self.stdout.write(self.style.SUCCESS(
                    f'\n[OK] Credenciales guardadas en: {archivo}'
                ))
                self.stdout.write(self.style.WARNING(
                    '     ATENCION: Proteger ese archivo. No compartir por correo ni mensajeria.'
                ))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'[ERROR] No se pudo escribir en D:\\: {exc}'))
                self.stdout.write(self.style.WARNING(
                    '   Los usuarios fueron creados. Anota las credenciales desde el panel admin.'
                ))
        else:
            self.stdout.write('\n  (No se generaron nuevas credenciales)\n')

        self.stdout.write(self.style.SUCCESS('=== Proceso completado ===\n'))
