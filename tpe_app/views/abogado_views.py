# tpe_app/views/abogado_views.py
from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Exists, OuterRef
from ..decorators import rol_requerido
from ..models import SIM, RES, RR, AUTOTPE, DocumentoAdjunto, CustodiaSIM
from datetime import date, timedelta

@rol_requerido('ABOGADO', 'ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR')
def abogado_dashboard(request):
    """Dashboard para abogados - solo ven sus sumarios asignados"""
    
    perfil = request.user.perfilusuario
    
    # Si el abogado no está vinculado a ABOG, mostrar error
    if not perfil.abogado:
        context = {'error': 'Tu usuario no está vinculado a un registro de abogado'}
        return render(request, 'tpe_app/dashboard_abogado.html', context)
    
    # ✅ NUEVO v3.1: Sumarios CON CUSTODIA ACTIVA (que NO son solicitudes)
    # Obtener IDs de SIM donde el abogado tiene custodia activa
    sim_ids_con_custodia = CustodiaSIM.objects.filter(
        abog=perfil.abogado,
        fecha_entrega__isnull=True
    ).values_list('sim_id', flat=True)

    mis_sumarios = SIM.objects.filter(
        pk__in=sim_ids_con_custodia
    ).exclude(SIM_TIPO__startswith='SOLICITUD').order_by('-SIM_FECREG').distinct()

    # ✅ NUEVO v3.1: Solicitudes CON CUSTODIA ACTIVA
    mis_solicitudes = SIM.objects.filter(
        pk__in=sim_ids_con_custodia,
        SIM_TIPO__startswith='SOLICITUD'
    ).order_by('-SIM_FECREG').distinct()
    
    # ✅ NUEVO v3.1: Recursos CON CUSTODIA ACTIVA — con investigados para mostrar en el panel
    # Solo mostrar RR donde el abogado tiene custodia activa
    mis_recursos = list(
        RR.objects.filter(
            abog=perfil.abogado,
            sim__pk__in=sim_ids_con_custodia
        )
        .select_related('sim', 'res')
        .prefetch_related('sim__militares')
        .order_by('-RR_FEC')
        .distinct()
    )
    for rr in mis_recursos:
        doc = DocumentoAdjunto.objects.filter(DOC_TABLA='res', DOC_ID_REG=rr.res.pk).first()
        rr.pdf_primera_res = doc.DOC_RUTA.url if doc else None
        rr.investigado = rr.sim.militares.first()
    
    # Todos los sumarios (para consulta opcional)
    todos_sumarios = SIM.objects.all().order_by('-SIM_FECREG')
    
    total_asignados = mis_sumarios.count() + mis_solicitudes.count() + len(mis_recursos)
    
    # Pendientes de ejecutoria (solo para ABOG2_AUTOS)
    pendientes_ej = []
    if perfil.rol in ('ABOG2_AUTOS', 'ADMINISTRADOR', 'MASTER'):
        from ..models import get_pendientes_ejecutoria
        por_res_ej, por_rr_ej = get_pendientes_ejecutoria()
        pendientes_ej = por_res_ej + por_rr_ej

    context = {
        'abogado': perfil.abogado,
        'mis_sumarios': mis_sumarios,
        'mis_solicitudes': mis_solicitudes,
        'mis_recursos': mis_recursos,
        'total_asignados': total_asignados,
        'total_res': RES.objects.filter(abog=perfil.abogado).count(),
        'total_rr': RR.objects.filter(abog=perfil.abogado).count(),
        'total_autotpe': AUTOTPE.objects.filter(abog=perfil.abogado).count(),
        'pendientes_ejecutoria': pendientes_ej,
        'total_pendientes_ejecutoria': len(pendientes_ej),
    }

    return render(request, 'tpe_app/dashboard_abogado.html', context)

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
    perfil = request.user.perfilusuario

    if request.method == 'POST':
        form = EntregarCarpetaAbogadoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Obtener custodia activa del abogado
                    custodia_abogado = CustodiaSIM.objects.filter(
                        sim=sim,
                        fecha_entrega__isnull=True,
                        abog=perfil.abogado
                    ).first()

                    if not custodia_abogado:
                        messages.error(request, '❌ No hay custodia activa para este sumario')
                        return redirect('abogado_sumario_detalle', sim_id=sim.pk)

                    # Registrar devolución del abogado (cierra custodia)
                    custodia_abogado.fecha_entrega = timezone.now()
                    custodia_abogado.observacion = form.cleaned_data.get('observacion', '')
                    custodia_abogado.save()

                    # Crear custodia para Archivo SIM (Admin2)
                    CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio='ADMIN2_ARCHIVO',
                        usuario=request.user,
                        observacion=f'Recibida de {perfil.abogado.AB_GRADO} {perfil.abogado.AB_PATERNO}. {form.cleaned_data.get("observacion", "")}'
                    )

                    messages.success(
                        request,
                        f'✅ Carpeta del sumario {sim.SIM_COD} entregada a Archivo SIM'
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
