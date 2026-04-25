# tpe_app/views/admin1_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, timedelta
import calendar
import json
from ..decorators import rol_requerido
from ..models import SIM, PM, ABOG, PM_SIM, ABOG_SIM, CustodiaSIM, AGENDA, DICTAMEN, Resolucion, AUTOTPE
from ..models import get_pendientes_ejecutoria
from ..forms import SIMForm, PMSIMFormSet, AgendarSumarioForm, RegistrarRRForm, AgendarRRForm, AgendaForm, AgendaResultadoForm, GestionarAbogadosSIMForm


@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR', 'ADMINISTRATIVO')
def admin1_dashboard(request):
    """Dashboard específico para ADMIN1_AGENDADOR - Gestión de agendas y sumarios"""

    perfil = request.user.perfilusuario

    # Si es Admin2, redirigir a su dashboard específico
    if perfil.rol == 'ADMIN2_ARCHIVO':
        return redirect('admin2_dashboard')

    # Si es Admin3, redirigir a su dashboard específico
    if perfil.rol == 'ADMIN3_NOTIFICADOR':
        return redirect('admin3_dashboard')

    # Si no, es Admin1 o ADMINISTRATIVO - mostrar dashboard
    query = (request.GET.get('q') or '').strip()

    filtros_q = Q()
    if query:
        filtros_q = (
            Q(SIM_COD__icontains=query) |
            Q(SIM_RESUM__icontains=query) |
            Q(SIM_OBJETO__icontains=query) |
            Q(militares__PM_PATERNO__icontains=query) |
            Q(militares__PM_MATERNO__icontains=query) |
            Q(militares__PM_NOMBRE__icontains=query)
        )

    # Sumarios recientes para referencia
    sumarios_recientes = (
        SIM.objects.prefetch_related('abogados', 'militares')
        .filter(filtros_q)
        .order_by('-SIM_FECREG')[:20]
    )

    # Sumarios en proceso (con abogado asignado) para gestión de abogados
    sumarios_en_proceso = (
        SIM.objects.filter(SIM_ESTADO='PROCESO_EN_EL_TPE')
        .prefetch_related('abogados', 'militares')
        .filter(filtros_q)
        .order_by('-SIM_FECING')[:30]
    )

    # Sumarios para agenda (sin abogado asignado - ignorando solicitudes)
    sumarios_sin_asignar = (
        SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True)
        .exclude(SIM_TIPO__startswith='SOLICITUD')
        .prefetch_related('militares')
        .filter(filtros_q)
        .distinct()
        .order_by('-SIM_FECING')
    )

    # Solicitudes para agendar
    solicitudes_sin_asignar = (
        SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True, SIM_TIPO__startswith='SOLICITUD')
        .prefetch_related('militares')
        .filter(filtros_q)
        .distinct()
        .order_by('-SIM_FECING')
    )

    # RR por agendar — calcular fecha límite 25 días y color de alerta
    rr_sin_asignar = list(
        Resolucion.objects.filter(RES_INSTANCIA='RECONSIDERACION', abog__isnull=True)
        .select_related('sim', 'resolucion_origen')
        .order_by('-RES_FECPRESEN')
    )
    hoy = date.today()
    for rr in rr_sin_asignar:
        # Compat de template (antes exponían .res y .RR_FECPRESEN)
        rr.res = rr.resolucion_origen
        rr.RR_FECPRESEN = rr.RES_FECPRESEN
        if rr.RES_FECPRESEN:
            rr.fecha_limite_25 = rr.RES_FECPRESEN + timedelta(days=25)
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

    # Pendientes de Auto de Ejecutoria (solo el conteo para la alerta)
    por_res_ej, por_rr_ej = get_pendientes_ejecutoria()

    # Documentos pendientes de notificar (RES y RR)
    res_sin_notificar = Resolucion.objects.filter(
        RES_INSTANCIA='PRIMERA', RES_FECNOT__isnull=True
    ).count()
    rr_sin_notificar = Resolucion.objects.filter(
        RES_INSTANCIA='RECONSIDERACION', RES_FECNOT__isnull=True
    ).count()
    total_sin_notificar = res_sin_notificar + rr_sin_notificar

    # Ejecutorias notificadas pendientes de ordenar archivo a SPRODA
    # Mostrar todos los Autos de Ejecutoria notificados que no hayan sido archivados
    ejecutorias_notificadas = (
        AUTOTPE.objects.filter(
            TPE_TIPO='AUTO_EJECUTORIA',
            TPE_FECNOT__isnull=False,
        )
        .exclude(sim__SIM_FASE__in=['PENDIENTE_ARCHIVO', 'CONCLUIDO'])
        .select_related('sim', 'pm', 'resolucion')
        .prefetch_related('sim__militares')
        .order_by('-TPE_FECNOT')
    )

    # Agendas realizadas para marcar en el calendario del sidebar
    agendas_realizadas = AGENDA.objects.filter(
        AG_ESTADO='REALIZADA', AG_FECREAL__isnull=False
    ).values_list('AG_FECREAL', flat=True).order_by('AG_FECREAL')

    # Formatear fechas de agendas realizadas para el JavaScript (JSON válido)
    agendas_dict = {}
    for fecha in agendas_realizadas:
        if fecha:
            agendas_dict[fecha.isoformat()] = True
    agendas_por_fecha = json.dumps(agendas_dict)

    context = {
        'query': query,
        'sumarios_recientes': sumarios_recientes,
        'sumarios_sin_asignar': sumarios_sin_asignar,
        'total_sin_asignar': sumarios_sin_asignar.count(),
        'solicitudes_sin_asignar': solicitudes_sin_asignar,
        'total_solicitudes_sin_asignar': solicitudes_sin_asignar.count(),
        'rr_sin_asignar': rr_sin_asignar,
        'total_rr_sin_asignar': len(rr_sin_asignar),
        'total_pendientes_ejecutoria': len(por_res_ej) + len(por_rr_ej),
        'sumarios_en_proceso': sumarios_en_proceso,
        'total_sin_notificar': total_sin_notificar,
        'agendas_por_fecha': agendas_por_fecha,
        'ejecutorias_notificadas': ejecutorias_notificadas,
        'total_ejecutorias_notificadas': ejecutorias_notificadas.count(),
    }

    return render(request, 'tpe_app/admin1/admin1_dashboard.html', context)


@rol_requerido('ADMIN2_ARCHIVO', 'MASTER', 'ADMINISTRADOR')
def registrar_sumario(request):
    """Formulario para registrar un nuevo sumario con militares"""

    if request.method == 'POST':
        form = SIMForm(request.POST)
        formset = PMSIMFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Guardar el sumario
                    sumario = form.save(commit=False)
                    sumario.SIM_ESTADO = 'PARA_AGENDA'  # Estado inicial
                    sumario.save()

                    # Crear custodia inicial: Admin2 es custodio desde que ingresa el SIM
                    CustodiaSIM.objects.create(
                        sim=sumario,
                        tipo_custodio='ADMIN2_ARCHIVO',
                        usuario=request.user,
                        motivo='AGENDA',
                    )

                    # Guardar los militares investigados
                    formset.instance = sumario

                    for i, inline_form in enumerate(formset):
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
                                        PM_ESPEC=pm_data.get('PM_ESPEC'),
                                        PM_NOMBRE=pm_data.get('PM_NOMBRE'),
                                        PM_PATERNO=pm_data.get('PM_PATERNO'),
                                        PM_MATERNO=pm_data.get('PM_MATERNO'),
                                        PM_ESTADO='ACTIVO',
                                    )
                                else:
                                    # Actualizar especialidad si ya existe
                                    if pm_data.get('PM_ESPEC'):
                                        pm.PM_ESPEC = pm_data['PM_ESPEC']
                                        pm.save(update_fields=['PM_ESPEC'])

                            # Guardar foto si se subió para este militar
                            foto = request.FILES.get(f'pm_sim_set-{i}-PM_FOTO')
                            if foto and pm:
                                if pm.PM_FOTO:
                                    pm.PM_FOTO.delete(save=False)
                                pm.PM_FOTO = foto
                                pm.save(update_fields=['PM_FOTO'])

                            if pm:
                                PM_SIM.objects.get_or_create(sim=sumario, pm=pm)

                    messages.success(
                        request,
                        f'✅ Sumario {sumario.SIM_COD} registrado exitosamente'
                    )
                    return redirect('admin1_dashboard')

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

    return render(request, 'tpe_app/admin1/registrar_sumario.html', context)


@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def agendar_sumario(request):
    """Formulario para agendar un sumario a una agenda existente"""

    if request.method == 'POST':
        form = AgendarSumarioForm(request.POST)

        if form.is_valid():
            agenda = form.cleaned_data['agenda']
            sumario = form.cleaned_data['sumario']
            abogados = form.cleaned_data['abogados']

            try:
                with transaction.atomic():
                    # Actualizar el sumario
                    sumario.SIM_ESTADO = 'PROCESO_EN_EL_TPE'
                    sumario.SIM_FASE = 'EN_DICTAMEN_1RA'
                    sumario.save()

                    # Crear ABOG_SIM: el primero es responsable de la carpeta
                    abogados_list = list(abogados)
                    for i, abog in enumerate(abogados_list):
                        ABOG_SIM.objects.create(
                            sim=sumario,
                            abog=abog,
                            es_responsable=(i == 0),
                        )

                    nombres = ", ".join(str(a) for a in abogados)
                    messages.success(
                        request,
                        f'✅ Sumario {sumario.SIM_COD} agendado en agenda {agenda.AG_NUM} '
                        f'con abogado(s): {nombres} — {agenda.AG_FECPROG.strftime("%d/%m/%Y")}. '
                        f'Admin2 debe entregar la carpeta.'
                    )
            except Exception as exc:
                messages.error(request, f'❌ Error al agendar: {exc}')
                return redirect('admin1_dashboard')

            return redirect('admin1_dashboard')
    else:
        initial = {}
        sim_id = request.GET.get('sim')
        if sim_id:
            initial['sumario'] = sim_id
        form = AgendarSumarioForm(initial=initial)

    context = {
        'form': form,
        'sumarios_pendientes': SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True).count(),
        'agendas_programadas': AGENDA.objects.filter(AG_ESTADO='PROGRAMADA').count(),
    }

    return render(request, 'tpe_app/admin1/agendar_sumario.html', context)

@rol_requerido('ADMIN2_ARCHIVO', 'MASTER', 'ADMINISTRADOR')
def registrar_rr(request):
    """Formulario para registrar un Recurso de Reconsideración (Resolucion RECONSIDERACION)"""
    if request.method == 'POST':
        form = RegistrarRRForm(request.POST)
        if form.is_valid():
            rr = form.save(commit=False)
            # La instancia se fija explícitamente
            rr.RES_INSTANCIA = 'RECONSIDERACION'
            # Heredar sim y pm de la resolución origen
            rr.sim = rr.resolucion_origen.sim
            rr.pm = rr.resolucion_origen.pm or rr.sim.militares.first()
            # Número se asigna al momento del fallo; por ahora vacío
            if not rr.RES_NUM:
                rr.RES_NUM = ''
            rr.save()

            # Crear custodia inicial: Admin2 es custodio del RR desde que se registra
            CustodiaSIM.objects.create(
                sim=rr.sim,
                tipo_custodio='ADMIN2_ARCHIVO',
                usuario=request.user,
                motivo='AGENDA',
            )

            messages.success(request, '✅ Recurso de Reconsideración registrado exitosamente. Ahora agendar con un abogado.')
            return redirect(f"{reverse('agendar_rr')}?rr={rr.id}")
        else:
            messages.error(request, '❌ Por favor corrija los errores en el formulario')
    else:
        form = RegistrarRRForm()

    return render(request, 'tpe_app/admin1/registrar_rr.html', {'form': form})

@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def agendar_rr(request):
    """Formulario para agendar un Recurso de Reconsideración (Resolucion RECONSIDERACION)"""
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
                f'✅ RR asignado para el abogado {abogado} el {fecha_agenda.strftime("%d/%m/%Y")}. Admin2 debe entregar la carpeta.'
            )
            return redirect('admin1_dashboard')
    else:
        initial = {}
        rr_id = request.GET.get('rr')
        if rr_id:
            initial['rr'] = rr_id
        form = AgendarRRForm(initial=initial)

    context = {
        'form': form,
        'rr_pendientes': Resolucion.objects.filter(
            RES_INSTANCIA='RECONSIDERACION', abog__isnull=True
        ).count(),
    }
    return render(request, 'tpe_app/admin1/agendar_rr.html', context)


# ============================================================
# Gestión de Abogados asignados a un SIM
# ============================================================

@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def gestionar_abogados_sim(request, sim_id):
    """Agregar o quitar abogados de un sumario ya agendado, elegir responsable"""
    sim = get_object_or_404(SIM, pk=sim_id)

    if request.method == 'POST':
        form = GestionarAbogadosSIMForm(request.POST)
        if form.is_valid():
            nuevos_abogados = set(form.cleaned_data['abogados'].values_list('pk', flat=True))
            responsable_id = request.POST.get('responsable')

            with transaction.atomic():
                # Borrar asignaciones anteriores y recrear
                ABOG_SIM.objects.filter(sim=sim).delete()
                for abog_pk in nuevos_abogados:
                    ABOG_SIM.objects.create(
                        sim=sim,
                        abog_id=abog_pk,
                        es_responsable=(str(abog_pk) == responsable_id),
                    )

            nombres = ", ".join(str(a) for a in form.cleaned_data['abogados'])
            messages.success(request, f'✅ Abogados del sumario {sim.SIM_COD} actualizados: {nombres}')
            return redirect('gestionar_abogados_sim', sim_id=sim.pk)
    else:
        form = GestionarAbogadosSIMForm(initial={'abogados': sim.abogados.all()})

    abogados_actuales = ABOG_SIM.objects.filter(sim=sim).select_related('abog')
    responsable_actual = ABOG_SIM.objects.filter(sim=sim, es_responsable=True).first()
    investigados = sim.militares.all()

    context = {
        'form': form,
        'sim': sim,
        'abogados_actuales': abogados_actuales,
        'responsable_actual': responsable_actual,
        'investigados': investigados,
    }
    return render(request, 'tpe_app/administrativo/gestionar_abogados_sim.html', context)


# ============================================================
# ✅ NUEVO v3.2: Gestión de Agendas (Admin1)
# ============================================================

@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def crear_agenda(request):
    """Admin1 crea una nueva agenda"""

    if request.method == 'POST':
        form = AgendaForm(request.POST)

        if form.is_valid():
            try:
                agenda = form.save()
                messages.success(
                    request,
                    f'✅ Agenda {agenda.AG_NUM} creada para {agenda.AG_FECPROG.strftime("%d/%m/%Y")}'
                )
                return redirect('lista_agendas')
            except Exception as exc:
                messages.error(request, f'❌ Error al crear agenda: {exc}')
    else:
        form = AgendaForm()

    # Obtener mes/año actual para el calendario (permitir navegación con GET params)
    today = date.today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # Agendas ordinarias y extraordinarias del mes actual
    agendas_mes = AGENDA.objects.filter(
        AG_FECPROG__year=year,
        AG_FECPROG__month=month
    ).exclude(AG_ESTADO='CANCELADA')

    # Importar feriados
    from ..models import FERIADOS_2026

    # Mapear nombres de feriados
    nombres_feriados = {
        (1, 23): 'Creación Estado',
        (2, 16): 'Carnaval',
        (2, 17): 'Carnaval',
        (4, 3): 'Viernes Santo',
        (5, 1): 'Día del Trabajo',
        (6, 4): 'Corpus Christi',
        (6, 5): 'Corpus Christi',
        (6, 22): 'Año Nuevo Andino',
        (8, 6): 'Independencia',
        (8, 7): 'Independencia',
        (11, 2): 'Día Difuntos',
        (12, 25): 'Navidad',
    }

    # Construir datos por día
    dias_datos = {}
    for agenda in agendas_mes:
        dia = agenda.AG_FECPROG.day
        if dia not in dias_datos:
            dias_datos[dia] = {'agendas': [], 'feriado': None}
        dias_datos[dia]['agendas'].append({
            'tipo': agenda.AG_TIPO,
            'num': agenda.AG_NUM
        })

    # Agregar feriados del mes
    for feriado in FERIADOS_2026:
        if feriado.year == year and feriado.month == month:
            dia = feriado.day
            if dia not in dias_datos:
                dias_datos[dia] = {'agendas': [], 'feriado': None}
            nombre = nombres_feriados.get((feriado.month, feriado.day), 'Feriado')
            dias_datos[dia]['feriado'] = nombre

    # Generar datos del calendario (comenzando desde lunes)
    calendar.setfirstweekday(calendar.MONDAY)
    mes_calendar = calendar.monthcalendar(year, month)

    # Obtener último día del mes anterior y días del mes siguiente
    if month == 1:
        prev_month_last_day = 31  # diciembre tiene 31 días
    else:
        prev_month_last_day = (date(year, month, 1) - timedelta(days=1)).day

    # Calcular cuántos días se muestran del mes siguiente
    first_week = mes_calendar[0]
    last_week = mes_calendar[-1]
    days_before = first_week.count(0)
    days_after = 7 - (last_week.count(0) + len([d for d in last_week if d != 0]))

    # Calcular mes anterior y siguiente para botones de navegación
    if month == 1:
        prev_month, prev_year = 12, year - 1
        next_month, next_year = 2, year
    elif month == 12:
        prev_month, prev_year = 11, year
        next_month, next_year = 1, year + 1
    else:
        prev_month, prev_year = month - 1, year
        next_month, next_year = month + 1, year

    context = {
        'form': form,
        'dias_datos': dias_datos,
        'mes_calendar': mes_calendar,
        'current_year': year,
        'current_month': month,
        'nombre_mes': ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'][month - 1],
        'prev_month_days': list(range(prev_month_last_day - days_before + 1, prev_month_last_day + 1)),
        'next_month_days': list(range(1, days_after + 1)) if days_after > 0 else [],
        'prev_month_url': f'?year={prev_year}&month={prev_month}',
        'next_month_url': f'?year={next_year}&month={next_month}',
    }
    return render(request, 'tpe_app/admin1/crear_agenda.html', context)


@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def lista_agendas(request):
    """Lista todas las agendas con su estado y opciones de edición"""

    agendas = AGENDA.objects.all().order_by('-AG_FECPROG')

    context = {
        'agendas': agendas,
        'total_programadas': AGENDA.objects.filter(AG_ESTADO='PROGRAMADA').count(),
        'total_realizadas': AGENDA.objects.filter(AG_ESTADO='REALIZADA').count(),
        'total_suspendidas': AGENDA.objects.filter(AG_ESTADO='SUSPENDIDA').count(),
    }

    return render(request, 'tpe_app/admin1/lista_agendas.html', context)


@rol_requerido('ADMIN1_AGENDADOR')
def ver_agenda_detalle(request, ag_id):
    """Ver detalles de una agenda: sumarios y militares involucrados"""

    agenda = get_object_or_404(AGENDA, pk=ag_id)

    # Obtener todos los dictámenes de esta agenda con sus sumarios y militares
    dictamenes = DICTAMEN.objects.filter(agenda=agenda).select_related(
        'sim', 'pm', 'abog'
    ).order_by('sim__id')

    context = {
        'agenda': agenda,
        'dictamenes': dictamenes,
    }

    return render(request, 'tpe_app/admin1/ver_agenda_detalle.html', context)


@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def editar_agenda_resultado(request, ag_id):
    """Admin1 registra el resultado de una agenda (realizada/suspendida/reprogramada)"""

    agenda = get_object_or_404(AGENDA, pk=ag_id)

    if request.method == 'POST':
        form = AgendaResultadoForm(request.POST, instance=agenda)

        if form.is_valid():
            try:
                with transaction.atomic():
                    agenda = form.save()

                    # Determinar mensaje según estado
                    if agenda.AG_ESTADO == 'REALIZADA':
                        msg = f'✅ Agenda {agenda.AG_NUM} registrada como REALIZADA el {agenda.AG_FECREAL.strftime("%d/%m/%Y")}'
                    elif agenda.AG_ESTADO == 'SUSPENDIDA':
                        msg = f'⚠️ Agenda {agenda.AG_NUM} registrada como SUSPENDIDA'
                    else:
                        msg = f'📅 Agenda {agenda.AG_NUM} REPROGRAMADA'

                    messages.success(request, msg)
                    return redirect('lista_agendas')
            except Exception as exc:
                messages.error(request, f'❌ Error: {exc}')
    else:
        form = AgendaResultadoForm(instance=agenda)

    context = {
        'form': form,
        'agenda': agenda,
    }

    return render(request, 'tpe_app/admin1/agenda_resultado.html', context)


@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def admin1_ordenar_ejecutoria(request, res_id):
    """Admin1 ordena a Admin2 que entregue carpeta a abogado de ejecutoria (ABOG2)"""
    res = get_object_or_404(Resolucion, pk=res_id, RES_INSTANCIA='PRIMERA')
    sim = res.sim

    # Validar: ¿ya existe custodia ACTIVA para ejecutoria?
    custodia_existente = CustodiaSIM.objects.filter(
        sim=sim,
        motivo='EJECUTORIA',
        estado='RECIBIDA_CONFORME'
    ).first()

    if custodia_existente:
        messages.warning(
            request,
            f'⚠️ Orden ya creada para {sim.SIM_COD}. Admin2 debe completar la entrega.'
        )
        return redirect('pendientes_ejecutoria')

    # Buscar el abogado ABOG2_AUTOS activo con perfil vinculado
    from django.contrib.auth.models import User
    abog2_user = User.objects.filter(
        perfilusuario__rol='ABOG2_AUTOS',
        perfilusuario__activo=True,
        perfilusuario__abogado__isnull=False
    ).select_related('perfilusuario__abogado').first()

    abog_destino = abog2_user.perfilusuario.abogado if abog2_user else None

    if not abog_destino:
        messages.error(request, '❌ No hay abogado ABOG2_AUTOS activo asignado. Contactar administrador.')
        return redirect('pendientes_ejecutoria')

    # Crear orden (custodia en estado ACTIVA) para Admin2
    try:
        with transaction.atomic():
            CustodiaSIM.objects.create(
                sim=sim,
                tipo_custodio='ADMIN2_ARCHIVO',
                motivo='EJECUTORIA',
                abog_destino=abog_destino,
                estado='RECIBIDA_CONFORME',
                usuario=request.user,
                observacion='Orden: Entregar a Abog. de Autos (Ejecutoria)'
            )
            messages.success(
                request,
                f'✅ Orden creada: {sim.SIM_COD} → Admin2 debe entregar a ABOG2'
            )
    except Exception as exc:
        messages.error(request, f'❌ Error al crear orden: {exc}')

    return redirect('pendientes_ejecutoria')


@rol_requerido('ADMIN2_ARCHIVO', 'MASTER', 'ADMINISTRADOR')
def autocomplete_pm(request):
    """Endpoint para autocompletar datos de PM por CI o Nombre+Paterno+Materno"""
    query_ci = (request.GET.get('ci', '') or '').strip()
    query_nombre = (request.GET.get('nombre', '') or '').strip().upper()
    query_paterno = (request.GET.get('paterno', '') or '').strip().upper()
    query_materno = (request.GET.get('materno', '') or '').strip().upper()

    pm = None

    # PRIORIDAD 1: Buscar por CI
    if query_ci:
        if query_ci.isdigit():
            pm = PM.objects.filter(PM_CI=query_ci).first()

    # PRIORIDAD 2: Buscar por Nombre + Paterno + Materno
    if not pm and query_nombre and query_paterno:
        query = PM.objects.filter(PM_NOMBRE=query_nombre, PM_PATERNO=query_paterno)
        if query_materno:
            query = query.filter(PM_MATERNO=query_materno)
        pm = query.first()

    if pm:
        return JsonResponse({
            'encontrado': True,
            'pm_id': pm.pm_id,
            'PM_CI': str(pm.PM_CI) if pm.PM_CI else '',
            'PM_NOMBRE': pm.PM_NOMBRE,
            'PM_PATERNO': pm.PM_PATERNO,
            'PM_MATERNO': pm.PM_MATERNO or '',
            'PM_GRADO': pm.PM_GRADO or '',
            'PM_ARMA': pm.PM_ARMA or '',
            'PM_ESCALAFON': pm.PM_ESCALAFON or '',
            'PM_ESPEC': pm.PM_ESPEC or '',
            'PM_FOTO': pm.PM_FOTO.url if pm.PM_FOTO else '',
        })
    else:
        return JsonResponse({'encontrado': False})


# ============================================================
# ADMIN1: Ordenar Archivo Final a SPRODA
# ============================================================

@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def admin1_ordenar_archivo_sproda(request, sim_id):
    """Admin1 ordena a Admin2 realizar el archivo final del SIM a SPRODA.
    Solo aplica a SIMs con ejecutoria notificada (EJECUTORIA_NOTIFICADA)."""

    sim = get_object_or_404(SIM, pk=sim_id)

    if sim.SIM_FASE != 'EJECUTORIA_NOTIFICADA':
        messages.error(request, "Este sumario no está en fase de ejecutoria notificada.")
        return redirect('admin1_dashboard')

    if request.method == 'POST':
        sim.SIM_FASE = 'PENDIENTE_ARCHIVO'
        sim.save()
        messages.success(
            request,
            f"✅ Archivo SPRODA ordenado para SIM {sim.SIM_COD}. Admin2 recibirá la instrucción."
        )
        return redirect('admin1_dashboard')

    # Obtener el Auto de Ejecutoria asociado
    auto_ej = AUTOTPE.objects.filter(
        sim=sim, TPE_TIPO='AUTO_EJECUTORIA', TPE_FECNOT__isnull=False
    ).order_by('-TPE_FEC').first()

    return render(request, 'tpe_app/admin1/ordenar_archivo_sproda.html', {
        'sim': sim,
        'auto': auto_ej,
        'militares': sim.militares.all(),
    })
