"""
Helper para emitir entradas en la bitacora de accesos (AccesoLog).

Diseno:
  - log_acceso() es la unica forma soportada de insertar entradas. Nunca
    debe modificarse o borrarse una entrada desde codigo de aplicacion.
  - Fallos al insertar (BD caida, transaccion en error) se silencian con
    un warning al log de seguridad, para que la auditoria nunca rompa la
    funcionalidad principal.
"""
import logging

security_log = logging.getLogger('tpe_app.security')


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


def log_acceso(request, accion, objeto_tipo='', objeto_id=None, detalle=''):
    """Registra una entrada en la bitacora de accesos.

    Args:
        request: HttpRequest. Se usa para extraer user, ip y user-agent.
        accion: Codigo de ACCION_CHOICES (ej. 'VIEW_SIM', 'EXPORT_PDF').
        objeto_tipo: Tipo del objeto consultado (ej. 'SIM', 'PM').
        objeto_id: ID del objeto consultado.
        detalle: Texto adicional (max 200 chars, se truncan).

    Errores de BD se reportan al log de seguridad pero no propagan.
    """
    from tpe_app.models import AccesoLog
    try:
        user = request.user if request.user.is_authenticated else None
        ua = request.META.get('HTTP_USER_AGENT', '')[:200]
        AccesoLog.objects.create(
            usuario=user,
            accion=accion,
            objeto_tipo=(objeto_tipo or '')[:30],
            objeto_id=objeto_id,
            detalle=(detalle or '')[:200],
            ip=_client_ip(request),
            user_agent=ua,
        )
    except Exception as e:
        security_log.warning(
            'AUDIT_INSERT_FAIL accion=%s tipo=%s id=%s err=%s:%s',
            accion, objeto_tipo, objeto_id, e.__class__.__name__, e,
        )
