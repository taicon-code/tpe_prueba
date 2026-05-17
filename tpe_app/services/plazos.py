"""
Servicio de plazos legales del TPE.

Cada plazo se expone como un objeto PlazoLegal con:
  - dias_habiles: duracion del plazo
  - articulo: referencia normativa para mostrar al usuario
  - calcular(fecha_inicio): retorna la fecha limite (None si fecha_inicio None)

Plazos del proceso disciplinario militar:
    RR (Reconsideracion):    15 dias habiles desde fecha_presentacion
    RAP (Apelacion TSP):      3 dias habiles desde fecha_oficio
    Ejecutoria tras RR sin RAP: 15 dias habiles desde notificacion del RR

Las citas normativas referenciadas aqui DEBEN actualizarse cuando cambie
la normativa boliviana. El responsable es el Asesor Juridico del TPE.
"""
from dataclasses import dataclass
from datetime import date

from tpe_app.models import (
    add_business_days,
    get_pendientes_ejecutoria,
)


@dataclass(frozen=True)
class PlazoLegal:
    """Plazo administrativo con cita normativa.

    El campo `articulo` se muestra al usuario para que comprenda el origen
    legal del plazo. Mantenerlo actualizado contra la normativa vigente.
    """
    dias_habiles: int
    articulo: str
    descripcion: str = ''

    def calcular(self, fecha_inicio):
        """Retorna fecha + N dias habiles, o None si fecha_inicio es None."""
        return add_business_days(fecha_inicio, self.dias_habiles)

    @property
    def etiqueta(self):
        """Texto listo para template: '15 dias habiles (Art. X, Reglamento...)'."""
        return f'{self.dias_habiles} dias habiles ({self.articulo})'


# ── Plazos del proceso disciplinario militar ───────────────────────────
# NOTA: actualizar `articulo` cuando cambie la normativa. El Asesor Juridico
# del TPE es el responsable de validar estas citas contra la version vigente
# del Reglamento de Faltas Disciplinarias de las FFAA de Bolivia.

PLAZO_RR = PlazoLegal(
    dias_habiles=15,
    articulo='Reglamento de Faltas Disciplinarias FFAA, plazo del RR',
    descripcion='Plazo para presentar Recurso de Reconsideracion ante el TPE.',
)

PLAZO_RAP = PlazoLegal(
    dias_habiles=3,
    articulo='Reglamento de Faltas Disciplinarias FFAA, plazo del RAP',
    descripcion='Plazo para elevar Apelacion al TSP via oficio de elevacion.',
)

PLAZO_EJECUTORIA_POST_RR = PlazoLegal(
    dias_habiles=15,
    articulo='Reglamento de Faltas Disciplinarias FFAA, ejecutoria tras RR sin RAP',
    descripcion='Plazo para emitir Auto de Ejecutoria tras RR no apelado.',
)


# ── Wrappers backward-compatible (no rompen llamadores existentes) ─────

DIAS_HABILES_RR = PLAZO_RR.dias_habiles
DIAS_HABILES_RAP = PLAZO_RAP.dias_habiles
DIAS_HABILES_EJECUTORIA_POST_RR = PLAZO_EJECUTORIA_POST_RR.dias_habiles


def calcular_fecha_limite_rr(fecha_presentacion):
    """Plazo legal del Recurso de Reconsideracion."""
    return PLAZO_RR.calcular(fecha_presentacion)


def calcular_fecha_limite_rap(fecha_oficio):
    """Plazo legal del Recurso de Apelacion al TSP."""
    return PLAZO_RAP.calcular(fecha_oficio)


def calcular_fecha_limite_ejecutoria(fecha_notificacion_rr):
    """Plazo para emitir Auto de Ejecutoria tras RR sin RAP."""
    return PLAZO_EJECUTORIA_POST_RR.calcular(fecha_notificacion_rr)


__all__ = [
    'add_business_days',
    'get_pendientes_ejecutoria',
    'PlazoLegal',
    'PLAZO_RR', 'PLAZO_RAP', 'PLAZO_EJECUTORIA_POST_RR',
    'calcular_fecha_limite_rr',
    'calcular_fecha_limite_rap',
    'calcular_fecha_limite_ejecutoria',
    'DIAS_HABILES_RR',
    'DIAS_HABILES_RAP',
    'DIAS_HABILES_EJECUTORIA_POST_RR',
]
