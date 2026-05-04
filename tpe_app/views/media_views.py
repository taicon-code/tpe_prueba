"""
Vista protegida para servir archivos de MEDIA_ROOT.

Sustituye `django.views.static.serve` directo, que expone PDFs escaneados de
sumarios militares a cualquier visitante anonimo. Aqui se exige login y se
valida path traversal antes de servir el archivo.
"""
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseForbidden


@login_required
def serve_protected_media(request, path):
    media_root = Path(settings.MEDIA_ROOT).resolve()
    requested = (media_root / path).resolve()

    try:
        requested.relative_to(media_root)
    except ValueError:
        return HttpResponseForbidden('Acceso denegado')

    if not requested.is_file():
        raise Http404('Archivo no encontrado')

    return FileResponse(requested.open('rb'))
