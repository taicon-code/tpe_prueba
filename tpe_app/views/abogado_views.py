# tpe_app/views/abogado_views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Exists, OuterRef
from ..decorators import rol_requerido
from ..models import SIM, AUTOTPE, DocumentoAdjunto, CustodiaSIM, Resolucion, RecursoTSP
from datetime import date, timedelta

@rol_requerido('ABOGADO', 'ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR')
def abogado_dashboard(request):
    """Dashboard para abogados - solo ven sus sumarios asignados"""

    perfil = request.perfil
    
    # Si el abogado no está vinculado a PM, mostrar error
    if not perfil.pm:
        context = {'error': 'Tu usuario no está vinculado a un registro de Personal Militar'}
        return render(request, 'tpe_app/abogado/dashboard_abogado.html', context)

    # ✅ NUEVO v3.1: Sumarios CON CUSTODIA ACTIVA (que NO son solicitudes)
    # Obtener IDs de SIM donde el abogado tiene custodia activa
    sim_ids_con_custodia = CustodiaSIM.objects.filter(
        abogado=perfil.pm,
        fecha_entrega__isnull=True
    ).values_list('sim_id', flat=True)

    mis_sumarios = SIM.objects.filter(
        pk__in=sim_ids_con_custodia
    ).exclude(tipo__startswith='SOLICITUD').order_by('-fecha_registro').distinct()

    # ✅ NUEVO v3.1: Solicitudes CON CUSTODIA ACTIVA
    mis_solicitudes = SIM.objects.filter(
        pk__in=sim_ids_con_custodia,
        tipo__startswith='SOLICITUD'
    ).order_by('-fecha_registro').distinct()
    
    # ✅ NUEVO v3.1: Recursos asignados a este abogado
    # Mostrar Resolucion RECONSIDERACION donde el abogado está asignado,
    # aunque Admin2 aún no haya entregado custodia
    mis_recursos = list(
        Resolucion.objects.filter(
            instancia='RECONSIDERACION',
            abogado=perfil.pm,
        )
        .select_related('sim', 'resolucion_origen', 'pm')
        .prefetch_related('sim__militares')
        .order_by('-fecha')
        .distinct()
    )
    for rr in mis_recursos:
        # Adjuntar PDF de la PRIMERA resolución impugnada (si existe)
        if rr.resolucion_origen_id:
            doc = DocumentoAdjunto.objects.filter(
                resolucion_id=rr.resolucion_origen_id
            ).first()
            rr.pdf_primera_res = doc.archivo.url if doc else None
        else:
            rr.pdf_primera_res = None
        # Mostrar el militar específico del RR (no el primero del sumario)
        rr.investigado = rr.pm if rr.pm else rr.sim.militares.first()
        # Compat de template: exponer .res (resolución origen) y .RR_FEC
        rr.res = rr.resolucion_origen
        rr.RR_FEC = rr.fecha
    
    # Todos los sumarios (para consulta opcional)
    todos_sumarios = SIM.objects.all().order_by('-fecha_registro')
    
    total_asignados = mis_sumarios.count() + mis_solicitudes.count() + len(mis_recursos)
    
    # Pendientes de ejecutoria (solo para ABOG2_AUTOS)
    pendientes_ej = []
    if perfil.rol in ('ABOG2_AUTOS', 'ADMINISTRADOR', 'MASTER'):
        from ..models import get_pendientes_ejecutoria
        por_res_ej, por_rr_ej = get_pendientes_ejecutoria()
        pendientes_ej = por_res_ej + por_rr_ej

    # RAPs para elaborar (solo para ABOG1_ASESOR y ABOG2_AUTOS)
    raps_para_elaborar = []
    if perfil.rol in ('ABOG1_ASESOR', 'ABOG2_AUTOS', 'ADMINISTRADOR', 'MASTER'):
        raps_para_elaborar = list(
            RecursoTSP.objects.filter(
                instancia='APELACION',
                numero__isnull=True,
                sim__custodias__tipo_custodio__in=['ABOG_ASESOR', 'ABOG_AUTOS'],
                sim__custodias__fecha_entrega__isnull=True,
            ).select_related('sim', 'pm', 'resolucion').distinct()
        )

    context = {
        'abogado': perfil.pm,
        'mis_sumarios': mis_sumarios,
        'mis_solicitudes': mis_solicitudes,
        'mis_recursos': mis_recursos,
        'total_asignados': total_asignados,
        'total_res': Resolucion.objects.filter(
            instancia='PRIMERA', abogado=perfil.pm
        ).count(),
        'total_rr': Resolucion.objects.filter(
            instancia='RECONSIDERACION', sim__pk__in=sim_ids_con_custodia
        ).count(),
        'total_autotpe': AUTOTPE.objects.filter(abogado=perfil.pm).count(),
        'raps_para_elaborar': raps_para_elaborar,
        'total_raps_elaborar': len(raps_para_elaborar),
        'pendientes_ejecutoria': pendientes_ej,
        'total_pendientes_ejecutoria': len(pendientes_ej),
    }

    return render(request, 'tpe_app/abogado/dashboard_abogado.html', context)

# ============================================================
# ENTREGA DE CARPETA (Custodia)
# ============================================================

@rol_requerido('ABOGADO', 'ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR')
def abogado_entregar_carpeta(request, sim_id):
    """El abogado entrega la carpeta a Archivo SIM (Admin2) después de terminar"""
    from django.shortcuts import redirect
    from django.contrib import messages
    from django.db import transaction
    from django.utils import timezone
    from ..models import CustodiaSIM
    from ..forms import EntregarCarpetaAbogadoForm

    sim = get_object_or_404(SIM, pk=sim_id)
    perfil = request.perfil

    if request.method == 'POST':
        form = EntregarCarpetaAbogadoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Obtener custodia activa del abogado
                    custodia_abogado = CustodiaSIM.objects.filter(
                        sim=sim,
                        fecha_entrega__isnull=True,
                        abogado=perfil.pm
                    ).first()

                    if not custodia_abogado:
                        messages.error(request, '❌ No hay custodia activa para este sumario')
                        return redirect('abogado_sumario_detalle', sim_id=sim.pk)

                    # Registrar devolución del abogado (cierra custodia)
                    custodia_abogado.fecha_entrega = timezone.now()
                    custodia_abogado.observacion = form.cleaned_data.get('observacion', '')
                    custodia_abogado.save()

                    # Crear custodia para Archivo SIM (Admin2) pendiente de confirmación
                    CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio='ADMIN2_ARCHIVO',
                        abogado=perfil.pm,
                        usuario=request.user,
                        observacion=f'Recibida de {perfil.pm.grado} {perfil.pm.paterno}. {form.cleaned_data.get("observacion", "")}',
                        estado='PENDIENTE_CONFIRMACION'
                    )

                    messages.success(
                        request,
                        f'✅ Carpeta del sumario {sim.codigo} entregada a Archivo SIM'
                    )
                    return redirect('abogado_dashboard')
            except Exception as e:
                messages.error(request, f'❌ Error al entregar: {str(e)}')
    else:
        form = EntregarCarpetaAbogadoForm()

    context = {
        'form': form,
        'sim': sim,
    }
    return render(request, 'tpe_app/abogado/entregar_carpeta.html', context)
