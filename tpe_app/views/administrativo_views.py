# tpe_app/views/administrativo_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from ..decorators import rol_requerido
from ..models import SIM, PM, ABOG, PM_SIM, ABOG_SIM, RR, CustodiaSIM, AGENDA, RES, DocumentoAdjunto
from ..forms import SIMForm, PMSIMFormSet, AgendarSumarioForm, RegistrarRRForm, AgendarRRForm, AgendaForm, AgendaResultadoForm, GestionarAbogadosSIMForm
from datetime import date, timedelta

@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def administrativo_dashboard(request):
    """Dashboard para administrativos - diferenciado por rol"""

    perfil = request.user.perfilusuario

    # Si es Admin2, redirigir a su dashboard específico
    if perfil.rol == 'ADMIN2_ARCHIVO':
        return admin2_dashboard(request)

    # Si es Admin3, redirigir a su dashboard específico
    if perfil.rol == 'ADMIN3_NOTIFICADOR':
        return admin3_dashboard(request)

    # Si no, es Admin1 - dashboard normal
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

    # Pendientes de Auto de Ejecutoria (solo el conteo para la alerta)
    from ..models import get_pendientes_ejecutoria
    por_res_ej, por_rr_ej = get_pendientes_ejecutoria()

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
    }

    return render(request, 'tpe_app/dashboard_administrativo.html', context)


@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR', 'AYUDANTE')
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

                    # Custodia solo al responsable (primer abogado)
                    responsable = abogados_list[0]
                    CustodiaSIM.objects.create(
                        sim=sumario,
                        tipo_custodio='ABOG_ASESOR',
                        abog=responsable,
                        usuario=request.user,
                        observacion='Entregado al agendar sumario (Admin1)'
                    )

                    nombres = ", ".join(str(a) for a in abogados)
                    messages.success(
                        request,
                        f'✅ Sumario {sumario.SIM_COD} agendado en agenda {agenda.AG_NUM} '
                        f'con abogado(s): {nombres} — {agenda.AG_FECPROG.strftime("%d/%m/%Y")}'
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
        'agendas_programadas': AGENDA.objects.filter(AG_ESTADO='PROGRAMADA').count(),
    }

    return render(request, 'tpe_app/agendar_sumario.html', context)

@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR', 'AYUDANTE')
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

@rol_requerido('ADMINISTRATIVO', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
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

    context = {'form': form}
    return render(request, 'tpe_app/crear_agenda.html', context)


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

    return render(request, 'tpe_app/lista_agendas.html', context)


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

    return render(request, 'tpe_app/agenda_resultado.html', context)



# ============================================================
# DASHBOARD ADMIN2 (ARCHIVO SIM)
# ============================================================

def admin2_dashboard(request):
    """Dashboard para Admin2 - Gestión de custodia de carpetas"""
    
    # Carpetas recibidas de abogados (sin entregar aún)
    carpetas_en_poder = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        fecha_entrega__isnull=True
    ).select_related('sim').order_by('-fecha_recepcion')

    # Historial de entregas
    entregas_pasadas = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        fecha_entrega__isnull=False
    ).select_related('sim').order_by('-fecha_entrega')[:20]

    context = {
        'carpetas_en_poder': carpetas_en_poder,
        'total_en_poder': carpetas_en_poder.count(),
        'entregas_pasadas': entregas_pasadas,
    }

    return render(request, 'tpe_app/admin2_dashboard.html', context)


# ============================================================
# DASHBOARD ADMIN3 (NOTIFICADOR)
# ============================================================

def admin3_dashboard(request):
    """Dashboard para Admin3 - Notificaciones de documentos"""

    # RES (Resoluciones) por notificar (RES_FECNOT es NULL = no notificada aún)
    resoluciones = RES.objects.filter(
        RES_FECNOT__isnull=True
    ).select_related('sim').order_by('-RES_FEC')[:20]

    # RR (Recursos) por notificar (RR_FECNOT es NULL = no notificado aún)
    recursos = RR.objects.filter(
        RR_FECNOT__isnull=True
    ).select_related('sim').order_by('-RR_FEC')[:20]

    # RES sin PDF (para dashboard administrativo)
    res_con_pdf = set(DocumentoAdjunto.objects.filter(DOC_TABLA='res').values_list('DOC_ID_REG', flat=True))
    res_sin_pdf = RES.objects.exclude(id__in=res_con_pdf).select_related('sim', 'abog').order_by('-RES_FEC')[:20]
    total_res_sin_pdf = RES.objects.exclude(id__in=res_con_pdf).count()

    context = {
        'resoluciones': resoluciones,
        'total_res': resoluciones.count(),
        'recursos': recursos,
        'total_rr': recursos.count(),
        'res_sin_pdf': res_sin_pdf,
        'total_res_sin_pdf': total_res_sin_pdf,
    }

    return render(request, 'tpe_app/admin3_dashboard.html', context)


# ============================================================
# ADMIN2: Gestión de custodia y entregas (v3.1+)
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_entregar_carpeta(request, sim_id):
    """Admin2 entrega la carpeta a un abogado (RR, RAP, ejecutoria, etc.)"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que la carpeta esté en poder de Admin2
    if not custodio_actual or custodio_actual.tipo_custodio != 'ADMIN2_ARCHIVO':
        messages.error(request, "❌ La carpeta no está registrada en poder de Archivo SIM")
        return redirect('admin2_dashboard')

    if request.method == 'POST':
        abog_id = request.POST.get('abogado')
        tipo_custodio = request.POST.get('tipo_custodio')
        observacion = request.POST.get('observacion', '').strip()

        if not abog_id or not tipo_custodio:
            messages.error(request, '❌ Debe seleccionar abogado y tipo de custodia')
        else:
            try:
                abog = ABOG.objects.get(pk=abog_id)
                with transaction.atomic():
                    # Cerrar custodia actual (Admin2)
                    custodio_actual.fecha_entrega = timezone.now()
                    custodio_actual.save()

                    # Crear nueva custodia con el abogado
                    CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio=tipo_custodio,
                        abog=abog,
                        usuario=request.user,
                        observacion=observacion or None
                    )

                    messages.success(
                        request,
                        f'✅ Carpeta entregada al {abog.AB_GRADO} {abog.AB_PATERNO}'
                    )
                    return redirect('admin2_dashboard')
            except ABOG.DoesNotExist:
                messages.error(request, '❌ Abogado no encontrado')
            except Exception as e:
                messages.error(request, f'❌ Error: {str(e)}')

    # Obtener abogados disponibles
    abogados = ABOG.objects.all().order_by('AB_PATERNO')

    # Tipos de custodia para entregas posteriores (no 1ra vez)
    TIPOS_CUSTODIA = [
        ('ABOG_RR', 'Abogado - Recurso de Reconsideración'),
        ('ABOG_AUTOS', 'Abogado - Autos/Ejecutoria'),
        ('ABOG_RAP', 'Abogado - Recurso de Apelación'),
    ]

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
        'abogados': abogados,
        'tipos_custodia': TIPOS_CUSTODIA,
    }

    return render(request, 'tpe_app/admin2/entregar_carpeta.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_recibir_carpeta(request, sim_id):
    """Admin2 recibe la carpeta devuelta por un abogado"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que la carpeta esté en poder de un abogado
    if not custodio_actual or not custodio_actual.abog:
        messages.error(request, "❌ La carpeta no está en poder de un abogado")
        return redirect('admin2_dashboard')

    if request.method == 'POST':
        observacion = request.POST.get('observacion', '').strip()

        try:
            with transaction.atomic():
                # Cerrar custodia del abogado
                custodio_actual.fecha_entrega = timezone.now()
                custodio_actual.save()

                # Crear nueva custodia con Admin2
                CustodiaSIM.objects.create(
                    sim=sim,
                    tipo_custodio='ADMIN2_ARCHIVO',
                    usuario=request.user,
                    observacion=observacion or None
                )

                messages.success(
                    request,
                    f'✅ Carpeta recibida de {custodio_actual.abog.AB_GRADO} {custodio_actual.abog.AB_PATERNO}'
                )
                return redirect('admin2_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
    }

    return render(request, 'tpe_app/admin2/recibir_carpeta.html', context)


# ============================================================
# SUBIR PDF DE RESOLUCIONES (RES)
# ============================================================

@rol_requerido('AYUDANTE', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def subir_pdf_res(request, res_id):
    """Sube PDF de una Resolución (RES) - Ayudante o Administrativos específicos"""

    res = get_object_or_404(RES, pk=res_id)

    if request.method == 'POST':
        archivo_pdf = request.FILES.get('archivo_pdf')

        if not archivo_pdf:
            messages.error(request, '❌ Selecciona un archivo PDF')
            return redirect('subir_pdf_res', res_id=res.pk)

        if not archivo_pdf.name.lower().endswith('.pdf'):
            messages.error(request, '❌ Solo se permiten archivos PDF')
            return redirect('subir_pdf_res', res_id=res.pk)

        try:
            with transaction.atomic():
                # Eliminar PDF anterior si existe
                DocumentoAdjunto.objects.filter(
                    DOC_TABLA='res',
                    DOC_ID_REG=res.pk
                ).delete()

                # Crear nuevo documento
                DocumentoAdjunto.objects.create(
                    DOC_TABLA='res',
                    DOC_ID_REG=res.pk,
                    DOC_RUTA=archivo_pdf,
                    DOC_DESCRIPCION=f'PDF de la Resolución {res.RES_NUM}'
                )

                messages.success(
                    request,
                    f'✅ PDF de la Resolución {res.RES_NUM} subido correctamente'
                )
                return redirect('administrativo_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error al subir PDF: {str(e)}')

    # Verificar si ya tiene PDF
    pdf_existente = DocumentoAdjunto.objects.filter(
        DOC_TABLA='res',
        DOC_ID_REG=res.pk
    ).first()

    context = {
        'res': res,
        'pdf_existente': pdf_existente,
    }

    return render(request, 'tpe_app/administrativo/subir_pdf_res.html', context)
