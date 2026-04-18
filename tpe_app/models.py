# ============================================================
#  MODELOS DJANGO — SISTEMA DE SUMARIOS INFORMATIVOS MILITARES
#  Versión 3.0 — Sincronizado con db_sumarios_v1.2
#  Correcciones: SIM_FECING, SIM_ESTADO, RES_EDICTO, RR_FECLIMITE,
#                RAP_FECLIMITE, RES_TIPO completo, DocumentoAdjunto
# ============================================================


from django.db import models
from django.utils import timezone
from datetime import timedelta


# ============================================================
# UTILIDAD: días hábiles (lunes=0 … viernes=4)
# ============================================================
from datetime import date, timedelta

FERIADOS_2026 = [
    date(2026, 5, 1),
    date(2026, 6, 4),
    date(2026, 6, 5),
    date(2026, 6, 22),
    date(2026, 8, 6),
    date(2026, 8, 7),
    date(2026, 11, 2),
    date(2026, 12, 25),
]

def add_business_days(fecha_inicio, dias):
    """Retorna la fecha resultante de sumar 'dias' días hábiles (lun-vier) a fecha_inicio, excluyendo los feriados de 2026."""
    fecha = fecha_inicio
    contados = 0
    while contados < dias:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha not in FERIADOS_2026:
            contados += 1
    return fecha


def get_pendientes_ejecutoria():
    """
    Retorna dos listas de casos pendientes de Auto de Ejecutoria:
    - por_res: Resolucion PRIMERA notificadas sin RECONSIDERACION presentada, plazo 15d vencido
    - por_rr:  Resolucion RECONSIDERACION notificadas sin APELACION presentada, plazo 3d vencido
    No incluye casos que ya tienen un AUTOTPE de tipo AUTO_EJECUTORIA.
    """
    from django.utils import timezone
    hoy = timezone.now().date()

    # ── Caso 1: PRIMERA notificada, sin RECONSIDERACION, plazo 15 días hábiles vencido ──
    por_res = []
    res_notificadas = (
        Resolucion.objects
        .filter(RES_INSTANCIA='PRIMERA', RES_FECNOT__isnull=False)
        .select_related('sim', 'pm', 'abog')
    )
    for res in res_notificadas:
        # ¿Ya tiene RECONSIDERACION?
        if res.recursos_reconsideracion.exists():
            continue
        # ¿Ya tiene Auto de Ejecutoria?
        if AUTOTPE.objects.filter(resolucion=res, TPE_TIPO='AUTO_EJECUTORIA').exists():
            continue
        fecha_limite = add_business_days(res.RES_FECNOT, 15)
        if fecha_limite <= hoy:
            res.fecha_limite = fecha_limite
            res.dias_vencido = (hoy - fecha_limite).days
            por_res.append(res)

    # ── Caso 2: RECONSIDERACION notificada, sin APELACION, plazo 3 días hábiles vencido ──
    por_rr = []
    rr_notificados = (
        Resolucion.objects
        .filter(RES_INSTANCIA='RECONSIDERACION', RES_FECNOT__isnull=False)
        .select_related('sim', 'pm', 'abog', 'resolucion_origen')
    )
    for rr in rr_notificados:
        # ¿Ya tiene APELACION (RecursoTSP.APELACION apuntando a esta RR)?
        if RecursoTSP.objects.filter(resolucion=rr, TSP_INSTANCIA='APELACION').exists():
            continue
        # ¿Ya tiene Auto de Ejecutoria?
        if AUTOTPE.objects.filter(resolucion=rr, TPE_TIPO='AUTO_EJECUTORIA').exists():
            continue
        fecha_limite = add_business_days(rr.RES_FECNOT, 3)
        if fecha_limite <= hoy:
            rr.fecha_limite = fecha_limite
            rr.dias_vencido = (hoy - fecha_limite).days
            por_rr.append(rr)

    return por_res, por_rr


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
        # Generales
        ('GRAL. EJTO.', 'GRAL. EJTO.'),
        ('GRAL. DIV.',  'GRAL. DIV.'),
        ('GRAL. BRIG.', 'GRAL. BRIG.'),
        # Oficiales Superiores
        ('CNL.',  'CNL.'),
        ('TCNL.', 'TCNL.'),
        ('MY.',   'MY.'),
        # Oficiales Subalternos
        ('CAP.',   'CAP.'),
        ('TTE.',   'TTE.'),
        ('SBTTE.', 'SBTTE.'),
        # Suboficiales
        ('SOF. MTRE.', 'SOF. MTRE.'),
        ('SOF. MY.',   'SOF. MY.'),
        ('SOF. 1RO.',  'SOF. 1RO.'),
        ('SOF. 2DO.',  'SOF. 2DO.'),
        ('SOF. INCL.', 'SOF. INCL.'),
        # Sargentos
        ('SGTO. 1RO.',  'SGTO. 1RO.'),
        ('SGTO. 2DO.',  'SGTO. 2DO.'),
        ('SGTO. INCL.', 'SGTO. INCL.'),
        # Tropa
        ('CABO',  'CABO'),
        ('DGTE.', 'DGTE.'),
        ('SLDO.', 'SLDO.'),
        # Empleados Civiles — Profesionales
        ('PROF. V',   'PROF. V'),   ('PROF. IV',  'PROF. IV'),
        ('PROF. III', 'PROF. III'), ('PROF. II',  'PROF. II'),
        ('PROF. I',   'PROF. I'),
        # Empleados Civiles — Técnicos
        ('TEC. V',   'TEC. V'),   ('TEC. IV',  'TEC. IV'),
        ('TEC. III', 'TEC. III'), ('TEC. II',  'TEC. II'),
        ('TEC. I',   'TEC. I'),
        # Empleados Civiles — Administrativos
        ('ADM. V',   'ADM. V'),   ('ADM. IV',  'ADM. IV'),
        ('ADM. III', 'ADM. III'), ('ADM. II',  'ADM. II'),
        ('ADM. I',   'ADM. I'),
        # Empleados Civiles — Apoyo Administrativo
        ('APAD. V',   'APAD. V'),   ('APAD. IV',  'APAD. IV'),
        ('APAD. III', 'APAD. III'), ('APAD. II',  'APAD. II'),
        ('APAD. I',   'APAD. I'),
    ]
    ARMA_CHOICES = [
        ('INF.',      'INF.'),
        ('CAB.',      'CAB.'),
        ('ART.',      'ART.'),
        ('ING.',      'ING.'),
        ('COM.',  'COM.'),
        ('LOG.',      'LOG.'),
        ('M.B.',       'M.B.'),
        ('INT.',     'INT.'),
        ('SAN.',         'SAN.'),
        ('TGRAFO.',       'TGRAFO.'),
        ('AV.',        'AV.'),
        ('MÚS.',          'MÚS.'),
    ]
    ESTADO_CHOICES = [
        ('ACTIVO',         'ACTIVO'),
        ('RETIRO OBLIGATORIO', 'RETIRO OBLIGATORIO'),
        ('RESERVA ACTIVA', 'RESERVA ACTIVA'),
        ('BAJA',           'BAJA'),
        ('FALLECIDO',      'FALLECIDO'),
        ('NO HABIDO',      'NO HABIDO'),
        ('OTRO',           'OTRO'),
    ]

    pm_id        = models.BigAutoField(primary_key=True, db_column='id')
    PM_CI        = models.DecimalField(max_digits=13, decimal_places=0, unique=True, null=True, blank=True, verbose_name='Cédula de Identidad')
    PM_ESCALAFON = models.CharField(max_length=20, choices=ESCALAFON_CHOICES, null=True, blank=True, verbose_name='Escalafón')
    PM_GRADO     = models.CharField(max_length=20, choices=GRADO_CHOICES,     null=True, blank=True, verbose_name='Grado')
    PM_ARMA      = models.CharField(max_length=20, choices=ARMA_CHOICES,      null=True, blank=True, verbose_name='Arma')
    PM_ESPEC     = models.CharField(max_length=15, null=True, blank=True, verbose_name='Especialidad')
    PM_NOMBRE    = models.CharField(max_length=25, verbose_name='Nombre')
    PM_PATERNO   = models.CharField(max_length=25, verbose_name='Apellido Paterno')
    PM_MATERNO   = models.CharField(max_length=25, null=True, blank=True, verbose_name='Apellido Materno')
    PM_ESTADO    = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='ACTIVO', verbose_name='Estado')
    PM_PROMOCION = models.DateField(null=True, blank=True, verbose_name='Fecha de Promoción')
    PM_FOTO      = models.ImageField(upload_to='fotos_pm/', null=True, blank=True, verbose_name='Foto')

    class Meta:
        db_table            = 'pm'
        verbose_name        = 'Personal Militar'
        verbose_name_plural = 'Personal Militar'
        ordering            = ['PM_PATERNO', 'PM_NOMBRE']

    def __str__(self):
        return f"{self.get_PM_GRADO_display()} {self.PM_NOMBRE} {self.PM_PATERNO}"
    def save(self, *args, **kwargs):
        self.PM_NOMBRE  = self.PM_NOMBRE.upper()  if self.PM_NOMBRE  else self.PM_NOMBRE
        self.PM_PATERNO = self.PM_PATERNO.upper() if self.PM_PATERNO else self.PM_PATERNO
        self.PM_MATERNO = self.PM_MATERNO.upper() if self.PM_MATERNO else self.PM_MATERNO
        self.PM_ESPEC   = self.PM_ESPEC.upper()   if self.PM_ESPEC   else self.PM_ESPEC
        super().save(*args, **kwargs)

# ============================================================
# MODELO 2: ABOG — Abogados del Tribunal
# ============================================================
class ABOG(models.Model):

    abog_id      = models.BigAutoField(primary_key=True, db_column='id')
    AB_CI      = models.DecimalField(max_digits=13, decimal_places=0, null=True, blank=True, verbose_name='Cédula de Identidad')
    AB_GRADO   = models.CharField(max_length=20, null=True, blank=True, verbose_name='Grado')
    AB_ARMA    = models.CharField(max_length=20, null=True, blank=True, verbose_name='Arma')
    AB_ESPEC   = models.CharField(max_length=15, null=True, blank=True, verbose_name='Especialidad')
    AB_NOMBRE  = models.CharField(max_length=25, verbose_name='Nombre')
    AB_PATERNO = models.CharField(max_length=25, verbose_name='Apellido Paterno')
    AB_MATERNO = models.CharField(max_length=25, null=True, blank=True, verbose_name='Apellido Materno')

    class Meta:
        db_table            = 'abog'
        verbose_name        = 'Abogado'
        verbose_name_plural = 'Abogados'
        ordering            = ['AB_PATERNO', 'AB_NOMBRE']

    def __str__(self):
        return f"{self.AB_GRADO} {self.AB_ARMA} {self.AB_NOMBRE} {self.AB_PATERNO}"
    def save(self, *args, **kwargs):
        self.AB_GRADO   = self.AB_GRADO.upper()   if self.AB_GRADO   else self.AB_GRADO
        self.AB_ARMA    = self.AB_ARMA.upper()    if self.AB_ARMA    else self.AB_ARMA
        self.AB_NOMBRE  = self.AB_NOMBRE.upper()  if self.AB_NOMBRE  else self.AB_NOMBRE
        self.AB_PATERNO = self.AB_PATERNO.upper() if self.AB_PATERNO else self.AB_PATERNO
        self.AB_MATERNO = self.AB_MATERNO.upper() if self.AB_MATERNO else self.AB_MATERNO
        self.AB_ESPEC   = self.AB_ESPEC.upper()   if self.AB_ESPEC   else self.AB_ESPEC
        super().save(*args, **kwargs)

# ============================================================
# MODELO 2B: VOCAL_TPE — Vocales del Tribunal
# ============================================================
class VOCAL_TPE(models.Model):

    CARGO_CHOICES = [
        ('PRESIDENTE',       'Presidente'),
        ('VICEPRESIDENTE',   'Vicepresidente'),
        ('VOCAL',            'Vocal'),
        ('SECRETARIO_ACTAS', 'Secretario de Actas'),
    ]

    pm     = models.ForeignKey(PM, on_delete=models.RESTRICT, verbose_name='Militar')
    cargo  = models.CharField(max_length=20, choices=CARGO_CHOICES, verbose_name='Cargo')
    activo = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table            = 'vocal_tpe'
        verbose_name        = 'Vocal del Tribunal'
        verbose_name_plural = 'Vocales del Tribunal'
        ordering            = ['cargo', 'pm__PM_PATERNO']

    def __str__(self):
        estado = '' if self.activo else ' (inactivo)'
        return f"{self.get_cargo_display()} — {self.pm}{estado}"

# ============================================================
# MODELO 3: SIM — Sumario Informativo Militar (tabla central)
# ============================================================
class SIM(models.Model):

    TIPO_CHOICES =  [
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

    # ✅ CORREGIDO v1.2: estados del sumario
    ESTADO_CHOICES = [
        ('PARA_AGENDA',      'Para Agenda'),
        ('PROCESO_EN_EL_TPE', 'Proceso en el TPE'),
        ('EN_APELACION_TSP',  'En Apelación TSP'),
        ('CONCLUIDO',          'Concluido'),
        ('OBSERVADO',           'Observado'),
    ]

    # ✅ NUEVO: estados detallados del flujo (fase dentro del TPE)
    FASE_CHOICES = [
        # Fase 1: Primera Resolución
        ('PARA_AGENDA',              'Para Agenda'),
        ('EN_DICTAMEN_1RA',          'En Dictamen (1ra. Resolución)'),
        ('1RA_RESOLUCION',           'Emitida 1ra. Resolución'),
        ('NOTIFICACION_1RA',         'En Proceso de Notificación (1ra.)'),
        ('NOTIFICADO_1RA',           'Notificado (1ra. Resolución)'),
        # Fase 2: RR
        ('EN_ESPERA_RR',             'En Espera de RR (plazo 15 días)'),
        ('PARA_AGENDA_RR',           'Para Agenda (RR)'),
        ('EN_DICTAMEN_RR',           'En Dictamen (2da. Resolución / RR)'),
        ('2DA_RESOLUCION',           'Emitida 2da. Resolución (RR)'),
        ('NOTIFICACION_RR',          'En Proceso de Notificación (RR)'),
        ('NOTIFICADO_RR',            'Notificado (RR)'),
        # Fase 3: RAP / TSP
        ('EN_ESPERA_RAP',            'En Espera de RAP (plazo 3 días)'),
        ('ELEVADO_TSP',              'Elevado al TSP'),
        ('EN_AGENDA_EJECUTORIA',     'En Agenda (Auto de Ejecutoria)'),
        # Fin
        ('CONCLUIDO',                'Concluido'),
    ]

    # Mapeo automático de FASE → ESTADO general
    FASE_A_ESTADO = {
        'PARA_AGENDA': 'PARA_AGENDA',
        'EN_DICTAMEN_1RA': 'PROCESO_EN_EL_TPE',
        '1RA_RESOLUCION': 'PROCESO_EN_EL_TPE',
        'NOTIFICACION_1RA': 'PROCESO_EN_EL_TPE',
        'NOTIFICADO_1RA': 'PROCESO_EN_EL_TPE',
        'EN_ESPERA_RR': 'PROCESO_EN_EL_TPE',
        'PARA_AGENDA_RR': 'PROCESO_EN_EL_TPE',
        'EN_DICTAMEN_RR': 'PROCESO_EN_EL_TPE',
        '2DA_RESOLUCION': 'PROCESO_EN_EL_TPE',
        'NOTIFICACION_RR': 'PROCESO_EN_EL_TPE',
        'NOTIFICADO_RR': 'PROCESO_EN_EL_TPE',
        'EN_ESPERA_RAP': 'PROCESO_EN_EL_TPE',
        'ELEVADO_TSP': 'EN_APELACION_TSP',
        'EN_AGENDA_EJECUTORIA': 'EN_APELACION_TSP',
        'CONCLUIDO': 'CONCLUIDO',
    }

    militares = models.ManyToManyField(
                    PM, through='PM_SIM', verbose_name='Militares investigados')
    abogados  = models.ManyToManyField(
                    'ABOG', through='ABOG_SIM', verbose_name='Abogados asignados')

    SIM_COD       = models.CharField(max_length=10,  unique=True, verbose_name='Código SIM')
    # ✅ CORREGIDO v1.2: renombrado de SIM_FECTPE → SIM_FECING
    SIM_FECING    = models.DateField(null=True, blank=True, verbose_name='Fecha de Ingreso al TPE')
    # ✅ NUEVO v1.2: estado del sumario
    SIM_ESTADO    = models.CharField(
                        max_length=30, choices=ESTADO_CHOICES,
                        default='PARA_AGENDA', verbose_name='Estado')
    # ✅ NUEVO v3.1: fase detallada del flujo (1ra res, en espera RR, 2da res, etc.)
    SIM_FASE      = models.CharField(
                        max_length=30, choices=FASE_CHOICES,
                        default='PARA_AGENDA', null=True, blank=True,
                        verbose_name='Fase detallada del flujo')
    SIM_OBJETO    = models.TextField(verbose_name='Objeto del sumario')
    SIM_RESUM     = models.CharField(max_length=200, verbose_name='Resumen', help_text='Breve descripción del caso (máx. 20 caracteres)')
    SIM_AUTOFINAL = models.TextField(null=True, blank=True, verbose_name='Auto Final / Dictamen')
    SIM_TIPO      = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo')
    SIM_FECREG    = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Registro')

    class Meta:
        db_table            = 'sim'
        verbose_name        = 'Sumario Informativo Militar'
        verbose_name_plural = 'Sumarios Informativos Militares'
        ordering            = ['-SIM_FECREG']

    def __str__(self):
        return f"{self.SIM_COD} — {self.SIM_RESUM}"

    def get_estado_color(self):
        """Devuelve el color de alerta según el estado del sumario."""
        colores = {
            'PARA_AGENDA':     'primary',
            'PROCESO_EN_EL_TPE':      'warning',
            'EN_APELACION_TSP': 'danger',
        }
        return colores.get(self.SIM_ESTADO, 'secondary')

    def get_fase_color(self):
        """Devuelve el color de badge según la fase detallada del sumario."""
        if not self.SIM_FASE:
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
        return colores.get(self.SIM_FASE, 'secondary')

    def custodio_actual(self):
        """Retorna la CustodiaSIM activa (fecha_entrega=None), o None."""
        return self.custodias.filter(fecha_entrega__isnull=True).first()

    def save(self, *args, **kwargs):
        # Convertir a MAYÚSCULAS
        self.SIM_COD       = self.SIM_COD.upper()       if self.SIM_COD       else self.SIM_COD
        self.SIM_OBJETO    = self.SIM_OBJETO.upper()    if self.SIM_OBJETO    else self.SIM_OBJETO
        self.SIM_RESUM     = self.SIM_RESUM.upper()     if self.SIM_RESUM     else self.SIM_RESUM
        self.SIM_TIPO      = self.SIM_TIPO.upper()      if self.SIM_TIPO      else self.SIM_TIPO
        self.SIM_AUTOFINAL = self.SIM_AUTOFINAL.upper() if self.SIM_AUTOFINAL else self.SIM_AUTOFINAL

        # ✅ NUEVO v3.1: Mapear SIM_FASE → SIM_ESTADO automáticamente
        if self.SIM_FASE and self.SIM_FASE in self.FASE_A_ESTADO:
            self.SIM_ESTADO = self.FASE_A_ESTADO[self.SIM_FASE]

        super().save(*args, **kwargs)

# ============================================================
# MODELO 4: PM_SIM — Tabla puente N:M (PM ↔ SIM)
# ============================================================
class PM_SIM(models.Model):

    sim = models.ForeignKey(SIM, on_delete=models.CASCADE,  verbose_name='Sumario')
    pm  = models.ForeignKey(PM,  on_delete=models.RESTRICT, verbose_name='Militar')

    class Meta:
        db_table            = 'pm_sim'
        verbose_name        = 'Militar en Sumario'
        verbose_name_plural = 'Militares en Sumario'
        unique_together     = ('sim', 'pm')

    def __str__(self):
        return f"{self.sim.SIM_COD} — {self.pm}"


# ============================================================
# MODELO 4B: ABOG_SIM — Tabla puente N:M (ABOG ↔ SIM)
# ============================================================
class ABOG_SIM(models.Model):

    sim  = models.ForeignKey(SIM,  on_delete=models.CASCADE,  verbose_name='Sumario')
    abog = models.ForeignKey(ABOG, on_delete=models.RESTRICT, verbose_name='Abogado')
    es_responsable = models.BooleanField(
        default=False,
        verbose_name='Responsable de carpeta',
        help_text='El responsable custodia la carpeta física y puede entregarla'
    )

    class Meta:
        db_table            = 'abog_sim'
        verbose_name        = 'Abogado en Sumario'
        verbose_name_plural = 'Abogados en Sumario'
        unique_together     = ('sim', 'abog')

    def __str__(self):
        marca = ' [RESP]' if self.es_responsable else ''
        return f"{self.abog} → {self.sim.SIM_COD}{marca}"


# ============================================================
# MODELO 4C: CustodiaSIM — Trazabilidad de quién tiene la carpeta física
# ============================================================
class CustodiaSIM(models.Model):
    """Registra quién tiene la carpeta física de cada sumario en cada momento."""

    TIPO_CHOICES = [
        ('ADMIN1',      'Administrativo 1 (Agendador)'),
        ('ADMIN2',      'Administrativo 2 (Archivo SIM)'),
        ('ADMIN3',      'Administrativo 3 (Notificador)'),
        ('ABOG_ASESOR', 'Abogado Asesor (1ra. Resolución)'),
        ('ABOG_RR',     'Abogado (Recurso de Reconsideración)'),
        ('ABOG_AUTOS',  'Abogado Autos (Ejecutoria/Cumplimiento)'),
        ('ABOG_RAP',    'Abogado 3 (Búsqueda/RAP)'),
        ('TSP',         'Elevado al TSP (externo)'),
        ('ARCHIVO',     'Archivado / Concluido'),
    ]

    MOTIVO_CHOICES = [
        ('AGENDA',         'Para agenda del tribunal'),
        ('REVISION',       'Revisión del abogado'),
        ('NOTIFICACION',   'Para notificación'),
        ('APELACION_TSP',  'Elevado al TSP'),
        ('ARCHIVO',        'Archivado / Concluido'),
    ]

    ESTADO_CHOICES = [
        ('ACTIVA',                  'Activa'),
        ('PENDIENTE_CONFIRMACION',  'Pendiente de Confirmación'),
    ]

    sim           = models.ForeignKey(SIM, on_delete=models.CASCADE,
                                      related_name='custodias', verbose_name='Sumario')
    tipo_custodio = models.CharField(max_length=20, choices=TIPO_CHOICES,
                                     verbose_name='Tipo de Custodio')
    abog          = models.ForeignKey('ABOG', on_delete=models.SET_NULL,
                                      null=True, blank=True, verbose_name='Abogado',
                                      help_text="Si el custodio es un abogado")
    usuario       = models.ForeignKey('auth.User', on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='custodias_registradas',
                                      verbose_name='Usuario que registró',
                                      help_text="Usuario que registró la entrega")
    observacion   = models.TextField(null=True, blank=True,
                                     verbose_name='Observación')
    fecha_recepcion = models.DateTimeField(auto_now_add=True,
                                           verbose_name='Fecha de Recepción')
    fecha_entrega   = models.DateTimeField(null=True, blank=True,
                                           verbose_name='Fecha de Entrega',
                                           help_text="Null = aún en su poder")
    motivo          = models.CharField(max_length=20, choices=MOTIVO_CHOICES,
                                       null=True, blank=True,
                                       verbose_name='Motivo de la custodia')
    nro_oficio      = models.CharField(max_length=30, null=True, blank=True,
                                       verbose_name='Número de Oficio (TSP)',
                                       help_text="Ej: OF-025/26 — solo para TSP")
    fecha_oficio    = models.DateField(null=True, blank=True,
                                       verbose_name='Fecha del Oficio (TSP)',
                                       help_text="Fecha de emisión del oficio al TSP")
    estado          = models.CharField(max_length=25, choices=ESTADO_CHOICES,
                                       default='ACTIVA',
                                       verbose_name='Estado de la Custodia')

    class Meta:
        db_table            = 'custodia_sim'
        verbose_name        = 'Custodia SIM'
        verbose_name_plural = 'Custodias SIM'
        ordering            = ['-fecha_recepcion']

    def __str__(self):
        estado = "en poder" if not self.fecha_entrega else "entregada"
        return f"[{self.sim.SIM_COD}] → {self.get_tipo_custodio_display()} ({estado})"

    @property
    def activa(self):
        """Indica si esta custodia está vigente (no entregada aún)."""
        return self.fecha_entrega is None


# ============================================================
# MODELO 3.5: AGENDA — Agendas de reuniones del tribunal
# ============================================================
class AGENDA(models.Model):
    """Agendas programadas de reuniones del tribunal TPE"""

    TIPO_AGENDA_CHOICES = [
        ('ORDINARIA',        'Sesión Ordinaria'),
        ('EXTRAORDINARIA',   'Sesión Extraordinaria'),
    ]

    # ✅ NUEVO v3.2: Estados de la agenda
    ESTADO_CHOICES = [
        ('PROGRAMADA',    'Programada'),
        ('REALIZADA',     'Realizada'),
        ('SUSPENDIDA',    'Suspendida'),
        ('REPROGRAMADA',  'Reprogramada'),
    ]

    AG_NUM = models.CharField(
        max_length=50,
        unique=True,
        db_column='AG_NUM',
        verbose_name='Número de Agenda'
    )
    AG_FECPROG = models.DateField(
        null=True,
        blank=True,
        db_column='AG_FECPROG',
        verbose_name='Fecha Programada'
    )
    AG_FECREAL = models.DateField(
        null=True,
        blank=True,
        db_column='AG_FECREAL',
        verbose_name='Fecha Realizada'
    )
    AG_TIPO = models.CharField(
        max_length=50,
        choices=TIPO_AGENDA_CHOICES,
        null=True,
        blank=True,
        db_column='AG_TIPO',
        verbose_name='Tipo de Agenda'
    )

    # ✅ NUEVO v3.2: Estado de la agenda (programada, realizada, suspendida, reprogramada)
    AG_ESTADO = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='PROGRAMADA',
        db_column='AG_ESTADO',
        verbose_name='Estado de la Agenda'
    )
    
    class Meta:
        db_table = 'agenda'
        verbose_name = 'Agenda'
        verbose_name_plural = 'Agendas'
        ordering = ['-AG_FECPROG']
    
    def __str__(self):
        return f"{self.AG_NUM} — {self.AG_FECPROG}"
# ============================================================
# MODELO 3.6: DICTAMEN — Dictamen de abogado en agenda
# ============================================================
class DICTAMEN(models.Model):
    """Dictamen emitido por abogado en una agenda"""
    
    # Nullable: registros históricos anteriores a esta gestión pueden no tener número
    DIC_NUM = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_column='DIC_NUM',
        verbose_name='Número de Dictamen'
    )
    DIC_CONCL = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='DIC_CONCL',
        verbose_name='Conclusión / Recomendación'
    )
    # FK a agenda: a qué reunión pertenece este dictamen
    agenda = models.ForeignKey(
        AGENDA,
        on_delete=models.CASCADE,
        verbose_name='Agenda'
    )
    # FK a SIM: qué sumario estudió el abogado en esa agenda
    sim = models.ForeignKey(
        SIM,
        on_delete=models.CASCADE,
        verbose_name='Sumario'
    )
    # Nullable: registros históricos pueden no tener abogado registrado
    abog = models.ForeignKey(
        ABOG,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Abogado'
    )
    pm = models.ForeignKey(
        PM,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Militar'
    )

    # ✅ NUEVO: Confirmación del Secretario de Actas
    secretario = models.ForeignKey(
        VOCAL_TPE,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Secretario de Actas que confirma',
        related_name='dictamenes_confirmados'
    )
    DIC_CONCL_SEC = models.TextField(
        null=True,
        blank=True,
        verbose_name='Conclusión confirmada/modificada por Secretario'
    )
    DIC_ESTADO = models.CharField(
        max_length=20,
        choices=[
            ('PENDIENTE', 'Pendiente de confirmar'),
            ('CONFIRMADO', 'Confirmado sin cambios'),
            ('MODIFICADO', 'Modificado por secretario'),
        ],
        default='PENDIENTE',
        verbose_name='Estado de confirmación'
    )
    DIC_CONFIR_FEC = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de confirmación'
    )

    class Meta:
        db_table = 'dictamen'
        verbose_name = 'Dictamen'
        verbose_name_plural = 'Dictámenes'
        ordering            = ['-id']

    def __str__(self):
        return f"Dictamen {self.DIC_NUM or 'S/N'} — {self.sim.SIM_COD}"

    def save(self, *args, **kwargs):
        self.DIC_NUM   = self.DIC_NUM.upper()   if self.DIC_NUM   else self.DIC_NUM
        self.DIC_CONCL = self.DIC_CONCL.upper() if self.DIC_CONCL else self.DIC_CONCL
        super().save(*args, **kwargs)
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
    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    sim = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario')  
    # add fk de abogado para cada auto (puede ser el mismo u otro diferente al de la RES)
    abog = models.ForeignKey(
        ABOG, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Abogado')

    # FK a la agenda que generó esta resolución
    agenda = models.ForeignKey(
        AGENDA, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Agenda')

    # FK al vocal que se excusa (solo para autos de excusa)
    vocal_excusado = models.ForeignKey(
        'VOCAL_TPE', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Vocal Excusado')

    # ✅ NUEVO: FK al militar al que aplica el auto
    pm = models.ForeignKey(
        PM, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Militar')

    # FKs a tablas unificadas
    resolucion = models.ForeignKey(
        'Resolucion', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Resolución origen (PRIMERA o RECONSIDERACION)')

    recurso_tsp = models.ForeignKey(
        'RecursoTSP', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Recurso TSP origen (APELACION o ACLARACION_ENMIENDA)')

    TPE_NUM   = models.CharField(null=True, blank=True, max_length=15,  verbose_name='Número de Auto')
    TPE_FEC   = models.DateField(null=True, blank=True, verbose_name='Fecha del Auto')
    TPE_RESOL = models.TextField(null=True, blank=True, verbose_name='Resolución')
    TPE_TIPO  = models.CharField(null=True, blank=True, max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

    # Notificación Tipo
    TPE_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES, null=True, blank=True, verbose_name='Tipo de Notificación')
    TPE_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a /Dirección/Periódico')
    TPE_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    TPE_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # Memorándum (exclusivo TPE)
    TPE_MEMO_NUM     = models.CharField(max_length=20, null=True, blank=True, verbose_name='N° Memorándum')
    TPE_MEMO_FEC     = models.DateField(null=True, blank=True, verbose_name='Fecha Memorándum')
    TPE_MEMO_ENTREGA = models.DateField(null=True, blank=True, verbose_name='Fecha Entrega Memorándum')

    class Meta:
        db_table            = 'autotpe'
        verbose_name        = 'Auto TPE'
        verbose_name_plural = 'Autos TPE'
        ordering            = ['-TPE_FEC']

    def __str__(self):
        return f"{self.TPE_NUM} — {self.get_TPE_TIPO_display()}"
    def save(self, *args, **kwargs):
        self.TPE_NUM          = self.TPE_NUM.upper()          if self.TPE_NUM          else self.TPE_NUM
        self.TPE_RESOL        = self.TPE_RESOL.upper()        if self.TPE_RESOL        else self.TPE_RESOL
        self.TPE_NOT          = self.TPE_NOT.upper()          if self.TPE_NOT          else self.TPE_NOT
        self.TPE_MEMO_NUM     = self.TPE_MEMO_NUM.upper()     if self.TPE_MEMO_NUM     else self.TPE_MEMO_NUM
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

    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    sim = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario', null=True, blank=True)

    TSP_NUM   = models.CharField(max_length=15,  verbose_name='Número de Auto')
    TSP_FEC   = models.DateField(verbose_name='Fecha del Auto')
    TSP_RESOL = models.TextField(verbose_name='Resolución')
    TSP_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

    # Notificación Tipo
    TSP_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES, null=True, blank=True, verbose_name='Tipo de Notificación')
    TSP_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a /Dirección/Periódico')
    TSP_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    TSP_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    class Meta:
        db_table            = 'autotsp'
        verbose_name        = 'Auto TSP'
        verbose_name_plural = 'Autos TSP'
        ordering            = ['-TSP_FEC']

    def __str__(self):
        return f"{self.TSP_NUM} — {self.get_TSP_TIPO_display()}"
    def save(self, *args, **kwargs):
        self.TSP_NUM   = self.TSP_NUM.upper()   if self.TSP_NUM   else self.TSP_NUM
        self.TSP_RESOL = self.TSP_RESOL.upper() if self.TSP_RESOL else self.TSP_RESOL
        self.TSP_NOT   = self.TSP_NOT.upper()   if self.TSP_NOT   else self.TSP_NOT
        super().save(*args, **kwargs)

# ============================================================
# MODELO 11: DocumentoAdjunto — PDFs escaneados (2013–2026)
# ✅ NUEVO v1.2
# ============================================================
class DocumentoAdjunto(models.Model):

    TABLA_CHOICES = [
        ('sim',         'Sumario SIM'),
        ('resolucion',  'Resolución (PRIMERA/RECONSIDERACION)'),
        ('recurso_tsp', 'Recurso TSP (APELACION/ACLARACION_ENMIENDA)'),
        ('autotpe',     'Auto TPE'),
        ('autotsp',     'Auto TSP'),
    ]
    TIPO_CHOICES = [
        ('resolucion',    'Resolución'),
        ('auto',          'Auto'),
        ('recurso',       'Recurso'),
        ('sim',           'Sumario SIM'),
        ('notificacion',  'Notificación'),
        ('otro',          'Otro'),
    ]

    DOC_TABLA  = models.CharField(max_length=30, choices=TABLA_CHOICES, verbose_name='Tabla de origen')
    DOC_ID_REG = models.BigIntegerField(verbose_name='ID del registro')
    DOC_TIPO   = models.CharField(max_length=50, choices=TIPO_CHOICES, verbose_name='Tipo de documento')
    DOC_RUTA   = models.FileField(upload_to='documentos/%Y/', verbose_name='Archivo PDF')
    DOC_NOMBRE = models.CharField(max_length=100, verbose_name='Nombre descriptivo')
    DOC_FECREG = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')

    class Meta:
        db_table            = 'documentos_adjuntos'
        verbose_name        = 'Documento Adjunto'
        verbose_name_plural = 'Documentos Adjuntos'
        indexes             = [
            models.Index(fields=['DOC_TABLA', 'DOC_ID_REG'], name='DOC_TABLA_ID'),
        ]

    def __str__(self):
        return f"{self.DOC_NOMBRE} ({self.get_DOC_TABLA_display()})"


# ============================================================
# MODELO 11b: Resolucion — Tabla unificada RES + RR
# Discriminador RES_INSTANCIA = PRIMERA | RECONSIDERACION
# Numeración consecutiva única anual (RES_NUM)
# ============================================================
class Resolucion(models.Model):

    INSTANCIA_CHOICES = [
        ('PRIMERA',          'Primera Resolución'),
        ('RECONSIDERACION',  'Recurso de Reconsideración'),
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
        ('OTRO',                           'Otro'),
    ]

    RESUM_CHOICES = [
        ('PROCEDENCIA',   'Procedencia a su Recurso de Reconsideración'),
        ('IMPROCEDENCIA', 'Improcedencia a su Recurso de Reconsideración'),
    ]

    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    # Discriminador
    RES_INSTANCIA = models.CharField(
        max_length=20, choices=INSTANCIA_CHOICES, default='PRIMERA',
        verbose_name='Instancia')

    # Relaciones comunes
    sim = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario')
    abog = models.ForeignKey(ABOG, on_delete=models.SET_NULL,
                             null=True, blank=True, verbose_name='Abogado')
    agenda = models.ForeignKey(AGENDA, on_delete=models.SET_NULL,
                               null=True, blank=True, verbose_name='Agenda')
    pm = models.ForeignKey(PM, on_delete=models.SET_NULL,
                           null=True, blank=True, verbose_name='Militar')

    # Solo PRIMERA
    dictamen = models.ForeignKey('DICTAMEN', on_delete=models.SET_NULL,
                                 null=True, blank=True,
                                 verbose_name='Dictamen origen (solo PRIMERA)')

    # Solo RECONSIDERACION (reemplaza RR.res)
    resolucion_origen = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='recursos_reconsideracion',
        verbose_name='Resolución impugnada (solo RECONSIDERACION)')

    # Numeración y cuerpo
    RES_NUM   = models.CharField(max_length=15, verbose_name='Número de Resolución')
    RES_FEC   = models.DateField(null=True, blank=True, verbose_name='Fecha')
    RES_RESOL = models.TextField(null=True, blank=True, verbose_name='Resolución')

    # Solo PRIMERA
    RES_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES,
                                 null=True, blank=True, verbose_name='Tipo (PRIMERA)')

    # Solo RECONSIDERACION
    RES_RESUM      = models.CharField(max_length=20, choices=RESUM_CHOICES,
                                      null=True, blank=True,
                                      verbose_name='Resumen (RECONSIDERACION)')
    RES_FECPRESEN  = models.DateField(null=True, blank=True,
                                      verbose_name='Fecha Presentación (RECONSIDERACION)')
    RES_FECLIMITE  = models.DateField(null=True, blank=True,
                                      verbose_name='Fecha Límite 15 días (RECONSIDERACION)')

    # Notificación
    RES_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES,
                                      null=True, blank=True, verbose_name='Tipo Notificación')
    RES_NOT    = models.CharField(max_length=100, null=True, blank=True,
                                  verbose_name='Notificado a /Dirección/Periódico')
    RES_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    RES_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    class Meta:
        db_table            = 'resolucion'
        verbose_name        = 'Resolución'
        verbose_name_plural = 'Resoluciones'
        ordering            = ['-RES_FEC']

    def __str__(self):
        return f"{self.RES_NUM} — {self.get_RES_INSTANCIA_display()}"

    def save(self, *args, **kwargs):
        if self.RES_INSTANCIA == 'RECONSIDERACION' and self.RES_FECPRESEN and not self.RES_FECLIMITE:
            self.RES_FECLIMITE = add_business_days(self.RES_FECPRESEN, 15)
        self.RES_NUM   = self.RES_NUM.upper()   if self.RES_NUM   else self.RES_NUM
        self.RES_RESOL = self.RES_RESOL.upper() if self.RES_RESOL else self.RES_RESOL
        self.RES_NOT   = self.RES_NOT.upper()   if self.RES_NOT   else self.RES_NOT
        super().save(*args, **kwargs)

    def get_alerta_plazo(self):
        if self.RES_INSTANCIA != 'RECONSIDERACION' or not self.RES_FECLIMITE:
            return 'secondary'
        hoy = timezone.now().date()
        diff = (self.RES_FECLIMITE - hoy).days
        if diff < 0:
            return 'danger'
        elif diff <= 5:
            return 'warning'
        return 'success'


def next_resolucion_num(year=None):
    """Genera el siguiente número 'NN/AA' de Resolucion de forma thread-safe.
    Consecutivo único anual (sin importar instancia PRIMERA/RECONSIDERACION)."""
    from django.db import transaction
    if year is None:
        year = timezone.now().year
    year_suffix = str(year)[-2:]
    with transaction.atomic():
        qs = (Resolucion.objects
              .select_for_update()
              .filter(RES_NUM__endswith=f'/{year_suffix}'))
        max_n = 0
        for r in qs:
            try:
                n = int(r.RES_NUM.split('/')[0])
                if n > max_n:
                    max_n = n
            except (ValueError, IndexError):
                pass
        return f'{max_n + 1:02d}/{year_suffix}'


# ============================================================
# MODELO 11c: RecursoTSP — Tabla unificada RAP + RAEE
# Discriminador TSP_INSTANCIA = APELACION | ACLARACION_ENMIENDA
# ============================================================
class RecursoTSP(models.Model):

    INSTANCIA_CHOICES = [
        ('APELACION',           'Recurso de Apelación'),
        ('ACLARACION_ENMIENDA', 'Aclaración, Explicación y Enmienda'),
    ]

    TIPO_CHOICES = [
        ('REVOCAR',                          'REVOCAR'),
        ('CONFIRMAR',                        'CONFIRMAR'),
        ('MODIFICAR',                        'MODIFICAR'),
        ('ANULAR HASTA EL VICIO MAS ANTIGUO','ANULAR HASTA EL VICIO MAS ANTIGUO'),
        ('OTRO',                             'OTRO'),
    ]

    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    TSP_INSTANCIA = models.CharField(
        max_length=25, choices=INSTANCIA_CHOICES, default='APELACION',
        verbose_name='Instancia')

    # Relaciones comunes
    sim  = models.ForeignKey(SIM, on_delete=models.CASCADE, verbose_name='Sumario')
    abog = models.ForeignKey(ABOG, on_delete=models.SET_NULL,
                             null=True, blank=True, verbose_name='Abogado')
    pm   = models.ForeignKey(PM, on_delete=models.SET_NULL,
                             null=True, blank=True, verbose_name='Militar')

    # Solo APELACION (reemplaza RAP.rr → ahora apunta a Resolucion RECONSIDERACION)
    resolucion = models.ForeignKey(
        Resolucion, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Resolución impugnada (solo APELACION)')

    # Solo ACLARACION_ENMIENDA (reemplaza RAEE.rap)
    recurso_origen = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='aclaraciones',
        verbose_name='Recurso origen (solo ACLARACION_ENMIENDA)')

    # Fechas y oficio (comunes)
    TSP_FECPRESEN = models.DateField(null=True, blank=True, verbose_name='Fecha de Presentación')
    TSP_OFI       = models.CharField(max_length=25, null=True, blank=True, verbose_name='N° Oficio Elevación')
    TSP_FECOFI    = models.DateField(null=True, blank=True, verbose_name='Fecha del Oficio')

    # Solo APELACION
    TSP_FECLIMITE = models.DateField(null=True, blank=True,
                                     verbose_name='Fecha Límite 3 días (APELACION)')
    TSP_TIPO      = models.CharField(max_length=50, choices=TIPO_CHOICES,
                                     null=True, blank=True,
                                     verbose_name='Tipo Resolución TSP (APELACION)')

    # Solo ACLARACION_ENMIENDA
    TSP_RESUM = models.CharField(max_length=200, null=True, blank=True,
                                 verbose_name='Resumen (ACLARACION_ENMIENDA)')

    # Resolución del TSP (comunes)
    TSP_NUM   = models.CharField(max_length=15,  null=True, blank=True, verbose_name='Número Resolución TSP')
    TSP_FEC   = models.DateField(null=True, blank=True, verbose_name='Fecha Resolución TSP')
    TSP_RESOL = models.TextField(null=True, blank=True, verbose_name='Resolución TSP')

    # Notificación
    TSP_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES,
                                      null=True, blank=True, verbose_name='Tipo Notificación')
    TSP_NOT    = models.CharField(max_length=100, null=True, blank=True,
                                  verbose_name='Notificado a /Dirección/Periódico')
    TSP_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    TSP_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    class Meta:
        db_table            = 'recurso_tsp'
        verbose_name        = 'Recurso TSP'
        verbose_name_plural = 'Recursos TSP'
        ordering            = ['-TSP_FEC']

    def __str__(self):
        return f"{self.TSP_NUM or 'Sin número'} — {self.get_TSP_INSTANCIA_display()}"

    def save(self, *args, **kwargs):
        if self.TSP_INSTANCIA == 'APELACION' and self.TSP_FECOFI and not self.TSP_FECLIMITE:
            self.TSP_FECLIMITE = add_business_days(self.TSP_FECOFI, 3)
        self.TSP_OFI   = self.TSP_OFI.upper()   if self.TSP_OFI   else self.TSP_OFI
        self.TSP_NUM   = self.TSP_NUM.upper()   if self.TSP_NUM   else self.TSP_NUM
        self.TSP_RESOL = self.TSP_RESOL.upper() if self.TSP_RESOL else self.TSP_RESOL
        self.TSP_TIPO  = self.TSP_TIPO.upper()  if self.TSP_TIPO  else self.TSP_TIPO
        self.TSP_RESUM = self.TSP_RESUM.upper() if self.TSP_RESUM else self.TSP_RESUM
        self.TSP_NOT   = self.TSP_NOT.upper()   if self.TSP_NOT   else self.TSP_NOT
        super().save(*args, **kwargs)

    def get_alerta_plazo(self):
        if self.TSP_INSTANCIA != 'APELACION' or not self.TSP_FECLIMITE:
            return 'secondary'
        hoy = timezone.now().date()
        diff = (self.TSP_FECLIMITE - hoy).days
        if diff < 0:
            return 'danger'
        elif diff <= 2:
            return 'warning'
        return 'success'


def next_recurso_tsp_num(year=None):
    from django.db import transaction
    if year is None:
        year = timezone.now().year
    year_suffix = str(year)[-2:]
    with transaction.atomic():
        qs = (RecursoTSP.objects
              .select_for_update()
              .filter(TSP_NUM__endswith=f'/{year_suffix}'))
        max_n = 0
        for r in qs:
            try:
                n = int(r.TSP_NUM.split('/')[0])
                if n > max_n:
                    max_n = n
            except (ValueError, IndexError):
                pass
        return f'{max_n + 1:02d}/{year_suffix}'


# ============================================================
# MODELO 12: PerfilUsuario — Sistema de roles
# ============================================================
class PerfilUsuario(models.Model):
    
    ROL_CHOICES = [
        # Sistema
        ('MASTER',                    'Master (Control Total)'),
        ('ADMINISTRADOR',             'Administrador de Sistemas'),
        ('AYUDANTE',                  'Ayudante (Registro Histórico)'),

        # Administrativo
        ('ADMIN1_AGENDADOR',          'Administrativo 1 (Agendador)'),
        ('ADMIN2_ARCHIVO',            'Administrativo 2 (Archivo SIM)'),
        ('ADMIN3_NOTIFICADOR',        'Administrativo 3 (Notificador)'),

        # Abogados
        ('ABOG1_ASESOR',              'Abogado 1 (Asesor/1ra Resolución)'),
        ('ABOG2_AUTOS',               'Abogado 2 (Autos de Ejecución)'),
        ('ABOG3_BUSCADOR',            'Abogado 3 (Búsqueda de Antecedentes)'),

        # Tribunal
        ('VOCAL_TPE',                 'Vocal TPE (Secretario de Actas)'),
        ('ASESOR_JURIDICO',           'Asesor Jurídico del DPTO-I'),

        # Legado (mantener compatibilidad)
        ('ABOGADO',                   'Abogado (General)'),
        ('BUSCADOR',                  'Buscador (General)'),
    ]

    user    = models.OneToOneField('auth.User', on_delete=models.CASCADE,
                                   verbose_name='Usuario del sistema')
    rol     = models.CharField(max_length=20, choices=ROL_CHOICES,
                               verbose_name='Rol/Perfil')
    abogado = models.ForeignKey(ABOG, on_delete=models.SET_NULL,
                                null=True, blank=True,
                                verbose_name='Vinculado a Abogado',
                                help_text='Solo para usuarios con rol ABOGADO')

    # ✅ NUEVO: Vinculación a VOCAL_TPE para usuarios con rol VOCAL_TPE
    vocal = models.ForeignKey(
        VOCAL_TPE, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Vinculado a Vocal TPE',
        help_text='Solo para usuarios con rol VOCAL_TPE')

    activo  = models.BooleanField(default=True, verbose_name='Usuario activo')
    
    class Meta:
        db_table            = 'perfil_usuario'
        verbose_name        = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    
    def __str__(self):
        return f"{self.user.username} ({self.get_rol_display()})"
