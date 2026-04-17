from datetime import date

from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from ..decorators import rol_requerido
from ..models import ABOG_SIM, AGENDA, AUTOTPE, DICTAMEN, DocumentoAdjunto, PM, RES, RR, SIM, VOCAL_TPE, CustodiaSIM
from ..utils.numeracion import next_num_yy


def _get_abogado_or_403(request):
    perfil = getattr(request.user, "perfilusuario", None)
    if not perfil or not getattr(perfil, "abogado", None):
        raise Http404
    return perfil.abogado


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_sumario_detalle(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(
        SIM.objects.prefetch_related('militares'),
        pk=sim_id,
    )

    dictamenes       = DICTAMEN.objects.filter(sim=sim).select_related("agenda", "abog").order_by("-id")
    resoluciones     = list(RES.objects.filter(sim=sim).select_related("agenda", "abog", "dictamen").order_by("-RES_FEC"))
    reconsideraciones = RR.objects.filter(sim=sim).select_related("res", "agenda", "abog").order_by("-RR_FEC")
    autos_tpe        = AUTOTPE.objects.filter(sim=sim).select_related("agenda", "abog").order_by("-TPE_FEC", "-id")

    # Adjuntar PDF a cada RES y AUTOTPE
    for res in resoluciones:
        doc = DocumentoAdjunto.objects.filter(DOC_TABLA='res', DOC_ID_REG=res.pk).first()
        res.pdf_url = doc.DOC_RUTA.url if doc else None

    autos_tpe = list(autos_tpe)
    for auto in autos_tpe:
        doc = DocumentoAdjunto.objects.filter(DOC_TABLA='autotpe', DOC_ID_REG=auto.pk).first()
        auto.pdf_url = doc.DOC_RUTA.url if doc else None

    # Determinar el rol del abogado en este SIM:
    # es_via_sim → asignado directamente al SIM (Etapa 1, acceso completo)
    # rrs_asignados → asignado por RR (Etapa 2, solo puede operar sobre sus propios documentos)
    es_via_sim = sim.abogados.filter(pk=abogado.pk).exists()
    rrs_asignados = list(RR.objects.filter(sim=sim, abog=abogado).select_related("res").order_by("-RR_FEC"))

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

    context = {
        "sim": sim,
        "abogado": abogado,
        "abogados_asignados": ABOG_SIM.objects.filter(sim=sim).select_related('abog'),
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
    }
    return render(request, "tpe_app/abogado/sumario_detalle.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_dictamen_crear(request, sim_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM.objects.prefetch_related('militares'), pk=sim_id)

    # Verificar que el abogado esté asignado al SIM (no requiere custodia)
    if not sim.abogados.filter(pk=abogado.pk).exists():
        rr_asignado = RR.objects.filter(sim=sim, abog=abogado).exists()
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
                    existentes = list(RES.objects.values_list("RES_NUM", flat=True))
                    res_num = next_num_yy(existentes, today=date.today())

                    RES.objects.create(
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
        "tipos": RES.TIPO_CHOICES,
    }
    return render(request, "tpe_app/abogado/res_form.html", context)


@rol_requerido("ABOGADO", "ABOG1_ASESOR", "ABOG2_AUTOS", "ABOG3_BUSCADOR")
def abogado_rr_crear(request, sim_id: int, res_id: int):
    abogado = _get_abogado_or_403(request)
    sim = get_object_or_404(SIM, pk=sim_id)
    res = get_object_or_404(RES, pk=res_id, sim=sim)

    if request.method == "POST":
        rr_fec = request.POST.get("RR_FEC") or ""
        rr_resum = (request.POST.get("RR_RESUM") or "").strip()
        rr_resol = (request.POST.get("RR_RESOL") or "").strip()
        autogen = request.POST.get("autogenerar_numero") == "1"

        try:
            with transaction.atomic():
                rr_num = None
                if autogen:
                    existentes = list(RR.objects.values_list("RR_NUM", flat=True))
                    rr_num = next_num_yy(existentes, today=date.today())

                RR.objects.create(
                    sim=sim,
                    res=res,
                    agenda=res.agenda,
                    abog=abogado,
                    RR_NUM=rr_num,
                    RR_FEC=rr_fec or None,
                    RR_RESUM=rr_resum or None,
                    RR_RESOL=rr_resol or None,
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
