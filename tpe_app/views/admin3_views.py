# tpe_app/views/admin3_views.py
from django.shortcuts import render
from ..decorators import rol_requerido
from ..models import Resolucion, DocumentoAdjunto


# ============================================================
# DASHBOARD ADMIN3 (NOTIFICADOR)
# ============================================================

@rol_requerido('ADMIN1', 'ADMIN1_AGENDADOR', 'ADMIN3', 'ADMIN3_NOTIFICADOR')
def admin3_dashboard(request):
    """Dashboard para Admin3 - Notificaciones de documentos (también accesible para Admin1)"""

    # RES (Resoluciones PRIMERA) por notificar (RES_FECNOT es NULL = no notificada aún)
    resoluciones = Resolucion.objects.filter(
        RES_INSTANCIA='PRIMERA', RES_FECNOT__isnull=True
    ).select_related('sim').order_by('-RES_FEC')[:20]

    # RR (Recursos RECONSIDERACION) por notificar
    recursos = list(
        Resolucion.objects.filter(
            RES_INSTANCIA='RECONSIDERACION', RES_FECNOT__isnull=True
        ).select_related('sim').order_by('-RES_FEC')[:20]
    )
    # Compat de template: exponer campos RR_*
    for rr in recursos:
        rr.RR_FEC = rr.RES_FEC
        rr.RR_NUM = rr.RES_NUM
        rr.RR_RESUM = rr.RES_RESUM
        rr.RR_FECPRESEN = rr.RES_FECPRESEN
        rr.RR_FECNOT = rr.RES_FECNOT

    # RES sin PDF (solo PRIMERA)
    res_con_pdf = set(
        DocumentoAdjunto.objects.filter(DOC_TABLA='resolucion').values_list('DOC_ID_REG', flat=True)
    )
    res_sin_pdf = (
        Resolucion.objects.filter(RES_INSTANCIA='PRIMERA')
        .exclude(id__in=res_con_pdf)
        .select_related('sim', 'abog').order_by('-RES_FEC')[:20]
    )
    total_res_sin_pdf = (
        Resolucion.objects.filter(RES_INSTANCIA='PRIMERA')
        .exclude(id__in=res_con_pdf).count()
    )

    context = {
        'resoluciones': resoluciones,
        'total_res': resoluciones.count(),
        'recursos': recursos,
        'total_rr': recursos.count(),
        'res_sin_pdf': res_sin_pdf,
        'total_res_sin_pdf': total_res_sin_pdf,
    }

    return render(request, 'tpe_app/admin3_dashboard.html', context)
