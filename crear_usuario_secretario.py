#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django
import secrets
import string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from tpe_app.models import PerfilUsuario, VOCAL_TPE

# Buscar Secretario de Actas
vocal_esten = VOCAL_TPE.objects.filter(cargo='SECRETARIO_ACTAS').first()

if vocal_esten:
    pm = vocal_esten.pm
    print(f"Encontrado: {pm}")

    # Generar contraseña
    caracteres = string.ascii_letters + string.digits + "!@#$%^&*"
    contraseña = ''.join(secrets.choice(caracteres) for _ in range(12))

    # Crear usuario
    usuario = User.objects.create_user(
        username='esten',
        email='esten@tpe.bo',
        password=contraseña,
        first_name=pm.PM_NOMBRE,
        last_name=f"{pm.PM_PATERNO} {pm.PM_MATERNO}"
    )

    # Crear perfil
    perfil = PerfilUsuario.objects.create(
        user=usuario,
        rol='VOCAL_TPE',
        vocal=vocal_esten,
        activo=True
    )

    print()
    print("=" * 80)
    print("USUARIO CREADO - SECRETARIO DE ACTAS")
    print("=" * 80)
    print(f"Nombre:      {pm.PM_PATERNO} {pm.PM_MATERNO}, {pm.PM_NOMBRE}")
    print(f"Grado:       {pm.PM_GRADO}")
    print(f"Cargo:       Secretario de Actas")
    print(f"Email:       esten@tpe.bo")
    print(f"Usuario:     esten")
    print(f"Contraseña:  {contraseña}")
    print(f"Rol:         VOCAL_TPE")
    print("=" * 80)
else:
    print("ERROR: No se encontro el Secretario de Actas")
