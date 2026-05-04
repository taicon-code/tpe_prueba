import logging

logger = logging.getLogger(__name__)


class SessionDiagnosticsMiddleware:
    """Middleware para diagnosticar problemas de sesión en wizard paso 3"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Registrar estado de sesión ANTES de procesar la solicitud
        if 'wizard' in request.path and 'paso3' in request.path:
            logger.debug(
                f"[BEFORE] {request.method} {request.path} | "
                f"User: {request.user.username if request.user.is_authenticated else 'ANONYMOUS'} | "
                f"Session ID: {request.session.session_key} | "
                f"CSRF Token: {request.POST.get('csrfmiddlewaretoken', 'NO TOKEN')[:10]}..."
            )

        response = self.get_response(request)

        # Registrar estado de sesión DESPUÉS de procesar la solicitud
        if 'wizard' in request.path and 'paso3' in request.path:
            logger.debug(
                f"[AFTER] {request.method} {request.path} | "
                f"Status: {response.status_code} | "
                f"User: {request.user.username if request.user.is_authenticated else 'ANONYMOUS'} | "
                f"Session ID: {request.session.session_key}"
            )

        return response
