"""
Vista protegida para servir archivos de MEDIA_ROOT.

Sustituye `django.views.static.serve` directo, que expone PDFs escaneados de
sumarios militares a cualquier visitante anonimo. Aqui se exige login, se
valida path traversal y se registra cada descarga en la bitacora.
"""
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden

from tpe_app.utils.audit import log_acceso


@login_required
def serve_protected_media(request, path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    requested = (media_root / path).resolve()

    try:
        requested.relative_to(media_root)
    except ValueError:
        log_acceso(request, 'PERMISSION_DENIED', detalle=f'path-traversal: {path[:150]}')
        return HttpResponseForbidden('Acceso denegado')

    if not requested.is_file():
        raise Http404('Archivo no encontrado')

    log_acceso(request, 'DOWNLOAD_MEDIA', detalle=path[:200])
    return FileResponse(requested.open('rb'))
