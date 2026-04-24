# tpe_app/views/ayudante_views.py
"""
Vistas para el rol AYUDANTE - Registro de datos históricos y búsqueda de antecedentes
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.urls import reverse
from datetime import date
from ..decorators import rol_requerido
from ..models import (
    SIM, PM, PM_SIM, AUTOTPE, AUTOTSP, ABOG, VOCAL_TPE, Resolucion, RecursoTSP
)
from ..forms import (
    RESForm, RESNotificacionForm, RAPForm, RAEEForm, AUTOTPEHistoricoForm, AUTOTPENotificacionForm,
    PMSIMFormSet, WizardSIMForm, WizardRESForm, WizardRRForm, WizardAUTOTPEForm, WizardRAPForm, WizardRAEEForm, WizardAUTOTSPForm
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
def ayudante_registrar_notificacion_auto(request, auto_id):
    """Registrar la notificación de un Auto TPE existente"""

    auto = get_object_or_404(AUTOTPE, id=auto_id)

    if request.method == 'POST':
        form = AUTOTPENotificacionForm(request.POST, instance=auto)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    # Si es Auto de Ejecutoria, transicionar SIM a EJECUTORIA_NOTIFICADA
                    # para que Admin1 pueda ordenar el archivo final a SPRODA
                    if auto.TPE_TIPO == 'AUTO_EJECUTORIA' and auto.sim:
                        sim = auto.sim
                        # Actualizar SIM_FASE a EJECUTORIA_NOTIFICADA si no está ya en estado final
                        if sim.SIM_FASE not in ['EJECUTORIA_NOTIFICADA', 'PENDIENTE_ARCHIVO', 'CONCLUIDO']:
                            sim.SIM_FASE = 'EJECUTORIA_NOTIFICADA'
                            sim.save()
                    messages.success(
                        request,
                        f'Notificación de Auto {auto.TPE_NUM} registrada exitosamente'
                    )
                    # Redirigir según el rol del usuario
                    rol = getattr(request.user.perfilusuario, 'rol', 'AYUDANTE')
                    if rol in ['ADMIN3', 'ADMIN3_NOTIFICADOR', 'ADMIN1', 'ADMIN1_AGENDADOR']:
                        return redirect('admin3_dashboard')
                    else:
                        return redirect('ayudante_dashboard')
            except Exception as e:
                messages.error(request, f'Error al registrar notificación: {str(e)}')
    else:
        form = AUTOTPENotificacionForm(instance=auto)

    context = {
        'form': form,
        'auto': auto,
        'titulo': f'Registrar Notificación - Auto {auto.TPE_NUM}',
    }

    return render(request, 'tpe_app/ayudante/registrar_notificacion_auto.html', context)


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


# ============================================================================
# WIZARD DE INGRESO RÁPIDO — 6 VISTAS NUEVAS
# ============================================================================

@rol_requerido('AYUDANTE')
def ayudante_wizard_buscar_sim(request):
    """AJAX: busca SIM por código"""
    codigo = (request.GET.get('q') or '').strip().upper()
    if not codigo:
        return JsonResponse({'found': False})
    sim = SIM.objects.filter(SIM_COD=codigo).order_by('SIM_VERSION').first()
    if sim:
        return JsonResponse({
            'found': True,
            'sim_id': sim.pk,
            'sim_cod': sim.SIM_COD,
            'sim_resum': sim.SIM_RESUM[:100] if sim.SIM_RESUM else '',
            'wizard_url': reverse('ayudante_wizard_paso2', kwargs={'sim_id': sim.pk}),
        })
    return JsonResponse({'found': False})


@rol_requerido('AYUDANTE')
def ayudante_wizard_paso1(request):
    """PASO 1 — Crear o seleccionar SIM (solo datos del sumario)"""
    if request.method == 'POST':
        sim_existente_id = request.POST.get('sim_existente_id')
        if sim_existente_id:
            sim = get_object_or_404(SIM, pk=sim_existente_id)
            messages.info(request, f'Usando SIM existente: {sim.SIM_COD}')
            return redirect('ayudante_wizard_paso2', sim_id=sim.pk)

        form = WizardSIMForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    sim = form.save()
                messages.success(request, f'SIM {sim.SIM_COD} creado. Ahora agregue los militares.')
                return redirect('ayudante_wizard_paso2', sim_id=sim.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar SIM: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores.')
    else:
        form = WizardSIMForm()

    return render(request, 'tpe_app/ayudante/wizard/paso1_sim.html', {
        'form': form,
        'paso_actual': 1,
        'total_pasos': 4,
    })


@rol_requerido('AYUDANTE')
def ayudante_wizard_paso2(request, sim_id):
    """PASO 2 — Verificación/Edición de Militares"""
    sim = get_object_or_404(SIM, pk=sim_id)

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'skip':
            if sim.militares.exists():
                return redirect('ayudante_wizard_paso3', sim_id=sim.pk)
            else:
                messages.warning(request, 'Debe haber al menos un militar antes de continuar.')

        elif action == 'save':
            formset = PMSIMFormSet(request.POST, request.FILES, instance=sim)
            if formset.is_valid():
                try:
                    with transaction.atomic():
                        for inline_form in formset:
                            if not inline_form.cleaned_data:
                                continue
                            if inline_form.cleaned_data.get('DELETE'):
                                pm_sim_pk = inline_form.instance.pk
                                if pm_sim_pk:
                                    PM_SIM.objects.filter(pk=pm_sim_pk).delete()
                                continue

                            # Caso 1: PM ya existía en BD
                            pm = inline_form.cleaned_data.get('pm')

                            # Caso 2: PM nuevo — crearlo con los datos del formulario
                            if not pm:
                                pm_data = inline_form.cleaned_data.get('pm_data')
                                if pm_data:
                                    pm = PM.objects.create(**pm_data)

                            if pm:
                                PM_SIM.objects.get_or_create(sim=sim, pm=pm)

                    messages.success(request, 'Militares guardados correctamente.')
                    return redirect('ayudante_wizard_paso3', sim_id=sim.pk)
                except Exception as e:
                    messages.error(request, f'Error: {str(e)}')
            else:
                messages.error(request, 'Por favor corrija los errores.')
        formset = PMSIMFormSet(request.POST, request.FILES, instance=sim)
    else:
        formset = PMSIMFormSet(instance=sim)

    militares_actuales = sim.militares.all()
    return render(request, 'tpe_app/ayudante/wizard/paso2_pm.html', {
        'sim': sim,
        'formset': formset,
        'militares_actuales': militares_actuales,
        'paso_actual': 2,
        'total_pasos': 4,
    })


@rol_requerido('AYUDANTE')
def ayudante_wizard_paso3(request, sim_id):
    """PASO 3 — Primera Resolución + RR opcional"""
    sim = get_object_or_404(SIM, pk=sim_id)

    res_existente = Resolucion.objects.filter(sim=sim, RES_INSTANCIA='PRIMERA').first()
    rr_existente = Resolucion.objects.filter(sim=sim, RES_INSTANCIA='RECONSIDERACION').first()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'skip':
            return redirect('ayudante_wizard_paso4', sim_id=sim.pk)

        guardar_res = request.POST.get('guardar_res') == '1'
        guardar_rr = request.POST.get('guardar_rr') == '1'

        res_form = WizardRESForm(request.POST if guardar_res else None, instance=res_existente, prefix='res')
        rr_form = WizardRRForm(request.POST if guardar_rr else None, instance=rr_existente, prefix='rr')

        errores = False
        try:
            with transaction.atomic():
                if guardar_res and res_form.is_valid():
                    res = res_form.save(commit=False)
                    res.sim = sim
                    if not res.pm:
                        res.pm = sim.militares.first()
                    res.save()
                    res_existente = res

                    if sim.SIM_FASE not in ['1RA_RESOLUCION', '2DA_RESOLUCION', 'NOTIFICADO_1RA', 'NOTIFICADO_RR', 'ELEVADO_TSP', 'CONCLUIDO']:
                        sim.SIM_FASE = '1RA_RESOLUCION'
                        sim.save()

                elif guardar_res and not res_form.is_valid():
                    errores = True

                if guardar_rr and res_existente:
                    if rr_form.is_valid():
                        rr = rr_form.save(commit=False)
                        rr.sim = sim
                        rr.pm = res_existente.pm
                        rr.resolucion_origen = res_existente
                        rr.save()

                        if sim.SIM_FASE not in ['2DA_RESOLUCION', 'NOTIFICADO_RR', 'ELEVADO_TSP', 'CONCLUIDO']:
                            sim.SIM_FASE = '2DA_RESOLUCION'
                            sim.save()
                    else:
                        errores = True

                if not errores:
                    messages.success(request, 'Resoluciones guardadas correctamente.')
                    return redirect('ayudante_wizard_paso4', sim_id=sim.pk)

        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')

        if errores:
            messages.error(request, 'Por favor corrija los errores.')

    else:
        res_form = WizardRESForm(instance=res_existente, prefix='res')
        rr_form = WizardRRForm(instance=rr_existente, prefix='rr')

    res_form.fields['pm'].queryset = sim.militares.all()

    return render(request, 'tpe_app/ayudante/wizard/paso3_resoluciones.html', {
        'sim': sim,
        'res_form': res_form,
        'rr_form': rr_form,
        'res_existente': res_existente,
        'rr_existente': rr_existente,
        'paso_actual': 3,
        'total_pasos': 4,
    })


@rol_requerido('AYUDANTE')
def ayudante_wizard_paso4(request, sim_id):
    """PASO 4 — Auto TPE, RAP, RAEE, Auto TSP (todos opcionales)"""
    sim = get_object_or_404(SIM, pk=sim_id)

    autotpe_existente = AUTOTPE.objects.filter(sim=sim).first()
    rap_existente = RecursoTSP.objects.filter(sim=sim, TSP_INSTANCIA='APELACION').first()
    raee_existente = RecursoTSP.objects.filter(sim=sim, TSP_INSTANCIA='ACLARACION_ENMIENDA').first()
    autotsp_existente = AUTOTSP.objects.filter(sim=sim).first()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'skip':
            return redirect('ayudante_wizard_resumen', sim_id=sim.pk)

        guardar_autotpe = request.POST.get('guardar_autotpe') == '1'
        guardar_rap = request.POST.get('guardar_rap') == '1'
        guardar_raee = request.POST.get('guardar_raee') == '1'
        guardar_autotsp = request.POST.get('guardar_autotsp') == '1'

        autotpe_form = WizardAUTOTPEForm(request.POST if guardar_autotpe else None, instance=autotpe_existente, prefix='autotpe')
        rap_form = WizardRAPForm(request.POST if guardar_rap else None, instance=rap_existente, prefix='rap', sim=sim)
        raee_form = WizardRAEEForm(request.POST if guardar_raee else None, instance=raee_existente, prefix='raee', sim=sim)
        autotsp_form = WizardAUTOTSPForm(request.POST if guardar_autotsp else None, instance=autotsp_existente, prefix='autotsp')

        errores = False
        try:
            with transaction.atomic():
                if guardar_autotpe:
                    if autotpe_form.is_valid():
                        auto = autotpe_form.save(commit=False)
                        auto.sim = sim
                        if not auto.pm:
                            auto.pm = sim.militares.first()
                        auto.save()
                        autotpe_existente = auto
                    else:
                        errores = True

                if guardar_rap:
                    if rap_form.is_valid():
                        rap = rap_form.save(commit=False)
                        rap.sim = sim
                        rap.TSP_INSTANCIA = 'APELACION'
                        if not rap.pm:
                            rap.pm = sim.militares.first()
                        rap.save()
                        if sim.SIM_FASE not in ['ELEVADO_TSP', 'CONCLUIDO']:
                            sim.SIM_FASE = 'ELEVADO_TSP'
                            sim.save()
                        rap_existente = rap
                    else:
                        errores = True

                if guardar_raee:
                    if raee_form.is_valid():
                        raee = raee_form.save(commit=False)
                        raee.sim = sim
                        raee.TSP_INSTANCIA = 'ACLARACION_ENMIENDA'
                        if not raee.pm:
                            raee.pm = sim.militares.first()
                        raee.save()
                        raee_existente = raee
                    else:
                        errores = True

                if guardar_autotsp:
                    if autotsp_form.is_valid():
                        autotsp = autotsp_form.save(commit=False)
                        autotsp.sim = sim
                        autotsp.save()
                        autotsp_existente = autotsp
                    else:
                        errores = True

                if not errores:
                    messages.success(request, 'Documentos guardados correctamente.')
                    return redirect('ayudante_wizard_resumen', sim_id=sim.pk)

        except Exception as e:
            messages.error(request, f'Error al guardar: {str(e)}')

        if errores:
            messages.error(request, 'Por favor corrija los errores en los formularios activos.')

    else:
        autotpe_form = WizardAUTOTPEForm(instance=autotpe_existente, prefix='autotpe')
        rap_form = WizardRAPForm(instance=rap_existente, prefix='rap', sim=sim)
        raee_form = WizardRAEEForm(instance=raee_existente, prefix='raee', sim=sim)
        autotsp_form = WizardAUTOTSPForm(instance=autotsp_existente, prefix='autotsp')

    autotpe_form.fields['pm'].queryset = sim.militares.all()

    return render(request, 'tpe_app/ayudante/wizard/paso4_autos.html', {
        'sim': sim,
        'autotpe_form': autotpe_form,
        'rap_form': rap_form,
        'raee_form': raee_form,
        'autotsp_form': autotsp_form,
        'autotpe_existente': autotpe_existente,
        'rap_existente': rap_existente,
        'raee_existente': raee_existente,
        'autotsp_existente': autotsp_existente,
        'paso_actual': 4,
        'total_pasos': 4,
    })


@rol_requerido('AYUDANTE')
def ayudante_wizard_resumen(request, sim_id):
    """Vista de resumen final del wizard — solo lectura"""
    sim = get_object_or_404(SIM.objects.prefetch_related('militares'), pk=sim_id)
    resoluciones = Resolucion.objects.filter(sim=sim).order_by('RES_FEC')
    autos_tpe = AUTOTPE.objects.filter(sim=sim).order_by('TPE_FEC')
    recursos_tsp = RecursoTSP.objects.filter(sim=sim).order_by('TSP_FEC')
    autos_tsp = AUTOTSP.objects.filter(sim=sim).order_by('TSP_FEC')

    return render(request, 'tpe_app/ayudante/wizard/resumen.html', {
        'sim': sim,
        'resoluciones': resoluciones,
        'autos_tpe': autos_tpe,
        'recursos_tsp': recursos_tsp,
        'autos_tsp': autos_tsp,
        'paso_actual': 5,
        'total_pasos': 4,
    })
