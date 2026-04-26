# tpe_app/views/admin3_views.py
from django.shortcuts import render
from ..decorators import rol_requerido
from ..models import Resolucion, AUTOTPE, DocumentoAdjunto


# ============================================================
# DASHBOARD ADMIN3 (NOTIFICADOR)
# ============================================================

@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN3_NOTIFICADOR')
def admin3_dashboard(request):
    """Dashboard para Admin3 - Notificaciones de documentos (también accesible para Admin1)"""

    # RES (Resoluciones PRIMERA) por notificar (fecha_notif es NULL = no notificada aún)
    resoluciones = Resolucion.objects.filter(
        instancia='PRIMERA', notificacion__isnull=True
    ).select_related('sim', 'pm').order_by('-fecha')[:20]

    # RR (Recursos RECONSIDERACION) por notificar
    recursos = list(
        Resolucion.objects.filter(
            instancia='RECONSIDERACION', notificacion__isnull=True
        ).select_related('sim').order_by('-fecha')[:20]
    )
    for rr in recursos:
        rr.RR_FEC = rr.fecha
        rr.RR_NUM = rr.numero
        rr.RR_RESUM = rr.resumen
        rr.RR_FECPRESEN = rr.fecha_presentacion

    # AUTOS TPE por notificar
    autos = AUTOTPE.objects.filter(
        notificacion__isnull=True
    ).select_related('sim', 'pm', 'abog').order_by('-fecha')[:20]

    # RES sin PDF (solo PRIMERA)
    res_con_pdf = set(
        DocumentoAdjunto.objects.filter(tabla='resolucion').values_list('registro_id', flat=True)
    )
    res_sin_pdf = (
        Resolucion.objects.filter(instancia='PRIMERA')
        .exclude(id__in=res_con_pdf)
        .select_related('sim', 'pm').order_by('-fecha')[:20]
    )
    total_res_sin_pdf = (
        Resolucion.objects.filter(instancia='PRIMERA')
        .exclude(id__in=res_con_pdf).count()
    )

    context = {
        'resoluciones': resoluciones,
        'total_res': resoluciones.count(),
        'recursos': recursos,
        'total_rr': len(recursos),
        'autos': autos,
        'total_autos': autos.count(),
        'res_sin_pdf': res_sin_pdf,
        'total_res_sin_pdf': total_res_sin_pdf,
    }

    return render(request, 'tpe_app/admin3/admin3_dashboard.html', context)
