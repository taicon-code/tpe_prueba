# tpe_app/views/admin1_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Exists, OuterRef
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import date, timedelta
import calendar
from ..decorators import rol_requerido
from ..models import SIM, PM, PM_SIM, ABOG_SIM, CustodiaSIM, AGENDA, DICTAMEN, Resolucion, AUTOTPE, ApelacionTSP, DocumentoRecurrente
from ..models import get_pendientes_ejecutoria
from ..forms import SIMForm, PMSIMFormSet, AgendarSumarioForm, AgendarRRForm, AgendaForm, AgendaResultadoForm, GestionarAbogadosSIMForm, SIMInstitucionalForm, ResolucionInstitucionalForm, AutoInstitucionalForm


@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def admin1_dashboard(request):
    """Dashboard específico para ADMIN1_AGENDADOR - Gestión de agendas y sumarios"""

    perfil = request.perfil

    # Si es Admin2, redirigir a su dashboard específico
    if perfil.rol == 'ADMIN2_ARCHIVO':
        return redirect('admin2_dashboard')

    # Si es Admin3, redirigir a su dashboard específico
    if perfil.rol == 'ADMIN3_NOTIFICADOR':
        return redirect('admin3_dashboard')

    # Si no, es Admin1 — mostrar dashboard
    query = (request.GET.get('q') or '').strip()

    filtros_q = Q()
    if query:
        filtros_q = (
            Q(codigo__icontains=query) |
            Q(resumen__icontains=query) |
            Q(objeto__icontains=query) |
            Q(militares__paterno__icontains=query) |
            Q(militares__materno__icontains=query) |
            Q(militares__nombre__icontains=query)
        )

    # Sumarios recientes para referencia
    sumarios_recientes = (
        SIM.objects.prefetch_related('abogados', 'militares')
        .filter(filtros_q)
        .order_by('-fecha_registro')[:20]
    )

    # Sumarios en proceso (con abogado asignado) para gestión de abogados
    sumarios_en_proceso = (
        SIM.objects.filter(estado='PROCESO_EN_EL_TPE')
        .prefetch_related('abogados', 'militares')
        .filter(filtros_q)
        .order_by('-fecha_ingreso')[:30]
    )

    # Sumarios para agenda (sin abogado asignado - ignorando solicitudes)
    sumarios_sin_asignar_qs = (
        SIM.objects.filter(estado='PARA_AGENDA', abogados__isnull=True)
        .exclude(tipo__startswith='SOLICITUD')
        .prefetch_related('militares')
        .filter(filtros_q)
        .distinct()
        .order_by('-fecha_ingreso')
    )
    paginator_sumarios = Paginator(sumarios_sin_asignar_qs, 15)  # 15 por página
    page_sumarios = request.GET.get('page_sumarios', 1)
    try:
        sumarios_sin_asignar = paginator_sumarios.page(page_sumarios)
    except (PageNotAnInteger, EmptyPage):
        sumarios_sin_asignar = paginator_sumarios.page(1)

    # Solicitudes para agendar
    solicitudes_sin_asignar_qs = (
        SIM.objects.filter(estado='PARA_AGENDA', abogados__isnull=True, tipo__startswith='SOLICITUD')
        .prefetch_related('militares')
        .filter(filtros_q)
        .distinct()
        .order_by('-fecha_ingreso')
    )
    paginator_solicitudes = Paginator(solicitudes_sin_asignar_qs, 15)  # 15 por página
    page_solicitudes = request.GET.get('page_solicitudes', 1)
    try:
        solicitudes_sin_asignar = paginator_solicitudes.page(page_solicitudes)
    except (PageNotAnInteger, EmptyPage):
        solicitudes_sin_asignar = paginator_solicitudes.page(1)

    # RR por agendar — calcular fecha límite 25 días y color de alerta.
    # Se excluyen RRs que ya fueron emitidas (tienen numero Y fecha distinto de vacío/null)
    # y RRs cuyo PM en ese SIM ya tiene documentos más avanzados
    # (AUTO_EJECUTORIA o RAP al TSP), lo que indica que el RR ya fue procesado
    # aunque no se registró el abogado (caso frecuente en datos históricos).
    auto_mas_avanzado = AUTOTPE.objects.filter(sim=OuterRef('sim'), pm=OuterRef('pm'))
    rap_presentado    = ApelacionTSP.objects.filter(
        sim=OuterRef('sim'), pm=OuterRef('pm')
    )
    rr_emitidas = Q(numero__isnull=False, numero__gt='', fecha__isnull=False)
    rr_sin_asignar = list(
        Resolucion.objects.filter(instancia='RECONSIDERACION', abogado__isnull=True)
        .exclude(rr_emitidas)  # Excluir RRs que ya fueron emitidas
        .exclude(Exists(auto_mas_avanzado))
        .exclude(Exists(rap_presentado))
        .select_related('sim', 'resolucion_origen')
        .order_by('-fecha_presentacion')
    )
    hoy = date.today()
    for rr in rr_sin_asignar:
        # Compat de template (antes exponían .res y .RR_FECPRESEN)
        rr.res = rr.resolucion_origen
        rr.RR_FECPRESEN = rr.fecha_presentacion
        if rr.fecha_presentacion:
            rr.fecha_limite_25 = rr.fecha_presentacion + timedelta(days=25)
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
        instancia='PRIMERA', notificacion__isnull=True
    ).count()
    rr_sin_notificar = Resolucion.objects.filter(
        instancia='RECONSIDERACION', notificacion__isnull=True
    ).count()
    total_sin_notificar = res_sin_notificar + rr_sin_notificar

    # RAPs pendientes de ordenar entrega (presentados pero sin orden de custodia)
    from ..models import add_business_days
    from django.utils import timezone
    hoy = timezone.now().date()

    raps_pendientes = ApelacionTSP.objects.filter(
        sim__fase='EN_ESPERA_RAP'
    ).exclude(
        sim__custodias__motivo='APELACION_TSP',
        sim__custodias__fecha_entrega__isnull=True
    ).select_related('sim', 'pm', 'resolucion').distinct().order_by('fecha_presentacion')

    # Agregar información de días transcurridos y alerta
    for rap in raps_pendientes:
        if rap.fecha_presentacion:
            dias_transcurridos = (hoy - rap.fecha_presentacion).days
            rap.dias_transcurridos = dias_transcurridos
            rap.alerta_dias = 'danger' if dias_transcurridos > 1 else ('warning' if dias_transcurridos == 1 else 'success')
        else:
            rap.dias_transcurridos = None
            rap.alerta_dias = 'secondary'

    # Ejecutorias notificadas pendientes de ordenar archivo a SPRODA
    ejecutorias_notificadas = (
        AUTOTPE.objects.filter(
            tipo='AUTO_EJECUTORIA',
            notificacion__isnull=False,
        )
        .exclude(sim__fase__in=['PENDIENTE_ARCHIVO', 'CONCLUIDO'])
        .select_related('sim', 'pm', 'resolucion', 'notificacion')
        .prefetch_related('sim__militares')
        .order_by('-notificacion__fecha')
    )

    # Documentos del Recurrente sin abogado asignado
    docs_recurrente_sin_abogado = (
        DocumentoRecurrente.objects
        .filter(abogado__isnull=True)
        .select_related('sim', 'pm')
        .order_by('-fecha_ingreso')
    )

    context = {
        'query': query,
        'sumarios_recientes': sumarios_recientes,
        'sumarios_sin_asignar': sumarios_sin_asignar,
        'total_sin_asignar': sumarios_sin_asignar_qs.count(),
        'solicitudes_sin_asignar': solicitudes_sin_asignar,
        'total_solicitudes_sin_asignar': solicitudes_sin_asignar_qs.count(),
        'rr_sin_asignar': rr_sin_asignar,
        'total_rr_sin_asignar': len(rr_sin_asignar),
        'raps_pendientes': raps_pendientes,
        'total_raps_pendientes': raps_pendientes.count(),
        'total_pendientes_ejecutoria': len(por_res_ej) + len(por_rr_ej),
        'sumarios_en_proceso': sumarios_en_proceso,
        'total_sin_notificar': total_sin_notificar,
        'ejecutorias_notificadas': ejecutorias_notificadas,
        'total_ejecutorias_notificadas': ejecutorias_notificadas.count(),
        'sims_institucionales': SIM.objects.filter(tipo='INSTITUCIONAL').prefetch_related('resolucion_set', 'autotpe_set').order_by('-fecha_ingreso'),
        'docs_recurrente_sin_abogado': docs_recurrente_sin_abogado,
        'total_docs_recurrente_sin_abogado': docs_recurrente_sin_abogado.count(),
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
                    sumario.estado = 'PARA_AGENDA'  # Estado inicial
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
                                ci = pm_data.get('ci')
                                if ci:
                                    pm = PM.objects.filter(ci=ci).first()
                                if not pm:
                                    pm = PM.objects.create(
                                        ci=pm_data.get('ci'),
                                        escalafon=pm_data.get('escalafon'),
                                        grado=pm_data.get('grado'),
                                        arma=pm_data.get('arma'),
                                        especialidad=pm_data.get('especialidad'),
                                        nombre=pm_data.get('nombre'),
                                        paterno=pm_data.get('paterno'),
                                        materno=pm_data.get('materno'),
                                        anio_promocion=pm_data.get('anio_promocion'),
                                        no_ascendio=pm_data.get('no_ascendio', False),
                                        estado='ACTIVO',
                                    )
                                else:
                                    # Actualizar campos complementarios si el PM ya existe
                                    update_fields = []
                                    if pm_data.get('especialidad'):
                                        pm.especialidad = pm_data['especialidad']
                                        update_fields.append('especialidad')
                                    if pm_data.get('anio_promocion') and not pm.anio_promocion:
                                        pm.anio_promocion = pm_data['anio_promocion']
                                        update_fields.append('anio_promocion')
                                    if update_fields:
                                        pm.save(update_fields=update_fields)

                            # Guardar foto si se subió para este militar
                            foto = request.FILES.get(f'pm_sim_set-{i}-foto')
                            if foto and pm:
                                if pm.foto:
                                    pm.foto.delete(save=False)
                                pm.foto = foto
                                pm.save(update_fields=['foto'])

                            if pm:
                                PM_SIM.objects.get_or_create(sim=sumario, pm=pm)

                    messages.success(
                        request,
                        f'✅ Sumario {sumario.codigo} registrado exitosamente'
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
    personal_militar = PM.objects.values('ci', 'nombre', 'paterno', 'grado')[:100]

    context = {
        'form': form,
        'formset': formset,
        'personal_militar': personal_militar,
    }

    return render(request, 'tpe_app/admin2/registrar_sumario.html', context)


@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
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
                    sumario.estado = 'PROCESO_EN_EL_TPE'
                    sumario.fase = 'EN_DICTAMEN_1RA'
                    sumario.save()

                    # Crear ABOG_SIM: el primero es responsable de la carpeta
                    abogados_list = list(abogados)
                    for i, abog in enumerate(abogados_list):
                        ABOG_SIM.objects.create(
                            sim=sumario,
                            abogado=abog,
                            agenda=agenda,
                            es_responsable=(i == 0),
                        )

                    # Notificar a ADMIN2: marcar custodia como pendiente de entregar
                    # Solo el abogado responsable (primero) recibe la carpeta física.
                    # Los demás abogados asignados pueden crear dictámenes vía ABOG_SIM sin custodia.
                    abog_responsable = abogados_list[0]
                    custodia_admin2 = CustodiaSIM.objects.filter(
                        sim=sumario,
                        tipo_custodio='ADMIN2_ARCHIVO',
                        fecha_entrega__isnull=True,
                    ).first()
                    if custodia_admin2:
                        custodia_admin2.estado = 'PENDIENTE_CONFIRMACION'
                        custodia_admin2.abogado_destino = abog_responsable
                        custodia_admin2.save()
                    else:
                        CustodiaSIM.objects.create(
                            sim=sumario,
                            tipo_custodio='ADMIN2_ARCHIVO',
                            abogado_destino=abog_responsable,
                            usuario=request.user,
                            motivo='AGENDA',
                            estado='PENDIENTE_CONFIRMACION',
                        )

                    nombres = ", ".join(str(a) for a in abogados)
                    messages.success(
                        request,
                        f'✅ Sumario {sumario.codigo} agendado en agenda {agenda.numero} '
                        f'con abogado(s): {nombres} — {agenda.fecha_prog.strftime("%d/%m/%Y")}. '
                        f'Admin2 debe entregar la carpeta a {abog_responsable.paterno}.'
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
        'sumarios_pendientes': SIM.objects.filter(estado='PARA_AGENDA', abogados__isnull=True).count(),
        'agendas_programadas': AGENDA.objects.filter(estado='PROGRAMADA').count(),
    }

    return render(request, 'tpe_app/admin1/agendar_sumario.html', context)

@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def agendar_rr(request):
    """Formulario para agendar un Recurso de Reconsideración (Resolucion RECONSIDERACION)"""
    if request.method == 'POST':
        form = AgendarRRForm(request.POST)
        if form.is_valid():
            rr = form.cleaned_data['rr']
            abogado = form.cleaned_data['abogado']
            agenda = form.cleaned_data['agenda']

            rr.abogado = abogado
            rr.agenda = agenda
            rr.save()

            sim = rr.sim
            if sim.fase == 'PARA_AGENDA_RR':
                sim.fase = 'EN_DICTAMEN_RR'
                sim.save()

            custodia_admin2 = CustodiaSIM.objects.filter(
                sim=rr.sim,
                tipo_custodio='ADMIN2_ARCHIVO',
                estado='PENDIENTE_CONFIRMACION',
                fecha_entrega__isnull=True,
            ).first()

            if custodia_admin2:
                custodia_admin2.abogado_destino = abogado
                custodia_admin2.save()
            else:
                CustodiaSIM.objects.create(
                    sim=rr.sim,
                    tipo_custodio='ADMIN2_ARCHIVO',
                    abogado_destino=abogado,
                    usuario=request.user,
                    motivo='AGENDA_RR',
                    estado='PENDIENTE_CONFIRMACION',
                )

            fecha_str = agenda.fecha_prog.strftime('%d/%m/%Y') if agenda.fecha_prog else agenda.numero
            messages.success(
                request,
                f'✅ RR asignado al abogado {abogado} en la Agenda {agenda.numero} ({fecha_str}). Admin2 debe entregar la carpeta.'
            )
            return redirect('admin1_dashboard')
    else:
        initial = {}
        rr_id = request.GET.get('rr')
        if rr_id:
            initial['rr'] = rr_id
        form = AgendarRRForm(initial=initial)

    rr_emitidas = Q(numero__isnull=False, numero__gt='', fecha__isnull=False)
    context = {
        'form': form,
        'rr_pendientes': Resolucion.objects.filter(
            instancia='RECONSIDERACION', abogado__isnull=True
        ).exclude(rr_emitidas).exclude(
            Exists(AUTOTPE.objects.filter(sim=OuterRef('sim'), pm=OuterRef('pm')))
        ).exclude(
            Exists(ApelacionTSP.objects.filter(sim=OuterRef('sim'), pm=OuterRef('pm')))
        ).count(),
    }
    return render(request, 'tpe_app/admin1/agendar_rr.html', context)


# ============================================================
# Gestión de Abogados asignados a un SIM
# ============================================================

@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
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
                        abogado_id=abog_pk,
                        es_responsable=(str(abog_pk) == responsable_id),
                    )

            nombres = ", ".join(str(a) for a in form.cleaned_data['abogados'])
            messages.success(request, f'✅ Abogados del sumario {sim.codigo} actualizados: {nombres}')
            return redirect('gestionar_abogados_sim', sim_id=sim.pk)
    else:
        form = GestionarAbogadosSIMForm(initial={'abogados': sim.abogados.all()})

    abogados_actuales = ABOG_SIM.objects.filter(sim=sim).select_related('abogado')
    responsable_actual = ABOG_SIM.objects.filter(sim=sim, es_responsable=True).first()
    investigados = sim.militares.all()

    context = {
        'form': form,
        'sim': sim,
        'abogados_actuales': abogados_actuales,
        'responsable_actual': responsable_actual,
        'investigados': investigados,
    }
    return render(request, 'tpe_app/admin1/gestionar_abogados_sim.html', context)


# ============================================================
# ✅ NUEVO v3.2: Gestión de Agendas (Admin1)
# ============================================================

@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def crear_agenda(request):
    """Admin1 crea una nueva agenda"""

    if request.method == 'POST':
        form = AgendaForm(request.POST)

        if form.is_valid():
            try:
                agenda = form.save()
                messages.success(
                    request,
                    f'✅ Agenda {agenda.numero} creada para {agenda.fecha_prog.strftime("%d/%m/%Y")}'
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
        fecha_prog__year=year,
        fecha_prog__month=month
    ).exclude(estado='CANCELADA')

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
        dia = agenda.fecha_prog.day
        if dia not in dias_datos:
            dias_datos[dia] = {'agendas': [], 'feriado': None}
        dias_datos[dia]['agendas'].append({
            'tipo': agenda.tipo,
            'num': agenda.numero
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


@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def lista_agendas(request):
    """Lista agendas filtradas por gestión (año). Por defecto muestra el año actual."""
    from datetime import date

    anio_actual = date.today().year
    anio_param = request.GET.get('anio', '')
    try:
        anio_sel = int(anio_param)
    except (ValueError, TypeError):
        anio_sel = anio_actual

    # Años disponibles en BD (para el selector)
    anios_disponibles = (
        AGENDA.objects
        .dates('fecha_prog', 'year', order='DESC')
    )
    anios = [d.year for d in anios_disponibles]
    if anio_sel not in anios:
        anio_sel = anios[0] if anios else anio_actual

    qs = AGENDA.objects.filter(fecha_prog__year=anio_sel).order_by('-fecha_prog')

    rol = request.perfil.rol
    if rol == 'ADMIN2_ARCHIVO':
        dashboard_url = 'admin2_dashboard'
    elif rol == 'ADMIN3_NOTIFICADOR':
        dashboard_url = 'admin3_dashboard'
    else:
        dashboard_url = 'admin1_dashboard'

    context = {
        'agendas': qs,
        'anio_sel': anio_sel,
        'anios': anios,
        'total_programadas': qs.filter(estado='PROGRAMADA').count(),
        'total_realizadas': qs.filter(estado='REALIZADA').count(),
        'total_suspendidas': qs.filter(estado='SUSPENDIDA').count(),
        'dashboard_url': dashboard_url,
    }

    return render(request, 'tpe_app/admin1/lista_agendas.html', context)


@rol_requerido('ADMIN1_AGENDADOR')
def ajax_caso_detalles(request, sim_id, ag_id):
    """Retorna detalles de un caso para el modal del dashboard de agenda"""
    from django.http import JsonResponse

    sim = get_object_or_404(SIM, pk=sim_id)
    agenda = get_object_or_404(AGENDA, pk=ag_id)

    # Militares involucrados
    militares = [{
        'grado': m.grado or '',
        'paterno': m.paterno,
        'materno': m.materno,
        'nombre': m.nombre,
    } for m in sim.militares.all()]

    # PRIMERA RESOLUCIÓN
    res_1ra = Resolucion.objects.filter(
        sim=sim, instancia='PRIMERA'
    ).select_related('abogado').first()

    dictamen_1ra = DICTAMEN.objects.filter(
        sim=sim, agenda=agenda
    ).select_related('abogado', 'pm').first()

    primera_resolucion = None
    if res_1ra:
        primera_resolucion = {
            'numero': res_1ra.numero or '—',
            'tipo': res_1ra.get_tipo_display(),
            'fecha': res_1ra.fecha.strftime('%d/%m/%Y') if res_1ra.fecha else '—',
            'abogado': f"{res_1ra.abogado.paterno}" if res_1ra.abogado else '—',
            'dictamen_en_agenda': bool(dictamen_1ra),
            'dictamen_fecha': dictamen_1ra.fecha.strftime('%d/%m/%Y') if dictamen_1ra and dictamen_1ra.fecha else None,
            'conclusión': dictamen_1ra.conclusion if dictamen_1ra else None,
        }

    # RECURSO DE RECONSIDERACIÓN
    rr = Resolucion.objects.filter(
        sim=sim, instancia='RECONSIDERACION'
    ).select_related('abogado', 'dictamen', 'agenda').first()

    recurso_reconsideracion = None
    if rr:
        # Verificar si el DICTAMEN del RR está en esta agenda
        dictamen_rr_en_agenda = rr.dictamen and rr.dictamen.agenda_id == agenda.id if rr.dictamen else False

        recurso_reconsideracion = {
            'numero': rr.numero or '—',
            'fecha_presentacion': rr.fecha_presentacion.strftime('%d/%m/%Y') if rr.fecha_presentacion else '—',
            'fecha_limite': rr.fecha_limite.strftime('%d/%m/%Y') if rr.fecha_limite else '—',
            'fecha_resolucion': rr.fecha.strftime('%d/%m/%Y') if rr.fecha else '—',
            'abogado': f"{rr.abogado.paterno}" if rr.abogado else '—',
            'agendado_en_esta': rr.agenda_id == agenda.id if rr.agenda else False,
            'dictamen_en_esta': dictamen_rr_en_agenda,
        }

    # AUTOS TPE
    autos_leidos = AUTOTPE.objects.filter(
        sim=sim, agenda=agenda
    ).select_related('abogado').order_by('fecha')

    autos = [{
        'numero': a.numero or '—',
        'tipo': a.get_tipo_display(),
        'fecha': a.fecha.strftime('%d/%m/%Y') if a.fecha else '—',
        'abogado': f"{a.abogado.paterno}" if a.abogado else '—',
    } for a in autos_leidos]

    return JsonResponse({
        'codigo': sim.codigo,
        'objeto': sim.objeto or '—',
        'estado': sim.get_estado_display(),
        'fase': sim.get_fase_display(),
        'militares': militares,
        'primera_resolucion': primera_resolucion,
        'recurso_reconsideracion': recurso_reconsideracion,
        'autos': autos,
    })


@rol_requerido('ADMIN1_AGENDADOR')
def ver_agenda_detalle(request, ag_id):
    """Ver detalles de una agenda: sumarios agendados o con dictámenes"""

    agenda = get_object_or_404(AGENDA, pk=ag_id)

    # DICTAMEN es la única fuente confiable de participación en una agenda.
    # ABOG_SIM solo existe en flujo normal; los históricos del Ayudante no lo crean.
    # Las Resoluciones históricas tampoco tienen FK agenda — solo el DICTAMEN lo tiene.
    dictamenes_qs = DICTAMEN.objects.filter(agenda=agenda).select_related(
        'sim', 'pm', 'abogado'
    ).order_by('sim__codigo')

    # SIMs únicos con dictamen en esta agenda, con sus militares y resoluciones/autos
    sim_ids_todos = set(dictamenes_qs.values_list('sim_id', flat=True))
    sims_qs = SIM.objects.filter(id__in=sim_ids_todos).prefetch_related('militares').order_by('codigo')

    # Prefetch resoluciones y autos de esos SIMs para evitar N+1
    res_por_sim = {}
    for r in Resolucion.objects.filter(sim_id__in=sim_ids_todos).select_related('abogado'):
        res_por_sim.setdefault(r.sim_id, {}).setdefault(r.instancia, []).append(r)

    autos_por_sim = {}
    for a in AUTOTPE.objects.filter(sim_id__in=sim_ids_todos).select_related('abogado'):
        autos_por_sim.setdefault(a.sim_id, []).append(a)

    # Construir filas enriquecidas: una por SIM (agrupando dictámenes del mismo SIM)
    casos_agenda = []
    vistos = set()
    for d in dictamenes_qs:
        sid = d.sim_id
        if sid in vistos:
            continue
        vistos.add(sid)
        dictamenes_sim = [x for x in dictamenes_qs if x.sim_id == sid]
        rrs_sim = res_por_sim.get(sid, {}).get('RECONSIDERACION', [])
        casos_agenda.append({
            'sim': d.sim,
            'dictamenes': dictamenes_sim,
            'res_1ra':  res_por_sim.get(sid, {}).get('PRIMERA', []),
            'rrs':      rrs_sim,
            'autos':    autos_por_sim.get(sid, []),
        })

    # Clasificar: si el SIM tiene RRs → sesión de RR; si no → 1ra resolución.
    # Los dictámenes en el histórico se crean para ambas instancias bajo la misma agenda,
    # por lo que la presencia de RRs es la señal definitiva de qué se trató en esta sesión.
    casos_1ra = [c for c in casos_agenda if not c['rrs']]
    casos_rr  = [c for c in casos_agenda if c['rrs']]

    # AUTOS DE EJECUTORIA con FK directa a esta agenda (para la sección de lectura)
    autos_ej_agenda = list(AUTOTPE.objects.filter(
        agenda=agenda, tipo='AUTO_EJECUTORIA'
    ).select_related('sim', 'pm', 'abogado').order_by('sim__codigo'))

    # Otros autos con FK directa a esta agenda
    autos_otros_agenda = list(AUTOTPE.objects.filter(
        agenda=agenda
    ).exclude(tipo='AUTO_EJECUTORIA').select_related('sim', 'pm', 'abogado').order_by('sim__codigo'))

    # Autos disponibles para agregar a la agenda
    autos_disponibles = AUTOTPE.objects.filter(
        agenda__isnull=True, tipo='AUTO_EJECUTORIA'
    ).select_related('sim', 'pm').order_by('sim__codigo')

    context = {
        'agenda': agenda,
        'casos_1ra': casos_1ra,             # solo casos sin RR → card 1ra Resolución
        'casos_rr': casos_rr,               # casos con RR → card Recurso de Reconsideración
        'autos_ej_agenda': autos_ej_agenda,
        'autos_otros_agenda': autos_otros_agenda,
        'autos_disponibles': autos_disponibles,
    }

    return render(request, 'tpe_app/admin1/ver_agenda_detalle.html', context)


@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def quitar_sim_de_agenda(request, ag_id, sim_id):
    """Quita un sumario de la agenda y lo devuelve al estado pendiente de agendar."""
    if request.method != 'POST':
        return redirect('ver_agenda_detalle', ag_id=ag_id)
    agenda = get_object_or_404(AGENDA, pk=ag_id)
    sim = get_object_or_404(SIM, pk=sim_id)

    FASES_PRIMERA_INSTANCIA = {
        'PARA_AGENDA', 'EN_DICTAMEN_1RA', '1RA_RESOLUCION',
        'NOTIFICACION_1RA', 'NOTIFICADO_1RA',
    }
    if sim.fase not in FASES_PRIMERA_INSTANCIA:
        messages.error(
            request,
            f'No se puede quitar {sim.codigo} de la agenda: el sumario ya avanzó a la fase "{sim.get_fase_display()}" (RR o posterior). '
            f'Use la acción correspondiente en el panel de RR.'
        )
        return redirect('ver_agenda_detalle', ag_id=ag_id)

    with transaction.atomic():
        ABOG_SIM.objects.filter(sim=sim, agenda=agenda).delete()
        if not ABOG_SIM.objects.filter(sim=sim).exists():
            sim.estado = 'PARA_AGENDA'
            sim.fase = 'PARA_AGENDA'
            sim.save()
    messages.success(request, f'Sumario {sim.codigo} quitado de la Agenda {agenda.numero}. Vuelve al listado de pendientes.')
    return redirect('ver_agenda_detalle', ag_id=ag_id)


@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def quitar_rr_de_agenda(request, ag_id, rr_id):
    """Quita un RR de la agenda y lo devuelve al estado pendiente de agendar."""
    if request.method != 'POST':
        return redirect('ver_agenda_detalle', ag_id=ag_id)
    agenda = get_object_or_404(AGENDA, pk=ag_id)
    rr = get_object_or_404(Resolucion, pk=rr_id, agenda=agenda, instancia='RECONSIDERACION')
    with transaction.atomic():
        rr.agenda = None
        rr.abogado = None
        rr.save()
        sim = rr.sim
        if sim.fase == 'EN_DICTAMEN_RR':
            sim.fase = 'PARA_AGENDA_RR'
            sim.save()
    messages.success(request, f'RR del sumario {rr.sim.codigo} quitado de la Agenda {agenda.numero}. Vuelve al listado de pendientes.')
    return redirect('ver_agenda_detalle', ag_id=ag_id)


@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def agregar_auto_a_agenda(request, ag_id):
    """Vincula un Auto de Ejecutoria existente a esta agenda para su lectura."""
    if request.method != 'POST':
        return redirect('ver_agenda_detalle', ag_id=ag_id)
    agenda = get_object_or_404(AGENDA, pk=ag_id)
    auto_id = request.POST.get('auto_id')
    if not auto_id:
        messages.error(request, 'Seleccione un auto de ejecutoria.')
        return redirect('ver_agenda_detalle', ag_id=ag_id)
    auto = get_object_or_404(AUTOTPE, pk=auto_id, agenda__isnull=True)
    auto.agenda = agenda
    auto.save()
    messages.success(request, f'Auto {auto.numero or "S/N"} del sumario {auto.sim.codigo} agregado a la Agenda {agenda.numero}.')
    return redirect('ver_agenda_detalle', ag_id=ag_id)


@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def quitar_auto_de_agenda(request, ag_id, auto_id):
    """Desvincula un Auto TPE de esta agenda."""
    if request.method != 'POST':
        return redirect('ver_agenda_detalle', ag_id=ag_id)
    agenda = get_object_or_404(AGENDA, pk=ag_id)
    auto = get_object_or_404(AUTOTPE, pk=auto_id, agenda=agenda)
    auto.agenda = None
    auto.save()
    messages.success(request, f'Auto del sumario {auto.sim.codigo} quitado de la Agenda {agenda.numero}.')
    return redirect('ver_agenda_detalle', ag_id=ag_id)


@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def agenda_detalle_pdf(request, ag_id):
    """Genera PDF de la agenda con los casos que se tratarán."""
    from io import BytesIO
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from django.http import HttpResponse

    agenda = get_object_or_404(AGENDA, pk=ag_id)

    # Misma lógica que ver_agenda_detalle: DICTAMEN como fuente única de participación
    dictamenes_qs = DICTAMEN.objects.filter(agenda=agenda).select_related(
        'sim', 'pm', 'abogado'
    ).order_by('sim__codigo')

    sim_ids_todos = set(dictamenes_qs.values_list('sim_id', flat=True))

    res_por_sim = {}
    for r in Resolucion.objects.filter(sim_id__in=sim_ids_todos).select_related('abogado', 'pm'):
        res_por_sim.setdefault(r.sim_id, {}).setdefault(r.instancia, []).append(r)

    autos_por_sim = {}
    for a in AUTOTPE.objects.filter(sim_id__in=sim_ids_todos).select_related('abogado', 'pm'):
        autos_por_sim.setdefault(a.sim_id, []).append(a)

    casos_agenda = []
    vistos = set()
    for d in dictamenes_qs:
        sid = d.sim_id
        if sid in vistos:
            continue
        vistos.add(sid)
        dictamenes_sim = [x for x in dictamenes_qs if x.sim_id == sid]
        rrs_sim = res_por_sim.get(sid, {}).get('RECONSIDERACION', [])
        casos_agenda.append({
            'sim': d.sim,
            'dictamenes': dictamenes_sim,
            'res_1ra': res_por_sim.get(sid, {}).get('PRIMERA', []),
            'rrs': rrs_sim,
        })

    casos_1ra = [c for c in casos_agenda if not c['rrs']]
    casos_rr  = [c for c in casos_agenda if c['rrs']]

    autos = AUTOTPE.objects.filter(agenda=agenda).select_related('sim', 'pm', 'abogado').order_by('sim__codigo')

    buffer = BytesIO()
    page_w, page_h = letter
    margin = 0.65 * inch

    styles = getSampleStyleSheet()
    s_titulo = ParagraphStyle('titulo', parent=styles['Normal'], fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=2)
    s_sub = ParagraphStyle('sub', parent=styles['Normal'], fontSize=10, fontName='Helvetica', alignment=TA_CENTER, spaceAfter=8)
    s_seccion = ParagraphStyle('sec', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4)
    s_cel = ParagraphStyle('cel', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', leading=10)
    s_cel_b = ParagraphStyle('celb', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', leading=10)

    from datetime import datetime
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    def _pie(canv, doc):
        canv.saveState()
        canv.setFont('Helvetica', 6.5)
        canv.setFillColor(colors.grey)
        canv.drawCentredString(page_w / 2, 0.35 * inch, f"Impreso: {fecha_hoy}  |  Pág. {doc.page}")
        canv.restoreState()

    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=0.5 * inch, bottomMargin=0.6 * inch)
    usable_w = page_w - 2 * margin
    story = []

    tipo_label = agenda.get_tipo_display() if hasattr(agenda, 'get_tipo_display') else agenda.tipo
    fecha_prog = agenda.fecha_prog.strftime('%d/%m/%Y') if agenda.fecha_prog else '—'
    fecha_real = agenda.fecha_real.strftime('%d/%m/%Y') if agenda.fecha_real else '—'

    story.append(Paragraph("TRIBUNAL DE PERSONAL DEL EJÉRCITO", s_titulo))
    story.append(Paragraph(f"AGENDA N° {agenda.numero}  —  {tipo_label}", s_sub))
    story.append(Paragraph(f"Fecha Programada: {fecha_prog}   |   Fecha Realizada: {fecha_real}   |   Estado: {agenda.get_estado_display()}", s_sub))
    story.append(Spacer(1, 8))

    header_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ])

    # Tabla: Primera Resolución
    story.append(Paragraph(f"PRIMERA RESOLUCIÓN  ({len(casos_1ra)} sumario(s))", s_seccion))
    if casos_1ra:
        cols_w = [usable_w * p for p in [0.12, 0.30, 0.26, 0.18, 0.14]]
        data = [[
            Paragraph('<b>N° SIM</b>', s_cel_b),
            Paragraph('<b>Objeto del Caso</b>', s_cel_b),
            Paragraph('<b>Militar(es)</b>', s_cel_b),
            Paragraph('<b>Abogado / Dictamen</b>', s_cel_b),
            Paragraph('<b>Resolución</b>', s_cel_b),
        ]]
        for caso in casos_1ra:
            sim = caso['sim']
            # Militares: usar pm del dictamen; fallback a militares del SIM
            mils_txt_parts = []
            for d in caso['dictamenes']:
                if d.pm:
                    mils_txt_parts.append(
                        f"{d.pm.grado or ''} {d.pm.paterno} {d.pm.materno}, {d.pm.nombre}".strip()
                    )
            if not mils_txt_parts:
                mils_txt_parts = [
                    f"{m.grado or ''} {m.paterno} {m.materno}, {m.nombre}".strip()
                    for m in sim.militares.all()
                ]
            militares_txt = '\n'.join(mils_txt_parts) or '—'

            # Abogado y dictamen: uno por línea si hay varios
            abog_dict_txt = '\n'.join(
                f"{d.abogado.grado or ''} {d.abogado.paterno}  [Dict. {d.numero or 'S/N'}]".strip()
                for d in caso['dictamenes'] if d.abogado
            ) or '—'

            res_txt = ' / '.join(r.numero for r in caso['res_1ra'] if r.numero) or '—'

            data.append([
                Paragraph(sim.codigo or '—', s_cel_b),
                Paragraph(sim.objeto or '—', s_cel),
                Paragraph(militares_txt, s_cel),
                Paragraph(abog_dict_txt, s_cel),
                Paragraph(res_txt, s_cel),
            ])
        t = Table(data, colWidths=cols_w, repeatRows=1)
        t.setStyle(header_style)
        story.append(t)
    else:
        story.append(Paragraph("Sin sumarios de primera instancia.", s_cel))

    # Tabla: Recurso de Reconsideración
    story.append(Paragraph(f"RECURSO DE RECONSIDERACIÓN  ({len(casos_rr)} sumario(s))", s_seccion))
    if casos_rr:
        cols_w = [usable_w * p for p in [0.12, 0.28, 0.24, 0.22, 0.14]]
        data = [[
            Paragraph('<b>N° SIM</b>', s_cel_b),
            Paragraph('<b>Objeto del Caso</b>', s_cel_b),
            Paragraph('<b>Militar Recurrente</b>', s_cel_b),
            Paragraph('<b>Abogado del RR</b>', s_cel_b),
            Paragraph('<b>N° RR</b>', s_cel_b),
        ]]
        for caso in casos_rr:
            sim = caso['sim']
            for rr in caso['rrs']:
                mil = '—'
                if rr.pm:
                    mil = f"{rr.pm.grado or ''} {rr.pm.paterno} {rr.pm.materno}, {rr.pm.nombre}".strip()
                abog = f"{rr.abogado.grado or ''} {rr.abogado.paterno}".strip() if rr.abogado else '—'
                fl = rr.fecha_limite.strftime('%d/%m/%Y') if rr.fecha_limite else ''
                abog_txt = abog + (f"\nLímite: {fl}" if fl else '')
                data.append([
                    Paragraph(sim.codigo or '—', s_cel_b),
                    Paragraph(sim.objeto or '—', s_cel),
                    Paragraph(mil, s_cel),
                    Paragraph(abog_txt, s_cel),
                    Paragraph(rr.numero or '—', s_cel),
                ])
        t = Table(data, colWidths=cols_w, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7b2d00')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fdf6f0')]),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Sin recursos de reconsideración.", s_cel))

    # Tabla: Autos vinculados
    if autos.exists():
        story.append(Paragraph(f"AUTOS TPE EN ESTA AGENDA  ({autos.count()})", s_seccion))
        cols_w = [usable_w * p for p in [0.13, 0.10, 0.12, 0.10, 0.30, 0.25]]
        data = [[
            Paragraph('<b>N° SIM</b>', s_cel_b),
            Paragraph('<b>Tipo Auto</b>', s_cel_b),
            Paragraph('<b>N° Auto</b>', s_cel_b),
            Paragraph('<b>Fecha</b>', s_cel_b),
            Paragraph('<b>Militar</b>', s_cel_b),
            Paragraph('<b>Abogado</b>', s_cel_b),
        ]]
        for auto in autos:
            fa = auto.fecha.strftime('%d/%m/%Y') if auto.fecha else '—'
            mil = '—'
            if auto.pm:
                mil = f"{auto.pm.grado or ''} {auto.pm.paterno} {auto.pm.materno}, {auto.pm.nombre}".strip()
            abog = f"{auto.abogado.grado or ''} {auto.abogado.paterno}".strip() if auto.abogado else '—'
            data.append([
                Paragraph(auto.sim.codigo or '—', s_cel_b),
                Paragraph(auto.get_tipo_display() if hasattr(auto, 'get_tipo_display') else auto.tipo or '—', s_cel),
                Paragraph(auto.numero or '—', s_cel),
                Paragraph(fa, s_cel),
                Paragraph(mil, s_cel),
                Paragraph(abog, s_cel),
            ])
        t = Table(data, colWidths=cols_w, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d9488')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdfa')]),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    buffer.seek(0)
    filename = f"Agenda_{agenda.numero.replace('/', '-')}.pdf"
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
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
                    if agenda.estado == 'REALIZADA':
                        msg = f'✅ Agenda {agenda.numero} registrada como REALIZADA el {agenda.fecha_real.strftime("%d/%m/%Y")}'
                    elif agenda.estado == 'SUSPENDIDA':
                        msg = f'⚠️ Agenda {agenda.numero} registrada como SUSPENDIDA'
                    else:
                        msg = f'📅 Agenda {agenda.numero} REPROGRAMADA'

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
    res = get_object_or_404(Resolucion, pk=res_id, instancia='PRIMERA')
    sim = res.sim

    # Validar: ¿ya existe custodia ACTIVA para ejecutoria?
    custodia_existente = CustodiaSIM.objects.filter(
        sim=sim,
        motivo='EJECUTORIA',
        estado__in=['PENDIENTE_CONFIRMACION', 'RECIBIDA_CONFORME']
    ).first()

    if custodia_existente:
        messages.warning(
            request,
            f'⚠️ Orden ya creada para {sim.codigo}. Admin2 debe completar la entrega.'
        )
        return redirect('pendientes_ejecutoria')

    # Buscar el abogado ABOG2_AUTOS activo con perfil vinculado
    from django.contrib.auth.models import User
    abog2_user = User.objects.filter(
        perfilusuario__rol='ABOG2_AUTOS',
        perfilusuario__activo=True,
        perfilusuario__pm__isnull=False
    ).select_related('perfilusuario__pm').first()

    abog_destino = abog2_user.perfilusuario.pm if abog2_user else None

    if not abog_destino:
        messages.error(request, '❌ No hay abogado ABOG2_AUTOS activo asignado. Contactar administrador.')
        return redirect('pendientes_ejecutoria')

    # Crear orden (custodia en estado PENDIENTE_CONFIRMACION) para Admin2
    try:
        with transaction.atomic():
            CustodiaSIM.objects.create(
                sim=sim,
                tipo_custodio='ADMIN2_ARCHIVO',
                motivo='EJECUTORIA',
                abogado_destino=abog_destino,
                estado='PENDIENTE_CONFIRMACION',
                usuario=request.user,
                observacion='Orden: Entregar a Abog. de Autos (Ejecutoria)'
            )
            messages.success(
                request,
                f'✅ Orden creada: {sim.codigo} → Admin2 debe entregar a ABOG2'
            )
    except Exception as exc:
        messages.error(request, f'❌ Error al crear orden: {exc}')

    return redirect('pendientes_ejecutoria')


@rol_requerido('ADMIN1_AGENDADOR', 'ADMINISTRADOR', 'MASTER')
def admin1_asignar_doc_recurrente(request, doc_id):
    """Admin1 asigna un Documento del Recurrente al abogado ABOG2_AUTOS y crea
    la orden de custodia (Admin2 deberá entregar los antecedentes)."""

    doc = get_object_or_404(DocumentoRecurrente, pk=doc_id)
    sim = doc.sim

    if doc.abogado_id:
        messages.warning(request, f'⚠️ El memorial NTD {doc.ntd} ya fue asignado.')
        return redirect('admin1_dashboard')

    # Buscar ABOG2_AUTOS activo (mismo patrón que admin1_ordenar_ejecutoria)
    from django.contrib.auth.models import User
    abog2_user = User.objects.filter(
        perfilusuario__rol='ABOG2_AUTOS',
        perfilusuario__activo=True,
        perfilusuario__pm__isnull=False
    ).select_related('perfilusuario__pm').first()

    abog_destino = abog2_user.perfilusuario.pm if abog2_user else None

    if not abog_destino:
        messages.error(request, '❌ No hay abogado ABOG2_AUTOS activo asignado. Contactar administrador.')
        return redirect('admin1_dashboard')

    try:
        with transaction.atomic():
            doc.abogado = abog_destino
            doc.save()

            CustodiaSIM.objects.create(
                sim=sim,
                tipo_custodio='ADMIN2_ARCHIVO',
                motivo='REVISION',
                abogado_destino=abog_destino,
                estado='PENDIENTE_CONFIRMACION',
                usuario=request.user,
                observacion=f'Entregar a ABOG2 para responder memorial de {doc.get_tipo_display()} NTD {doc.ntd}',
            )
            messages.success(
                request,
                f'✅ Memorial de {doc.get_tipo_display()} NTD {doc.ntd} asignado a {abog_destino}. '
                f'Admin2 debe entregar antecedentes.'
            )
    except Exception as exc:
        messages.error(request, f'❌ Error al asignar documento: {exc}')

    return redirect('admin1_dashboard')


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
            pm = PM.objects.filter(ci=query_ci).first()

    # PRIORIDAD 2: Buscar por Nombre + Paterno + Materno
    if not pm and query_nombre and query_paterno:
        query = PM.objects.filter(nombre=query_nombre, paterno=query_paterno)
        if query_materno:
            query = query.filter(materno=query_materno)
        pm = query.first()

    if pm:
        return JsonResponse({
            'encontrado': True,
            'pm_id': pm.id,
            'ci': str(pm.ci) if pm.ci else '',
            'nombre': pm.nombre,
            'paterno': pm.paterno,
            'materno': pm.materno or '',
            'grado': pm.grado or '',
            'arma': pm.arma or '',
            'escalafon': pm.escalafon or '',
            'especialidad': pm.especialidad or '',
            'foto': pm.foto.url if pm.foto else '',
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

    if sim.fase != 'EJECUTORIA_NOTIFICADA':
        messages.error(request, "Este sumario no está en fase de ejecutoria notificada.")
        return redirect('admin1_dashboard')

    if request.method == 'POST':
        sim.fase = 'PENDIENTE_ARCHIVO'
        sim.save()
        messages.success(
            request,
            f"✅ Archivo SPRODA ordenado para SIM {sim.codigo}. Admin2 recibirá la instrucción."
        )
        return redirect('admin1_dashboard')

    # Obtener el Auto de Ejecutoria asociado
    auto_ej = AUTOTPE.objects.filter(
        sim=sim, tipo='AUTO_EJECUTORIA', notificacion__isnull=False
    ).select_related('notificacion', 'memorandum').order_by('-fecha').first()

    return render(request, 'tpe_app/admin1/ordenar_archivo_sproda.html', {
        'sim': sim,
        'auto': auto_ej,
        'militares': sim.militares.all(),
    })


# ============================================================
# ADMIN1: Ordenar entrega de RAP al abogado (v4.0+)
# ============================================================

@rol_requerido('ADMIN1_AGENDADOR', 'MASTER', 'ADMINISTRADOR')
def admin1_ordenar_rap(request, rap_id):
    """Admin1 ordena a Admin2 que entregue el RAP a un abogado (ABOG1 o ABOG2)"""

    rap = get_object_or_404(ApelacionTSP, pk=rap_id, sim__fase='EN_ESPERA_RAP')
    sim = rap.sim

    if request.method == 'POST':
        abog_id = request.POST.get('abogado')

        if not abog_id:
            messages.error(request, '❌ Debe seleccionar un abogado.')
        else:
            try:
                abog = PM.objects.filter(
                    pk=abog_id,
                    perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS']
                ).first()

                if not abog:
                    messages.error(request, '❌ El abogado seleccionado no existe o no tiene rol válido.')
                    return redirect('admin1_ordenar_rap', rap_id=rap_id)

                # Guard: verificar idempotencia
                orden_existente = CustodiaSIM.objects.filter(
                    sim=sim,
                    motivo='APELACION_TSP',
                    fecha_entrega__isnull=True
                ).exists()

                if orden_existente:
                    messages.warning(request, '⚠️ Ya existe una orden de entrega para este RAP.')
                    return redirect('admin1_dashboard')

                with transaction.atomic():
                    # Crear la orden para Admin2
                    CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio='ADMIN2_ARCHIVO',
                        abogado_destino=abog,
                        motivo='APELACION_TSP',
                        usuario=request.user,
                        estado='RECIBIDA_CONFORME',
                        observacion=f'Orden: Entregar RAP a {abog.grado} {abog.paterno}'
                    )

                    messages.success(
                        request,
                        f'✅ Orden enviada a Admin2: entregar RAP a {abog.grado} {abog.paterno}'
                    )
                    return redirect('admin1_dashboard')
            except Exception as e:
                messages.error(request, f'❌ Error: {str(e)}')

    # Obtener abogados disponibles
    abogados = PM.objects.filter(
        perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS']
    ).order_by('paterno', 'nombre')

    context = {
        'rap': rap,
        'sim': sim,
        'pm': rap.pm,
        'abogados': abogados,
    }
    return render(request, 'tpe_app/admin1/ordenar_rap.html', context)


# ─────────────────────────────────────────────────────────────
# Vistas para SIM Institucional (posesión, cierre, autos)
# ─────────────────────────────────────────────────────────────

def _dashboard_url_para_rol(rol):
    """Devuelve la URL del dashboard según el rol del usuario."""
    if rol == 'AYUDANTE':
        return reverse('ayudante_dashboard')
    return reverse('admin1_dashboard')


@rol_requerido('ADMIN1_AGENDADOR', 'MASTER', 'ADMINISTRADOR', 'AYUDANTE')
def registrar_sim_institucional(request):
    back_url = _dashboard_url_para_rol(request.perfil.rol)
    if request.method == 'POST':
        form = SIMInstitucionalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    sim = form.save(commit=False)
                    sim.tipo   = 'INSTITUCIONAL'
                    sim.fase   = 'INSTITUCIONAL'
                    sim.estado = 'INSTITUCIONAL_VIGENTE'
                    sim.version = 1
                    sim.save()
                messages.success(request, f'Acto institucional {sim.codigo} registrado.')
                return redirect('sim_institucional_detalle', sim_id=sim.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
    else:
        form = SIMInstitucionalForm()

    return render(request, 'tpe_app/admin1/sim_institucional_form.html', {
        'form': form,
        'back_url': back_url,
    })


@rol_requerido('ADMIN1_AGENDADOR', 'MASTER', 'ADMINISTRADOR', 'AYUDANTE')
def sim_institucional_detalle(request, sim_id):
    sim = get_object_or_404(SIM, pk=sim_id, tipo='INSTITUCIONAL')
    resoluciones = sim.resolucion_set.order_by('fecha')
    autos        = sim.autotpe_set.order_by('fecha')
    back_url     = _dashboard_url_para_rol(request.perfil.rol)

    if request.method == 'POST' and 'concluir' in request.POST:
        sim.estado = 'INSTITUCIONAL_CONCLUIDO'
        sim.save(update_fields=['estado'])
        messages.success(request, 'Acto institucional marcado como concluido.')
        return redirect('sim_institucional_detalle', sim_id=sim.pk)

    return render(request, 'tpe_app/admin1/sim_institucional_detalle.html', {
        'sim': sim,
        'resoluciones': resoluciones,
        'autos': autos,
        'back_url': back_url,
    })


@rol_requerido('ADMIN1_AGENDADOR', 'MASTER', 'ADMINISTRADOR', 'AYUDANTE')
def agregar_resolucion_institucional(request, sim_id):
    sim = get_object_or_404(SIM, pk=sim_id, tipo='INSTITUCIONAL')
    if request.method == 'POST':
        form = ResolucionInstitucionalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    res = form.save(commit=False)
                    res.sim       = sim
                    res.instancia = 'PRIMERA'
                    res.save()
                messages.success(request, f'Resolución {res.numero} agregada.')
                return redirect('sim_institucional_detalle', sim_id=sim.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
    else:
        from ..models import next_resolucion_num
        form = ResolucionInstitucionalForm(initial={'numero': next_resolucion_num()})

    return render(request, 'tpe_app/admin1/resolucion_institucional_form.html', {
        'form': form,
        'sim': sim,
    })


@rol_requerido('ADMIN1_AGENDADOR', 'MASTER', 'ADMINISTRADOR', 'AYUDANTE')
def agregar_auto_institucional(request, sim_id):
    sim = get_object_or_404(SIM, pk=sim_id, tipo='INSTITUCIONAL')
    if request.method == 'POST':
        form = AutoInstitucionalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    auto = form.save(commit=False)
                    auto.sim = sim
                    auto.save()
                messages.success(request, f'Auto {auto.numero} agregado.')
                return redirect('sim_institucional_detalle', sim_id=sim.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
    else:
        form = AutoInstitucionalForm()

    return render(request, 'tpe_app/admin1/auto_institucional_form.html', {
        'form': form,
        'sim': sim,
    })
