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
    Resolucion, AUTOTPE, SIM,
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
        res = get_object_or_404(Resolucion, pk=origen_id, instancia='PRIMERA')
        resolucion_link = res
        sim = res.sim
        pm  = res.pm
        origen_label = f"Resolución {res.numero} — Sumario {sim.codigo}"
    elif origen == 'rr':
        rr  = get_object_or_404(Resolucion, pk=origen_id, instancia='RECONSIDERACION')
        resolucion_link = rr
        sim = rr.sim
        pm  = rr.pm
        origen_label = f"RR {rr.numero} — Sumario {sim.codigo}"
    else:
        messages.error(request, "Origen inválido.")
        return redirect('pendientes_ejecutoria')

    if request.method == 'POST':
        form = AutoEjecutoriaForm(request.POST)
        if form.is_valid():
            auto = form.save(commit=False)
            auto.tipo = 'AUTO_EJECUTORIA'
            auto.sim = sim
            auto.pm  = pm
            auto.resolucion = resolucion_link
            auto.save()
            # Auto emitido: SIM pasa a EN_EJECUTORIA (pendiente de notificación y archivo)
            sim.fase = 'EN_EJECUTORIA'
            sim.save()
            messages.success(request, f"Auto de Ejecutoria {auto.numero or ''} registrado correctamente.")
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
