# tpe_app/views/ayudante_views.py
"""
Vistas para el rol AYUDANTE - Registro de datos históricos y búsqueda de antecedentes
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import date
from ..decorators import rol_requerido
from ..models import (
    SIM, PM, AUTOTPE, ABOG, VOCAL_TPE, Resolucion, RecursoTSP
)
from ..forms import (
    RESForm, RESNotificacionForm, RAPForm, RAEEForm, AUTOTPEHistoricoForm
)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_dashboard(request):
    """Dashboard principal del AYUDANTE"""
    from ..models import DocumentoAdjunto, ABOG

    # Últimos SIM registrados
    ultimos_sim = SIM.objects.all().order_by('-SIM_FECREG')[:10]

    # Últimas Resoluciones PRIMERA registradas
    ultimas_res = Resolucion.objects.filter(RES_INSTANCIA='PRIMERA').order_by('-RES_FEC')[:10]

    # RES sin PDF (panel principal) — solo PRIMERA
    res_con_pdf = set(
        DocumentoAdjunto.objects.filter(DOC_TABLA='resolucion').values_list('DOC_ID_REG', flat=True)
    )
    res_sin_pdf = (
        Resolucion.objects.filter(RES_INSTANCIA='PRIMERA')
        .exclude(id__in=res_con_pdf)
        .select_related('sim', 'abog').order_by('-RES_FEC')[:10]
    )
    total_res_sin_pdf = (
        Resolucion.objects.filter(RES_INSTANCIA='PRIMERA')
        .exclude(id__in=res_con_pdf).count()
    )

    # Contadores
    total_sim = SIM.objects.count()
    total_res = Resolucion.objects.filter(RES_INSTANCIA='PRIMERA').count()
    total_rr = Resolucion.objects.filter(RES_INSTANCIA='RECONSIDERACION').count()
    total_rap = RecursoTSP.objects.filter(TSP_INSTANCIA='APELACION').count()

    context = {
        'ultimos_sim': ultimos_sim,
        'ultimas_res': ultimas_res,
        'res_sin_pdf': res_sin_pdf,
        'total_res_sin_pdf': total_res_sin_pdf,
        'total_sim': total_sim,
        'total_res': total_res,
        'total_rr': total_rr,
        'total_rap': total_rap,
    }

    return render(request, 'tpe_app/ayudante/dashboard.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_lista_res(request):
    """Lista de RES filtrada por gestión (año) con: grado, nombres, RES_TIPO, notificado"""

    # Parámetro GET: gestion (año), default = año actual
    gestion = request.GET.get('gestion', str(date.today().year))

    try:
        gestion = int(gestion)
    except (ValueError, TypeError):
        gestion = date.today().year

    # Query: Resoluciones PRIMERA del año especificado, ordenadas por grado/apellido
    resoluciones = (
        Resolucion.objects
        .filter(RES_INSTANCIA='PRIMERA', RES_FEC__year=gestion)
        .select_related('pm', 'sim')
        .order_by('pm__PM_GRADO', 'pm__PM_PATERNO', 'pm__PM_NOMBRE')
    )

    # Opciones de gestión disponibles (años únicos)
    gestiones_disponibles = (
        Resolucion.objects.filter(RES_INSTANCIA='PRIMERA')
        .values_list('RES_FEC__year', flat=True)
        .distinct()
        .order_by('-RES_FEC__year')
    )

    context = {
        'resoluciones': resoluciones,
        'gestion_actual': gestion,
        'gestiones_disponibles': gestiones_disponibles,
    }

    return render(request, 'tpe_app/ayudante/lista_res.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_res(request):
    """Registrar una Resolución histórica (sin dictamen previo)"""

    if request.method == 'POST':
        form = RESForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    res = form.save(commit=False)
                    res.save()

                    # Actualizar la fase del SIM si es necesario
                    sim = res.sim
                    if sim.SIM_FASE not in ['1RA_RESOLUCION', '2DA_RESOLUCION', 'ELEVADO_TSP', 'CONCLUIDO']:
                        sim.SIM_FASE = '1RA_RESOLUCION'
                        sim.SIM_ESTADO = 'PROCESO_EN_EL_TPE'
                        sim.save()

                    messages.success(request, f'Resolución {res.RES_NUM} registrada exitosamente')
                    return redirect('ayudante_lista_res')
            except Exception as e:
                messages.error(request, f'Error al registrar la resolución: {str(e)}')
    else:
        form = RESForm()

    context = {
        'form': form,
        'titulo': 'Registrar Resolución Histórica',
    }

    return render(request, 'tpe_app/ayudante/registrar_res.html', context)


@rol_requerido('AYUDANTE', 'ADMIN1', 'ADMIN1_AGENDADOR', 'ADMIN3', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_notificacion(request, res_id):
    """Registrar la notificación de una RES existente"""

    res = get_object_or_404(Resolucion, id=res_id)

    if request.method == 'POST':
        form = RESNotificacionForm(request.POST, instance=res)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    messages.success(
                        request,
                        f'Notificación de RES {res.RES_NUM} registrada exitosamente'
                    )
                    # Redirigir según el rol del usuario
                    rol = getattr(request.user.perfilusuario, 'rol', 'AYUDANTE')
                    if rol in ['ADMIN3', 'ADMIN3_NOTIFICADOR', 'ADMIN1', 'ADMIN1_AGENDADOR']:
                        return redirect('admin3_dashboard')
                    else:
                        return redirect('ayudante_lista_res')
            except Exception as e:
                messages.error(request, f'Error al registrar notificación: {str(e)}')
    else:
        form = RESNotificacionForm(instance=res)

    context = {
        'form': form,
        'res': res,
        'titulo': f'Registrar Notificación - RES {res.RES_NUM}',
    }

    return render(request, 'tpe_app/ayudante/registrar_notificacion.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_rap(request):
    """Registrar un Recurso de Apelación al TSP histórico"""

    if request.method == 'POST':
        form = RAPForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    rap = form.save(commit=False)
                    rap.save()

                    # Actualizar fase del SIM
                    sim = rap.sim
                    if sim.SIM_FASE not in ['ELEVADO_TSP', 'CONCLUIDO']:
                        sim.SIM_FASE = 'ELEVADO_TSP'
                        sim.SIM_ESTADO = 'PROCESO_EN_EL_TSP'
                        sim.save()

                    messages.success(
                        request,
                        f'Recurso de Apelación {rap.TSP_NUM} registrado exitosamente'
                    )
                    return redirect('ayudante_dashboard')
            except Exception as e:
                messages.error(request, f'Error al registrar RAP: {str(e)}')
    else:
        form = RAPForm()

    context = {
        'form': form,
        'titulo': 'Registrar Recurso de Apelación (RAP) Histórico',
    }

    return render(request, 'tpe_app/ayudante/registrar_rap.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_raee(request):
    """Registrar un RAEE (Aclaración, Explicación y Enmienda) histórico"""

    if request.method == 'POST':
        form = RAEEForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    raee = form.save(commit=False)
                    raee.save()

                    messages.success(
                        request,
                        f'RAEE {raee.TSP_NUM} registrado exitosamente'
                    )
                    return redirect('ayudante_dashboard')
            except Exception as e:
                messages.error(request, f'Error al registrar RAEE: {str(e)}')
    else:
        form = RAEEForm()

    context = {
        'form': form,
        'titulo': 'Registrar RAEE (Aclaración, Explicación y Enmienda) Histórico',
    }

    return render(request, 'tpe_app/ayudante/registrar_raee.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_autotpe(request):
    """Registrar un Auto del TPE histórico (incluyendo memorándum)"""

    if request.method == 'POST':
        form = AUTOTPEHistoricoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    autotpe = form.save(commit=False)
                    autotpe.save()

                    messages.success(
                        request,
                        f'Auto TPE {autotpe.TPE_NUM} registrado exitosamente'
                    )
                    return redirect('ayudante_dashboard')
            except Exception as e:
                messages.error(request, f'Error al registrar Auto TPE: {str(e)}')
    else:
        form = AUTOTPEHistoricoForm()

    context = {
        'form': form,
        'titulo': 'Registrar Auto del TPE Histórico (incluyendo Memorándum)',
    }

    return render(request, 'tpe_app/ayudante/registrar_autotpe.html', context)


@rol_requerido('AYUDANTE', 'ADMIN1', 'ADMIN1_AGENDADOR', 'ADMIN3', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_notificacion_rr(request, rr_id):
    """Registrar la notificación de un RR existente"""

    rr = get_object_or_404(Resolucion, id=rr_id, RES_INSTANCIA='RECONSIDERACION')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                rr.RES_FECNOT = timezone.now().date()
                rr.RES_HORNOT = timezone.now().time()
                rr.RES_NOT = request.POST.get('RR_NOT', '')
                rr.save()
                messages.success(
                    request,
                    f'Notificación de RR {rr.RES_NUM} registrada exitosamente'
                )
                # Redirigir según el rol del usuario
                rol = getattr(request.user.perfilusuario, 'rol', 'AYUDANTE')
                if rol in ['ADMIN3', 'ADMIN3_NOTIFICADOR', 'ADMIN1', 'ADMIN1_AGENDADOR']:
                    return redirect('admin3_dashboard')
                else:
                    return redirect('ayudante_dashboard')
        except Exception as e:
            messages.error(request, f'Error al registrar notificación: {str(e)}')

    # Compat de template
    rr.RR_NUM = rr.RES_NUM
    rr.RR_FECPRESEN = rr.RES_FECPRESEN
    context = {
        'rr': rr,
        'titulo': f'Registrar Notificación - RR {rr.RES_NUM}',
    }

    return render(request, 'tpe_app/admin3/registrar_notificacion_rr.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_lista_res_sin_pdf(request):
    """Lista de RES pendientes de subir PDF"""

    from ..models import DocumentoAdjunto
    res_con_pdf = DocumentoAdjunto.objects.filter(
        DOC_TABLA='resolucion'
    ).values_list('DOC_ID_REG', flat=True)

    resoluciones_sin_pdf = (
        Resolucion.objects
        .filter(RES_INSTANCIA='PRIMERA')
        .exclude(id__in=res_con_pdf)
        .select_related('pm', 'sim')
        .order_by('-RES_FEC')
    )

    # Contadores
    total_sin_pdf = resoluciones_sin_pdf.count()
    total_con_pdf = Resolucion.objects.filter(
        RES_INSTANCIA='PRIMERA', id__in=res_con_pdf
    ).count()
    total_res = Resolucion.objects.filter(RES_INSTANCIA='PRIMERA').count()

    context = {
        'resoluciones': resoluciones_sin_pdf,
        'total_sin_pdf': total_sin_pdf,
        'total_con_pdf': total_con_pdf,
        'total_res': total_res,
    }

    return render(request, 'tpe_app/ayudante/lista_res_sin_pdf.html', context)
