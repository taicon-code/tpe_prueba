# tpe_app/views/buscador_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from ..decorators import rol_requerido
from ..models import SIM, PM, AUTOTPE, AUTOTSP, Resolucion, RecursoTSP


def _obtener_historial_completo(personal_id):
    """Obtiene el historial completo de un personal"""
    try:
        personal = PM.objects.get(pm_id=personal_id)
    except PM.DoesNotExist:
        return None

    # Obtener todos los SIM donde participa este personal
    sims = SIM.objects.filter(militares__pm_id=personal_id).distinct()
    sim_ids = list(sims.values_list('id', flat=True))

    historial = {
        'personal': personal,
        'sumarios': sims,
        'resoluciones': Resolucion.objects.filter(sim__in=sim_ids, RES_INSTANCIA='PRIMERA'),
        'segundas_resoluciones': Resolucion.objects.filter(sim__in=sim_ids, RES_INSTANCIA='RECONSIDERACION'),
        'recursos_apelacion': RecursoTSP.objects.filter(sim__in=sim_ids, TSP_INSTANCIA='APELACION'),
        'raees': RecursoTSP.objects.filter(sim__in=sim_ids, TSP_INSTANCIA='ACLARACION_ENMIENDA'),
        'autos_tpe': AUTOTPE.objects.filter(sim__in=sim_ids),
        'autos_tsp': AUTOTSP.objects.filter(sim__in=sim_ids),
    }

    return historial


def _obtener_estado_actual(personal_id):
    """Obtiene el estado actual del personal"""
    historial = _obtener_historial_completo(personal_id)
    if not historial:
        return None

    return {
        'total_sumarios': historial['sumarios'].count(),
        'total_resoluciones': historial['resoluciones'].count(),
        'total_apelaciones': historial['recursos_apelacion'].count(),
        'total_raees': historial['raees'].count(),
        'estado_actual': 'Historial disponible'
    }


def buscador_dashboard(request):
    """Dashboard para búsqueda unificada - búsqueda por código SIM, nombre, apellido paterno, materno"""

    query = request.GET.get('q', '').strip()
    personal_seleccionado = None
    historial = None
    estado = None
    resultados_pm = []
    resultados_sim = []

    if query:
        resultados_pm = list(
            PM.objects.filter(
                Q(PM_NOMBRE__icontains=query) |
                Q(PM_PATERNO__icontains=query) |
                Q(PM_MATERNO__icontains=query)
            ).distinct()[:20]
        )

        resultados_sim = list(
            SIM.objects.filter(
                Q(SIM_COD__icontains=query) |
                Q(SIM_RESUM__icontains=query) |
                Q(SIM_OBJETO__icontains=query)
            ).prefetch_related('abogados', 'militares').distinct()[:20]
        )

        # Si hay exactamente 1 PM, mostrar su historial completo
        if len(resultados_pm) == 1:
            personal_seleccionado = resultados_pm[0]
            historial = _obtener_historial_completo(personal_seleccionado.pm_id)
            estado = _obtener_estado_actual(personal_seleccionado.pm_id)

    context = {
        'query': query,
        'resultados_pm': resultados_pm,
        'resultados_sim': resultados_sim,
        'total_pm': len(resultados_pm),
        'total_sim': len(resultados_sim),
        'personal_seleccionado': personal_seleccionado,
        'historial': historial,
        'estado': estado,
    }
    return render(request, 'tpe_app/dashboard_buscador.html', context)


def upload_foto_pm(request, pm_id):
    """Subir o reemplazar la foto de un Personal Militar"""
    pm = get_object_or_404(PM, pk=pm_id)

    if request.method == 'POST':
        foto = request.FILES.get('foto')
        if foto:
            # Validar que sea imagen
            content_type = foto.content_type or ''
            if not content_type.startswith('image/'):
                messages.error(request, '❌ El archivo debe ser una imagen (JPG, PNG, etc.)')
            else:
                # Eliminar foto anterior si existe
                if pm.PM_FOTO:
                    pm.PM_FOTO.delete(save=False)
                pm.PM_FOTO = foto
                pm.save(update_fields=['PM_FOTO'])
                messages.success(request, f'✅ Foto actualizada para {pm.PM_NOMBRE} {pm.PM_PATERNO}')
        else:
            messages.error(request, '❌ No se seleccionó ningún archivo')

    # Volver al buscador con la misma búsqueda si venía de ahí
    referer = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if 'buscador' in referer or 'q=' in referer:
        return redirect(referer)
    return redirect('buscador_dashboard')
