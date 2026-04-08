# tpe_app/views/auxiliar_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ..decorators import rol_requerido
from ..models import SIM, PM, ABOG, RES, RR, AUTOTPE
from datetime import date

@rol_requerido('AUXILIAR')
def auxiliar_dashboard(request):
    """Dashboard para auxiliares - registrar sumarios y notificaciones"""
    
    # Sumarios recientes para referencia
    sumarios_recientes = SIM.objects.all().order_by('-SIM_FECREG')[:20]
    
    # Sumarios para agenda (sin abogado asignado)
    sumarios_sin_asignar = SIM.objects.filter(SIM_ESTADO='PARA_AGENDA').order_by('-SIM_FECING')
    
    context = {
        'sumarios_recientes': sumarios_recientes,
        'sumarios_sin_asignar': sumarios_sin_asignar,
        'total_sin_asignar': sumarios_sin_asignar.count(),
    }
    
    return render(request, 'tpe_app/dashboard_auxiliar.html', context)