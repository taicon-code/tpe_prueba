#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django
import secrets
import string
from pathlib import Path

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from tpe_app.models import PerfilUsuario

# Datos de integrantes
integrantes = [
    ("Cnl.", "DAEN.", "Ruben Nicolas", "Vargas", "Villa", "vargas@tpe.bo", "ASESOR_JEFE"),
    ("Cap.", "Inf.", "Marcelo", "Medina", "Nunez Del Prado", "medina@tpe.bo", "ABOG1_ASESOR"),
    ("Cap.", "Inf.", "Grover Efrain", "Chipana", "Fernandez", "chipana@tpe.bo", "ABOG1_ASESOR"),
    ("Sof. My.", "DEPSS.", "Julio Cesar", "Choque", "Mamani", "choque@tpe.bo", "ABOG2_AUTOS"),
    ("Sof. 1ro.", "DEPSS.", "Jose Luis", "Quispe", "Ticona", "quispe@tpe.bo", "ABOG2_AUTOS"),
    ("Sof. 1ro.", "DEPSS.", "Gonzalo", "Soliz", "Trujillo", "soliz@tpe.bo", "ABOG1_ASESOR"),
    ("Sof. 1ro.", "DEPSS.", "Efrain", "Vela", "Calle", "vela@tpe.bo", "ABOG3_BUSCADOR"),
    ("Sof. 2do.", "DEPSS.", "Freddy Jaime", "Urquieta", "Villarroel", "urquieta@tpe.bo", "ABOG1_ASESOR"),
    ("Sof. 2do.", "DEPSS.", "Edgar", "Ticona", "Colquehuanca", "ticona@tpe.bo", "MASTER"),
    ("Sof. 2do.", "DEPSS.", "Jhon", "Santalla", "Tarquino", "santalla@tpe.bo", "ABOG3_BUSCADOR"),
    ("Sof. 2do.", "DEPSS.", "Ali Edil", "Cruz", "Rivas", "cruz@tpe.bo", "ADMIN1_AGENDADOR"),
    ("Sof. 2do.", "DEPSS.", "Rosaly", "Troche", "Rios", "troche@tpe.bo", "ABOG1_ASESOR"),
    ("Sof. Incl.", "Mus.", "Victor Marcelo", "Mamani", "Flores", "mamani@tpe.bo", "ADMIN1_AGENDADOR"),
    ("Sof. Incl.", "Com.", "Haruzi Andrea", "Mercado", "Mamani", "mercado@tpe.bo", "ADMIN2_ARCHIVO"),
    ("Sgto.1ro.", "Tgrafo.", "Reynaldo Felix", "Paredes", "Aliaga", "paredes@tpe.bo", "AYUDANTE"),
    ("Prof. V", "ABOG", "Daniela Tania", "Romero", "Carvajal", "romero@tpe.bo", "ABOG1_ASESOR"),
    ("Prof. V", "ABOG", "Jhonatan Kevin", "Andia", "Cortez", "andia@tpe.bo", "ABOG1_ASESOR"),
    ("Adm. IV", "ABOG", "Graciela", "Martinez", "Quispe", "martinez@tpe.bo", "BUSCADOR"),
]

def generar_contraseña(longitud=12):
    caracteres = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(caracteres) for _ in range(longitud))

def generar_username(nombres, paterno, materno):
    parts = nombres.split()
    nombre_parte = parts[0].lower()[:3]
    paterno_parte = paterno.lower()[:3]
    materno_parte = materno.lower()[:3] if materno else ""

    username = f"{nombre_parte}{paterno_parte}{materno_parte}".replace(" ", "")

    contador = 1
    username_final = username
    while User.objects.filter(username=username_final).exists():
        username_final = f"{username}{contador}"
        contador += 1

    return username_final

print("=" * 80)
print("CREANDO USUARIOS PARA PRODUCCION".center(80))
print("=" * 80)
print()

resumen = []

for grado, especialidad, nombres, paterno, materno, email, rol in integrantes:
    username = generar_username(nombres, paterno, materno)
    contraseña = generar_contraseña()

    try:
        usuario = User.objects.create_user(
            username=username,
            email=email,
            password=contraseña,
            first_name=nombres,
            last_name=f"{paterno} {materno}"
        )

        PerfilUsuario.objects.create(
            user=usuario,
            rol=rol,
            activo=True
        )

        resumen.append({
            'nombre': f"{paterno} {materno}, {nombres}",
            'grado': grado,
            'email': email,
            'username': username,
            'contraseña': contraseña,
            'rol': rol
        })

        print(f"OK - {paterno.upper()} {materno.upper()}, {nombres}")

    except Exception as e:
        print(f"ERROR - {paterno} {materno}: {e}")

print()
print("=" * 80)
print(f"TOTAL CREADOS: {len(resumen)} usuarios".center(80))
print("=" * 80)
print()

# Guardar credenciales en archivo CSV
with open('credenciales_produccion.csv', 'w', encoding='utf-8') as f:
    f.write("GRADO|NOMBRE COMPLETO|EMAIL|USUARIO|CONTRASEÑA|ROL\n")
    for item in resumen:
        f.write(f"{item['grado']}|{item['nombre']}|{item['email']}|{item['username']}|{item['contraseña']}|{item['rol']}\n")

print("CREDENCIALES GUARDADAS EN: credenciales_produccion.csv")
print()
print("=" * 80)
print("RESUMEN DE USUARIOS Y CONTRASEÑAS")
print("=" * 80)

for item in resumen:
    print()
    print(f"Nombre:      {item['nombre'].upper()}")
    print(f"Grado:       {item['grado']}")
    print(f"Email:       {item['email']}")
    print(f"Usuario:     {item['username']}")
    print(f"Contraseña:  {item['contraseña']}")
    print(f"Rol:         {item['rol']}")
    print("-" * 80)

print()
print("Sistema listo para PRODUCCION")
print("=" * 80)
