# tpe_app/views/administrativo_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from ..decorators import rol_requerido
from ..models import SIM, PM, ABOG, PM_SIM, RR, CustodiaSIM
from ..forms import SIMForm, PMSIMFormSet, AgendarSumarioForm, RegistrarRRForm, AgendarRRForm
from datetime import date, timedelta

@rol_requerido('ADMINISTRATIVO')
def administrativo_dashboard(request):
    """Dashboard para administrativos - registrar sumarios y notificaciones"""

    query = (request.GET.get('q') or '').strip()

    filtros_q = Q()
    if query:
        filtros_q = (
            Q(SIM_COD__icontains=query) |
            Q(SIM_RESUM__icontains=query) |
            Q(SIM_OBJETO__icontains=query)
        )

    # Sumarios recientes para referencia
    sumarios_recientes = (
        SIM.objects.prefetch_related('abogados')
        .filter(filtros_q)
        .order_by('-SIM_FECREG')[:20]
    )

    # Sumarios para agenda (sin abogado asignado - ignorando solicitudes)
    sumarios_sin_asignar = (
        SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True)
        .exclude(SIM_TIPO__startswith='SOLICITUD')
        .prefetch_related('militares')
        .filter(filtros_q)
        .order_by('-SIM_FECING')
    )

    # Solicitudes para agendar
    solicitudes_sin_asignar = (
        SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True, SIM_TIPO__startswith='SOLICITUD')
        .prefetch_related('militares')
        .filter(filtros_q)
        .order_by('-SIM_FECING')
    )

    # RR por agendar — calcular fecha límite 25 días y color de alerta
    rr_sin_asignar = list(
        RR.objects.filter(abog__isnull=True)
        .select_related('sim', 'res')
        .order_by('-RR_FECPRESEN')
    )
    hoy = date.today()
    for rr in rr_sin_asignar:
        if rr.RR_FECPRESEN:
            rr.fecha_limite_25 = rr.RR_FECPRESEN + timedelta(days=25)
            dias = (rr.fecha_limite_25 - hoy).days
            if dias < 0:
                rr.alerta_25 = 'danger'
            elif dias <= 5:
                rr.alerta_25 = 'warning'
            elif dias <= 10:
                rr.alerta_25 = 'info'
            else:
                rr.alerta_25 = 'success'
        else:
            rr.fecha_limite_25 = None
            rr.alerta_25 = 'secondary'
    
    context = {
        'query': query,
        'sumarios_recientes': sumarios_recientes,
        'sumarios_sin_asignar': sumarios_sin_asignar,
        'total_sin_asignar': sumarios_sin_asignar.count(),
        'solicitudes_sin_asignar': solicitudes_sin_asignar,
        'total_solicitudes_sin_asignar': solicitudes_sin_asignar.count(),
        'rr_sin_asignar': rr_sin_asignar,
        'total_rr_sin_asignar': len(rr_sin_asignar),
    }
    
    return render(request, 'tpe_app/dashboard_administrativo.html', context)


@rol_requerido('ADMINISTRATIVO')
def registrar_sumario(request):
    """Formulario para registrar un nuevo sumario con militares"""
    
    if request.method == 'POST':
        form = SIMForm(request.POST)
        formset = PMSIMFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Guardar el sumario
                    sumario = form.save(commit=False)
                    sumario.SIM_ESTADO = 'PARA_AGENDA'  # Estado inicial
                    sumario.save()
                    
                    # Guardar los militares investigados
                    formset.instance = sumario
                    
                    for inline_form in formset:
                        if inline_form.cleaned_data and not inline_form.cleaned_data.get('DELETE'):
                            pm = inline_form.cleaned_data.get('pm')
                            if not pm:
                                pm_data = inline_form.cleaned_data.get('pm_data') or {}
                                if not pm_data:
                                    continue
                                ci = pm_data.get('PM_CI')
                                if ci:
                                    pm = PM.objects.filter(PM_CI=ci).first()
                                if not pm:
                                    pm = PM.objects.create(
                                        PM_CI=pm_data.get('PM_CI'),
                                        PM_ESCALAFON=pm_data.get('PM_ESCALAFON'),
                                        PM_GRADO=pm_data.get('PM_GRADO'),
                                        PM_ARMA=pm_data.get('PM_ARMA'),
                                        PM_NOMBRE=pm_data.get('PM_NOMBRE'),
                                        PM_PATERNO=pm_data.get('PM_PATERNO'),
                                        PM_MATERNO=pm_data.get('PM_MATERNO'),
                                        PM_ESTADO='ACTIVO',
                                    )

                            if pm:
                                PM_SIM.objects.get_or_create(sim=sumario, pm=pm)
                    
                    messages.success(
                        request, 
                        f'✅ Sumario {sumario.SIM_COD} registrado exitosamente'
                    )
                    return redirect('administrativo_dashboard')
                    
            except Exception as e:
                messages.error(request, f'❌ Error al guardar: {str(e)}')
        else:
            messages.error(request, '❌ Por favor corrija los errores en el formulario')
    else:
        form = SIMForm()
        formset = PMSIMFormSet()
    
    # Lista de personal militar para autocompletado
    personal_militar = PM.objects.values('PM_CI', 'PM_NOMBRE', 'PM_PATERNO', 'PM_GRADO')[:100]
    
    context = {
        'form': form,
        'formset': formset,
        'personal_militar': personal_militar,
    }
    
    return render(request, 'tpe_app/registrar_sumario.html', context)


@rol_requerido('ADMINISTRATIVO')
def agendar_sumario(request):
    """Formulario para agendar un sumario (asignar abogado)"""

    if request.method == 'POST':
        form = AgendarSumarioForm(request.POST)

        if form.is_valid():
            sumario = form.cleaned_data['sumario']
            abogado = form.cleaned_data['abogado']
            fecha_agenda = form.cleaned_data['fecha_agenda']

            try:
                with transaction.atomic():
                    # Actualizar el sumario
                    sumario.SIM_ESTADO = 'PROCESO_EN_EL_TPE'
                    sumario.SIM_FASE = 'EN_DICTAMEN_1RA'  # ✅ NUEVO: fase detallada
                    sumario.save()
                    sumario.abogados.set([abogado])

                    # ✅ NUEVO v3.1: Registrar custodia automática (Admin1 entrega al abogado)
                    CustodiaSIM.objects.create(
                        sim=sumario,
                        tipo_custodio='ABOG_ASESOR',
                        abog=abogado,
                        usuario=request.user,
                        observacion='Entregado al agendar sumario (Admin1)'
                    )

                    messages.success(
                        request,
                        f'✅ Sumario {sumario.SIM_COD} agendado para {abogado} '
                        f'el {fecha_agenda.strftime("%d/%m/%Y")}'
                    )
            except Exception as exc:
                messages.error(request, f'❌ Error al agendar: {exc}')
                return redirect('administrativo_dashboard')

            return redirect('administrativo_dashboard')
    else:
        initial = {}
        sim_id = request.GET.get('sim')
        if sim_id:
            initial['sumario'] = sim_id
        form = AgendarSumarioForm(initial=initial)
    
    context = {
        'form': form,
        'sumarios_pendientes': SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True).count(),
    }
    
    return render(request, 'tpe_app/agendar_sumario.html', context)

@rol_requerido('ADMINISTRATIVO')
def registrar_rr(request):
    """Formulario para registrar un Recurso de Reconsideración (RR)"""
    if request.method == 'POST':
        form = RegistrarRRForm(request.POST)
        if form.is_valid():
            rr = form.save(commit=False)
            rr.sim = rr.res.sim
            rr.save()
            messages.success(request, '✅ Recurso de Reconsideración registrado exitosamente')
            return redirect('administrativo_dashboard')
        else:
            messages.error(request, '❌ Por favor corrija los errores en el formulario')
    else:
        form = RegistrarRRForm()
    
    return render(request, 'tpe_app/registrar_rr.html', {'form': form})

@rol_requerido('ADMINISTRATIVO')
def agendar_rr(request):
    """Formulario para agendar un Recurso de Reconsideración (RR)"""
    if request.method == 'POST':
        form = AgendarRRForm(request.POST)
        if form.is_valid():
            rr = form.cleaned_data['rr']
            abogado = form.cleaned_data['abogado']
            fecha_agenda = form.cleaned_data['fecha_agenda']
            
            rr.abog = abogado
            rr.save()
            
            messages.success(
                request,
                f'✅ RR asignado para el abogado {abogado} el {fecha_agenda.strftime("%d/%m/%Y")}'
            )
            return redirect('administrativo_dashboard')
    else:
        initial = {}
        rr_id = request.GET.get('rr')
        if rr_id:
            initial['rr'] = rr_id
        form = AgendarRRForm(initial=initial)
        
    context = {
        'form': form,
        'rr_pendientes': RR.objects.filter(abog__isnull=True).count(),
    }
    return render(request, 'tpe_app/agendar_rr.html', context)

