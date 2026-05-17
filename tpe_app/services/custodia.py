"""
Servicio de custodia de carpetas SIM.

Centraliza consultas y operaciones sobre CustodiaSIM para no duplicar
logica entre admin1_views, admin2_views y abogado_documentos_views.

Convencion: las funciones de consulta retornan QuerySets o None; las de
mutacion lanzan ValidationError ante reglas de negocio violadas.
"""
from django.core.exceptions import ValidationError


# Conjuntos de tipo_custodio para clasificar quien tiene la carpeta.
TIPOS_ABOGADO = ('ABOG_ASESOR', 'ABOG_RR', 'ABOG_AUTOS')
TIPOS_ADMIN = ('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')


def custodia_activa(sim):
    """Retorna la CustodiaSIM activa (RECIBIDA_CONFORME, sin fecha_entrega) o None."""
    from tpe_app.models import CustodiaSIM
    return (
        CustodiaSIM.objects
        .filter(sim=sim, estado='RECIBIDA_CONFORME', fecha_entrega__isnull=True)
        .select_related('abogado')
        .first()
    )


def custodia_pendiente_entregar(sim):
    """Retorna la CustodiaSIM en estado PENDIENTE_CONFIRMACION o None."""
    from tpe_app.models import CustodiaSIM
    return (
        CustodiaSIM.objects
        .filter(sim=sim, estado='PENDIENTE_CONFIRMACION', fecha_entrega__isnull=True)
        .select_related('abogado_destino')
        .first()
    )


def abogado_tiene_carpeta(sim, abogado):
    """True si el abogado tiene la carpeta del SIM activa en su poder."""
    from tpe_app.models import CustodiaSIM
    return CustodiaSIM.objects.filter(
        sim=sim,
        abogado=abogado,
        estado='RECIBIDA_CONFORME',
        fecha_entrega__isnull=True,
        tipo_custodio__in=TIPOS_ABOGADO,
    ).exists()


def hay_custodia_ejecutoria_abierta(sim):
    """True si hay una custodia con motivo='EJECUTORIA' aun no cerrada."""
    from tpe_app.models import CustodiaSIM
    return CustodiaSIM.objects.filter(
        sim=sim, motivo='EJECUTORIA', fecha_entrega__isnull=True
    ).exists()


def validar_puede_entregar(sim):
    """Reglas previas a marcar una entrega como PENDIENTE_CONFIRMACION."""
    pendiente = custodia_pendiente_entregar(sim)
    if pendiente:
        raise ValidationError(
            f'El SIM {sim.codigo} ya tiene una entrega pendiente de confirmacion '
            f'(custodia #{pendiente.id}). Cancele o confirme antes de iniciar otra.'
        )
    return True
