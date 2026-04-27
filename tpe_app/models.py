# ============================================================
#  MODELOS DJANGO — SISTEMA DE SUMARIOS INFORMATIVOS MILITARES
#  Versión 4.1 — Feriados en BD, Notificacion y Memorandum en tablas propias,
#                DocumentoAdjunto con FKs reales
# ============================================================

from django.db import models
from django.utils import timezone
from datetime import date, timedelta


# ============================================================
# MODELO 0: FeriadoBolivia — feriados nacionales configurables
# ============================================================
class FeriadoBolivia(models.Model):
    fecha       = models.DateField(unique=True, verbose_name='Fecha')
    descripcion = models.CharField(max_length=100, verbose_name='Descripción')
    anio        = models.IntegerField(db_index=True, verbose_name='Año')

    class Meta:
        db_table            = 'feriado_bolivia'
        verbose_name        = 'Feriado Bolivia'
        verbose_name_plural = 'Feriados Bolivia'
        ordering            = ['fecha']

    def __str__(self):
        return f"{self.fecha} — {self.descripcion}"


# Fallback para cuando la tabla aún no existe (primera migración)
_FERIADOS_FALLBACK = [
    date(2026, 1, 23), date(2026, 2, 16), date(2026, 2, 17),
    date(2026, 4, 3),  date(2026, 5, 1),  date(2026, 6, 4),
    date(2026, 6, 5),  date(2026, 6, 22), date(2026, 8, 6),
    date(2026, 8, 7),  date(2026, 11, 2), date(2026, 12, 25),
]


def add_business_days(fecha_inicio, dias):
    """Suma 'dias' días hábiles a fecha_inicio, excluyendo feriados de la BD."""
    try:
        años = {fecha_inicio.year, (fecha_inicio + timedelta(days=dias * 2 + 10)).year}
        feriados = set(
            FeriadoBolivia.objects.filter(anio__in=años).values_list('fecha', flat=True)
        )
        if not feriados:
            feriados = set(_FERIADOS_FALLBACK)
    except Exception:
        feriados = set(_FERIADOS_FALLBACK)

    fecha = fecha_inicio
    contados = 0
    while contados < dias:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha not in feriados:
            contados += 1
    return fecha


def get_pendientes_ejecutoria():
    """
    Retorna dos listas de casos pendientes de Auto de Ejecutoria:
    - por_res: Resoluciones PRIMERA notificadas sin RECONSIDERACION, plazo 15d vencido
    - por_rr:  Resoluciones RECONSIDERACION notificadas sin APELACION, plazo 3d vencido
    """
    from django.utils import timezone
    hoy = timezone.now().date()

    por_res = []
    res_notificadas = (
        Resolucion.objects
        .filter(instancia='PRIMERA', notificacion__isnull=False)
        .select_related('sim', 'pm', 'abog', 'notificacion')
    )
    for res in res_notificadas:
        if res.recursos_reconsideracion.exists():
            continue
        if AUTOTPE.objects.filter(resolucion=res, tipo='AUTO_EJECUTORIA').exists():
            continue
        if CustodiaSIM.objects.filter(sim=res.sim, motivo='EJECUTORIA', estado='ACTIVA').exists():
            continue
        fecha_limite = add_business_days(res.notificacion.fecha, 15)
        if fecha_limite <= hoy:
            res.fecha_limite = fecha_limite
            res.dias_vencido = (hoy - fecha_limite).days
            por_res.append(res)

    por_rr = []
    rr_notificados = (
        Resolucion.objects
        .filter(instancia='RECONSIDERACION', notificacion__isnull=False)
        .select_related('sim', 'pm', 'abog', 'resolucion_origen', 'notificacion')
    )
    for rr in rr_notificados:
        if RecursoTSP.objects.filter(resolucion=rr, instancia='APELACION').exists():
            continue
        if AUTOTPE.objects.filter(resolucion=rr, tipo='AUTO_EJECUTORIA').exists():
            continue
        if CustodiaSIM.objects.filter(sim=rr.sim, motivo='EJECUTORIA', estado='ACTIVA').exists():
            continue
        fecha_limite = add_business_days(rr.notificacion.fecha, 3)
        if fecha_limite <= hoy:
            rr.fecha_limite = fecha_limite
            rr.dias_vencido = (hoy - fecha_limite).days
            por_rr.append(rr)

    return por_res, por_rr


def calcular_grado_esperado(anio_promocion, escalafon, anio_referencia=None):
    """Retorna el grado que debería tener un militar según años de servicio y escalafón."""
    if not anio_promocion or not escalafon:
        return None
    if anio_referencia is None:
        from datetime import datetime
        anio_referencia = datetime.now().year
    años = anio_referencia - anio_promocion

    if escalafon in ('GENERAL', 'OFICIAL SUPERIOR', 'OFICIAL SUBALTERNO'):
        if años < 6:    return 'SBTTE.'
        elif años < 11: return 'TTE.'
        elif años < 16: return 'CAP.'
        elif años < 21: return 'MY.'
        elif años < 26: return 'TCNL.'
        elif años < 31: return 'CNL.'
        else:           return 'GRAL. BRIG.'

    elif escalafon in ('SUBOFICIAL', 'SARGENTO'):
        if años < 4:    return 'SGTO. INCL.'
        elif años < 7:  return 'SGTO. 2DO.'
        elif años < 11: return 'SGTO. 1RO.'
        elif años < 16: return 'SOF. INCL.'
        elif años < 21: return 'SOF. 2DO.'
        elif años < 26: return 'SOF. 1RO.'
        elif años < 31: return 'SOF. MY.'
        else:           return 'SOF. MTRE.'

    return None


# ============================================================
# MODELO 1: PM — Personal Militar
# ============================================================
class PM(models.Model):

    ESCALAFON_CHOICES = [
        ('GENERAL',            'GENERAL'),
        ('OFICIAL SUPERIOR',   'OFICIAL SUPERIOR'),
        ('OFICIAL SUBALTERNO', 'OFICIAL SUBALTERNO'),
        ('SUBOFICIAL',         'SUBOFICIAL'),
        ('SARGENTO',           'SARGENTO'),
        ('TROPA',              'TROPA'),
        ('EMPLEADO CIVIL',     'EMPLEADO CIVIL'),
    ]
    GRADO_CHOICES = [
        ('GRAL. EJTO.', 'GRAL. EJTO.'), ('GRAL. DIV.',  'GRAL. DIV.'),
        ('GRAL. BRIG.', 'GRAL. BRIG.'),
        ('CNL.',  'CNL.'), ('TCNL.', 'TCNL.'), ('MY.',   'MY.'),
        ('CAP.',   'CAP.'), ('TTE.',   'TTE.'), ('SBTTE.', 'SBTTE.'),
        ('SOF. MTRE.', 'SOF. MTRE.'), ('SOF. MY.',   'SOF. MY.'),
        ('SOF. 1RO.',  'SOF. 1RO.'),  ('SOF. 2DO.',  'SOF. 2DO.'),
        ('SOF. INCL.', 'SOF. INCL.'),
        ('SGTO. 1RO.',  'SGTO. 1RO.'), ('SGTO. 2DO.',  'SGTO. 2DO.'),
        ('SGTO. INCL.', 'SGTO. INCL.'),
        ('CABO',  'CABO'), ('DGTE.', 'DGTE.'), ('SLDO.', 'SLDO.'),
        ('PROF. V', 'PROF. V'), ('PROF. IV', 'PROF. IV'), ('PROF. III', 'PROF. III'),
        ('PROF. II', 'PROF. II'), ('PROF. I', 'PROF. I'),
        ('TEC. V', 'TEC. V'), ('TEC. IV', 'TEC. IV'), ('TEC. III', 'TEC. III'),
        ('TEC. II', 'TEC. II'), ('TEC. I', 'TEC. I'),
        ('ADM. V', 'ADM. V'), ('ADM. IV', 'ADM. IV'), ('ADM. III', 'ADM. III'),
        ('ADM. II', 'ADM. II'), ('ADM. I', 'ADM. I'),
        ('APAD. V', 'APAD. V'), ('APAD. IV', 'APAD. IV'), ('APAD. III', 'APAD. III'),
        ('APAD. II', 'APAD. II'), ('APAD. I', 'APAD. I'),
    ]
    ARMA_CHOICES = [
        ('INF.',    'INF.'), ('CAB.',    'CAB.'), ('ART.',    'ART.'),
        ('ING.',    'ING.'), ('COM.',    'COM.'), ('LOG.',    'LOG.'),
        ('M.B.',    'M.B.'), ('INT.',    'INT.'), ('SAN.',    'SAN.'),
        ('TGRAFO.', 'TGRAFO.'), ('AV.', 'AV.'), ('MÚS.',   'MÚS.'),
    ]
    ESTADO_CHOICES = [
        ('ACTIVO',             'ACTIVO'),
        ('SERVICIO ACTIVO',    'SERVICIO ACTIVO'),
        ('LETRA A',            'LETRA A'),
        ('SERVICIO PASIVO',    'SERVICIO PASIVO'),
        ('RETIRO OBLIGATORIO', 'RETIRO OBLIGATORIO'),
        ('RESERVA ACTIVA',     'RESERVA ACTIVA'),
        ('BAJA',               'BAJA'),
        ('FALLECIDO',          'FALLECIDO'),
        ('NO HABIDO',          'NO HABIDO'),
        ('OTRO',               'OTRO'),
    ]

    ci            = models.DecimalField(max_digits=13, decimal_places=0, unique=True, null=True, blank=True, verbose_name='Cédula de Identidad')
    escalafon     = models.CharField(max_length=20, choices=ESCALAFON_CHOICES, null=True, blank=True, verbose_name='Escalafón')
    grado         = models.CharField(max_length=20, choices=GRADO_CHOICES,     null=True, blank=True, verbose_name='Grado Actual')
    arma          = models.CharField(max_length=20, choices=ARMA_CHOICES,      null=True, blank=True, verbose_name='Arma')
    especialidad  = models.CharField(max_length=30, null=True, blank=True, verbose_name='Especialidad')
    nombre        = models.CharField(max_length=50, verbose_name='Nombre')
    paterno       = models.CharField(max_length=50, db_index=True, verbose_name='Apellido Paterno')
    materno       = models.CharField(max_length=50, null=True, blank=True, verbose_name='Apellido Materno')
    estado        = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='ACTIVO', verbose_name='Estado')
    anio_promocion = models.IntegerField(null=True, blank=True, verbose_name='Año de Egreso')
    no_ascendio   = models.BooleanField(default=False, verbose_name='No ascendió al grado correspondiente')
    foto          = models.ImageField(upload_to='fotos_pm/', null=True, blank=True, verbose_name='Foto')

    class Meta:
        db_table            = 'pm'
        verbose_name        = 'Personal Militar'
        verbose_name_plural = 'Personal Militar'
        ordering            = ['paterno', 'nombre']

    def __str__(self):
        return f"{self.get_grado_display()} {self.nombre} {self.paterno}"

    def save(self, *args, **kwargs):
        self.nombre      = self.nombre.upper()      if self.nombre      else self.nombre
        self.paterno     = self.paterno.upper()     if self.paterno     else self.paterno
        self.materno     = self.materno.upper()     if self.materno     else self.materno
        self.especialidad = self.especialidad.upper() if self.especialidad else self.especialidad
        super().save(*args, **kwargs)

    @property
    def años_servicio(self):
        if not self.anio_promocion:
            return None
        from datetime import datetime
        return datetime.now().year - self.anio_promocion

    @property
    def grado_esperado(self):
        if self.no_ascendio or not self.anio_promocion or not self.escalafon:
            return None
        return calcular_grado_esperado(self.anio_promocion, self.escalafon)

    @property
    def estado_carrera_calculado(self):
        años = self.años_servicio
        if años is None:
            return None
        if años < 30:
            return 'ACTIVO'
        elif años < 35:
            es_tope = (self.grado in ('GRAL. EJTO.', 'GRAL. DIV.', 'GRAL. BRIG.', 'SOF. MTRE.')
                       and not self.no_ascendio)
            return 'ACTIVO' if es_tope else 'SERVICIO ACTIVO'
        elif años == 35:
            return 'LETRA A'
        else:
            return 'SERVICIO PASIVO'



# ============================================================
# MODELO 2B: VOCAL_TPE — Vocales del Tribunal
# ============================================================
class VOCAL_TPE(models.Model):

    CARGO_CHOICES = [
        ('PRESIDENTE',       'Presidente'),
        ('VICEPRESIDENTE',   'Vicepresidente'),
        ('VOCAL',            'Vocal'),
        ('RELATOR',          'Vocal Relator'),
        ('SECRETARIO_ACTAS', 'Secretario de Actas'),
        ('ASESOR_JEFE',      'Asesor Jurídico del Dpto. I-PERS'),
        ('ASESOR_JURIDICO',  'Asesor Jurídico del Comando General'),
    ]

    pm       = models.ForeignKey(PM, on_delete=models.RESTRICT, verbose_name='Militar')
    cargo    = models.CharField(max_length=20, choices=CARGO_CHOICES, verbose_name='Cargo en Tribunal')
    cargo_em = models.CharField(max_length=100, null=True, blank=True, verbose_name='Cargo en Estado Mayor')
    activo   = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table            = 'vocal_tpe'
        verbose_name        = 'Vocal del Tribunal'
        verbose_name_plural = 'Vocales del Tribunal'
        ordering            = ['cargo', 'pm__paterno']

    def __str__(self):
        estado = '' if self.activo else ' (inactivo)'
        return f"{self.get_cargo_display()} — {self.pm}{estado}"

    @property
    def identificacion_completa(self):
        """Grado + nombre + cargo EM para mostrar en documentos."""
        partes = [str(self.pm)]
        if self.cargo_em:
            partes.append(self.cargo_em)
        return ' — '.join(partes)


# ============================================================
# MODELO 3: SIM — Sumario Informativo Militar (tabla central)
# ============================================================
class SIM(models.Model):

    TIPO_CHOICES = [
        ('DISCIPLINARIO',  'DISCIPLINARIO'),
        ('ADMINISTRATIVO', 'ADMINISTRATIVO'),
        ('ASCENSO POSTUMO', 'ASCENSO POSTUMO'),
        ('SOLICITUD DE RETIRO VOLUNTARIO', 'SOLICITUD DE RETIRO VOLUNTARIO'),
        ('SOLICITUD_LETRA_D',        'SOLICITUD LETRA D'),
        ('SOLICITUD_LICENCIA_MAXIMA', 'SOLICITUD LICENCIA MAXIMA'),
        ('SOLICITUD_RESTITUCION_ANTIGUEDAD', 'SOLICITUD RESTITUCIÓN ANTIGUEDAD'),
        ('SOLICITUD_DE_RESTITUCION_DE_DERECHOS_PROFESIONALES', 'SOLICITUD DE RESTITUCIÓN DE DERECHOS PROFESIONALES'),
        ('SOLICITUD_ASCENSO_AL_GRADO_INMEDIATO_SUPERIOR', 'SOLICITUD ASCENSO AL GRADO INMEDIATO SUPERIOR'),
        ('SOLICITUD_ART_114_(Invalidez Instructor)',   'SOLICITUD ARTÍCULO 114 (INVALIDEZ INSTRUCTOR)'),
        ('SOLICITUD_ART_117_(Fallecimiento)',  'SOLICITUD ARTÍCULO 117 (FALLECIMIENTO)'),
        ('SOLICITUD_ART_118_(Invalidez Sldo)', 'SOLICITUD ARTÍCULO 118 (INVALIDEZ SLDO)'),
    ]

    MOTIVO_REAPERTURA_CHOICES = [
        ('NULIDAD_OBRADOS',    'Nulidad de Obrados'),
        ('VICIO_PROCESAL',     'Vicio Procesal'),
        ('ERROR_JURIDICO',     'Error Jurídico'),
        ('FALTA_NOTIFICACION', 'Falta de Notificación'),
        ('OTRO',               'Otro Motivo'),
    ]

    ESTADO_CHOICES = [
        ('PARA_AGENDA',           'Para Agenda'),
        ('PROCESO_EN_EL_TPE',     'Proceso en el TPE'),
        ('PROCESO_EN_EL_TSP',     'Proceso en el TSP'),
        ('PROCESO_CONCLUIDO_TPE', 'Proceso Concluido (TPE)'),
        ('PROCESO_EJECUTADO',     'Proceso Ejecutado'),
        ('OBSERVADO',             'Observado'),
    ]

    FASE_CHOICES = [
        ('PARA_AGENDA',           'Para Agenda'),
        ('EN_DICTAMEN_1RA',       'En Dictamen (1ra. Resolución)'),
        ('1RA_RESOLUCION',        'Emitida 1ra. Resolución'),
        ('NOTIFICACION_1RA',      'En Proceso de Notificación (1ra.)'),
        ('NOTIFICADO_1RA',        'Notificado (1ra. Resolución)'),
        ('EN_ESPERA_RR',          'En Espera de RR (plazo 15 días)'),
        ('PARA_AGENDA_RR',        'Para Agenda (RR)'),
        ('EN_DICTAMEN_RR',        'En Dictamen (2da. Resolución / RR)'),
        ('2DA_RESOLUCION',        'Emitida 2da. Resolución (RR)'),
        ('NOTIFICACION_RR',       'En Proceso de Notificación (RR)'),
        ('NOTIFICADO_RR',         'Notificado (RR)'),
        ('EN_ESPERA_RAP',         'En Espera de RAP (plazo 3 días)'),
        ('ELEVADO_TSP',           'Elevado al TSP'),
        ('EN_AGENDA_EJECUTORIA',  'En Agenda (Auto de Ejecutoria)'),
        ('EN_EJECUTORIA',         'Auto de Ejecutoria Emitido'),
        ('EJECUTORIA_NOTIFICADA', 'Ejecutoria Notificada (Pte. Archivo)'),
        ('PENDIENTE_ARCHIVO',     'Pendiente Archivo SPRODA'),
        ('CONCLUIDO',             'Archivado / Concluido (TPE)'),
        ('MEMORANDUM_RETORNADO',  'Memorandum Retornado (Proceso Ejecutado)'),
    ]

    ESTADO_JERARQUIA = {
        'PARA_AGENDA':           0,
        'OBSERVADO':             0,
        'PROCESO_EN_EL_TPE':     1,
        'PROCESO_EN_EL_TSP':     2,
        'PROCESO_CONCLUIDO_TPE': 3,
        'PROCESO_EJECUTADO':     4,
    }

    FASE_A_ESTADO = {
        'PARA_AGENDA':          'PARA_AGENDA',
        'EN_DICTAMEN_1RA':      'PROCESO_EN_EL_TPE',
        '1RA_RESOLUCION':       'PROCESO_EN_EL_TPE',
        'NOTIFICACION_1RA':     'PROCESO_EN_EL_TPE',
        'NOTIFICADO_1RA':       'PROCESO_EN_EL_TPE',
        'EN_ESPERA_RR':         'PROCESO_EN_EL_TPE',
        'PARA_AGENDA_RR':       'PROCESO_EN_EL_TPE',
        'EN_DICTAMEN_RR':       'PROCESO_EN_EL_TPE',
        '2DA_RESOLUCION':       'PROCESO_EN_EL_TPE',
        'NOTIFICACION_RR':      'PROCESO_EN_EL_TPE',
        'NOTIFICADO_RR':        'PROCESO_EN_EL_TPE',
        'EN_ESPERA_RAP':        'PROCESO_EN_EL_TPE',
        'ELEVADO_TSP':          'PROCESO_EN_EL_TSP',
        'EN_AGENDA_EJECUTORIA': 'PROCESO_EN_EL_TPE',        # aún reversible, no concluido
        'EN_EJECUTORIA':        'PROCESO_EN_EL_TPE',        # auto firmado, pendiente notificar
        'EJECUTORIA_NOTIFICADA':'PROCESO_CONCLUIDO_TPE',   # notificado con fecha+hora → concluye
        'PENDIENTE_ARCHIVO':    'PROCESO_CONCLUIDO_TPE',
        'CONCLUIDO':            'PROCESO_CONCLUIDO_TPE',
        'MEMORANDUM_RETORNADO': 'PROCESO_EJECUTADO',
    }

    militares = models.ManyToManyField(PM, through='PM_SIM', verbose_name='Militares investigados')
    abogados  = models.ManyToManyField(PM, through='ABOG_SIM', related_name='sumarios_como_abogado', verbose_name='Abogados asignados')

    codigo             = models.CharField(max_length=25, db_index=True, verbose_name='Código SIM', help_text='Formato: PREFIJO-NUM/AÑO (ej: DJE-95/25)')
    version            = models.IntegerField(default=1, verbose_name='Versión', help_text='1=original, 2=1ª reapertura, etc.')
    origen             = models.ForeignKey(
                            'self', null=True, blank=True, on_delete=models.PROTECT,
                            related_name='reaperturas', verbose_name='SIM Original',
                            help_text='Si este SIM es reapertura de otro, referencia el original aquí')
    motivo_reapertura  = models.CharField(max_length=30, choices=MOTIVO_REAPERTURA_CHOICES,
                            null=True, blank=True, verbose_name='Motivo de Reapertura')
    fecha_ingreso      = models.DateField(null=True, blank=True, db_index=True, verbose_name='Fecha de Ingreso al TPE')
    numero_carpeta     = models.IntegerField(null=True, blank=True, verbose_name='N° Carpeta Física',
                            help_text='Número de ubicación física de la carpeta en el archivo (ej: 40–250)')
    estado             = models.CharField(max_length=30, choices=ESTADO_CHOICES,
                            default='PARA_AGENDA', db_index=True, verbose_name='Estado')
    fase               = models.CharField(max_length=30, choices=FASE_CHOICES,
                            default='PARA_AGENDA', null=True, blank=True, db_index=True,
                            verbose_name='Fase detallada del flujo')
    objeto             = models.TextField(verbose_name='Objeto del sumario')
    resumen            = models.CharField(max_length=200, verbose_name='Resumen')
    auto_final         = models.TextField(null=True, blank=True, verbose_name='Auto Final / Dictamen')
    tipo               = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo')
    fecha_registro     = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')

    class Meta:
        db_table            = 'sim'
        verbose_name        = 'Sumario Informativo Militar'
        verbose_name_plural = 'Sumarios Informativos Militares'
        ordering            = ['-fecha_registro']
        unique_together     = [('codigo', 'version')]

    def __str__(self):
        ver = f" v{self.version}" if self.version > 1 else ""
        estado_reap = " [REAPERTURA]" if self.origen else ""
        return f"{self.codigo}{ver}{estado_reap} — {self.resumen}"

    def get_estado_color(self):
        colores = {
            'PARA_AGENDA':      'primary',
            'PROCESO_EN_EL_TPE': 'warning',
            'EN_APELACION_TSP':  'danger',
        }
        return colores.get(self.estado, 'secondary')

    def get_fase_color(self):
        if not self.fase:
            return 'secondary'
        colores = {
            'PARA_AGENDA': 'primary', 'PARA_AGENDA_RR': 'primary',
            'EN_DICTAMEN_1RA': 'warning', 'EN_DICTAMEN_RR': 'warning',
            '1RA_RESOLUCION': 'success', '2DA_RESOLUCION': 'success',
            'NOTIFICACION_1RA': 'info', 'NOTIFICACION_RR': 'info',
            'EN_ESPERA_RR': 'danger', 'EN_ESPERA_RAP': 'danger',
            'ELEVADO_TSP': 'danger',
            'CONCLUIDO': 'success',
        }
        return colores.get(self.fase, 'secondary')

    def custodio_actual(self):
        return self.custodias.filter(fecha_entrega__isnull=True).first()

    def get_sim_original(self):
        if self.origen is None:
            return self
        return self.origen.get_sim_original()

    def get_arbol_genealogico(self):
        arbol = [self]
        for reapertura in self.reaperturas.order_by('id'):
            arbol.extend(reapertura.get_arbol_genealogico())
        return arbol

    def tiene_reaperturas(self):
        return self.reaperturas.exists()

    def save(self, *args, **kwargs):
        self.codigo    = self.codigo.upper()    if self.codigo    else self.codigo
        self.objeto    = self.objeto.upper()    if self.objeto    else self.objeto
        self.resumen   = self.resumen.upper()   if self.resumen   else self.resumen
        self.tipo      = self.tipo.upper()      if self.tipo      else self.tipo
        self.auto_final = self.auto_final.upper() if self.auto_final else self.auto_final

        if self.fase and self.fase in self.FASE_A_ESTADO:
            nuevo_estado = self.FASE_A_ESTADO[self.fase]
            nivel_actual = self.ESTADO_JERARQUIA.get(self.estado, 0)
            nivel_nuevo  = self.ESTADO_JERARQUIA.get(nuevo_estado, 0)
            if nivel_nuevo >= nivel_actual:
                self.estado = nuevo_estado

        super().save(*args, **kwargs)


# ============================================================
# MODELO 4: PM_SIM — Tabla puente N:M (PM ↔ SIM)
# ============================================================
class PM_SIM(models.Model):

    sim           = models.ForeignKey(SIM, on_delete=models.CASCADE,  verbose_name='Sumario')
    pm            = models.ForeignKey(PM,  on_delete=models.RESTRICT, verbose_name='Militar')
    grado_en_fecha = models.CharField(
        max_length=20, choices=PM.GRADO_CHOICES,
        null=True, blank=True,
        verbose_name='Grado al momento del sumario'
    )

    class Meta:
        db_table            = 'pm_sim'
        verbose_name        = 'Militar en Sumario'
        verbose_name_plural = 'Militares en Sumario'
        unique_together     = ('sim', 'pm')

    def __str__(self):
        return f"{self.sim.codigo} — {self.pm}"


# ============================================================
# MODELO 4B: ABOG_SIM — Tabla puente N:M (ABOG ↔ SIM)
# ============================================================
class ABOG_SIM(models.Model):

    sim      = models.ForeignKey(SIM, on_delete=models.CASCADE,  verbose_name='Sumario')
    abogado  = models.ForeignKey(PM,  on_delete=models.RESTRICT, verbose_name='Abogado',
                                 related_name='asignaciones_abogado')
    es_responsable = models.BooleanField(
        default=False,
        verbose_name='Responsable de carpeta',
        help_text='El responsable custodia la carpeta física y puede entregarla'
    )

    class Meta:
        db_table            = 'abog_sim'
        verbose_name        = 'Abogado en Sumario'
        verbose_name_plural = 'Abogados en Sumario'
        unique_together     = ('sim', 'abogado')

    def __str__(self):
        marca = ' [RESP]' if self.es_responsable else ''
        return f"{self.abogado} → {self.sim.codigo}{marca}"


# ============================================================
# MODELO 4C: CustodiaSIM — Trazabilidad de quién tiene la carpeta física
# ============================================================
class CustodiaSIM(models.Model):

    TIPO_CHOICES = [
        ('ADMIN2_ARCHIVO',      'Archivo del Tribunal'),
        ('ABOG_ASESOR',         'Abogado Asesor'),
        ('ABOG_RR',             'Abogado (Reconsideración)'),
        ('ABOG_AUTOS',          'Abogado (Autos)'),
        ('VOCAL_SESION',        'Secretario de Actas'),
        ('ADMIN1_AGENDADOR',    'Agendador'),
        ('ADMIN3_NOTIFICADOR',  'Notificador'),
        ('TSP',                 'Tribunal Supremo Policial'),
        ('ARCHIVO',             'Archivo Permanente'),
    ]

    MOTIVO_CHOICES = [
        ('AGENDA',        'Para agenda del tribunal'),
        ('REVISION',      'Revisión del abogado'),
        ('NOTIFICACION',  'Para notificación'),
        ('APELACION_TSP', 'Elevado al TSP'),
        ('EJECUTORIA',    'Para ejecutoria/cumplimiento'),
        ('ARCHIVO',       'Archivado / Concluido'),
    ]

    ESTADO_CHOICES = [
        ('RECIBIDA_CONFORME',      'Recibida Conforme'),
        ('PENDIENTE_CONFIRMACION', 'Pendiente de Confirmación'),
    ]

    sim              = models.ForeignKey(SIM, on_delete=models.CASCADE,
                                         related_name='custodias', verbose_name='Sumario')
    tipo_custodio    = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo de Custodio')
    abogado          = models.ForeignKey(PM, on_delete=models.SET_NULL,
                                         null=True, blank=True, verbose_name='Abogado',
                                         related_name='custodias_como_abogado')
    abogado_destino  = models.ForeignKey(PM, on_delete=models.SET_NULL,
                                         null=True, blank=True, verbose_name='Abogado Destino',
                                         related_name='custodias_como_destino')
    usuario          = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name='custodias_registradas',
                                         verbose_name='Usuario que registró')
    observacion      = models.TextField(null=True, blank=True, verbose_name='Observación')
    fecha_recepcion  = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Recepción')
    fecha_entrega    = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de Entrega')
    motivo           = models.CharField(max_length=20, choices=MOTIVO_CHOICES,
                                        null=True, blank=True, verbose_name='Motivo')
    nro_oficio       = models.CharField(max_length=30, null=True, blank=True, verbose_name='Número de Oficio (TSP)')
    fecha_oficio     = models.DateField(null=True, blank=True, verbose_name='Fecha del Oficio (TSP)')
    nro_oficio_archivo = models.CharField(max_length=30, null=True, blank=True, verbose_name='Número de Oficio (ARCHIVO/SPRODA)')
    fecha_oficio_archivo = models.DateField(null=True, blank=True, verbose_name='Fecha del Oficio (ARCHIVO/SPRODA)')
    estado           = models.CharField(max_length=25, choices=ESTADO_CHOICES,
                                        default='RECIBIDA_CONFORME', verbose_name='Estado de la Custodia')

    class Meta:
        db_table            = 'custodia_sim'
        verbose_name        = 'Custodia SIM'
        verbose_name_plural = 'Custodias SIM'
        ordering            = ['-fecha_recepcion']

    def __str__(self):
        estado = "en poder" if not self.fecha_entrega else "entregada"
        return f"[{self.sim.codigo}] → {self.get_tipo_custodio_display()} ({estado})"

    @property
    def activa(self):
        return self.fecha_entrega is None


# ============================================================
# MODELO 3.5: AGENDA — Agendas de reuniones del tribunal
# ============================================================
class AGENDA(models.Model):

    TIPO_AGENDA_CHOICES = [
        ('ORDINARIA',      'Sesión Ordinaria'),
        ('EXTRAORDINARIA', 'Sesión Extraordinaria'),
    ]

    ESTADO_CHOICES = [
        ('PROGRAMADA',   'Programada'),
        ('REALIZADA',    'Realizada'),
        ('SUSPENDIDA',   'Suspendida'),
        ('REPROGRAMADA', 'Reprogramada'),
    ]

    numero     = models.CharField(max_length=50, unique=True, verbose_name='Número de Agenda')
    fecha_prog = models.DateField(null=True, blank=True, verbose_name='Fecha Programada')
    fecha_real = models.DateField(null=True, blank=True, verbose_name='Fecha Realizada')
    tipo       = models.CharField(max_length=50, choices=TIPO_AGENDA_CHOICES,
                                  null=True, blank=True, verbose_name='Tipo de Agenda')
    estado     = models.CharField(max_length=20, choices=ESTADO_CHOICES,
                                  default='PROGRAMADA', verbose_name='Estado de la Agenda')

    class Meta:
        db_table            = 'agenda'
        verbose_name        = 'Agenda'
        verbose_name_plural = 'Agendas'
        ordering            = ['-fecha_prog']

    def __str__(self):
        return f"{self.numero} — {self.fecha_prog}"


# ============================================================
# MODELO 3.6: DICTAMEN — Dictamen de abogado en agenda
# ============================================================
class DICTAMEN(models.Model):

    numero     = models.CharField(max_length=20, null=True, blank=True, verbose_name='Número de Dictamen')
    conclusion = models.CharField(max_length=255, null=True, blank=True, verbose_name='Conclusión / Recomendación')
    agenda     = models.ForeignKey(AGENDA, on_delete=models.CASCADE, verbose_name='Agenda')
    sim        = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario')
    abogado    = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Abogado',
                   related_name='dictamenes_como_abogado')
    pm         = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Militar',
                   related_name='dictamenes_como_militar')
    secretario = models.ForeignKey(
        VOCAL_TPE, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Secretario de Actas que confirma',
        related_name='dictamenes_confirmados'
    )
    conclusion_secretario = models.TextField(null=True, blank=True, verbose_name='Conclusión confirmada/modificada por Secretario')
    estado     = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE',  'Pendiente de confirmar'),
            ('CONFIRMADO', 'Confirmado sin cambios'),
            ('MODIFICADO', 'Modificado por secretario'),
        ],
        default='PENDIENTE',
        verbose_name='Estado de confirmación'
    )
    fecha_confirmacion = models.DateField(null=True, blank=True, verbose_name='Fecha de confirmación')
    resultado_tribunal = models.CharField(
        max_length=15,
        choices=[
            ('PROCEDENTE',   'Procedente'),
            ('IMPROCEDENTE', 'Improcedente'),
            ('MIXTO',        'Votos divididos'),
        ],
        null=True, blank=True,
        verbose_name='Resultado del tribunal'
    )

    class Meta:
        db_table            = 'dictamen'
        verbose_name        = 'Dictamen'
        verbose_name_plural = 'Dictámenes'
        ordering            = ['-id']

    def __str__(self):
        return f"Dictamen {self.numero or 'S/N'} — {self.sim.codigo}"

    def save(self, *args, **kwargs):
        self.numero    = self.numero.upper()    if self.numero    else self.numero
        self.conclusion = self.conclusion.upper() if self.conclusion else self.conclusion
        super().save(*args, **kwargs)


# ============================================================
# MODELO 4B: VotoVocal — Voto de cada vocal en un dictamen
# ============================================================
class VotoVocal(models.Model):

    VOTO_CHOICES = [
        ('APRUEBA',  'Aprueba / Procedente'),
        ('RECHAZA',  'Rechaza / Improcedente'),
        ('ABSTIENE', 'Se abstiene'),
        ('AUSENTE',  'Ausente en sesión'),
    ]

    dictamen      = models.ForeignKey(DICTAMEN, on_delete=models.CASCADE, related_name='votos')
    vocal         = models.ForeignKey(VOCAL_TPE, on_delete=models.PROTECT, related_name='votos_emitidos')
    voto          = models.CharField(max_length=15, choices=VOTO_CHOICES)
    observacion   = models.TextField(null=True, blank=True)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'voto_vocal'
        verbose_name        = 'Voto del Vocal'
        verbose_name_plural = 'Votos de Vocales'
        unique_together     = ('dictamen', 'vocal')
        ordering            = ['vocal__cargo', 'vocal__pm__paterno']

    def __str__(self):
        return f"{self.vocal} → {self.get_voto_display()} en Dictamen {self.dictamen.numero}"


# ============================================================
# MODELO 4C: AsistenciaVocal — Asistencia de vocales a sesiones
# ============================================================
class AsistenciaVocal(models.Model):

    ESTADO_CHOICES = [
        ('PRESENTE', 'Presente'),
        ('AUSENTE',  'Ausente'),
        ('EXCUSADO', 'Excusado'),
    ]

    agenda        = models.ForeignKey(AGENDA, on_delete=models.CASCADE, related_name='asistencias')
    vocal         = models.ForeignKey(VOCAL_TPE, on_delete=models.PROTECT, related_name='asistencias')
    estado        = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='PRESENTE')
    justificacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table            = 'asistencia_vocal'
        verbose_name        = 'Asistencia a Sesión'
        verbose_name_plural = 'Asistencias a Sesiones'
        unique_together     = ('agenda', 'vocal')
        ordering            = ['vocal__cargo', 'vocal__pm__paterno']

    def __str__(self):
        return f"{self.vocal} en {self.agenda.numero}: {self.get_estado_display()}"


# ============================================================
# MODELO 5: AUTOTPE — Autos del Tribunal de Personal del Ejército
# ============================================================
class AUTOTPE(models.Model):

    TIPO_CHOICES = [
        ('SOBRESEIDO',                 'Sobreseído'),
        ('NULIDAD_OBRADOS',            'Nulidad de Obrados'),
        ('SANCION_ARRESTO',            'Sanción Arresto'),
        ('SANCION_LETRA_B',            'Sanción Letra B'),
        ('SANCION_RETIRO_OBLIGATORIO', 'Sanción Retiro Obligatorio'),
        ('AUTO_CUMPLIMIENTO',          'Auto de Cumplimiento'),
        ('AUTO_EJECUTORIA',            'Auto de Ejecutoria'),
        ('AUTO_EXCUSA',                'Auto de Excusa'),
        ('AUTO_RECHAZO_RECURSO',       'Auto de Rechazo de Recurso'),
    ]

    sim            = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario')
    abogado        = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Abogado',
                        related_name='autos_como_abogado')
    agenda         = models.ForeignKey(AGENDA, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Agenda')
    vocal_excusado = models.ForeignKey('VOCAL_TPE', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Vocal Excusado')
    pm             = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Militar')
    resolucion     = models.ForeignKey('Resolucion', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Resolución origen')
    recurso_tsp    = models.ForeignKey('RecursoTSP', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Recurso TSP origen')

    numero         = models.CharField(null=True, blank=True, max_length=15, db_index=True, verbose_name='Número de Auto')
    fecha          = models.DateField(null=True, blank=True, verbose_name='Fecha del Auto')
    texto          = models.TextField(null=True, blank=True, verbose_name='Resolución')
    tipo           = models.CharField(null=True, blank=True, max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

    class Meta:
        db_table            = 'autotpe'
        verbose_name        = 'Auto TPE'
        verbose_name_plural = 'Autos TPE'
        ordering            = ['-fecha']

    def __str__(self):
        return f"{self.numero} — {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        self.numero = self.numero.upper() if self.numero else self.numero
        self.texto  = self.texto.upper()  if self.texto  else self.texto
        super().save(*args, **kwargs)


# ============================================================
# MODELO 5b: Memorandum — Memorándum de ejecutoria (solo AUTO_EJECUTORIA)
# ============================================================
class Memorandum(models.Model):

    autotpe       = models.OneToOneField(AUTOTPE, on_delete=models.CASCADE,
                                         related_name='memorandum', verbose_name='Auto TPE')
    numero        = models.CharField(max_length=60, verbose_name='N° Memorándum')
    fecha         = models.DateField(verbose_name='Fecha Memorándum')
    fecha_entrega = models.DateField(null=True, blank=True, verbose_name='Fecha Entrega Memorándum')

    class Meta:
        db_table            = 'memorandum'
        verbose_name        = 'Memorándum'
        verbose_name_plural = 'Memorándums'

    def __str__(self):
        return f"Memo {self.numero} — Auto {self.autotpe.numero}"

    def save(self, *args, **kwargs):
        self.numero = self.numero.upper() if self.numero else self.numero
        super().save(*args, **kwargs)


# ============================================================
# MODELO 10: AUTOTSP — Autos del TSP
# ============================================================
class AUTOTSP(models.Model):

    TIPO_CHOICES = [
        ('SOBRESEIDO',        'Sobreseído'),
        ('NULIDAD_OBRADOS',   'Nulidad de Obrados'),
        ('CONFIRMA_SANCION',  'Confirma Sanción'),
        ('REDUCE_SANCION',    'Reduce Sanción'),
        ('REVOCA_SANCION',    'Revoca Sanción'),
        ('AUTO_CUMPLIMIENTO', 'Auto de Cumplimiento'),
        ('AUTO_EJECUTORIA',   'Auto de Ejecutoria'),
        ('AUTO_EXCUSA',       'Auto de Excusa'),
    ]

    sim    = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario', null=True, blank=True)
    numero = models.CharField(max_length=15, verbose_name='Número de Auto')
    fecha  = models.DateField(verbose_name='Fecha del Auto')
    texto  = models.TextField(verbose_name='Resolución')
    tipo   = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

    class Meta:
        db_table            = 'autotsp'
        verbose_name        = 'Auto TSP'
        verbose_name_plural = 'Autos TSP'
        ordering            = ['-fecha']

    def __str__(self):
        return f"{self.numero} — {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        self.numero = self.numero.upper() if self.numero else self.numero
        self.texto  = self.texto.upper()  if self.texto  else self.texto
        super().save(*args, **kwargs)


# ============================================================
# MODELO 11: DocumentoAdjunto — PDFs escaneados
# ============================================================
class DocumentoAdjunto(models.Model):

    TIPO_CHOICES = [
        ('resolucion',   'Resolución'),
        ('auto',         'Auto'),
        ('recurso',      'Recurso'),
        ('sim',          'Sumario SIM'),
        ('notificacion', 'Notificación'),
        ('otro',         'Otro'),
    ]

    sim         = models.ForeignKey('SIM',        null=True, blank=True, on_delete=models.CASCADE, related_name='documentos', verbose_name='Sumario SIM')
    resolucion  = models.ForeignKey('Resolucion', null=True, blank=True, on_delete=models.CASCADE, related_name='documentos', verbose_name='Resolución')
    autotpe     = models.ForeignKey('AUTOTPE',    null=True, blank=True, on_delete=models.CASCADE, related_name='documentos', verbose_name='Auto TPE')
    autotsp     = models.ForeignKey('AUTOTSP',    null=True, blank=True, on_delete=models.CASCADE, related_name='documentos', verbose_name='Auto TSP')
    recurso_tsp = models.ForeignKey('RecursoTSP', null=True, blank=True, on_delete=models.CASCADE, related_name='documentos', verbose_name='Recurso TSP')

    tipo           = models.CharField(max_length=50, choices=TIPO_CHOICES, verbose_name='Tipo de documento')
    archivo        = models.FileField(upload_to='documentos/%Y/', verbose_name='Archivo PDF')
    nombre         = models.CharField(max_length=100, verbose_name='Nombre descriptivo')
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        db_table            = 'documentos_adjuntos'
        verbose_name        = 'Documento Adjunto'
        verbose_name_plural = 'Documentos Adjuntos'

    def __str__(self):
        return self.nombre


# ============================================================
# MODELO 11b: Resolucion — Tabla unificada RES + RR
# ============================================================
class Resolucion(models.Model):

    INSTANCIA_CHOICES = [
        ('PRIMERA',         'Primera Resolución'),
        ('RECONSIDERACION', 'Recurso de Reconsideración'),
    ]

    TIPO_CHOICES = [
        ('ARCHIVO_OBRADOS',                'Archivo de Obrados'),
        ('ADMINISTRATIVO',                 'Administrativo'),
        ('SANCIONES_DISCIPLINARIAS',       'Sanciones Disciplinarias'),
        ('NO_HA_LUGAR_SANCION_DISCIPLINARIA', 'No ha Lugar a la Sanción Disciplinaria'),
        ('SOLICITUD_DE_RETIRO_VOLUNTARIO', 'Solicitud de Retiro Voluntario'),
        ('SANCION_ARRESTO',                'Sanción Arresto (Ejecutiva)'),
        ('SANCION_LETRA_B',                'Sanción Letra B (Pérdida de Antigüedad)'),
        ('SANCION_RETIRO_OBLIGATORIO',     'Sanción Retiro Obligatorio'),
        ('SANCION_BAJA',                   'Sanción Baja'),
        ('SOLICITUD_LETRA_D',              'Solicitud Letra D (Permiso Médico)'),
        ('SOLICITUD_LICENCIA_MAXIMA',      'Solicitud Licencia Máxima'),
        ('SOLICITUD_ASCENSO',              'Solicitud de Ascenso'),
        ('SOLICITUD_RESTITUCION_ANTIGUEDAD','Solicitud de Restitución de Antigüedad'),
        ('SOLICITUD_RESTITUCION_DE_DERECHOS_PROFESIONALES', 'Solicitud de Restitución de Derechos Profesionales'),
        ('SOLICITUD_ART_114_(Invalidez Instructor)',   'Solicitud Artículo 114 (Invalides Instructor)'),
        ('SOLICITUD_ART_117_(Fallecimiento)',  'Solicitud Artículo 117 (Fallecimiento)'),
        ('SOLICITUD_ART_118_(Invalidez Sldo)', 'Solicitud Artículo 118 (Invalidez Sldo)'),
        ('OTRO', 'Otro'),
    ]

    RESUM_CHOICES = [
        ('PROCEDENCIA',   'Procedencia a su Recurso de Reconsideración'),
        ('IMPROCEDENCIA', 'Improcedencia a su Recurso de Reconsideración'),
    ]

    instancia          = models.CharField(max_length=20, choices=INSTANCIA_CHOICES, default='PRIMERA', verbose_name='Instancia')
    sim                = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario')
    abogado            = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Abogado',
                             related_name='resoluciones_como_abogado')
    agenda             = models.ForeignKey(AGENDA, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Agenda')
    pm                 = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Militar',
                             related_name='resoluciones_como_militar')
    dictamen           = models.ForeignKey('DICTAMEN', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Dictamen origen (solo PRIMERA)')
    resolucion_origen  = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True,
        related_name='recursos_reconsideracion',
        verbose_name='Resolución impugnada (solo RECONSIDERACION)')

    numero             = models.CharField(max_length=15, db_index=True, verbose_name='Número de Resolución')
    fecha              = models.DateField(null=True, blank=True, verbose_name='Fecha')
    texto              = models.TextField(null=True, blank=True, verbose_name='Resolución')
    tipo               = models.CharField(max_length=100, choices=TIPO_CHOICES, null=True, blank=True, verbose_name='Tipo (PRIMERA)')
    resumen            = models.CharField(max_length=20, choices=RESUM_CHOICES, null=True, blank=True, verbose_name='Resumen (RECONSIDERACION)')
    fecha_presentacion = models.DateField(null=True, blank=True, verbose_name='Fecha Presentación (RECONSIDERACION)')
    fecha_limite       = models.DateField(null=True, blank=True, verbose_name='Fecha Límite 15 días (RECONSIDERACION)')

    class Meta:
        db_table            = 'resolucion'
        verbose_name        = 'Resolución'
        verbose_name_plural = 'Resoluciones'
        ordering            = ['-fecha']
        unique_together     = [('numero', 'instancia')]

    def __str__(self):
        return f"{self.numero} — {self.get_instancia_display()}"

    def save(self, *args, **kwargs):
        if self.instancia == 'RECONSIDERACION' and self.fecha_presentacion and not self.fecha_limite:
            self.fecha_limite = add_business_days(self.fecha_presentacion, 15)
        self.numero = self.numero.upper() if self.numero else self.numero
        self.texto  = self.texto.upper()  if self.texto  else self.texto
        super().save(*args, **kwargs)

    def get_alerta_plazo(self):
        if self.instancia != 'RECONSIDERACION' or not self.fecha_limite:
            return 'secondary'
        hoy = timezone.now().date()
        diff = (self.fecha_limite - hoy).days
        if diff < 0:    return 'danger'
        elif diff <= 5: return 'warning'
        return 'success'


def next_resolucion_num(year=None):
    """Genera el siguiente número 'NN/AA' de Resolucion de forma thread-safe."""
    from django.db import transaction
    if year is None:
        year = timezone.now().year
    year_suffix = str(year)[-2:]
    with transaction.atomic():
        qs = (Resolucion.objects
              .select_for_update()
              .filter(numero__endswith=f'/{year_suffix}'))
        max_n = 0
        for r in qs:
            try:
                n = int(r.numero.split('/')[0])
                if n > max_n:
                    max_n = n
            except (ValueError, IndexError):
                pass
        return f'{max_n + 1:02d}/{year_suffix}'


# ============================================================
# MODELO 11c: RecursoTSP — Tabla unificada RAP + RAEE
# ============================================================
class RecursoTSP(models.Model):

    INSTANCIA_CHOICES = [
        ('APELACION',           'Recurso de Apelación'),
        ('ACLARACION_ENMIENDA', 'Aclaración, Explicación y Enmienda'),
    ]

    TIPO_CHOICES = [
        ('REVOCAR',                           'REVOCAR'),
        ('CONFIRMAR',                         'CONFIRMAR'),
        ('MODIFICAR',                         'MODIFICAR'),
        ('ANULAR HASTA EL VICIO MAS ANTIGUO', 'ANULAR HASTA EL VICIO MAS ANTIGUO'),
        ('OTRO',                              'OTRO'),
    ]

    instancia          = models.CharField(max_length=25, choices=INSTANCIA_CHOICES, default='APELACION', verbose_name='Instancia')
    sim                = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario')
    abogado            = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Abogado',
                             related_name='recursos_tsp_como_abogado')
    pm                 = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Militar',
                             related_name='recursos_tsp_como_militar')
    resolucion         = models.ForeignKey(Resolucion, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Resolución impugnada (solo APELACION)')
    recurso_origen     = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                           related_name='aclaraciones',
                                           verbose_name='Recurso origen (solo ACLARACION_ENMIENDA)')

    fecha_presentacion = models.DateField(null=True, blank=True, verbose_name='Fecha de Presentación')
    numero_oficio      = models.CharField(max_length=25, null=True, blank=True, verbose_name='N° Oficio Elevación')
    fecha_oficio       = models.DateField(null=True, blank=True, verbose_name='Fecha del Oficio')
    fecha_limite       = models.DateField(null=True, blank=True, verbose_name='Fecha Límite 3 días (APELACION)')
    tipo               = models.CharField(max_length=50, choices=TIPO_CHOICES, null=True, blank=True, verbose_name='Tipo Resolución TSP (APELACION)')
    numero             = models.CharField(max_length=15, null=True, blank=True, db_index=True, verbose_name='Número Resolución TSP')
    fecha              = models.DateField(null=True, blank=True, verbose_name='Fecha Resolución TSP')
    texto              = models.TextField(null=True, blank=True, verbose_name='Resolución TSP')

    class Meta:
        db_table            = 'recurso_tsp'
        verbose_name        = 'Recurso TSP'
        verbose_name_plural = 'Recursos TSP'
        ordering            = ['-fecha']

    def __str__(self):
        return f"{self.numero or 'Sin número'} — {self.get_instancia_display()}"

    def save(self, *args, **kwargs):
        if self.instancia == 'APELACION' and self.fecha_oficio and not self.fecha_limite:
            self.fecha_limite = add_business_days(self.fecha_oficio, 3)
        self.numero_oficio = self.numero_oficio.upper() if self.numero_oficio else self.numero_oficio
        self.numero = self.numero.upper() if self.numero else self.numero
        self.texto  = self.texto.upper()  if self.texto  else self.texto
        self.tipo   = self.tipo.upper()   if self.tipo   else self.tipo
        super().save(*args, **kwargs)

    def get_alerta_plazo(self):
        if self.instancia != 'APELACION' or not self.fecha_limite:
            return 'secondary'
        hoy = timezone.now().date()
        diff = (self.fecha_limite - hoy).days
        if diff < 0:    return 'danger'
        elif diff <= 2: return 'warning'
        return 'success'


def next_recurso_tsp_num(year=None):
    from django.db import transaction
    if year is None:
        year = timezone.now().year
    year_suffix = str(year)[-2:]
    with transaction.atomic():
        qs = (RecursoTSP.objects
              .select_for_update()
              .filter(numero__endswith=f'/{year_suffix}'))
        max_n = 0
        for r in qs:
            try:
                n = int(r.numero.split('/')[0])
                if n > max_n:
                    max_n = n
            except (ValueError, IndexError):
                pass
        return f'{max_n + 1:02d}/{year_suffix}'


# ============================================================
# MODELO 11d: Notificacion — Datos de notificación de cualquier documento
# ============================================================
class Notificacion(models.Model):

    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    tipo         = models.CharField(max_length=10, choices=NOTIF_CHOICES, verbose_name='Tipo de Notificación')
    notificado_a = models.CharField(max_length=100, blank=True, verbose_name='Notificado a / Periódico / Dirección')
    fecha        = models.DateField(null=True, blank=True, verbose_name='Fecha de Notificación')
    hora         = models.TimeField(null=True, blank=True, verbose_name='Hora de Notificación')

    # Exactamente uno de estos debe ser no-nulo
    resolucion  = models.OneToOneField('Resolucion',  null=True, blank=True, on_delete=models.CASCADE,
                                       related_name='notificacion', verbose_name='Resolución')
    autotpe     = models.OneToOneField('AUTOTPE',     null=True, blank=True, on_delete=models.CASCADE,
                                       related_name='notificacion', verbose_name='Auto TPE')
    autotsp     = models.OneToOneField('AUTOTSP',     null=True, blank=True, on_delete=models.CASCADE,
                                       related_name='notificacion', verbose_name='Auto TSP')
    recurso_tsp = models.OneToOneField('RecursoTSP',  null=True, blank=True, on_delete=models.CASCADE,
                                       related_name='notificacion', verbose_name='Recurso TSP')

    class Meta:
        db_table            = 'notificacion'
        verbose_name        = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering            = ['-fecha']

    def __str__(self):
        doc = (self.resolucion or self.autotpe or self.autotsp or self.recurso_tsp)
        return f"Notif {self.fecha} — {doc}"

    def save(self, *args, **kwargs):
        self.notificado_a = self.notificado_a.upper() if self.notificado_a else self.notificado_a
        vinculados = sum([
            bool(self.resolucion_id),
            bool(self.autotpe_id),
            bool(self.autotsp_id),
            bool(self.recurso_tsp_id),
        ])
        if vinculados != 1:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f'Notificacion debe estar vinculada a exactamente un documento '
                f'(resolucion, autotpe, autotsp o recurso_tsp). Actualmente: {vinculados}.'
            )
        super().save(*args, **kwargs)


# ============================================================
# MODELO 12: PerfilUsuario — Sistema de roles
# ============================================================
class PerfilUsuario(models.Model):

    ROL_CHOICES = [
        ('MASTER',             'Master (Control Total)'),
        ('ADMINISTRADOR',      'Administrador de Sistemas'),
        ('AYUDANTE',           'Ayudante (Registro Histórico)'),
        ('ADMIN1_AGENDADOR',   'Administrativo 1 (Agendador)'),
        ('ADMIN2_ARCHIVO',     'Administrativo 2 (Archivo SIM)'),
        ('ADMIN3_NOTIFICADOR', 'Administrativo 3 (Notificador)'),
        ('ABOG1_ASESOR',       'Abogado 1 (Asesor/1ra Resolución)'),
        ('ABOG2_AUTOS',        'Abogado 2 (Autos de Ejecución)'),
        ('ABOG3_BUSCADOR',     'Abogado 3 (Búsqueda de Antecedentes)'),
        ('SECRETARIO_ACTAS',   'Secretario de Actas'),
        ('ASESOR_JEFE',        'Asesor Jefe (Supervisor de Procesos)'),
        ('ASESOR_JURIDICO',    'Asesor Jurídico del DPTO-I'),
        ('ABOGADO',            'Abogado (General)'),
        ('BUSCADOR',           'Buscador (General)'),
    ]

    # Todos los roles requieren vinculación a PM (fuente única de identidad)
    ROLES_CON_PM = {
        'MASTER', 'ADMINISTRADOR', 'AYUDANTE',
        'ADMIN1_AGENDADOR', 'ADMIN2_ARCHIVO', 'ADMIN3_NOTIFICADOR',
        'ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR', 'ABOGADO',
        'ASESOR_JEFE', 'ASESOR_JURIDICO', 'BUSCADOR',
    }

    user   = models.OneToOneField('auth.User', on_delete=models.CASCADE, verbose_name='Usuario del sistema')
    rol    = models.CharField(max_length=20, choices=ROL_CHOICES, verbose_name='Rol/Perfil')
    vocal  = models.ForeignKey(VOCAL_TPE, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name='Vinculado a Vocal TPE')
    pm     = models.ForeignKey(PM, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name='Vinculado a Personal Militar')
    activo = models.BooleanField(default=True, verbose_name='Usuario activo')

    class Meta:
        db_table            = 'perfil_usuario'
        verbose_name        = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'

    def __str__(self):
        if self.pm:
            return f"{self.pm.grado} {self.pm.paterno} [{self.get_rol_display()}]"
        if self.vocal:
            return f"{self.vocal.pm.paterno} [{self.get_rol_display()}]"
        return f"{self.user.username} ({self.get_rol_display()})"

    @property
    def grado(self):
        if self.pm:
            return self.pm.grado
        if self.vocal:
            return self.vocal.pm.grado
        return ''

    @property
    def nombre_completo(self):
        if self.pm:
            return f"{self.pm.grado} {self.pm.nombre} {self.pm.paterno}".strip()
        if self.vocal:
            return str(self.vocal.pm)
        return self.user.get_full_name() or self.user.username
