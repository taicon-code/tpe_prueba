from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.utils import timezone

from ..decorators import rol_requerido
from ..models import AGENDA, SIM, DICTAMEN, Resolucion, AUTOTPE, PerfilUsuario


def _get_asesor_jefe_or_403(request):
    """Obtiene el perfil ASESOR_JEFE del usuario actual, o None si no está vinculado"""
    perfil = getattr(request.user, "perfilusuario", None)
    return perfil if perfil and perfil.rol == 'ASESOR_JEFE' else None


@rol_requerido("ASESOR_JEFE")
def asesor_jefe_dashboard(request):
    """Dashboard principal del Asesor Jefe - Supervisor del sistema"""
    asesor = _get_asesor_jefe_or_403(request)

    # Próximas agendas (próximos 30 días)
    hoy = date.today()
    fecha_limite = hoy + timedelta(days=30)

    proximas_agendas = AGENDA.objects.filter(
        AG_FECPROG__gte=hoy,
        AG_FECPROG__lte=fecha_limite
    ).order_by('AG_FECPROG')

    # Enriquecer agendas con información
    for agenda in proximas_agendas:
        agenda.sims_count = SIM.objects.filter(
            dictamen__agenda=agenda
        ).distinct().count()
        agenda.dictamenes_pendientes = DICTAMEN.objects.filter(
            agenda=agenda, DIC_ESTADO='PENDIENTE'
        ).count()

    # Resumen de estados
    resumen = {
        'para_agenda': SIM.objects.filter(SIM_ESTADO='PARA_AGENDA').count(),
        'en_proceso': SIM.objects.filter(SIM_ESTADO='PROCESO_EN_EL_TPE').count(),
        'en_apelacion': SIM.objects.filter(SIM_ESTADO='EN_APELACION_TSP').count(),
        'concluido': SIM.objects.filter(SIM_ESTADO='PROCESO_CONCLUIDO_TPE').count(),
    }

    # Estadísticas del mes
    mes_actual = hoy.replace(day=1)
    siguiente_mes = (mes_actual + timedelta(days=32)).replace(day=1)

    estadisticas = {
        'sims_ingresados_mes': SIM.objects.filter(
            SIM_FECING__gte=mes_actual,
            SIM_FECING__lt=siguiente_mes
        ).count(),
        'resoluciones_mes': Resolucion.objects.filter(
            RES_FEC__gte=mes_actual,
            RES_FEC__lt=siguiente_mes,
            RES_INSTANCIA='PRIMERA'
        ).count(),
        'autos_mes': AUTOTPE.objects.filter(
            TPE_FEC__gte=mes_actual,
            TPE_FEC__lt=siguiente_mes
        ).count(),
    }

    context = {
        'asesor': asesor,
        'proximas_agendas': proximas_agendas,
        'resumen': resumen,
        'estadisticas': estadisticas,
        'hoy': hoy,
    }

    return render(request, 'tpe_app/asesor_jefe/dashboard.html', context)


@rol_requerido("ASESOR_JEFE")
def asesor_jefe_agendas(request):
    """Monitoreo detallado de próximas agendas del mes"""
    asesor = _get_asesor_jefe_or_403(request)
    hoy = date.today()
    mes_actual = hoy.replace(day=1)
    siguiente_mes = (mes_actual + timedelta(days=32)).replace(day=1)

    agendas = AGENDA.objects.filter(
        AG_FECPROG__gte=mes_actual,
        AG_FECPROG__lt=siguiente_mes
    ).order_by('AG_FECPROG')

    # Enriquecer agendas
    for agenda in agendas:
        sims = SIM.objects.filter(
            dictamen__agenda=agenda
        ).distinct()
        agenda.sims = sims
        agenda.sims_count = sims.count()
        agenda.militares_count = sum(
            pm_sim_set.count() for pm_sim_set in [sim.pm_sim.all() for sim in sims]
        )
        agenda.dictamenes_pendientes = DICTAMEN.objects.filter(
            agenda=agenda, DIC_ESTADO='PENDIENTE'
        ).count()
        agenda.dictamenes_confirmados = DICTAMEN.objects.filter(
            agenda=agenda
        ).exclude(DIC_ESTADO='PENDIENTE').count()

    context = {
        'asesor': asesor,
        'agendas': agendas,
        'mes': mes_actual.strftime('%B %Y'),
    }

    return render(request, 'tpe_app/asesor_jefe/agendas.html', context)


@rol_requerido("ASESOR_JEFE")
def asesor_jefe_estadisticas(request):
    """Estadísticas globales del tribunal"""
    asesor = _get_asesor_jefe_or_403(request)

    # Totales generales
    total_sims = SIM.objects.count()
    sims_por_estado = {}
    for estado, _ in SIM._meta.get_field('SIM_ESTADO').choices:
        count = SIM.objects.filter(SIM_ESTADO=estado).count()
        sims_por_estado[estado] = count

    # Resoluciones
    total_res = Resolucion.objects.filter(RES_INSTANCIA='PRIMERA').count()
    res_notificadas = Resolucion.objects.filter(
        RES_INSTANCIA='PRIMERA', RES_FECNOT__isnull=False
    ).count()

    # Autos
    total_autos = AUTOTPE.objects.count()
    autos_por_tipo = {}
    for tipo, _ in AUTOTPE._meta.get_field('TPE_TIPO').choices:
        count = AUTOTPE.objects.filter(TPE_TIPO=tipo).count()
        if count > 0:
            autos_por_tipo[tipo] = count

    # Estadísticas por mes (últimos 12 meses)
    hoy = date.today()
    estadisticas_mensuales = []
    for i in range(11, -1, -1):
        mes_fecha = hoy - timedelta(days=30*i)
        mes_inicio = mes_fecha.replace(day=1)
        mes_fin = (mes_fecha.replace(day=1) + timedelta(days=32)).replace(day=1)

        sims_mes = SIM.objects.filter(
            SIM_FECING__gte=mes_inicio,
            SIM_FECING__lt=mes_fin
        ).count()

        res_mes = Resolucion.objects.filter(
            RES_FEC__gte=mes_inicio,
            RES_FEC__lt=mes_fin,
            RES_INSTANCIA='PRIMERA'
        ).count()

        autos_mes = AUTOTPE.objects.filter(
            TPE_FEC__gte=mes_inicio,
            TPE_FEC__lt=mes_fin
        ).count()

        estadisticas_mensuales.append({
            'mes': mes_inicio.strftime('%b %Y'),
            'sims': sims_mes,
            'resoluciones': res_mes,
            'autos': autos_mes,
        })

    context = {
        'asesor': asesor,
        'total_sims': total_sims,
        'sims_por_estado': sims_por_estado,
        'total_res': total_res,
        'res_notificadas': res_notificadas,
        'total_autos': total_autos,
        'autos_por_tipo': autos_por_tipo,
        'estadisticas_mensuales': estadisticas_mensuales,
    }

    return render(request, 'tpe_app/asesor_jefe/estadisticas.html', context)
