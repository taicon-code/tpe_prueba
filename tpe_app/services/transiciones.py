"""
Servicio de transiciones de fase del SIM.

Centraliza la validacion contra SIM.FASE_TRANSICIONES_VALIDAS para que
ningun caller pueda saltar a una fase invalida sin reportar el error.
"""
import logging

from django.core.exceptions import ValidationError

security_log = logging.getLogger('tpe_app.security')


class TransicionInvalida(ValidationError):
    """La transicion solicitada no esta en FASE_TRANSICIONES_VALIDAS."""
    pass


def cambiar_fase(sim, nueva_fase, *, actor=None, motivo=''):
    """Cambia la fase de un SIM validando la transicion.

    Args:
        sim: instancia de SIM.
        nueva_fase: codigo de la nueva fase (de SIM.FASE_CHOICES).
        actor: User que origino la transicion (para auditoria).
        motivo: descripcion corta (max 200 chars) para auditoria.

    Raises:
        TransicionInvalida si la transicion no esta en la whitelist y la
        fase actual SI esta listada en FASE_TRANSICIONES_VALIDAS (modo
        permisivo: si la fase actual no esta listada, cualquier nueva fase
        se acepta, por compat con datos historicos).
    """
    from tpe_app.models import SIM

    fase_actual = sim.fase
    validas = SIM.FASE_TRANSICIONES_VALIDAS.get(fase_actual)

    if validas is not None and nueva_fase not in validas:
        raise TransicionInvalida(
            f'Transicion invalida: {fase_actual or "(sin fase)"} -> {nueva_fase}. '
            f'Validas desde {fase_actual}: {", ".join(validas)}.'
        )

    fase_previa = sim.fase
    sim.fase = nueva_fase
    # SIM.save() ya sincroniza estado segun FASE_A_ESTADO.
    sim.save()

    actor_label = actor.username if (actor and hasattr(actor, 'username')) else 'sistema'
    security_log.info(
        'FASE_CHANGE sim=%s prev=%s nueva=%s actor=%s motivo=%s',
        sim.codigo, fase_previa, nueva_fase, actor_label, motivo[:200],
    )
    return sim
