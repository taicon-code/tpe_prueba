# tpe_app/views/buscador_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from ..decorators import rol_requerido
from ..models import SIM, PM, RES, RR, RAP, RAEE


@rol_requerido('BUSCADOR')
def buscador_dashboard(request):
    """Dashboard para buscadores - búsqueda y consulta"""

    query = request.GET.get('q', '').strip()
    resultados_sim = []
    resultados_pm  = []

    if query:
        resultados_sim = list(
            SIM.objects.filter(
                Q(SIM_COD__icontains=query)   |
                Q(SIM_RESUM__icontains=query)  |
                Q(SIM_OBJETO__icontains=query)
            ).prefetch_related('abogados', 'militares')[:20]
        )

        resultados_pm = list(
            PM.objects.filter(
                Q(PM_CI__icontains=query)      |
                Q(PM_NOMBRE__icontains=query)  |
                Q(PM_PATERNO__icontains=query) |
                Q(PM_MATERNO__icontains=query)
            )[:20]
        )

    context = {
        'query':        query,
        'resultados_sim': resultados_sim,
        'resultados_pm':  resultados_pm,
        'total_sim':    len(resultados_sim),
        'total_pm':     len(resultados_pm),
    }
    return render(request, 'tpe_app/dashboard_buscador.html', context)


@rol_requerido('BUSCADOR')
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
