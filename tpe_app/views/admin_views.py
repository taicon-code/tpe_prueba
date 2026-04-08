# tpe_app/views/admin_views.py
from django.shortcuts import render
from django.db.models import Count, Q
from ..decorators import rol_requerido
from ..models import SIM, PM, ABOG, RES, RR, RAP, PerfilUsuario
from datetime import date

@rol_requerido('ADMINISTRADOR')
def admin_dashboard(request):
    """Dashboard principal para administradores"""
    
    # Estadísticas generales
    context = {
        'total_sumarios': SIM.objects.count(),
        'sumarios_para_agenda': SIM.objects.filter(SIM_ESTADO='PARA_AGENDA').count(),
        'sumarios_en_tpe': SIM.objects.filter(SIM_ESTADO='PROCESO_EN_EL_TPE').count(),
        'sumarios_en_tsp': SIM.objects.filter(SIM_ESTADO='EN_APELACION_TSP').count(),
        'total_personal': PM.objects.count(),
        'total_abogados': ABOG.objects.count(),
        'total_usuarios': PerfilUsuario.objects.filter(activo=True).count(),
        
        # Sumarios recientes
        'sumarios_recientes': SIM.objects.order_by('-SIM_FECREG')[:10],
    }
    
    return render(request, 'tpe_app/dashboard_admin.html', context)