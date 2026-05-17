import ipaddress
import logging

from django.conf import settings
from django.http import HttpResponseForbidden

logger = logging.getLogger(__name__)
security_log = logging.getLogger('tpe_app.security')


class SessionDiagnosticsMiddleware:
    """Diagnostico de sesion del wizard paso 3.

    Loguea identificadores de sesion y fragmentos del token CSRF, asi que SOLO
    debe activarse cuando DEBUG=True. En produccion se convierte en un no-op.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._enabled = bool(settings.DEBUG)

    def __call__(self, request):
        if not self._enabled:
            return self.get_response(request)

        is_wizard_paso3 = 'wizard' in request.path and 'paso3' in request.path

        if is_wizard_paso3:
            logger.debug(
                f"[BEFORE] {request.method} {request.path} | "
                f"User: {request.user.username if request.user.is_authenticated else 'ANONYMOUS'} | "
                f"Session ID: {request.session.session_key} | "
                f"CSRF Token: {request.POST.get('csrfmiddlewaretoken', 'NO TOKEN')[:10]}..."
            )

        response = self.get_response(request)

        if is_wizard_paso3:
            logger.debug(
                f"[AFTER] {request.method} {request.path} | "
                f"Status: {response.status_code} | "
                f"User: {request.user.username if request.user.is_authenticated else 'ANONYMOUS'} | "
                f"Session ID: {request.session.session_key}"
            )

        return response


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or ''


def _parse_allowlist(raw_list):
    """Convierte una lista de strings ('10.0.0.0/8', '127.0.0.1') en ip_network objs.

    Acepta tanto IPs sueltas como rangos CIDR. Las entradas invalidas se omiten
    con warning al log de seguridad.
    """
    redes = []
    for entrada in raw_list:
        entrada = entrada.strip()
        if not entrada:
            continue
        try:
            redes.append(ipaddress.ip_network(entrada, strict=False))
        except ValueError:
            security_log.warning('IP_ALLOWLIST entrada invalida: %s', entrada)
    return redes


class IPAllowlistMiddleware:
    """Restringe acceso a la app a un conjunto de redes/IPs.

    Configuracion via .env:
        IP_ALLOWLIST=10.0.0.0/8,192.168.1.0/24,127.0.0.1

    Si la lista esta vacia (default), el middleware es no-op: NO filtra nada.
    Esto permite habilitar la restriccion de forma opt-in sin romper deploys
    existentes.

    Cuando rechaza, emite un AccesoLog con accion='PERMISSION_DENIED' y
    detalle='ip-not-in-allowlist'.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        raw = getattr(settings, 'IP_ALLOWLIST', None) or []
        self._redes = _parse_allowlist(raw)
        self._activo = bool(self._redes)
        if self._activo:
            security_log.info('IP_ALLOWLIST activa con %s redes', len(self._redes))

    def __call__(self, request):
        if not self._activo:
            return self.get_response(request)

        ip_str = _client_ip(request)
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            # IP malformada o ausente: rechazamos por defecto cuando la
            # allowlist esta activa.
            security_log.warning('IP_BLOCKED ip=<invalida:%s> path=%s', ip_str[:40], request.path)
            return HttpResponseForbidden('Acceso denegado.')

        if not any(ip_obj in red for red in self._redes):
            security_log.warning('IP_BLOCKED ip=%s path=%s', ip_str, request.path)
            return HttpResponseForbidden('Acceso denegado: IP fuera del rango permitido.')

        return self.get_response(request)
