# tpe_app/views/abogado_views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from ..decorators import rol_requerido
from ..models import SIM, RES, RR, AUTOTPE
from datetime import date, timedelta

@rol_requerido('ABOGADO')
def abogado_dashboard(request):
    """Dashboard para abogados - solo ven sus sumarios asignados"""
    
    perfil = request.user.perfilusuario
    
    # Si el abogado no está vinculado a ABOG, mostrar error
    if not perfil.abogado:
        context = {'error': 'Tu usuario no está vinculado a un registro de abogado'}
        return render(request, 'tpe_app/dashboard_abogado.html', context)
    
    # Sumarios asignados a este abogado
    mis_sumarios = SIM.objects.filter(abogados=perfil.abogado)
    
    # Todos los sumarios (para consulta)
    todos_sumarios = SIM.objects.all().order_by('-SIM_FECREG')
    
    context = {
        'abogado': perfil.abogado,
        'mis_sumarios': mis_sumarios.order_by('-SIM_FECREG'),
        'total_asignados': mis_sumarios.count(),
        'para_agenda': mis_sumarios.filter(SIM_ESTADO='PARA_AGENDA').count(),
        'en_proceso': mis_sumarios.filter(SIM_ESTADO='PROCESO_EN_EL_TPE').count(),
        'en_apelacion': mis_sumarios.filter(SIM_ESTADO='EN_APELACION_TSP').count(),
        'todos_sumarios': todos_sumarios[:50],  # Limitar a 50 para no sobrecargar
    }
    
    return render(request, 'tpe_app/dashboard_abogado.html', context)