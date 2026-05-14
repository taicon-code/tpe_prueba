# tpe_app/views/admin2_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from datetime import datetime
from ..decorators import rol_requerido
from ..models import SIM, PM, CustodiaSIM, DocumentoAdjunto, Resolucion, ABOG_SIM, AUTOTPE, ApelacionTSP, DocumentoRecurrente
from ..forms import RegistrarRRForm, DocumentoRecurrenteForm


# ============================================================
# DASHBOARD ADMIN2 (ARCHIVO SIM)
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_dashboard(request):
    """Dashboard para Admin2 - Gestión de custodia de carpetas

    Garantiza que TODOS los SIM registrados aparezcan en ALGUNA sección del dashboard.
    Cada SIM se muestra según su custodia actual.
    """

    # ✅ 1. SIM PENDIENTES DE ENTREGAR AL ABOGADO
    # Detecta tres casos:
    #   A) Custodia ADMIN2 PENDIENTE_CONFIRMACION + abogado_destino (agendados con el nuevo flujo)
    #   B) SIM PROCESO_EN_EL_TPE con ABOG_SIM pero custodia ADMIN2 aún RECIBIDA_CONFORME (datos viejos)
    #   C) SIM PROCESO_EN_EL_TPE con ABOG_SIM y sin ninguna custodia activa (entrega fallida)
    from django.db.models import Exists, OuterRef

    # Caso A: custodia formal de entrega pendiente
    custodias_para_entregar_qs = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        estado='PENDIENTE_CONFIRMACION',
        fecha_entrega__isnull=True,
        abogado_destino__isnull=False,
    ).select_related('sim', 'abogado_destino').prefetch_related('sim__militares')

    carpetas_para_entregar = []
    sim_ids_caso_a = set()
    for custodia in custodias_para_entregar_qs:
        custodio = custodia.sim.custodio_actual()
        if custodio and custodio.id == custodia.id:
            abog_sim_qs = ABOG_SIM.objects.filter(sim=custodia.sim).select_related('abogado')
            custodia.todos_abogados = [a.abogado for a in abog_sim_qs]
            custodia.sin_custodia_formal = False
            carpetas_para_entregar.append(custodia)
            sim_ids_caso_a.add(custodia.sim_id)

    # Casos B y C: SIM en proceso con abogado asignado pero sin custodia activa de abogado
    tiene_custodia_abogado_activa = Exists(
        CustodiaSIM.objects.filter(
            sim=OuterRef('pk'),
            tipo_custodio__in=['ABOG_ASESOR', 'ABOG_RR', 'ABOG_AUTOS'],
            fecha_entrega__isnull=True,
        )
    )
    # Si Admin2 ya tiene custodia activa (carpeta devuelta por abogado o en su poder),
    # el SIM no debe aparecer en "Para entregar" — ya está en otra sección.
    tiene_custodia_admin2_activa = Exists(
        CustodiaSIM.objects.filter(
            sim=OuterRef('pk'),
            tipo_custodio='ADMIN2_ARCHIVO',
            fecha_entrega__isnull=True,
        )
    )
    fases_excluidas = [
        'PENDIENTE_ARCHIVO', 'CONCLUIDO', 'MEMORANDUM_RETORNADO',
        'EN_EJECUTORIA', 'EJECUTORIA_NOTIFICADA', 'EN_AGENDA_EJECUTORIA',
    ]
    sims_sin_custodia_abogado = (
        SIM.objects.filter(estado='PROCESO_EN_EL_TPE', abogados__isnull=False)
        .exclude(pk__in=sim_ids_caso_a)
        .exclude(fase__in=fases_excluidas)
        .annotate(tiene_custodia_abogado=tiene_custodia_abogado_activa)
        .annotate(tiene_custodia_admin2=tiene_custodia_admin2_activa)
        .filter(tiene_custodia_abogado=False)
        .filter(tiene_custodia_admin2=False)
        .prefetch_related('militares', 'abogados')
        .distinct()
    )
    for sim in sims_sin_custodia_abogado:
        abog_resp = ABOG_SIM.objects.filter(sim=sim, es_responsable=True).select_related('abogado').first()
        todos = ABOG_SIM.objects.filter(sim=sim).select_related('abogado')
        # Crear objeto proxy con los mismos atributos que usa el template
        class _FakeEntrega:
            pass
        fe = _FakeEntrega()
        fe.sim = sim
        fe.abogado_destino = abog_resp.abogado if abog_resp else None
        fe.todos_abogados = [a.abogado for a in todos]
        fe.sin_custodia_formal = True
        fe.fecha_recepcion = sim.fecha_ingreso or timezone.now()
        carpetas_para_entregar.append(fe)

    carpetas_para_entregar.sort(
        key=lambda x: x.fecha_recepcion if x.fecha_recepcion else timezone.now(),
        reverse=True,
    )

    # ✅ 1b. PENDIENTES DE CONFIRMAR RECEPCIÓN (Admin2 recibió carpeta de vuelta)
    # Custodias ADMIN2 en PENDIENTE_CONFIRMACION sin abogado_destino (devueltas por abogados).
    custodias_admin2_pendientes = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        estado='PENDIENTE_CONFIRMACION',
        fecha_entrega__isnull=True,
        abogado_destino__isnull=True,
    ).select_related('sim', 'abogado').prefetch_related('sim__militares')

    carpetas_admin2_pendientes = []
    for custodia in custodias_admin2_pendientes:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            carpetas_admin2_pendientes.append(custodia)

    carpetas_admin2_pendientes.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 2. CARPETAS EN PODER DE ADMIN2 (Activas)
    # Son custodias ADMIN2_ARCHIVO en estado ACTIVA (excepto ejecutoria)
    custodias_admin2_activas = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        estado='RECIBIDA_CONFORME',
        fecha_entrega__isnull=True
    ).exclude(
        motivo='EJECUTORIA'  # Las de ejecutoria van en otra sección
    ).select_related('sim').prefetch_related('sim__militares')

    carpetas_en_poder = []
    for custodia in custodias_admin2_activas:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            # Abogados de primera instancia (ABOG_SIM)
            abog_primera = ABOG_SIM.objects.filter(sim=custodia.sim).select_related('abogado')
            custodia.abog_primera_list = [a.abogado for a in abog_primera]

            # Abogado de RR si existe
            rr = Resolucion.objects.filter(
                sim=custodia.sim, instancia='RECONSIDERACION', abogado__isnull=False
            ).select_related('abogado').last()
            custodia.abog_rr = rr.abogado if rr else None

            carpetas_en_poder.append(custodia)

    carpetas_en_poder.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 3. PARA EJECUTORIA
    # Son custodias ADMIN2_ARCHIVO con motivo='EJECUTORIA'
    custodias_ejecutoria = CustodiaSIM.objects.filter(
        tipo_custodio='ADMIN2_ARCHIVO',
        motivo='EJECUTORIA',
        estado='RECIBIDA_CONFORME',
        fecha_entrega__isnull=True
    ).select_related('sim', 'abogado_destino').order_by('-fecha_recepcion')

    para_ejecutoria = []
    for custodia in custodias_ejecutoria:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            para_ejecutoria.append(custodia)

    # ✅ 4. PENDIENTES DE CONFIRMACIÓN (Abogados/Vocales)
    # Son custodias de otros tipos en estado PENDIENTE_CONFIRMACION
    custodias_otros_pendientes = CustodiaSIM.objects.filter(
        estado='PENDIENTE_CONFIRMACION',
        fecha_entrega__isnull=True
    ).exclude(
        tipo_custodio='ADMIN2_ARCHIVO'
    ).select_related('sim').prefetch_related('sim__militares')

    carpetas_pendientes = []
    for custodia in custodias_otros_pendientes:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            carpetas_pendientes.append(custodia)

    carpetas_pendientes.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 5. CARPETAS PRESTADAS (En poder de abogados/vocales/otros)
    # Son custodias de otros tipos en estado ACTIVA
    custodias_otros_activas = CustodiaSIM.objects.filter(
        estado='RECIBIDA_CONFORME',
        fecha_entrega__isnull=True
    ).exclude(
        tipo_custodio__in=['ADMIN2_ARCHIVO', 'ARCHIVO']
    ).select_related('sim').prefetch_related('sim__militares')

    carpetas_prestadas = []
    for custodia in custodias_otros_activas:
        if custodia.sim.custodio_actual() and custodia.sim.custodio_actual().id == custodia.id:
            carpetas_prestadas.append(custodia)

    carpetas_prestadas.sort(key=lambda x: x.fecha_recepcion, reverse=True)

    # ✅ 6. PENDIENTE ARCHIVO SPRODA (Admin1 ordenó el archivo final)
    sims_pendiente_archivo = list(
        SIM.objects.filter(fase='PENDIENTE_ARCHIVO')
        .prefetch_related('militares')
        .order_by('-fecha_ingreso')
    )
    for sim_pa in sims_pendiente_archivo:
        sim_pa.auto_ejecutoria = AUTOTPE.objects.filter(
            sim=sim_pa, tipo='AUTO_EJECUTORIA'
        ).order_by('-fecha').first()

    # ✅ 8. PROCESO_CONCLUIDO_TPE con memorándum pendiente de retorno
    sims_memo_pendiente = list(
        SIM.objects.filter(estado='PROCESO_CONCLUIDO_TPE')
        .prefetch_related('militares')
        .order_by('-fecha_ingreso')
    )
    sims_con_memo_pendiente = []
    for sim_m in sims_memo_pendiente:
        auto = AUTOTPE.objects.filter(
            sim=sim_m, tipo='AUTO_EJECUTORIA',
            memorandums__isnull=False,
            memorandums__fecha_entrega__isnull=True,
        ).prefetch_related('memorandums').first()
        if auto:
            sim_m.auto_ejecutoria = auto
            sims_con_memo_pendiente.append(sim_m)

    # ✅ 9. RAPs PENDIENTES DE ENTREGAR (presentados, orden creada, en poder de Admin2)
    raps_para_entregar = ApelacionTSP.objects.filter(
        sim__fase='EN_ESPERA_RAP',
        sim__custodias__motivo='APELACION_TSP',
        sim__custodias__abogado_destino__isnull=False,
        sim__custodias__fecha_entrega__isnull=True,
        sim__custodias__tipo_custodio='ADMIN2_ARCHIVO'
    ).select_related('sim', 'pm', 'resolucion').distinct().order_by('fecha_presentacion')

    # ✅ 10. RAPs ELABORADOS, PENDIENTES DE ENVÍO AL TSP
    raps_para_enviar = ApelacionTSP.objects.filter(
        numero__isnull=False,
        numero_oficio__isnull=True,
        sim__fase='EN_ESPERA_RAP',
    ).select_related('sim', 'pm').order_by('fecha_presentacion')

    # Filtro de historial por código SIM o militar
    from django.db.models import Q

    query = (request.GET.get('q') or '').strip()
    historial_sim = None

    if query:
        try:
            # Buscar en codigo, militares paterno/materno/nombre
            filtros_q = (
                Q(codigo__icontains=query) |
                Q(militares__paterno__icontains=query) |
                Q(militares__materno__icontains=query) |
                Q(militares__nombre__icontains=query)
            )
            sims = SIM.objects.filter(filtros_q).distinct()
            historial_sim = CustodiaSIM.objects.filter(sim__in=sims).select_related('abogado').order_by('fecha_recepcion')
        except Exception:
            historial_sim = []

    # Aplicar paginación (15 items por página)
    paginator = Paginator(carpetas_admin2_pendientes, 15)
    page = request.GET.get('page_admin2_pendientes')
    try:
        carpetas_admin2_pendientes_page = paginator.page(page)
    except PageNotAnInteger:
        carpetas_admin2_pendientes_page = paginator.page(1)
    except EmptyPage:
        carpetas_admin2_pendientes_page = paginator.page(paginator.num_pages)

    paginator_en_poder = Paginator(carpetas_en_poder, 15)
    page_en_poder = request.GET.get('page_en_poder')
    try:
        carpetas_en_poder_page = paginator_en_poder.page(page_en_poder)
    except PageNotAnInteger:
        carpetas_en_poder_page = paginator_en_poder.page(1)
    except EmptyPage:
        carpetas_en_poder_page = paginator_en_poder.page(paginator_en_poder.num_pages)

    paginator_ejecutoria = Paginator(para_ejecutoria, 15)
    page_ejecutoria = request.GET.get('page_ejecutoria')
    try:
        para_ejecutoria_page = paginator_ejecutoria.page(page_ejecutoria)
    except PageNotAnInteger:
        para_ejecutoria_page = paginator_ejecutoria.page(1)
    except EmptyPage:
        para_ejecutoria_page = paginator_ejecutoria.page(paginator_ejecutoria.num_pages)

    paginator_entregar = Paginator(carpetas_para_entregar, 15)
    page_entregar = request.GET.get('page_entregar')
    try:
        carpetas_para_entregar_page = paginator_entregar.page(page_entregar)
    except PageNotAnInteger:
        carpetas_para_entregar_page = paginator_entregar.page(1)
    except EmptyPage:
        carpetas_para_entregar_page = paginator_entregar.page(paginator_entregar.num_pages)

    context = {
        'carpetas_para_entregar': carpetas_para_entregar_page,
        'total_para_entregar': len(carpetas_para_entregar),
        'carpetas_admin2_pendientes': carpetas_admin2_pendientes_page,
        'total_admin2_pendientes': len(carpetas_admin2_pendientes),
        'carpetas_en_poder': carpetas_en_poder_page,
        'total_en_poder': len(carpetas_en_poder),
        'carpetas_pendientes': carpetas_pendientes,
        'total_pendientes': len(carpetas_pendientes),
        'carpetas_prestadas': carpetas_prestadas,
        'total_prestadas': len(carpetas_prestadas),
        'para_ejecutoria': para_ejecutoria_page,
        'total_ejecutoria': len(para_ejecutoria),
        'sims_pendiente_archivo': sims_pendiente_archivo,
        'total_pendiente_archivo': len(sims_pendiente_archivo),
        'sims_con_memo_pendiente': sims_con_memo_pendiente,
        'total_memo_pendiente': len(sims_con_memo_pendiente),
        'raps_para_entregar': raps_para_entregar,
        'total_raps_entregar': len(raps_para_entregar),
        'raps_para_enviar': raps_para_enviar,
        'total_raps_enviar': len(raps_para_enviar),
        'query': query,
        'historial_sim': historial_sim,
    }

    return render(request, 'tpe_app/admin2/admin2_dashboard.html', context)


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
        motivo = request.POST.get('motivo')
        observacion = request.POST.get('observacion', '').strip()
        nro_oficio = request.POST.get('nro_oficio', '').strip() if tipo_custodio == 'TSP' else None
        fecha_oficio_str = request.POST.get('fecha_oficio') if tipo_custodio == 'TSP' else None
        nro_oficio_archivo = request.POST.get('nro_oficio_archivo', '').strip() or None
        fecha_oficio_archivo_str = request.POST.get('fecha_oficio_archivo') or None

        if not tipo_custodio:
            messages.error(request, '❌ Debe seleccionar tipo de custodia')
        elif tipo_custodio != 'ARCHIVO' and not abog_id:
            messages.error(request, '❌ Debe seleccionar abogado (excepto para Archivado)')
        else:
            try:
                abog = PM.objects.filter(
                    pk=abog_id,
                    perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR', 'ABOGADO']
                ).first() if abog_id else None
                if abog_id and not abog:
                    messages.error(request, '❌ El personal seleccionado no tiene rol de abogado en el sistema.')
                    return redirect('admin2_dashboard')
                fecha_oficio = None
                if fecha_oficio_str:
                    fecha_oficio = datetime.strptime(fecha_oficio_str, '%Y-%m-%d').date()
                fecha_oficio_archivo = None
                if fecha_oficio_archivo_str:
                    fecha_oficio_archivo = datetime.strptime(fecha_oficio_archivo_str, '%Y-%m-%d').date()

                with transaction.atomic():
                    # Cerrar custodia actual (Admin2)
                    custodio_actual.fecha_entrega = timezone.now()
                    custodio_actual.save()

                    # Determinar estado: si va a un abogado, queda PENDIENTE hasta que él confirme.
                    # El modelo exige abogado_destino (no abogado) cuando es PENDIENTE_CONFIRMACION.
                    es_entrega_a_abogado = tipo_custodio.startswith('ABOG_')
                    estado_custodia = 'PENDIENTE_CONFIRMACION' if es_entrega_a_abogado else 'RECIBIDA_CONFORME'

                    CustodiaSIM.objects.create(
                        sim=sim,
                        tipo_custodio=tipo_custodio,
                        abogado_destino=abog if es_entrega_a_abogado else None,
                        abogado=abog if not es_entrega_a_abogado else None,
                        usuario=request.user,
                        observacion=observacion or None,
                        motivo=motivo,
                        nro_oficio=nro_oficio,
                        fecha_oficio=fecha_oficio,
                        nro_oficio_archivo=nro_oficio_archivo,
                        fecha_oficio_archivo=fecha_oficio_archivo,
                        estado=estado_custodia,
                    )

                    if es_entrega_a_abogado:
                        messages.success(
                            request,
                            f'✅ Carpeta de {sim.codigo} entregada a {abog}. '
                            f'El abogado debe confirmar la recepción desde su panel.'
                        )
                    else:
                        messages.success(request, f'✅ Carpeta de {sim.codigo} entregada correctamente.')
                    return redirect('admin2_dashboard')
            except PM.DoesNotExist:
                messages.error(request, '❌ Abogado no encontrado')
            except Exception as e:
                messages.error(request, f'❌ Error: {str(e)}')

    # Obtener abogados disponibles
    abogados = PM.objects.filter(perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR']).order_by('paterno')

    # Tipos de custodia disponibles para entregar
    TIPOS_CUSTODIA = [
        ('ABOG_ASESOR', 'Abogado 1 - Asesor (1ra Resolución)'),
        ('ABOG_RR', 'Abogado 2 - Recurso de Reconsideración'),
        ('ABOG_AUTOS', 'Abogado 3 - Autos/Ejecutoria'),
        ('ADMIN3', 'Admin3 - Notificador'),
        ('TSP', 'Tribunal Superior de Personal (TSP)'),
        ('ARCHIVO', 'Archivado / Concluido'),
    ]

    # Motivos disponibles
    MOTIVOS = [
        ('AGENDA', 'Para agenda del tribunal'),
        ('REVISION', 'Revisión del abogado'),
        ('NOTIFICACION', 'Para notificación'),
        ('APELACION_TSP', 'Elevado al TSP'),
        ('EJECUTORIA',         'Para ejecutoria/cumplimiento'),
        ('RESPUESTA_MEMORIAL', 'Respuesta a Memorial'),
        ('ARCHIVO',            'Archivado / Concluido'),
    ]

    # Detectar si hay una orden de ejecutoria previa
    orden_ejecutoria = CustodiaSIM.objects.filter(
        sim=sim,
        motivo='EJECUTORIA',
        fecha_entrega__isnull=True
    ).select_related('abogado_destino').first()

    # Pre-llenar si hay orden de ejecutoria
    pre_llenar_tipo = None
    pre_llenar_abog = None
    mensaje_orden = None

    if orden_ejecutoria and orden_ejecutoria.abogado_destino:
        pre_llenar_tipo = 'ABOG_AUTOS'
        pre_llenar_abog = orden_ejecutoria.abogado_destino.pk
        mensaje_orden = f'Orden: Entregar a ABOG2 ({orden_ejecutoria.abogado_destino.paterno}) para Ejecutoria'

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
        'abogados': abogados,
        'tipos_custodia': TIPOS_CUSTODIA,
        'motivos': MOTIVOS,
        'orden_ejecutoria': orden_ejecutoria,
        'mensaje_orden': mensaje_orden,
        'pre_llenar_tipo': pre_llenar_tipo,
        'pre_llenar_abog': pre_llenar_abog,
    }

    return render(request, 'tpe_app/admin2/entregar_carpeta.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_recibir_carpeta(request, sim_id):
    """Admin2 recibe la carpeta devuelta por un abogado"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que la carpeta esté en poder de un abogado
    if not custodio_actual or not custodio_actual.abogado:
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
                    abogado=custodio_actual.abogado,
                    usuario=request.user,
                    observacion=observacion or None
                )

                messages.success(
                    request,
                    f'✅ Carpeta recibida de {custodio_actual.abogado.grado} {custodio_actual.abogado.paterno}'
                )
                return redirect('admin2_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
    }

    return render(request, 'tpe_app/admin2/recibir_carpeta.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_confirmar_recepcion(request, sim_id):
    """Admin2 confirma que recibió la carpeta conforme (entregada por abogado)"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodio_actual = sim.custodio_actual()

    # Verificar que hay una custodia pendiente de confirmación
    if (not custodio_actual or
        custodio_actual.tipo_custodio != 'ADMIN2_ARCHIVO' or
        custodio_actual.estado != 'PENDIENTE_CONFIRMACION'):
        messages.error(request, "❌ No hay recepción pendiente para este sumario")
        return redirect('admin2_dashboard')

    if request.method == 'POST':
        observacion = request.POST.get('observacion', '').strip()

        try:
            with transaction.atomic():
                # Cambiar estado a RECIBIDA_CONFORME
                custodio_actual.estado = 'RECIBIDA_CONFORME'
                if observacion:
                    custodia_obs = (custodio_actual.observacion or '') + f' | Recibido conforme: {observacion}'
                    custodio_actual.observacion = custodia_obs
                custodio_actual.save()

                messages.success(
                    request,
                    f'✅ Carpeta {sim.codigo} recibida conforme y en su poder'
                )
                return redirect('admin2_dashboard')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {
        'sim': sim,
        'custodio_actual': custodio_actual,
    }

    return render(request, 'tpe_app/admin2/confirmar_recepcion.html', context)


# ============================================================
# SUBIR PDF DE RESOLUCIONES (RES)
# ============================================================

@rol_requerido('AYUDANTE', 'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def subir_pdf_res(request, res_id):
    """Sube PDF de una Resolución (RES) - Ayudante o Administrativos específicos"""

    res = get_object_or_404(Resolucion, pk=res_id)

    if request.method == 'POST':
        archivo_pdf = request.FILES.get('archivo_pdf')

        if not archivo_pdf:
            messages.error(request, '❌ Selecciona un archivo PDF')
            return redirect('subir_pdf_res', res_id=res.pk)

        if not archivo_pdf.name.lower().endswith('.pdf'):
            messages.error(request, '❌ Solo se permiten archivos PDF')
            return redirect('subir_pdf_res', res_id=res.pk)

        next_url = request.POST.get('next', '').strip()
        try:
            with transaction.atomic():
                # Eliminar PDF anterior si existe
                DocumentoAdjunto.objects.filter(
                    resolucion_id=res.pk
                ).delete()

                # Crear nuevo documento
                DocumentoAdjunto.objects.create(
                    resolucion=res,
                    tipo='resolucion',
                    archivo=archivo_pdf,
                    nombre=f'RES {res.numero} - {res.pm.grado} {res.pm.paterno}' if res.pm else f'RES {res.numero}'
                )

                messages.success(
                    request,
                    f'✅ PDF de la Resolución {res.numero} subido correctamente'
                )
                if next_url:
                    return redirect(next_url)
                return redirect('subir_pdf_res', res_id=res.pk)
        except Exception as e:
            messages.error(request, f'❌ Error al subir PDF: {str(e)}')

    # Verificar si ya tiene PDF
    pdf_existente = DocumentoAdjunto.objects.filter(
        resolucion_id=res.pk
    ).first()

    context = {
        'res': res,
        'pdf_existente': pdf_existente,
    }

    return render(request, 'tpe_app/admin2/subir_pdf_res.html', context)


# ============================================================
# VER HISTORIAL DE CUSTODIA DE UN SIM
# ============================================================

@rol_requerido('ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR')
def ver_historial_custodia_sim(request, sim_id):
    """Ver dónde está un SIM actualmente y su historial de custodia"""

    sim = get_object_or_404(SIM, pk=sim_id)
    custodia_actual = sim.custodio_actual()

    # Obtener historial completo de custodia
    historial = list(CustodiaSIM.objects.filter(sim=sim).select_related('abogado', 'usuario').order_by('fecha_recepcion'))

    # Enriquecer datos de historial con nombre legible del custodio
    TIPO_CUSTODIO_DISPLAY = {
        'ADMIN1_AGENDADOR': 'Agendador',
        'ADMIN2_ARCHIVO': 'Archivo del Tribunal',
        'ADMIN3_NOTIFICADOR': 'Notificador',
        'ABOG_ASESOR': 'Abogado Asesor',
        'ABOG_RR': 'Abogado (Reconsideración)',
        'ABOG_AUTOS': 'Abogado (Autos)',
        'VOCAL_SESION': 'Secretario de Actas',
        'TSP': 'Tribunal Superior de Personal',
        'ARCHIVO': 'Archivo Permanente',
    }

    for custodia in historial:
        custodia.tipo_custodio_display = TIPO_CUSTODIO_DISPLAY.get(custodia.tipo_custodio, custodia.tipo_custodio)

    if custodia_actual:
        custodia_actual.tipo_custodio_display = TIPO_CUSTODIO_DISPLAY.get(custodia_actual.tipo_custodio, custodia_actual.tipo_custodio)

    context = {
        'sim': sim,
        'custodia_actual': custodia_actual,
        'historial': historial,
    }

    return render(request, 'tpe_app/admin2/ver_historial_custodia.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_adjuntar_oficio_custodia(request, custodia_id):
    """Admin2 adjunta o reemplaza el PDF del oficio de una custodia."""
    custodia = get_object_or_404(CustodiaSIM, pk=custodia_id)

    if request.method == 'POST':
        archivo = request.FILES.get('archivo_oficio')
        if not archivo:
            messages.error(request, '❌ Debe seleccionar un archivo PDF.')
        elif not archivo.name.lower().endswith('.pdf'):
            messages.error(request, '❌ Solo se aceptan archivos PDF.')
        else:
            if custodia.archivo_oficio:
                custodia.archivo_oficio.delete(save=False)
            custodia.archivo_oficio = archivo
            custodia.save()
            messages.success(request, f'✅ PDF adjuntado correctamente a la custodia #{custodia_id}.')
        return redirect('ver_historial_custodia', sim_id=custodia.sim_id)

    return render(request, 'tpe_app/admin2/adjuntar_oficio_custodia.html', {
        'custodia': custodia,
        'sim': custodia.sim,
    })


# ============================================================
# ADMIN2: Confirmar Archivo Final a SPRODA
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_confirmar_archivo_sproda(request, sim_id):
    """Admin2 confirma que realizó el archivo final (SPRODA + copias a secciones si corresponde).
    Transiciona el SIM a CONCLUIDO → PROCESO_CONCLUIDO_TPE."""

    sim = get_object_or_404(SIM, pk=sim_id, fase='PENDIENTE_ARCHIVO')

    if request.method == 'POST':
        observacion = request.POST.get('observacion', '').strip()
        with transaction.atomic():
            sim.fase = 'CONCLUIDO'
            sim.estado = 'PROCESO_CONCLUIDO_TPE'
            sim.save()
            # Registrar en historial de custodia
            CustodiaSIM.objects.create(
                sim=sim,
                tipo_custodio='ARCHIVO',
                usuario=request.user,
                motivo='ARCHIVO',
                observacion=observacion or 'Archivo final SPRODA',
                estado='RECIBIDA_CONFORME',
            )
        messages.success(
            request,
            f"✅ SIM {sim.codigo} archivado correctamente. Estado: Proceso Concluido (TPE)."
        )
        return redirect('admin2_dashboard')

    auto_ej = AUTOTPE.objects.filter(
        sim=sim, tipo='AUTO_EJECUTORIA'
    ).order_by('-fecha').first()

    return render(request, 'tpe_app/admin2/confirmar_archivo_sproda.html', {
        'sim': sim,
        'auto': auto_ej,
        'militares': sim.militares.all(),
    })


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_registrar_retorno_memo(request, auto_id):
    """Admin2 registra el retorno del memorándum del Auto de Ejecutoria.
    Cuando el memo retorna, el SIM pasa a PROCESO_EJECUTADO."""

    auto = get_object_or_404(AUTOTPE, id=auto_id, tipo='AUTO_EJECUTORIA')

    if request.method == 'POST':
        fecha_entrega = request.POST.get('fecha_entrega')
        if not fecha_entrega:
            messages.error(request, "Debe ingresar la fecha de retorno del memorándum.")
        else:
            from datetime import datetime as dt
            try:
                fecha = dt.strptime(fecha_entrega, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Formato de fecha inválido.")
                fecha = None

            if fecha:
                with transaction.atomic():
                    memo = auto.memorandums.first()
                    if memo:
                        memo.fecha_entrega = fecha
                        memo.save(update_fields=['fecha_entrega'])
                    sim = auto.sim
                    # Guardia multi-persona: no avanzar si otro militar del SIM
                    # tiene proceso activo en instancia externa (TSP o cumplimiento).
                    ESTADOS_ACTIVOS_EXTERNOS = {'PROCESO_EN_EL_TSP', 'CUMPLIMIENTO_EN_TPE'}
                    if sim.estado not in ESTADOS_ACTIVOS_EXTERNOS:
                        sim.fase = 'MEMORANDUM_RETORNADO'
                        sim.save()
                messages.success(
                    request,
                    f"✅ Retorno de memorándum registrado. SIM {sim.codigo}: Proceso Ejecutado."
                )
                return redirect('admin2_dashboard')

    return render(request, 'tpe_app/admin2/registrar_retorno_memo.html', {
        'auto': auto,
        'sim': auto.sim,
    })


# ============================================================
# ADMIN2: Registrar presentación del RAP (v4.0+)
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO')
def admin2_registrar_rap(request):
    """Admin2 registra que el militar presentó el RAP (Recurso de Apelación)"""
    from ..forms import Admin2RegistrarRAPForm

    if request.method == 'POST':
        form = Admin2RegistrarRAPForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Guard: verificar que no exista ya un RAP para ese (sim, pm)
                    existente = ApelacionTSP.objects.filter(
                        sim=form.cleaned_data['sim'],
                        pm=form.cleaned_data['pm'],
                    ).exists()

                    if existente:
                        messages.warning(request, '⚠️ Ya existe un RAP registrado para este militar en este sumario.')
                        return redirect('admin2_registrar_rap')

                    # Crear el RAP con solo datos iniciales
                    rap = form.save()

                    # Actualizar fase del SIM si aún no está en EN_ESPERA_RAP
                    sim = rap.sim
                    if sim.fase not in ['EN_ESPERA_RAP', 'ELEVADO_TSP', 'PROCESO_EN_EL_TSP']:
                        sim.fase = 'EN_ESPERA_RAP'
                        sim.save()

                    messages.success(
                        request,
                        f'✅ RAP registrado para {rap.pm.grado} {rap.pm.paterno} (SIM: {rap.sim.codigo})'
                    )
                    return redirect('admin2_dashboard')
            except Exception as e:
                messages.error(request, f'❌ Error al registrar RAP: {str(e)}')
    else:
        form = Admin2RegistrarRAPForm()

    context = {
        'form': form,
        'titulo': 'Registrar Recurso de Apelación (RAP)',
    }
    return render(request, 'tpe_app/admin2/registrar_rap.html', context)


# ============================================================
# DOCUMENTO DEL RECURRENTE (incidente / recurso fuera plazo / amparo)
# ============================================================
@rol_requerido('ADMIN2_ARCHIVO', 'ADMINISTRADOR', 'MASTER')
def admin2_buscar_sim_doc_recurrente(request):
    """Buscador de SIMs (cualquier estado, incluso archivados) para registrar
    un documento del recurrente. Permite registrar contra SIMs ya archivados en SPRODA
    cuando llega un amparo constitucional u otro documento años después."""

    query = (request.GET.get('q') or '').strip()
    resultados = None

    if query:
        from django.db.models import Q
        resultados = (
            SIM.objects
            .filter(
                Q(codigo__icontains=query) |
                Q(militares__paterno__icontains=query.upper()) |
                Q(militares__nombre__icontains=query.upper()) |
                Q(militares__ci__icontains=query)
            )
            .prefetch_related('militares')
            .distinct()
            .order_by('-fecha_ingreso')[:30]
        )

    return render(request, 'tpe_app/admin2/buscar_sim_doc_recurrente.html', {
        'query': query,
        'resultados': resultados,
        'titulo': 'Buscar SIM para registrar Memorial Presentado',
    })


@rol_requerido('ADMIN2_ARCHIVO', 'ADMINISTRADOR', 'MASTER')
def admin2_registrar_documento_recurrente(request, sim_id):
    """Admin2 registra un documento presentado por el recurrente (incidente,
    recurso fuera de plazo o amparo constitucional). No modifica la fase del SIM."""

    sim = get_object_or_404(SIM, pk=sim_id)

    if request.method == 'POST':
        form = DocumentoRecurrenteForm(request.POST, sim=sim)
        if form.is_valid():
            try:
                with transaction.atomic():
                    doc = form.save(commit=False)
                    doc.sim = sim
                    doc.save()
                messages.success(
                    request,
                    f'✅ Memorial de {doc.get_tipo_display()} registrado (NTD {doc.ntd}). '
                    f'Admin1 debe asignar abogado.'
                )
                return redirect('admin2_dashboard')
            except Exception as e:
                messages.error(request, f'❌ Error al registrar documento: {e}')
    else:
        form = DocumentoRecurrenteForm(sim=sim)

    context = {
        'form':  form,
        'sim':   sim,
        'titulo': 'Registrar Memorial Presentado',
    }
    return render(request, 'tpe_app/admin2/documento_recurrente_form.html', context)


@rol_requerido('ADMIN2_ARCHIVO')
def admin2_registrar_salida_tsp(request, rap_id):
    """Admin2 registra la salida del RAP al TSP con número y fecha de oficio"""

    rap = get_object_or_404(ApelacionTSP, pk=rap_id)

    if request.method == 'POST':
        numero_oficio = request.POST.get('numero_oficio', '').strip()
        fecha_oficio_str = request.POST.get('fecha_oficio', '').strip()

        if not numero_oficio or not fecha_oficio_str:
            messages.error(request, '❌ Número y fecha de oficio son obligatorios.')
        else:
            try:
                fecha_oficio = datetime.strptime(fecha_oficio_str, '%Y-%m-%d').date()

                with transaction.atomic():
                    # Actualizar el RAP con número y fecha de oficio
                    rap.numero_oficio = numero_oficio
                    rap.fecha_oficio = fecha_oficio
                    rap.save()

                    # Cerrar custodia actual de Admin2
                    custodia_admin2 = rap.sim.custodias.filter(
                        tipo_custodio='ADMIN2_ARCHIVO',
                        fecha_entrega__isnull=True
                    ).first()

                    if custodia_admin2:
                        custodia_admin2.fecha_entrega = timezone.now()
                        custodia_admin2.save()

                    # Crear custodia TSP
                    CustodiaSIM.objects.create(
                        sim=rap.sim,
                        tipo_custodio='TSP',
                        motivo='APELACION_TSP',
                        nro_oficio=numero_oficio,
                        fecha_oficio=fecha_oficio,
                        usuario=request.user,
                        estado='RECIBIDA_CONFORME',
                        observacion=f'RAP {rap.numero} elevado al TSP'
                    )

                    # Cambiar fase a ELEVADO_TSP → PROCESO_EN_EL_TSP
                    sim = rap.sim
                    sim.fase = 'ELEVADO_TSP'
                    sim.save()

                    messages.success(
                        request,
                        f'✅ RAP {rap.numero} elevado al TSP con Oficio {numero_oficio} ({fecha_oficio.strftime("%d/%m/%Y")})'
                    )
                    return redirect('admin2_dashboard')
            except ValueError:
                messages.error(request, '❌ Formato de fecha inválido.')
            except Exception as e:
                messages.error(request, f'❌ Error: {str(e)}')

    context = {
        'rap': rap,
        'sim': rap.sim,
        'pm': rap.pm,
    }
    return render(request, 'tpe_app/admin2/registrar_salida_tsp.html', context)


# ============================================================
# ADMIN2: ANULAR ENTREGA DE CUSTODIA (Huérfanas)
# ============================================================
@rol_requerido('ADMIN2_ARCHIVO')
def anular_entrega_custodia(request, custodia_id):
    """Anular una entrega de custodia si el receptor no confirmó (> 24h sin confirmar).

    Caso: Admin2 entregó un SIM a un Abogado, éste nunca confirmó recepción.
    Acción: Revertir a custodia anterior (vuelve a Admin2).
    """
    custodia = get_object_or_404(CustodiaSIM, pk=custodia_id)
    sim = custodia.sim

    # Solo puede anular custodias en estado PENDIENTE_CONFIRMACION
    if custodia.estado != 'PENDIENTE_CONFIRMACION':
        messages.error(request, '❌ Solo se pueden anular custodias pendientes de confirmación.')
        return redirect('admin2_dashboard')

    try:
        with transaction.atomic():
            # Buscar la custodia anterior (la más reciente antes de ésta)
            custodia_anterior = CustodiaSIM.objects.filter(
                sim=sim,
                fecha_recepcion__lt=custodia.fecha_recepcion
            ).order_by('-fecha_recepcion').first()

            # Cancelar la custodia pendiente
            custodia.estado = 'CANCELADA'
            custodia.save()

            # Si hay custodia anterior, reactivarla
            if custodia_anterior:
                custodia_anterior.estado = 'ACTIVA'
                custodia_anterior.save()
                destino_txt = f'{custodia_anterior.tipo_custodio}'
            else:
                # Si no hay anterior, vuelve a Admin2
                custodia_nueva = CustodiaSIM.objects.create(
                    sim=sim,
                    tipo_custodio='ADMIN2_ARCHIVO',
                    estado='ACTIVA',
                    usuario=request.user,
                    observacion='Recuperada por anulación de entrega pendiente'
                )
                destino_txt = 'Admin2 (Archivo)'

            messages.success(
                request,
                f'✅ Entrega anulada: {sim.codigo} retorna a {destino_txt}'
            )
    except Exception as e:
        messages.error(request, f'❌ Error al anular: {str(e)}')

    return redirect('admin2_dashboard')


# ============================================================
# REGISTRO DE RECURSO DE RECONSIDERACIÓN (RR)
# ============================================================

@rol_requerido('ADMIN2_ARCHIVO', 'MASTER', 'ADMINISTRADOR')
def registrar_rr(request):
    """Formulario para registrar un Recurso de Reconsideración (Resolucion RECONSIDERACION)"""
    if request.method == 'POST':
        form = RegistrarRRForm(request.POST)
        if form.is_valid():
            rr = form.save(commit=False)
            rr.instancia = 'RECONSIDERACION'
            rr.sim = rr.resolucion_origen.sim
            rr.pm = rr.resolucion_origen.pm or rr.sim.militares.first()
            rr.numero = None
            rr.save()

            sim = rr.sim
            if sim.fase in ['1RA_RESOLUCION', 'NOTIFICADO_1RA', 'EN_ESPERA_RR']:
                sim.fase = 'PARA_AGENDA_RR'
                sim.save()

            CustodiaSIM.objects.create(
                sim=rr.sim,
                tipo_custodio='ADMIN2_ARCHIVO',
                usuario=request.user,
                motivo='AGENDA',
            )

            messages.success(request, '✅ Recurso de Reconsideración registrado. Admin1 deberá agendarlo con un abogado.')
            return redirect('admin2_dashboard')
        else:
            messages.error(request, '❌ Por favor corrija los errores en el formulario')
    else:
        form = RegistrarRRForm()

    return render(request, 'tpe_app/admin2/registrar_rr.html', {'form': form})
