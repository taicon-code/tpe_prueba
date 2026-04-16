# tpe_app/views/ejecutoria_views.py
"""
Vistas para Auto de Ejecutoria — detección semi-automática y registro.
Roles con acceso:
  - Lista pendientes:  ADMIN1_AGENDADOR, ADMIN3_NOTIFICADOR, ABOG2_AUTOS, ADMINISTRADOR, MASTER
  - Crear auto:        ABOG2_AUTOS, ADMINISTRADOR, MASTER
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from ..decorators import rol_requerido
from ..models import (
    RES, RR, AUTOTPE, SIM,
    get_pendientes_ejecutoria,
)
from ..forms import AutoEjecutoriaForm


ROLES_VER   = ('ADMIN1_AGENDADOR', 'ADMIN3_NOTIFICADOR', 'ABOG2_AUTOS', 'ADMINISTRADOR', 'MASTER')
ROLES_CREAR = ('ABOG2_AUTOS', 'ADMINISTRADOR', 'MASTER')


@rol_requerido(*ROLES_VER)
def pendientes_ejecutoria(request):
    """Lista los casos con plazo de ejecutoria vencido que aún no tienen Auto de Ejecutoria."""
    por_res, por_rr = get_pendientes_ejecutoria()
    return render(request, 'tpe_app/ejecutoria/lista_pendientes.html', {
        'por_res':   por_res,
        'por_rr':    por_rr,
        'total':     len(por_res) + len(por_rr),
    })


@rol_requerido(*ROLES_CREAR)
def crear_auto_ejecutoria(request, origen, origen_id):
    """
    Crea un AUTOTPE de tipo AUTO_EJECUTORIA.
    - origen='res'  → vincula al RES con id=origen_id
    - origen='rr'   → vincula al RR  con id=origen_id
    """
    if origen == 'res':
        res = get_object_or_404(RES, pk=origen_id)
        rr  = None
        sim = res.sim
        pm  = res.pm
        origen_label = f"Resolución {res.RES_NUM} — Sumario {sim.SIM_COD}"
    elif origen == 'rr':
        rr  = get_object_or_404(RR, pk=origen_id)
        res = rr.res
        sim = rr.sim
        pm  = rr.pm
        origen_label = f"RR {rr.RR_NUM} — Sumario {sim.SIM_COD}"
    else:
        messages.error(request, "Origen inválido.")
        return redirect('pendientes_ejecutoria')

    if request.method == 'POST':
        form = AutoEjecutoriaForm(request.POST)
        if form.is_valid():
            auto = form.save(commit=False)
            auto.TPE_TIPO = 'AUTO_EJECUTORIA'
            auto.sim = sim
            auto.pm  = pm
            auto.res = res
            auto.rr  = rr
            auto.save()
            # Marcar SIM como concluido (save() completo para que FASE_A_ESTADO actualice SIM_ESTADO)
            sim.SIM_FASE = 'CONCLUIDO'
            sim.save()
            messages.success(request, f"Auto de Ejecutoria {auto.TPE_NUM or ''} registrado correctamente.")
            return redirect('pendientes_ejecutoria')
    else:
        form = AutoEjecutoriaForm()

    return render(request, 'tpe_app/ejecutoria/crear_auto_ejecutoria.html', {
        'form':         form,
        'origen':       origen,
        'origen_id':    origen_id,
        'origen_label': origen_label,
        'sim':          sim,
        'pm':           pm,
    })
