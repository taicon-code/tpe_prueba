from datetime import date

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..decorators import rol_requerido
from ..models import (
    ABOG_SIM, AGENDA, AUTOTPE, DICTAMEN, DocumentoAdjunto, PM, SIM, VOCAL_TPE,
    CustodiaSIM, Resolucion, next_resolucion_num,
)
from ..utils.numeracion import next_num_yy


def _get_abogado_or_403(request):
    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil or not getattr(perfil, "abogado", None):
        raise PermissionDenied()
    return perfil.abogado


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_sumario_detalle(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(
        SIM.objects.prefetch_related('militares'),
        pk=sim_id,
    )

    dictamenes       = DICTAMEN.objects.filter(sim=sim).select_related("agenda", "abog").order_by("-id")
    resoluciones     = list(
        Resolucion.objects.filter(sim=sim, RES_INSTANCIA='PRIMERA')
        .select_related("agenda", "abog", "dictamen").order_by("-RES_FEC")
    )
    reconsideraciones = Resolucion.objects.filter(
        sim=sim, RES_INSTANCIA='RECONSIDERACION'
    ).select_related("resolucion_origen", "agenda", "abog").order_by("-RES_FEC")
    autos_tpe        = AUTOTPE.objects.filter(sim=sim).select_related("agenda", "abog").order_by("-TPE_FEC", "-id")

    # Adjuntar PDF a cada Resolucion y AUTOTPE
    for res in resoluciones:
        doc = DocumentoAdjunto.objects.filter(DOC_TABLA='resolucion', DOC_ID_REG=res.pk).first()
        res.pdf_url = doc.DOC_RUTA.url if doc else None

    autos_tpe = list(autos_tpe)
    for auto in autos_tpe:
        doc = DocumentoAdjunto.objects.filter(DOC_TABLA='autotpe', DOC_ID_REG=auto.pk).first()
        auto.pdf_url = doc.DOC_RUTA.url if doc else None

    # Determinar el rol del abogado en este SIM:
    # es_via_sim → asignado directamente al SIM (Etapa 1, acceso completo)
    # rrs_asignados → asignado por RR (Etapa 2, solo puede operar sobre sus propios documentos)
    es_via_sim = sim.abogados.filter(pk=abogado.pk).exists()
    rrs_asignados = list(
        Resolucion.objects.filter(sim=sim, RES_INSTANCIA='RECONSIDERACION', abog=abogado)
        .select_related("resolucion_origen").order_by("-RES_FEC")
    )

    # Verificar si este abogado es el responsable de la carpeta
    es_responsable = ABOG_SIM.objects.filter(
        sim=sim, abog=abogado, es_responsable=True
    ).exists()

    # Custodia activa (solo relevante para el responsable — botón entregar)
    tiene_custodia = CustodiaSIM.objects.filter(
        sim=sim,
        fecha_entrega__isnull=True,
        abog=abogado
    ).exists()
    custodio_actual = sim.custodio_actual()

    # Documentos adjuntos al SIM (PDFs escaneados)
    documentos_sim = DocumentoAdjunto.objects.filter(
        DOC_TABLA='sim', DOC_ID_REG=sim.pk
    ).order_by('-id')

    # Identificar si el abogado es ABOG2 (ejecutoria)
    perfil = getattr(request.user, 'perfilusuario', None)
    es_abog2 = perfil and perfil.rol == 'ABOG2_AUTOS'

    # Para Abog2: verificar acceso via autos asignados
    autos_asignados = [a for a in autos_tpe if a.abog_id == abogado.pk]

    # Validar acceso: Abog2 solo puede ver si tiene autos asignados
    if es_abog2 and not autos_asignados and not es_via_sim and not rrs_asignados:
        raise PermissionDenied("No tiene autos asignados en este sumario")

    context = {
        "sim": sim,
        "abogado": abogado,
        "abogados_asignados": ABOG_SIM.objects.filter(sim=sim, es_responsable=True).select_related('abog'),
        "investigados": sim.militares.all(),
        "dictamenes": dictamenes,
        "resoluciones": resoluciones,
        "reconsideraciones": reconsideraciones,
        "autos_tpe": autos_tpe,
        "es_via_sim": es_via_sim,
        "rrs_asignados": rrs_asignados,
        "es_responsable": es_responsable,
        "tiene_custodia": tiene_custodia,
        "custodio_actual": custodio_actual,
        "documentos_sim": documentos_sim,
        "es_abog2": es_abog2,
        "autos_asignados": autos_asignados,
    }
    return render(request, "tpe_app/abogado/sumario_detalle.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_dictamen_crear(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM.objects.prefetch_related('militares'), pk=sim_id)

    # Verificar que el abogado esté asignado al SIM (no requiere custodia)
    if not sim.abogados.filter(pk=abogado.pk).exists():
        rr_asignado = Resolucion.objects.filter(
            sim=sim, abog=abogado, RES_INSTANCIA='RECONSIDERACION'
        ).exists()
        if not rr_asignado:
            messages.error(request, "❌ No está asignado a este sumario.")
            return redirect("abogado_sumario_detalle", sim_id=sim.pk)

    militares = list(sim.militares.all())
    agendas = AGENDA.objects.all().order_by("-AG_FECPROG")

    if request.method == "POST":
        agenda_id = request.POST.get("agenda") or ""

        if not agenda_id:
            messages.error(request, "Seleccione una agenda.")
        else:
            agenda = get_object_or_404(AGENDA, pk=agenda_id)
            autogenerar = request.POST.get("autogenerar_numero") == "1"

            try:
                with transaction.atomic():
                    dictamenes_creados = 0

                    if militares:
                        # Crear un dictamen por cada militar del sumario
                        for pm in militares:
                            conclusion = (request.POST.get(f"DIC_CONCL_{pm.pk}") or "").strip()
                            dic_num = None

                            if autogenerar:
                                existentes = list(
                                    DICTAMEN.objects.filter(DIC_NUM__isnull=False)
                                    .values_list("DIC_NUM", flat=True)
                                )
                                dic_num = next_num_yy(existentes, today=date.today())

                            DICTAMEN.objects.create(
                                agenda=agenda,
                                sim=sim,
                                abog=abogado,
                                pm=pm,
                                DIC_NUM=dic_num,
                                DIC_CONCL=conclusion or None,
                            )
                            dictamenes_creados += 1
                    else:
                        # Fallback: si no hay militares, crear un dictamen sin PM
                        conclusion = (request.POST.get("DIC_CONCL") or "").strip()
                        dic_num = None

                        if autogenerar:
                            existentes = list(
                                DICTAMEN.objects.filter(DIC_NUM__isnull=False)
                                .values_list("DIC_NUM", flat=True)
                            )
                            dic_num = next_num_yy(existentes, today=date.today())

                        DICTAMEN.objects.create(
                            agenda=agenda,
                            sim=sim,
                            abog=abogado,
                            DIC_NUM=dic_num,
                            DIC_CONCL=conclusion or None,
                        )
                        dictamenes_creados = 1

                messages.success(request, f"✅ {dictamenes_creados} dictamen(es) creado(s).")
                return redirect("abogado_sumario_detalle", sim_id=sim.pk)
            except Exception as exc:
                messages.error(request, f"❌ Error al crear dictamen: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "agendas": agendas,
        "militares": militares,
    }
    return render(request, "tpe_app/abogado/dictamen_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_res_crear(request, sim_id: int, dictamen_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    dictamen = get_object_or_404(DICTAMEN, pk=dictamen_id, sim=sim)

    # Seguridad: solo puede crear RES desde un dictamen propio si accede via RR (Etapa 2)
    es_via_sim = sim.abogados.filter(pk=abogado.pk).exists()
    if not es_via_sim and dictamen.abog != abogado:
        messages.error(request, "No tiene autorización para crear una RES desde este dictamen.")
        return redirect("abogado_sumario_detalle", sim_id=sim.pk)

    if request.method == "POST":
        res_fec = request.POST.get("RES_FEC") or ""
        res_tipo = request.POST.get("RES_TIPO") or ""
        res_resol = (request.POST.get("RES_RESOL") or "").strip()

        if not res_fec or not res_tipo or not res_resol:
            messages.error(request, "Complete Fecha, Tipo y Resolución.")
        else:
            try:
                with transaction.atomic():
                    res_num = next_resolucion_num()

                    Resolucion.objects.create(
                        RES_INSTANCIA='PRIMERA',
                        sim=sim,
                        abog=abogado,
                        agenda=dictamen.agenda if dictamen.agenda_id else None,
                        dictamen=dictamen,
                        pm=dictamen.pm,
                        RES_NUM=res_num,
                        RES_FEC=res_fec,
                        RES_TIPO=res_tipo,
                        RES_RESOL=res_resol,
                    )
                messages.success(request, f"✅ RES creada ({res_num}).")
                return redirect("abogado_sumario_detalle", sim_id=sim.pk)
            except Exception as exc:
                messages.error(request, f"❌ Error al crear RES: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "dictamen": dictamen,
        "tipos": Resolucion.TIPO_CHOICES,
    }
    return render(request, "tpe_app/abogado/res_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_rr_crear(request, sim_id: int, res_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    res = get_object_or_404(Resolucion, pk=res_id, sim=sim, RES_INSTANCIA='PRIMERA')

    if request.method == "POST":
        rr_fec = request.POST.get("RR_FEC") or ""
        rr_resum = (request.POST.get("RR_RESUM") or "").strip() or None
        rr_resol = (request.POST.get("RR_RESOL") or "").strip()
        autogen = request.POST.get("autogenerar_numero") == "1"

        try:
            with transaction.atomic():
                rr_num = next_resolucion_num() if autogen else None

                Resolucion.objects.create(
                    RES_INSTANCIA='RECONSIDERACION',
                    sim=sim,
                    resolucion_origen=res,
                    agenda=res.agenda,
                    abog=abogado,
                    pm=res.pm,
                    RES_NUM=rr_num or '',
                    RES_FEC=rr_fec or None,
                    RES_RESUM=rr_resum,
                    RES_RESOL=rr_resol or None,
                )
            messages.success(request, f"✅ RR creada ({rr_num or 'S/N'}).")
            return redirect("abogado_sumario_detalle", sim_id=sim.pk)
        except Exception as exc:
            messages.error(request, f"❌ Error al crear RR: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "res": res,
    }
    return render(request, "tpe_app/abogado/rr_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_autotpe_crear(request, sim_id: int, dictamen_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    dictamen = get_object_or_404(DICTAMEN, pk=dictamen_id, sim=sim)

    # Seguridad: solo puede crear Auto desde un dictamen propio si accede via RR (Etapa 2)
    es_via_sim = sim.abogados.filter(pk=abogado.pk).exists()
    if not es_via_sim and dictamen.abog != abogado:
        messages.error(request, "No tiene autorización para crear un Auto desde este dictamen.")
        return redirect("abogado_sumario_detalle", sim_id=sim.pk)

    if request.method == "POST":
        tpe_fec = request.POST.get("TPE_FEC") or ""
        tpe_tipo = request.POST.get("TPE_TIPO") or ""
        tpe_resol = (request.POST.get("TPE_RESOL") or "").strip()
        autogen = request.POST.get("autogenerar_numero") == "1"

        try:
            with transaction.atomic():
                tpe_num = None
                if autogen:
                    existentes = list(AUTOTPE.objects.values_list("TPE_NUM", flat=True))
                    tpe_num = next_num_yy(existentes, today=date.today())

                AUTOTPE.objects.create(
                    sim=sim,
                    abog=abogado,
                    agenda=dictamen.agenda if dictamen.agenda_id else None,
                    TPE_NUM=tpe_num,
                    TPE_FEC=tpe_fec or None,
                    TPE_TIPO=tpe_tipo or None,
                    TPE_RESOL=tpe_resol or None,
                )
            messages.success(request, f"✅ Auto TPE creado ({tpe_num or 'S/N'}).")
            return redirect("abogado_sumario_detalle", sim_id=sim.pk)
        except Exception as exc:
            messages.error(request, f"❌ Error al crear Auto TPE: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "dictamen": dictamen,
        "tipos": AUTOTPE.TIPO_CHOICES,
    }
    return render(request, "tpe_app/abogado/autotpe_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_auto_excusa_crear(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)

    # Cargar vocales activos
    vocales = VOCAL_TPE.objects.filter(activo=True).select_related("pm")
    agendas = AGENDA.objects.all().order_by("-AG_FECPROG")

    if request.method == "POST":
        vocal_id = request.POST.get("vocal_id") or ""
        agenda_id = request.POST.get("agenda") or ""
        fecha_str = request.POST.get("TPE_FEC") or ""
        resolucion = (request.POST.get("TPE_RESOL") or "").strip()

        if not vocal_id or not agenda_id or not fecha_str:
            messages.error(request, "Complete Vocal, Agenda y Fecha.")
        else:
            try:
                vocal = get_object_or_404(VOCAL_TPE, pk=vocal_id, activo=True)
                agenda = get_object_or_404(AGENDA, pk=agenda_id)

                with transaction.atomic():
                    tpe_num = None

                    if request.POST.get("autogenerar_numero") == "1":
                        existentes = list(
                            AUTOTPE.objects.filter(TPE_NUM__isnull=False)
                            .values_list("TPE_NUM", flat=True)
                        )
                        tpe_num = next_num_yy(existentes, today=date.today())

                    auto = AUTOTPE.objects.create(
                        sim=sim,
                        abog=abogado,
                        agenda=agenda,
                        vocal_excusado=vocal,
                        TPE_NUM=tpe_num,
                        TPE_FEC=fecha_str,
                        TPE_TIPO="AUTO_EXCUSA",
                        TPE_RESOL=resolucion or None,
                    )

                messages.success(request, f"✅ Auto de Excusa creado ({tpe_num or 'S/N'}).")
                return redirect("abogado_sumario_detalle", sim_id=sim.pk)
            except Exception as exc:
                messages.error(request, f"❌ Error al crear Auto de Excusa: {exc}")

    context = {
        "sim": sim,
        "abogado": abogado,
        "vocales": vocales,
        "agendas": agendas,
    }
    return render(request, "tpe_app/abogado/auto_excusa_form.html", context)


# ============================================================
# CUSTODIA: Confirmación y devolución de carpetas
# ============================================================

@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_confirmar_recepcion(request, sim_id: int):
    """El abogado confirma que recibió la carpeta física de Admin2"""
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)

    custodia = CustodiaSIM.objects.filter(
        sim=sim, abog=abogado, estado='PENDIENTE_CONFIRMACION', fecha_entrega__isnull=True
    ).first()

    if not custodia:
        messages.error(request, "❌ No hay carpeta pendiente de confirmación")
        return redirect('abogado_sumario_detalle', sim_id=sim_id)

    if request.method == 'POST':
        try:
            custodia.estado = 'ACTIVA'
            custodia.save()
            messages.success(request, "✅ Recepción confirmada. La carpeta está en su poder.")
            return redirect('abogado_sumario_detalle', sim_id=sim_id)
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")

    return render(request, 'tpe_app/abogado/confirmar_recepcion.html', {'sim': sim, 'custodia': custodia})


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_devolver_carpeta(request, sim_id: int):
    """El abogado devuelve la carpeta a Admin2"""
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)

    custodia = CustodiaSIM.objects.filter(
        sim=sim, abog=abogado, estado='ACTIVA', fecha_entrega__isnull=True
    ).first()

    if not custodia:
        messages.error(request, "❌ No tiene la carpeta en su poder")
        return redirect('abogado_sumario_detalle', sim_id=sim_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Cerrar custodia del abogado
                custodia.fecha_entrega = timezone.now()
                custodia.save()

                # Crear nueva custodia con Admin2 pendiente de confirmación
                CustodiaSIM.objects.create(
                    sim=sim,
                    tipo_custodio='ADMIN2_ARCHIVO',
                    usuario=request.user,
                    motivo='REVISION',
                    estado='PENDIENTE_CONFIRMACION',
                )

            messages.success(request, "✅ Carpeta devuelta. Admin2 debe confirmar la recepción.")
            return redirect('abogado_sumario_detalle', sim_id=sim_id)
        except Exception as e:
            messages.error(request, f"❌ Error: {str(e)}")

    return render(request, 'tpe_app/abogado/devolver_carpeta.html', {'sim': sim, 'custodia': custodia})
