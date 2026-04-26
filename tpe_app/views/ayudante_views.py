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
    RESForm, NotificacionForm, RAPForm, RAEEForm, AUTOTPEHistoricoForm, MemorandumForm,
    PMSIMFormSet, WizardSIMForm, WizardRESForm, WizardRRForm, WizardAUTOTPEForm, WizardRAPForm, WizardRAEEForm, WizardAUTOTSPForm
)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_dashboard(request):
    """Dashboard principal del AYUDANTE"""
    from ..models import DocumentoAdjunto, ABOG

    # Últimos SIM registrados
    ultimos_sim = SIM.objects.all().order_by('-fecha_registro')[:10]

    # Últimas Resoluciones PRIMERA registradas
    ultimas_res = Resolucion.objects.filter(instancia='PRIMERA').order_by('-fecha')[:10]

    # RES sin PDF (panel principal) — solo PRIMERA
    res_con_pdf = set(
        DocumentoAdjunto.objects.filter(resolucion__isnull=False).values_list('resolucion_id', flat=True)
    )
    res_sin_pdf = (
        Resolucion.objects.filter(instancia='PRIMERA')
        .exclude(id__in=res_con_pdf)
        .select_related('sim', 'abog').order_by('-fecha')[:10]
    )
    total_res_sin_pdf = (
        Resolucion.objects.filter(instancia='PRIMERA')
        .exclude(id__in=res_con_pdf).count()
    )

    # Contadores
    total_sim = SIM.objects.count()
    total_pm = PM.objects.count()
    total_res = Resolucion.objects.filter(instancia='PRIMERA').count()
    total_res_sin_notif = Resolucion.objects.filter(
        instancia='PRIMERA', notificacion__isnull=True
    ).count()
    total_rr = Resolucion.objects.filter(instancia='RECONSIDERACION').count()
    total_rap = RecursoTSP.objects.filter(instancia='APELACION').count()
    total_autotpe = AUTOTPE.objects.count()
    total_autotpe_sin_notif = AUTOTPE.objects.filter(notificacion__isnull=True).count()

    context = {
        'ultimos_sim': ultimos_sim,
        'ultimas_res': ultimas_res,
        'res_sin_pdf': res_sin_pdf,
        'total_res_sin_pdf': total_res_sin_pdf,
        'total_sim': total_sim,
        'total_pm': total_pm,
        'total_res': total_res,
        'total_res_sin_notif': total_res_sin_notif,
        'total_rr': total_rr,
        'total_rap': total_rap,
        'total_autotpe': total_autotpe,
        'total_autotpe_sin_notif': total_autotpe_sin_notif,
    }

    return render(request, 'tpe_app/ayudante/dashboard.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_lista_res(request):
    """Lista de RES filtrada por gestión (año) con: grado, nombres, tipo, notificado"""

    # Parámetro GET: gestion (año), default = año actual
    gestion = request.GET.get('gestion', str(date.today().year))

    try:
        gestion = int(gestion)
    except (ValueError, TypeError):
        gestion = date.today().year

    # Query: Resoluciones PRIMERA del año especificado, ordenadas por grado/apellido
    resoluciones = (
        Resolucion.objects
        .filter(instancia='PRIMERA', fecha__year=gestion)
        .select_related('pm', 'sim')
        .order_by('pm__grado', 'pm__paterno', 'pm__nombre')
    )

    # Opciones de gestión disponibles (años únicos)
    gestiones_disponibles = (
        Resolucion.objects.filter(instancia='PRIMERA')
        .values_list('fecha__year', flat=True)
        .distinct()
        .order_by('-fecha__year')
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
                    if sim.fase not in ['1RA_RESOLUCION', '2DA_RESOLUCION', 'ELEVADO_TSP', 'CONCLUIDO']:
                        sim.fase = '1RA_RESOLUCION'
                        sim.estado = 'PROCESO_EN_EL_TPE'
                        sim.save()

                    messages.success(request, f'Resolución {res.numero} registrada exitosamente')
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


@rol_requerido('AYUDANTE', 'ADMIN1_AGENDADOR', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_notificacion(request, res_id):
    """Registrar la notificación de una RES existente"""
    from ..models import Notificacion

    res = get_object_or_404(Resolucion, id=res_id)
    notif_existente = getattr(res, 'notificacion', None)

    if request.method == 'POST':
        form = NotificacionForm(request.POST, instance=notif_existente)
        if form.is_valid():
            try:
                with transaction.atomic():
                    notif = form.save(commit=False)
                    notif.resolucion = res
                    notif.save()
                    messages.success(request, f'Notificación de RES {res.numero} registrada exitosamente')
                    rol = getattr(request.user.perfilusuario, 'rol', 'AYUDANTE')
                    if rol in ['ADMIN3_NOTIFICADOR', 'ADMIN1_AGENDADOR']:
                        return redirect('admin3_dashboard')
                    else:
                        return redirect('ayudante_lista_res')
            except Exception as e:
                messages.error(request, f'Error al registrar notificación: {str(e)}')
    else:
        form = NotificacionForm(instance=notif_existente)

    context = {
        'form': form,
        'res': res,
        'titulo': f'Registrar Notificación - RES {res.numero}',
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
                    if sim.fase not in ['ELEVADO_TSP', 'CONCLUIDO']:
                        sim.fase = 'ELEVADO_TSP'
                        sim.estado = 'PROCESO_EN_EL_TSP'
                        sim.save()

                    messages.success(
                        request,
                        f'Recurso de Apelación {rap.numero} registrado exitosamente'
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
                        f'RAEE {raee.numero} registrado exitosamente'
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
    """Registrar un Auto del TPE histórico (con memorándum opcional)"""

    if request.method == 'POST':
        form = AUTOTPEHistoricoForm(request.POST)
        memo_form = MemorandumForm(request.POST)
        tiene_memo = bool(request.POST.get('numero'))  # campo del MemorandumForm
        if form.is_valid():
            try:
                with transaction.atomic():
                    autotpe = form.save()
                    if tiene_memo and memo_form.is_valid():
                        memo = memo_form.save(commit=False)
                        memo.autotpe = autotpe
                        memo.save()
                    messages.success(request, f'Auto TPE {autotpe.numero} registrado exitosamente')
                    return redirect('ayudante_dashboard')
            except Exception as e:
                messages.error(request, f'Error al registrar Auto TPE: {str(e)}')
    else:
        form = AUTOTPEHistoricoForm()
        memo_form = MemorandumForm()

    context = {
        'form': form,
        'memo_form': memo_form,
        'titulo': 'Registrar Auto del TPE Histórico (con Memorándum)',
    }

    return render(request, 'tpe_app/ayudante/registrar_autotpe.html', context)


@rol_requerido('AYUDANTE', 'ADMIN1_AGENDADOR', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_notificacion_rr(request, rr_id):
    """Registrar la notificación de un RR existente"""

    rr = get_object_or_404(Resolucion, id=rr_id, instancia='RECONSIDERACION')

    from ..models import Notificacion
    notif_existente = getattr(rr, 'notificacion', None)

    if request.method == 'POST':
        form = NotificacionForm(request.POST, instance=notif_existente)
        if form.is_valid():
            try:
                with transaction.atomic():
                    notif = form.save(commit=False)
                    notif.resolucion = rr
                    notif.save()
                    messages.success(request, f'Notificación de RR {rr.numero} registrada exitosamente')
                    rol = getattr(request.user.perfilusuario, 'rol', 'AYUDANTE')
                    if rol in ['ADMIN3_NOTIFICADOR', 'ADMIN1_AGENDADOR']:
                        return redirect('admin3_dashboard')
                    else:
                        return redirect('ayudante_dashboard')
            except Exception as e:
                messages.error(request, f'Error al registrar notificación: {str(e)}')
    else:
        form = NotificacionForm(instance=notif_existente)

    rr.RR_NUM = rr.numero
    rr.RR_FECPRESEN = rr.fecha_presentacion
    context = {
        'form': form,
        'rr': rr,
        'titulo': f'Registrar Notificación - RR {rr.numero}',
    }

    return render(request, 'tpe_app/admin3/registrar_notificacion_rr.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_registrar_notificacion_auto(request, auto_id):
    """Registrar la notificación de un Auto TPE existente"""
    from ..models import Notificacion

    auto = get_object_or_404(AUTOTPE, id=auto_id)
    notif_existente = getattr(auto, 'notificacion', None)

    if request.method == 'POST':
        form = NotificacionForm(request.POST, instance=notif_existente)
        if form.is_valid():
            try:
                with transaction.atomic():
                    notif = form.save(commit=False)
                    notif.autotpe = auto
                    notif.save()
                    if auto.tipo == 'AUTO_EJECUTORIA' and auto.sim:
                        sim = auto.sim
                        if sim.fase not in ['EJECUTORIA_NOTIFICADA', 'PENDIENTE_ARCHIVO', 'CONCLUIDO']:
                            sim.fase = 'EJECUTORIA_NOTIFICADA'
                            sim.save()
                    messages.success(request, f'Notificación de Auto {auto.numero} registrada exitosamente')
                    rol = getattr(request.user.perfilusuario, 'rol', 'AYUDANTE')
                    if rol in ['ADMIN3_NOTIFICADOR', 'ADMIN1_AGENDADOR']:
                        return redirect('admin3_dashboard')
                    else:
                        return redirect('ayudante_dashboard')
            except Exception as e:
                messages.error(request, f'Error al registrar notificación: {str(e)}')
    else:
        form = NotificacionForm(instance=notif_existente)

    context = {
        'form': form,
        'auto': auto,
        'titulo': f'Registrar Notificación - Auto {auto.numero}',
    }

    return render(request, 'tpe_app/ayudante/registrar_notificacion_auto.html', context)


@rol_requerido('AYUDANTE', 'ADMIN3_NOTIFICADOR')
def ayudante_lista_res_sin_pdf(request):
    """Lista de RES pendientes de subir PDF"""

    from ..models import DocumentoAdjunto
    res_con_pdf = DocumentoAdjunto.objects.filter(
        resolucion__isnull=False
    ).values_list('resolucion_id', flat=True)

    resoluciones_sin_pdf = (
        Resolucion.objects
        .filter(instancia='PRIMERA')
        .exclude(id__in=res_con_pdf)
        .select_related('pm', 'sim')
        .order_by('-fecha')
    )

    # Contadores
    total_sin_pdf = resoluciones_sin_pdf.count()
    total_con_pdf = Resolucion.objects.filter(
        instancia='PRIMERA', id__in=res_con_pdf
    ).count()
    total_res = Resolucion.objects.filter(instancia='PRIMERA').count()

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
    sim = SIM.objects.filter(codigo=codigo).order_by('version').first()
    if sim:
        return JsonResponse({
            'found': True,
            'sim_id': sim.pk,
            'sim_cod': sim.codigo,
            'sim_resum': sim.resumen[:100] if sim.resumen else '',
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
            messages.info(request, f'Usando SIM existente: {sim.codigo}')
            return redirect('ayudante_wizard_paso2', sim_id=sim.pk)

        form = WizardSIMForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    sim = form.save()
                messages.success(request, f'SIM {sim.codigo} creado. Ahora agregue los militares.')
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
                                grado_fecha = inline_form.cleaned_data.get('pmsim_grado_en_fecha') or None
                                pm_sim, _ = PM_SIM.objects.get_or_create(sim=sim, pm=pm)
                                if grado_fecha:
                                    pm_sim.grado_en_fecha = grado_fecha
                                    pm_sim.save(update_fields=['grado_en_fecha'])

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

    res_existente = Resolucion.objects.filter(sim=sim, instancia='PRIMERA').first()
    rr_existente = Resolucion.objects.filter(sim=sim, instancia='RECONSIDERACION').first()

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

                    if sim.fase not in ['1RA_RESOLUCION', '2DA_RESOLUCION', 'NOTIFICADO_1RA', 'NOTIFICADO_RR', 'ELEVADO_TSP', 'CONCLUIDO']:
                        sim.fase = '1RA_RESOLUCION'
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

                        if sim.fase not in ['2DA_RESOLUCION', 'NOTIFICADO_RR', 'ELEVADO_TSP', 'CONCLUIDO']:
                            sim.fase = '2DA_RESOLUCION'
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
    rap_existente = RecursoTSP.objects.filter(sim=sim, instancia='APELACION').first()
    raee_existente = RecursoTSP.objects.filter(sim=sim, instancia='ACLARACION_ENMIENDA').first()
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
                        rap.instancia = 'APELACION'
                        if not rap.pm:
                            rap.pm = sim.militares.first()
                        rap.save()
                        if sim.fase not in ['ELEVADO_TSP', 'CONCLUIDO']:
                            sim.fase = 'ELEVADO_TSP'
                            sim.save()
                        rap_existente = rap
                    else:
                        errores = True

                if guardar_raee:
                    if raee_form.is_valid():
                        raee = raee_form.save(commit=False)
                        raee.sim = sim
                        raee.instancia = 'ACLARACION_ENMIENDA'
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
    resoluciones = Resolucion.objects.filter(sim=sim).order_by('fecha')
    autos_tpe = AUTOTPE.objects.filter(sim=sim).order_by('fecha')
    recursos_tsp = RecursoTSP.objects.filter(sim=sim).order_by('fecha')
    autos_tsp = AUTOTSP.objects.filter(sim=sim).order_by('fecha')

    return render(request, 'tpe_app/ayudante/wizard/resumen.html', {
        'sim': sim,
        'resoluciones': resoluciones,
        'autos_tpe': autos_tpe,
        'recursos_tsp': recursos_tsp,
        'autos_tsp': autos_tsp,
        'paso_actual': 5,
        'total_pasos': 4,
    })


# ============================================================================
# EDICIÓN DE PERSONAL MILITAR — Grado actual, año de egreso, no ascendió
# ============================================================================

@rol_requerido('AYUDANTE', 'ADMIN1_AGENDADOR')
def ayudante_editar_pm(request, pm_id):
    """Permite al Ayudante actualizar grado actual, año de egreso y estado de ascenso."""
    pm = get_object_or_404(PM, pm_id=pm_id)

    if request.method == 'POST':
        grado      = request.POST.get('grado') or None
        escalafon  = request.POST.get('escalafon') or None
        estado     = request.POST.get('estado') or pm.estado
        promocion  = request.POST.get('anio_promocion') or None
        no_asc     = request.POST.get('no_ascendio') == 'on'

        if promocion:
            try:
                promocion = int(promocion)
                if not (1950 <= promocion <= 2100):
                    messages.error(request, 'Año de egreso fuera de rango (1950-2100).')
                    promocion = pm.anio_promocion
            except ValueError:
                messages.error(request, 'Año de egreso inválido.')
                promocion = pm.anio_promocion
        else:
            promocion = None

        pm.grado       = grado
        pm.escalafon   = escalafon
        pm.estado      = estado
        pm.anio_promocion   = promocion
        pm.no_ascendio = no_asc
        pm.save(update_fields=['grado', 'escalafon', 'estado', 'anio_promocion', 'no_ascendio'])

        messages.success(request, f'Datos de {pm.nombre} {pm.paterno} actualizados.')
        next_url = request.POST.get('next') or request.GET.get('next') or 'ayudante_dashboard'
        return redirect(next_url)

    return render(request, 'tpe_app/ayudante/editar_pm.html', {
        'pm': pm,
        'grado_choices': PM.GRADO_CHOICES,
        'escalafon_choices': PM.ESCALAFON_CHOICES,
        'estado_choices': PM.ESTADO_CHOICES,
        'grado_esperado': pm.grado_esperado,
        'estado_calculado': pm.estado_carrera_calculado,
        'años_servicio': pm.años_servicio,
    })
