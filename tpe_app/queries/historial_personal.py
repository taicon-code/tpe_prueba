# ============================================================
#  CONSULTAS PARA OBTENER HISTORIAL DE PERSONAL MILITAR
#  Archivo: tpe_app/queries/historial_personal.py
# ============================================================

from django.db.models import Q, Prefetch
from tpe_app.models import PM, PM_SIM, SIM, RES, RR, RAP, RAEE, AUTOTPE, AUTOTSP


class ConsultasHistorialPersonal:
    """
    Consultas para obtener el historial disciplinario de un personal militar.
    """

    @staticmethod
    def buscar_personal(nombre=None, apellido_paterno=None, apellido_materno=None, ci=None):
        """
        Busca personal por nombre, apellidos o cédula de identidad.
        
        Args:
            nombre (str): Nombre del personal
            apellido_paterno (str): Apellido paterno
            apellido_materno (str): Apellido materno
            ci (str): Cédula de identidad
        
        Returns:
            QuerySet: Personal militar encontrado
        
        Ejemplos:
            >>> ConsultasHistorialPersonal.buscar_personal(nombre="Juan")
            >>> ConsultasHistorialPersonal.buscar_personal(apellido_paterno="García")
            >>> ConsultasHistorialPersonal.buscar_personal(
            ...     apellido_paterno="García",
            ...     apellido_materno="López",
            ...     nombre="Juan"
            ... )
            >>> ConsultasHistorialPersonal.buscar_personal(ci="1234567")
        """
        queryset = PM.objects.all()
        
        if ci:
            queryset = queryset.filter(PM_CI=ci)
        else:
            if nombre:
                queryset = queryset.filter(PM_NOMBRE__icontains=nombre)
            if apellido_paterno:
                queryset = queryset.filter(PM_PATERNO__icontains=apellido_paterno)
            if apellido_materno:
                queryset = queryset.filter(PM_MATERNO__icontains=apellido_materno)
        
        return queryset.order_by('PM_PATERNO', 'PM_MATERNO', 'PM_NOMBRE')

    @staticmethod
    def obtener_sumarios_de_personal(personal_id):
        """
        Obtiene todos los sumarios (SIM) donde está involucrado un personal.
        
        Args:
            personal_id (int): ID del personal (PM)
        
        Returns:
            QuerySet: Sumarios relacionados al personal
        
        Ejemplo:
            >>> personal = PM.objects.first()
            >>> ConsultasHistorialPersonal.obtener_sumarios_de_personal(personal.id)
        """
        return SIM.objects.filter(
            militares__pm_id=personal_id
        ).prefetch_related('pm_sim_set').distinct()

    @staticmethod
    def obtener_historial_completo(personal_id):
        """
        Obtiene el historial COMPLETO de un personal en el sistema TPE/TSP.
        
        Incluye:
        - Sumarios (SIM)
        - Resoluciones (RES)
        - Segundas Resoluciones (RR)
        - Recursos de Apelación (RAP)
        - RAEE
        - Autos TPE
        - Autos TSP
        
        Args:
            personal_id (int): ID del personal
        
        Returns:
            dict: Diccionario con todo el historial
        
        Ejemplo:
            >>> personal = PM.objects.first()
            >>> historial = ConsultasHistorialPersonal.obtener_historial_completo(personal.id)
            >>> print(historial['sumarios'].count())
            >>> print(historial['resoluciones'].count())
        """
        # Obtener el personal
        try:
            personal = PM.objects.get(pm_id=personal_id)
        except PM.DoesNotExist:
            return None
        
        # Obtener todos los SIM donde participa este personal
        sims = SIM.objects.filter(militares__pm_id=personal_id).distinct()
        sim_ids = list(sims.values_list('id', flat=True))
        
        historial = {
            'personal': personal,
            'sumarios': sims,
            'resoluciones': RES.objects.filter(ID_SIM__in=sim_ids),
            'segundas_resoluciones': RR.objects.filter(ID_SIM__in=sim_ids),
            'recursos_apelacion': RAP.objects.filter(ID_SIM__in=sim_ids),
            'raees': RAEE.objects.filter(ID_SIM__in=sim_ids),
            'autos_tpe': AUTOTPE.objects.filter(ID_SIM__in=sim_ids),
            'autos_tsp': AUTOTSP.objects.filter(ID_SIM__in=sim_ids),
        }
        
        return historial

    @staticmethod
    def obtener_historial_formateado(personal_id):
        """
        Obtiene el historial formateado de manera legible.
        
        Returns:
            str: Historial en formato de texto legible
        
        Ejemplo:
            >>> personal = PM.objects.first()
            >>> print(ConsultasHistorialPersonal.obtener_historial_formateado(personal.id))
        """
        historial = ConsultasHistorialPersonal.obtener_historial_completo(personal_id)
        
        if not historial:
            return "Personal no encontrado"
        
        personal = historial['personal']
        
        texto = f"""
═══════════════════════════════════════════════════════════════
  HISTORIAL DISCIPLINARIO
═══════════════════════════════════════════════════════════════

PERSONAL:
  Nombre:          {personal.PM_NOMBRE} {personal.PM_PATERNO} {personal.PM_MATERNO}
  Cédula:          {personal.PM_CI}
  Grado:           {personal.get_PM_GRADO_display() if personal.PM_GRADO else 'N/A'}
  Escalafón:       {personal.get_PM_ESCALAFON_display() if personal.PM_ESCALAFON else 'N/A'}
  Arma:            {personal.get_PM_ARMA_display() if personal.PM_ARMA else 'N/A'}
  Estado:          {personal.get_PM_ESTADO_display()}

═══════════════════════════════════════════════════════════════

SUMARIOS (SIM):  {historial['sumarios'].count()} registro(s)
"""
        
        for sim in historial['sumarios']:
            texto += f"""
  [{sim.SIM_COD}] - {sim.SIM_TIPO}
    Objeto:        {sim.SIM_RESUM}
    Abogado:       {sim.abogados.all().first()}
    Fecha Ingreso: {sim.SIM_FECING}
    Estado:        {sim.SIM_ESTADO}
"""
        
        texto += f"""
═══════════════════════════════════════════════════════════════

RESOLUCIONES (RES):  {historial['resoluciones'].count()} registro(s)
"""
        
        for res in historial['resoluciones']:
            texto += f"""
  [{res.RES_NUM}] - {res.get_RES_TIPO_display()}
    Fecha:         {res.RES_FEC}
    Notificado:    {res.RES_NOT or 'Pendiente'}
    Fecha Notif:   {res.RES_FECNOT}
"""
        
        texto += f"""
═══════════════════════════════════════════════════════════════

SEGUNDAS RESOLUCIONES (RR):  {historial['segundas_resoluciones'].count()} registro(s)
"""
        
        for rr in historial['segundas_resoluciones']:
            texto += f"""
  [{rr.RR_NUM}] 
    Fecha:         {rr.RR_FEC}
    Presentado:    {rr.RR_FECPRESEN}
    Notificado:    {rr.RR_NOT or 'Pendiente'}
"""
        
        texto += f"""
═══════════════════════════════════════════════════════════════

RECURSOS DE APELACIÓN (RAP):  {historial['recursos_apelacion'].count()} registro(s)
"""
        
        for rap in historial['recursos_apelacion']:
            texto += f"""
  [{rap.RAP_NUM}]
    Fecha Oficio:  {rap.RAP_FECOFI}
    Fecha Resolución TSP: {rap.RAP_FEC}
    Notificado:    {rap.RAP_NOT or 'Pendiente'}
"""
        
        texto += f"""
═══════════════════════════════════════════════════════════════

RAEE (Aclaración, Explicación y Enmienda):  {historial['raees'].count()} registro(s)
"""
        
        for raee in historial['raees']:
            texto += f"""
  [{raee.RAE_NUM}]
    Fecha:         {raee.RAE_FEC}
    Notificado:    {raee.RAE_NOT or 'Pendiente'}
"""
        
        texto += f"""
═══════════════════════════════════════════════════════════════

AUTOS TPE:  {historial['autos_tpe'].count()} registro(s)
"""
        
        for auto in historial['autos_tpe']:
            texto += f"""
  [{auto.TPE_NUM}] - {auto.get_TPE_TIPO_display()}
    Fecha:         {auto.TPE_FEC}
    Notificado:    {auto.TPE_NOT or 'Pendiente'}
"""
        
        texto += f"""
═══════════════════════════════════════════════════════════════

AUTOS TSP:  {historial['autos_tsp'].count()} registro(s)
"""
        
        for auto in historial['autos_tsp']:
            texto += f"""
  [{auto.TSP_NUM}] - {auto.get_TSP_TIPO_display()}
    Fecha:         {auto.TSP_FEC}
    Notificado:    {auto.TSP_NOT or 'Pendiente'}
"""
        
        texto += """
═══════════════════════════════════════════════════════════════
"""
        
        return texto

    @staticmethod
    def obtener_estado_actual(personal_id):
        """
        Obtiene el estado actual del personal en el proceso disciplinario.
        
        Returns:
            dict: Estado actual con información resumida
        
        Ejemplo:
            >>> personal = PM.objects.first()
            >>> estado = ConsultasHistorialPersonal.obtener_estado_actual(personal.id)
            >>> print(f"Sumarios: {estado['total_sumarios']}")
            >>> print(f"Actualmente en: {estado['estado_actual']}")
        """
        historial = ConsultasHistorialPersonal.obtener_historial_completo(personal_id)
        
        if not historial:
            return None
        
        # Buscar el estado más reciente
        estado_actual = "Sin procesos"
        ultimo_sumario = historial['sumarios'].order_by('-SIM_FECREG').first()
        
        if ultimo_sumario:
            estado_actual = ultimo_sumario.get_SIM_ESTADO_display()
        
        return {
            'personal': historial['personal'],
            'total_sumarios': historial['sumarios'].count(),
            'total_resoluciones': historial['resoluciones'].count(),
            'total_apelaciones': historial['recursos_apelacion'].count(),
            'total_raees': historial['raees'].count(),
            'estado_actual': estado_actual,
            'ultimo_sumario': ultimo_sumario,
        }
