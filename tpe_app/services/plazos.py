"""
Servicio de plazos legales del TPE.

Re-exporta y centraliza utilidades de calculo de dias habiles + feriados.
La implementacion vive en models.py por restriccion historica (cache de
feriados + funcion legacy add_business_days). Este modulo es la fachada
que las nuevas vistas y comandos deben usar.

Plazos del proceso disciplinario militar:
    RR (Reconsideracion):    15 dias habiles desde fecha_presentacion
    RAP (Apelacion TSP):      3 dias habiles desde fecha_oficio
    Ejecutoria tras RR sin RAP: 15 dias habiles desde notificacion del RR
"""
from tpe_app.models import (
    add_business_days,
    get_pendientes_ejecutoria,
)

DIAS_HABILES_RR = 15
DIAS_HABILES_RAP = 3
DIAS_HABILES_EJECUTORIA_POST_RR = 15


def calcular_fecha_limite_rr(fecha_presentacion):
    """Plazo legal del Recurso de Reconsideracion."""
    return add_business_days(fecha_presentacion, DIAS_HABILES_RR)


def calcular_fecha_limite_rap(fecha_oficio):
    """Plazo legal del Recurso de Apelacion al TSP."""
    return add_business_days(fecha_oficio, DIAS_HABILES_RAP)


def calcular_fecha_limite_ejecutoria(fecha_notificacion_rr):
    """Plazo para emitir Auto de Ejecutoria tras RR sin RAP."""
    return add_business_days(fecha_notificacion_rr, DIAS_HABILES_EJECUTORIA_POST_RR)


__all__ = [
    'add_business_days',
    'get_pendientes_ejecutoria',
    'calcular_fecha_limite_rr',
    'calcular_fecha_limite_rap',
    'calcular_fecha_limite_ejecutoria',
    'DIAS_HABILES_RR',
    'DIAS_HABILES_RAP',
    'DIAS_HABILES_EJECUTORIA_POST_RR',
]
