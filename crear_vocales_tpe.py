#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from tpe_app.models import PM, VOCAL_TPE, PerfilUsuario

# Datos de vocales del TPE
vocales_data = [
    ("GRAL.", "BRIG.", "HECTOR ALEJANDRO", "ALARCON", "ANTEZANA", "PRESIDENTE"),
    ("GRAL.", "BRIG.", "ROSSMER FRANCISCO", "GUTIERREZ", "LOPEZ", "VICEPRESIDENTE"),
    ("GRAL.", "BRIG.", "JAVIER ERWIN", "FERNANDEZ", "REVOLLO", "VOCAL"),
    ("GRAL.", "BRIG.", "CARMELO EDUARDO", "ARDAYA", "FARIA", "VOCAL"),
    ("GRAL.", "BRIG.", "VICTOR HUGO", "SORIA GALVARRO", "CHAVARRIA", "VOCAL"),
    ("GRAL.", "BRIG.", "ESTEBAN EDWIN", "TAPIA", "ENCINAS", "VOCAL"),
    ("CNL.", "DAEN.", "AMILCAR", "ALVAREZ", "VACA", "VOCAL"),
    ("CNL.", "DAEN.", "EDMUNDO GUERY", "SORIA", "RODRIGO", "VOCAL"),
    ("CNL.", "DAEN.", "AIBEN VLADIMIR", "BALDIVIEZO", "BALDIVIEZO", "VOCAL"),
    ("CNL.", "DAEN.", "FELIX MARCELO", "VILLARROEL SANJINES", "", "RELATOR"),
    ("SOF.", "MTRE.", "ELIAS", "FLORES", "LEON", "VOCAL"),
    ("CNL.", "DAEN.", "ERICK VLADIMIR", "MENDOZA", "LLAMPA", "ASESOR"),
    ("CNL.", "DAEN.", "RUBEN NICOLAS", "VARGAS", "VILLA", "ASESOR"),
    ("MY.", "DEM.", "LUIS FERNANDO", "ESTEN", "ZABALA", "SECRETARIO_ACTAS"),
]

# Mapeo de cargos a VOCAL_TPE.cargo
CARGO_MAP = {
    "PRESIDENTE": "PRESIDENTE",
    "VICEPRESIDENTE": "VICEPRESIDENTE",
    "VOCAL": "VOCAL",
    "RELATOR": "RELATOR",
    "ASESOR": "ASESOR_JEFE",
    "SECRETARIO_ACTAS": "SECRETARIO_ACTAS",
}

print("=" * 80)
print("CREANDO VOCALES DEL TRIBUNAL (VOCAL_TPE)".center(80))
print("=" * 80)
print()

vocales_creados = []
secretario_esten = None

for grado, espec, nombre, paterno, materno, cargo_input in vocales_data:
    try:
        # 1. Crear o actualizar PM (Personal Militar)
        pm, creado = PM.objects.get_or_create(
            PM_GRADO=grado.upper(),
            PM_NOMBRE=nombre.upper(),
            PM_PATERNO=paterno.upper(),
            PM_MATERNO=materno.upper() if materno else "",
            defaults={
                'PM_ESPEC': espec.upper(),
                'PM_ARMA': '',
                'PM_ESTADO': 'ACTIVO',
            }
        )

        # 2. Crear VOCAL_TPE
        cargo_vocal = CARGO_MAP.get(cargo_input, "VOCAL")
        vocal, vocal_creado = VOCAL_TPE.objects.get_or_create(
            pm=pm,
            defaults={
                'cargo': cargo_vocal,
                'activo': True,
            }
        )

        # 3. Si es Secretario de Actas, preparar para crear usuario
        if cargo_input == "SECRETARIO_ACTAS":
            secretario_esten = {
                'pm': pm,
                'vocal': vocal,
                'nombre_completo': f"{paterno} {materno}, {nombre}".strip(),
                'email': 'esten@tpe.bo',
                'grado': grado,
            }

        vocales_creados.append({
            'grado': grado,
            'nombre': nombre,
            'paterno': paterno,
            'materno': materno,
            'cargo': cargo_input,
            'pm_id': pm.pm_id,
        })

        print(f"OK - {grado} {nombre} {paterno} {materno} ({cargo_input})")

    except Exception as e:
        print(f"ERROR - {paterno} {nombre}: {e}")

print()
print("=" * 80)
print(f"TOTAL CREADOS: {len(vocales_creados)} vocales del TPE".center(80))
print("=" * 80)
print()

# Crear usuario para Secretario de Actas
if secretario_esten:
    print("Asignando usuario a SECRETARIO DE ACTAS...")
    print()

    try:
        # Verificar si ya existe usuario "esten"
        usuario_esten = User.objects.filter(username='esten').first()

        if usuario_esten:
            print(f"Usuario 'esten' ya existe")
            # Actualizar perfil si existe
            perfil, _ = PerfilUsuario.objects.get_or_create(
                user=usuario_esten,
                defaults={'rol': 'VOCAL_TPE', 'vocal': secretario_esten['vocal'], 'activo': True}
            )
            if perfil.rol != 'VOCAL_TPE':
                perfil.rol = 'VOCAL_TPE'
                perfil.vocal = secretario_esten['vocal']
                perfil.save()
                print(f"Perfil actualizado: rol=VOCAL_TPE, vocal asignado")
        else:
            print(f"ERROR: Usuario 'esten' no existe en la BD")
            print(f"Debes crear el usuario manualmente o pasar su email")

        print()
        print(f"Secretario de Actas: {secretario_esten['nombre_completo']}")
        print(f"Cargo: SECRETARIO DE ACTAS")
        print(f"Rol: VOCAL_TPE")
        print(f"Email: {secretario_esten['email']}")

    except Exception as e:
        print(f"ERROR asignando usuario a Esten: {e}")

print()
print("=" * 80)
print("PROCESO COMPLETADO - TPE CONFIGURADO".center(80))
print("=" * 80)
