# tpe_app/views/abogado_views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from ..decorators import rol_requerido
from ..models import SIM, RES, RR, AUTOTPE, DocumentoAdjunto
from datetime import date, timedelta

@rol_requerido('ABOGADO')
def abogado_dashboard(request):
    """Dashboard para abogados - solo ven sus sumarios asignados"""
    
    perfil = request.user.perfilusuario
    
    # Si el abogado no está vinculado a ABOG, mostrar error
    if not perfil.abogado:
        context = {'error': 'Tu usuario no está vinculado a un registro de abogado'}
        return render(request, 'tpe_app/dashboard_abogado.html', context)
    
    # Sumarios asignados (que NO son solicitudes)
    mis_sumarios = SIM.objects.filter(abogados=perfil.abogado).exclude(SIM_TIPO__startswith='SOLICITUD').order_by('-SIM_FECREG')
    
    # Solicitudes asignadas
    mis_solicitudes = SIM.objects.filter(abogados=perfil.abogado, SIM_TIPO__startswith='SOLICITUD').order_by('-SIM_FECREG')
    
    # Recursos asignados
    mis_recursos = RR.objects.filter(abog=perfil.abogado).select_related('sim', 'res').order_by('-RR_FEC')
    for rr in mis_recursos:
        doc = DocumentoAdjunto.objects.filter(DOC_TABLA='res', DOC_ID_REG=rr.res.pk).first()
        rr.pdf_primera_res = doc.DOC_RUTA.url if doc else None
    
    # Todos los sumarios (para consulta opcional)
    todos_sumarios = SIM.objects.all().order_by('-SIM_FECREG')
    
    total_asignados = mis_sumarios.count() + mis_solicitudes.count() + mis_recursos.count()
    
    context = {
        'abogado': perfil.abogado,
        'mis_sumarios': mis_sumarios,
        'mis_solicitudes': mis_solicitudes,
        'mis_recursos': mis_recursos,
        'total_asignados': total_asignados,
        'total_res': RES.objects.filter(abog=perfil.abogado).count(),
        'total_rr': RR.objects.filter(abog=perfil.abogado).count(),
        'total_autotpe': AUTOTPE.objects.filter(abog=perfil.abogado).count(),
    }
    
    return render(request, 'tpe_app/dashboard_abogado.html', context)