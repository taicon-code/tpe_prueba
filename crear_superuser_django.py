#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import django
import secrets
import string

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

# Generar contraseña segura
caracteres = string.ascii_letters + string.digits + "!@#$%^&*"
contraseña = ''.join(secrets.choice(caracteres) for _ in range(12))

# Crear superuser
usuario = User.objects.create_superuser(
    username='django_admin',
    email='admin@tpe.bo',
    password=contraseña
)

print()
print("=" * 80)
print("SUPERUSER CREADO - DJANGO ADMIN")
print("=" * 80)
print(f"Usuario:     django_admin")
print(f"Email:       admin@tpe.bo")
print(f"Contraseña:  {contraseña}")
print(f"URL Admin:   http://127.0.0.1:8000/admin/")
print("=" * 80)
print()
print("Este usuario tiene acceso TOTAL a Django Admin")
print("Para cambiar contraseña despues: /admin/ → Users → django_admin")
print()
