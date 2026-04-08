# tpe_app/views/buscador_views.py
from django.shortcuts import render
from django.db.models import Q
from ..decorators import rol_requerido
from ..models import SIM, PM, RES, RR, RAP, RAEE

@rol_requerido('BUSCADOR')
def buscador_dashboard(request):
    """Dashboard para buscadores - solo consulta"""
    
    # Búsqueda
    query = request.GET.get('q', '')
    resultados_sim = []
    resultados_pm = []
    
    if query:
        # Buscar en sumarios
        resultados_sim = SIM.objects.filter(
            Q(SIM_COD__icontains=query) |
            Q(SIM_RESUM__icontains=query) |
            Q(SIM_OBJETO__icontains=query)
        )[:20]
        
        # Buscar en personal militar
        resultados_pm = PM.objects.filter(
            Q(PM_CI__icontains=query) |
            Q(PM_NOMBRE__icontains=query) |
            Q(PM_PATERNO__icontains=query) |
            Q(PM_MATERNO__icontains=query)
        )[:20]
    
    context = {
        'query': query,
        'resultados_sim': resultados_sim,
        'resultados_pm': resultados_pm,
        'total_sim': len(resultados_sim),
        'total_pm': len(resultados_pm),
    }
    
    return render(request, 'tpe_app/dashboard_buscador.html', context)