"""Checks de Django para detectar configuraciones incompletas al startup."""
from datetime import datetime

from django.core.checks import Warning, register


@register('tpe_app.feriados')
def check_feriados_del_anio(app_configs, **kwargs):
    """Warning si la tabla FeriadoBolivia no tiene feriados del ano en curso.

    Sin feriados cargados, add_business_days() cae al fallback hardcoded
    de _FERIADOS_FALLBACK (que solo cubre 2026). Los plazos de RR/RAP
    pueden calcular dias incorrectos en anos posteriores.
    """
    try:
        from tpe_app.models import FeriadoBolivia
    except Exception:
        # En collectstatic, migraciones iniciales o ambientes sin BD,
        # el import del modelo puede fallar. Saltar silenciosamente.
        return []

    anio = datetime.now().year
    try:
        count = FeriadoBolivia.objects.filter(anio=anio).count()
    except Exception:
        # Tabla aun no existe (primera migracion) o BD no accesible.
        return []

    if count == 0:
        return [Warning(
            f'No hay feriados cargados para el ano {anio} en FeriadoBolivia.',
            hint=f'Ejecute: python manage.py cargar_feriados {anio}',
            id='tpe_app.W001',
        )]
    return []
