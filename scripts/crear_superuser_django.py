#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Crea un superusuario de Django de forma segura.

Uso:
    python scripts/crear_superuser_django.py --username django_admin --email admin@tpe.bo

La contrasena se solicita por getpass (no se imprime, no queda en historial de shell
ni en logs de la terminal). Si el usuario ya existe, aborta sin modificarlo.
"""
import argparse
import getpass
import os
import sys
from pathlib import Path

# Asegurar que la raiz del proyecto este en sys.path para que 'config' sea importable
# sin importar desde donde se invoque el script (scripts/, raiz, etc.).
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password, password_validators_help_texts
from django.core.exceptions import ValidationError


def main():
    parser = argparse.ArgumentParser(description='Crea un superusuario Django de forma segura.')
    parser.add_argument('--username', required=True, help='Nombre de usuario del superuser')
    parser.add_argument('--email', required=True, help='Email del superuser')
    args = parser.parse_args()

    if User.objects.filter(username=args.username).exists():
        print(f'ERROR: El usuario "{args.username}" ya existe. Operacion cancelada.', file=sys.stderr)
        sys.exit(1)

    if User.objects.filter(email=args.email).exists():
        print(f'ERROR: El email "{args.email}" ya esta en uso. Operacion cancelada.', file=sys.stderr)
        sys.exit(1)

    print('Politica de contrasenas:')
    for help_text in password_validators_help_texts():
        print(f'  - {help_text}')
    print()

    password = getpass.getpass('Contrasena: ')
    password_confirm = getpass.getpass('Confirmar contrasena: ')

    if password != password_confirm:
        print('ERROR: Las contrasenas no coinciden.', file=sys.stderr)
        sys.exit(1)

    user_stub = User(username=args.username, email=args.email)
    try:
        validate_password(password, user=user_stub)
    except ValidationError as e:
        print('ERROR: Contrasena no cumple la politica:', file=sys.stderr)
        for msg in e.messages:
            print(f'  - {msg}', file=sys.stderr)
        sys.exit(1)

    User.objects.create_superuser(
        username=args.username,
        email=args.email,
        password=password,
    )

    print()
    print('Superusuario creado correctamente.')
    print(f'  Usuario: {args.username}')
    print(f'  Email:   {args.email}')
    print('  URL Admin: /admin/')
    print()
    print('La contrasena NO se imprime por seguridad.')
    print('Cambiela despues en /admin/ -> Users si fue temporal.')


if __name__ == '__main__':
    main()
