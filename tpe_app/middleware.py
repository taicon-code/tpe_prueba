import logging

from django.conf import settings

logger = logging.getLogger(__name__)


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
