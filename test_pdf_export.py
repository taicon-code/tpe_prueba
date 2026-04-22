#!/usr/bin/env python
import os
import sys
import django
from io import BytesIO

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from tpe_app.models import PM
from tpe_app.views.export_views import export_person_historial_pdf

# Crear un usuario de prueba (mock request)
try:
    user = User.objects.first()
    if not user:
        user = User.objects.create_user(username='test', password='test')
except:
    user = User.objects.create_user(username='test_' + str(os.urandom(4).hex()), password='test')

# Obtener un PM existente
pm = PM.objects.first()
if not pm:
    print("No hay Personal Militar en la BD")
    sys.exit(1)

# Crear un mock request
factory = RequestFactory()
request = factory.get(f'/buscador/dashboard/{pm.pm_id}/exportar/pdfs/')
request.user = user

print(f"Generando PDF para {pm.PM_NOMBRE} (ID: {pm.pm_id})...")
print(f"Usuario autenticado como: {user.username}")

try:
    response = export_person_historial_pdf(request, pm.pm_id)

    # Guardar el PDF
    filename = f"TEST_HISTORIAL_{pm.pm_id}.pdf"
    with open(filename, 'wb') as f:
        f.write(response.content)

    print("PDF generado exitosamente: " + filename)
    print("Tamaño: " + str(os.path.getsize(filename)) + " bytes")

except Exception as e:
    print("Error al generar PDF: " + str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
