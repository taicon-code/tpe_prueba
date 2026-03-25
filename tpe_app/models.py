# ============================================================
#  MODELOS DJANGO — SISTEMA DE SUMARIOS INFORMATIVOS MILITARES
#  Versión 3.0 — Sincronizado con db_sumarios_v1.2
#  Correcciones: SIM_FECING, SIM_ESTADO, RES_EDICTO, RR_FECLIMITE,
#                RAP_FECLIMITE, RES_TIPO completo, DocumentoAdjunto
# ============================================================

from typing import Self

from django.db import models
from django.utils import timezone


# ============================================================
# MODELO 1: PM — Personal Militar
# ============================================================
class PM(models.Model):

    ESCALAFON_CHOICES = [
        ('GENERAL',            'General'),
        ('OFICIAL_SUPERIOR',   'Oficial Superior'),
        ('OFICIAL_SUBALTERNO', 'Oficial Subalterno'),
        ('SUBOFICIAL',         'Suboficial'),
        ('SARGENTO',           'Sargento'),
        ('TROPA',              'Tropa'),
        ('EMPLEADO_CIVIL',     'Empleado Civil'),
    ]
    GRADO_CHOICES = [
        # Generales
        ('GENERAL_EJERCITO',   'General de Ejército'),
        ('GENERAL_DIVISION',   'General de División'),
        ('GENERAL_BRIGADA',    'General de Brigada'),
        # Oficiales Superiores
        ('CORONEL',            'Coronel'),
        ('TCNEL',              'Teniente Coronel'),
        ('MAYOR',              'Mayor'),
        # Oficiales Subalternos
        ('CAPITAN',            'Capitán'),
        ('TENIENTE',           'Teniente'),
        ('SUBTENIENTE',        'Subteniente'),
        # Suboficiales
        ('SUBOFICIAL_MAESTRE', 'Suboficial Maestre'),
        ('SUBOFICIAL_MAYOR',   'Suboficial Mayor'),      
        ('SUBOFICIAL_1RO',     'Suboficial Primero'),
        ('SUBOFICIAL_2DO',     'Suboficial Segundo'),
        ('SUBOFICIAL_INICIAL', 'Suboficial Inicial'),
        # Sargentos
        ('SARGENTO_1RO',       'Sargento Primero'),
        ('SARGENTO_2DO',       'Sargento Segundo'),
        ('SARGENTO_INICIAL',   'Sargento Inicial'),
        # Tropa
        ('CABO',               'Cabo'),
        ('DRAGONEANTE',        'Dragoneante'),
        ('SOLDADO',            'Soldado'),
        # Empleados Civiles — Profesionales
        ('PROF_V',   'Prof. V'),   ('PROF_IV',  'Prof. IV'),
        ('PROF_III', 'Prof. III'), ('PROF_II',  'Prof. II'),
        ('PROF_I',   'Prof. I'),
        # Empleados Civiles — Técnicos
        ('TEC_V',   'Tec. V'),   ('TEC_IV',  'Tec. IV'),
        ('TEC_III', 'Tec. III'), ('TEC_II',  'Tec. II'),
        ('TEC_I',   'Tec. I'),
        # Empleados Civiles — Administrativos
        ('ADM_V',   'Adm. V'),   ('ADM_IV',  'Adm. IV'),
        ('ADM_III', 'Adm. III'), ('ADM_II',  'Adm. II'),
        ('ADM_I',   'Adm. I'),
        # Empleados Civiles — Apoyo Administrativo
        ('APAD_V',   'Apad. V'),   ('APAD_IV',  'Apad. IV'),
        ('APAD_III', 'Apad. III'), ('APAD_II',  'Apad. II'),
        ('APAD_I',   'Apad. I'),
    ]
    ARMA_CHOICES = [
        ('INFANTERIA',      'Infantería'),
        ('CABALLERIA',      'Caballería'),
        ('ARTILLERIA',      'Artillería'),
        ('INGENIERIA',      'Ingeniería'),
        ('COMUNICACIONES',  'Comunicaciones'),
        ('INTENDENCIA',     'Intendencia'),
        ('SANIDAD',         'Sanidad'),
        ('TOPOGRAFIA',       'Topografía'),
        ('AVIACION',        'Aviación del Ejército'),
        ('MÚSICA',          'Música'),
    ]
    ESTADO_CHOICES = [
        ('ACTIVO',         'Activo'),
        ('RETIRO OBLIGATORIO', 'Retiro Obligatorio'),
        ('RESERVA_ACTIVA', 'Reserva Activa'),
        ('BAJA',           'Baja'),
        ('FALLECIDO',      'Fallecido'),
    ]

    PM_CI        = models.DecimalField(max_digits=13, decimal_places=0, unique=True, verbose_name='Cédula de Identidad')
    PM_ESCALAFON = models.CharField(max_length=20, choices=ESCALAFON_CHOICES, null=True, blank=True, verbose_name='Escalafón')
    PM_GRADO     = models.CharField(max_length=20, choices=GRADO_CHOICES,     null=True, blank=True, verbose_name='Grado')
    PM_ARMA      = models.CharField(max_length=20, choices=ARMA_CHOICES,      null=True, blank=True, verbose_name='Arma')
    PM_ESPEC     = models.CharField(max_length=15, null=True, blank=True, verbose_name='Especialidad')
    PM_NOMBRE    = models.CharField(max_length=25, verbose_name='Nombre')
    PM_PATERNO   = models.CharField(max_length=25, verbose_name='Apellido Paterno')
    PM_MATERNO   = models.CharField(max_length=25, null=True, blank=True, verbose_name='Apellido Materno')
    PM_ESTADO    = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='ACTIVO', verbose_name='Estado')
    PM_PROMOCION = models.DateField(null=True, blank=True, verbose_name='Fecha de Promoción')

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
# MODELO 3: SIM — Sumario Informativo Militar (tabla central)
# ============================================================
class SIM(models.Model):

    TIPO_CHOICES =  [
        ('DISCIPLINARIO',  'DISCIPLINARIO'),
        ('ASCENSO POSTUMO', 'ASCENSO POSTUMO'),
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
    ]

    militares = models.ManyToManyField(
                    PM, through='PM_SIM', verbose_name='Militares investigados')

    SIM_COD       = models.CharField(max_length=10,  unique=True, verbose_name='Código SIM')
    # ✅ CORREGIDO v1.2: renombrado de SIM_FECTPE → SIM_FECING
    SIM_FECING    = models.DateField(null=True, blank=True, verbose_name='Fecha de Ingreso al TPE')
    # ✅ NUEVO v1.2: estado del sumario
    SIM_ESTADO    = models.CharField(
                        max_length=30, choices=ESTADO_CHOICES,
                        default='PARA_AGENDA', verbose_name='Estado')
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
    
    def save(self, *args, **kwargs):
        # Convertir a MAYÚSCULAS
        self.SIM_COD       = self.SIM_COD.upper()       if self.SIM_COD       else self.SIM_COD
        self.SIM_OBJETO    = self.SIM_OBJETO.upper()    if self.SIM_OBJETO    else self.SIM_OBJETO
        self.SIM_RESUM     = self.SIM_RESUM.upper()     if self.SIM_RESUM     else self.SIM_RESUM
        self.SIM_TIPO      = self.SIM_TIPO.upper()      if self.SIM_TIPO      else self.SIM_TIPO    
        self.SIM_AUTOFINAL = self.SIM_AUTOFINAL.upper() if self.SIM_AUTOFINAL else self.SIM_AUTOFINAL
        super().save(*args, **kwargs)

# ============================================================
# MODELO 4: PM_SIM — Tabla puente N:M (PM ↔ SIM)
# ============================================================
class PM_SIM(models.Model):

    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE,  db_column='ID_SIM', verbose_name='Sumario')
    ID_PM  = models.ForeignKey(PM,  on_delete=models.RESTRICT, db_column='ID_PM',  verbose_name='Militar')

    class Meta:
        db_table            = 'pm_sim'
        verbose_name        = 'Militar en Sumario'
        verbose_name_plural = 'Militares en Sumario'
        unique_together     = ('ID_SIM', 'ID_PM')

    def __str__(self):
        return f"{self.ID_SIM.SIM_COD} — {self.ID_PM}"


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

    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')
   
    # add fk de abogado para cada auto (puede ser el mismo u otro diferente al de la RES)
    ID_ABOG = models.ForeignKey(
        ABOG, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='ID_ABOG', verbose_name='Abogado')

    TPE_NUM   = models.CharField(max_length=15,  verbose_name='Número de Auto')
    TPE_FEC   = models.DateField(verbose_name='Fecha del Auto')
    TPE_RESOL = models.TextField(verbose_name='Resolución')
    TPE_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

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
# MODELO 6: RES — Primera Resolución del TPE
# ============================================================
class RES(models.Model):

    # ✅ CORREGIDO v1.2: lista completa de tipos de resolución
    TIPO_CHOICES = [
        ('ARCHIVO_OBRADOS',                'Archivo de Obrados'),
        ('ADMINISTRATIVO',                   'Administrativo'),
        ('SANCIONES_DISCIPLINARIAS',       'Sanciones Disciplinarias'),
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

    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')

    ID_ABOG = models.ForeignKey(
        ABOG, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='ID_ABOG', verbose_name='Abogado')

    RES_NUM   = models.CharField(max_length=15,  verbose_name='Número de Resolución')
    RES_FEC   = models.DateField(verbose_name='Fecha')
    RES_RESOL = models.TextField(verbose_name='Resolución')
    RES_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo')
    RES_RESUM = models.CharField(max_length=200, null=True, blank=True, verbose_name='Resumen')

    # Notificación Tipo
    RES_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES, null=True, blank=True, verbose_name='Tipo de Notificación')
    RES_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a /Dirección/Periódico')
    RES_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    RES_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # Agenda
    RES_AGENDA  = models.CharField(max_length=40, null=True, blank=True, verbose_name='Agenda')
    RES_FECAGEN = models.DateField(null=True, blank=True, verbose_name='Fecha Agenda')

    class Meta:
        db_table            = 'res'
        verbose_name        = 'Primera Resolución'
        verbose_name_plural = 'Primeras Resoluciones'
        ordering            = ['-RES_FEC']

    def __str__(self):
        return f"{self.RES_NUM} — {self.get_RES_TIPO_display()}"
    def save(self, *args, **kwargs):
        self.RES_NUM   = self.RES_NUM.upper()   if self.RES_NUM   else self.RES_NUM
        self.RES_RESOL = self.RES_RESOL.upper() if self.RES_RESOL else self.RES_RESOL
        self.RES_RESUM = self.RES_RESUM.upper() if self.RES_RESUM else self.RES_RESUM
        self.RES_NOT   = self.RES_NOT.upper()   if self.RES_NOT   else self.RES_NOT
        self.RES_AGENDA= self.RES_AGENDA.upper()if self.RES_AGENDA else self.RES_AGENDA
        super().save(*args, **kwargs)

# ============================================================
# MODELO 7: RR — Segunda Resolución (Recurso de Reconsideración)
# ============================================================
class RR(models.Model):

    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    ID_RES = models.ForeignKey(RES, on_delete=models.CASCADE, db_column='ID_RES', verbose_name='Primera Resolución')
    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')

    RR_FECPRESEN = models.DateField(null=True, blank=True, verbose_name='Fecha de Presentación del Recurso')
    # ✅ NUEVO v1.2: fecha límite para alertas (15 días hábiles)
    RR_FECLIMITE = models.DateField(null=True, blank=True, verbose_name='Fecha Límite (15 días hábiles)')

# estes aumente para agregar campo para abogado del RR (puede ser el mismo u otro diferente al de la RES)
    ID_ABOG = models.ForeignKey(
        ABOG, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='ID_ABOG', verbose_name='Abogado')

    RR_NUM   = models.CharField(max_length=10,  verbose_name='Número')
    RR_FEC   = models.DateField(verbose_name='Fecha')
    RR_RESOL = models.TextField(verbose_name='Resolución')
    RR_RESUM = models.CharField(max_length=200, null=True, blank=True, verbose_name='Resumen')

    # Notificación Tipo
    RR_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES, null=True, blank=True, verbose_name='Tipo de Notificación')
    RR_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a /Dirección/Periódico')
    RR_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    RR_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # Agenda
    RR_AGENDA  = models.CharField(max_length=20, null=True, blank=True, verbose_name='Agenda')
    RR_FECAGEN = models.DateField(null=True, blank=True, verbose_name='Fecha Agenda')

    class Meta:
        db_table            = 'rr'
        verbose_name        = 'Segunda Resolución (RR)'
        verbose_name_plural = 'Segundas Resoluciones (RR)'
        ordering            = ['-RR_FEC']

    def __str__(self):
        return f"{self.RR_NUM} — {self.RR_RESUM or 'Sin resumen'}"
    def save(self, *args, **kwargs):
        self.RR_NUM    = self.RR_NUM.upper()    if self.RR_NUM    else self.RR_NUM
        self.RR_RESOL  = self.RR_RESOL.upper()  if self.RR_RESOL  else self.RR_RESOL
        self.RR_RESUM  = self.RR_RESUM.upper()  if self.RR_RESUM  else self.RR_RESUM
        self.RR_NOT    = self.RR_NOT.upper()    if self.RR_NOT    else self.RR_NOT
        self.RR_AGENDA = self.RR_AGENDA.upper() if self.RR_AGENDA else self.RR_AGENDA
        super().save(*args, **kwargs)

    def get_alerta_plazo(self):
        """Devuelve color de alerta según proximidad a RR_FECLIMITE."""
        if not self.RR_FECLIMITE:
            return 'secondary'
        hoy = timezone.now().date()
        diff = (self.RR_FECLIMITE - hoy).days
        if diff < 0:
            return 'danger'    # vencido
        elif diff <= 5:
            return 'warning'   # próximo a vencer
        return 'success'       # tiempo suficiente


# ============================================================
# MODELO 8: RAP — Recurso de Apelación al TSP
# ============================================================
class RAP(models.Model):
    
    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]
    ID_RR  = models.ForeignKey(RR,  on_delete=models.SET_NULL, null=True, blank=True,
                                db_column='ID_RR',  verbose_name='Segunda Resolución (RR)')
    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE,
                                db_column='ID_SIM', verbose_name='Sumario')

    # Elevación al TSP
    RAP_OFI    = models.CharField(max_length=15, null=True, blank=True, verbose_name='N° Oficio Elevación')
    RAP_FECOFI = models.DateField(null=True, blank=True, verbose_name='Fecha del Oficio')
    # ✅ NUEVO v1.2: fecha límite para alertas (3 días hábiles)
    RAP_FECLIMITE = models.DateField(null=True, blank=True, verbose_name='Fecha Límite remisión TSP (3 días hábiles)')

    # Resolución del TSP
    RAP_NUM   = models.CharField(max_length=15,  null=True, blank=True, verbose_name='Número Resolución TSP')
    RAP_FEC   = models.DateField(null=True, blank=True, verbose_name='Fecha Resolución TSP')
    RAP_RESOL = models.TextField(null=True, blank=True, verbose_name='Resolución TSP')
    RAP_RESUM = models.TextField(null=True, blank=True, verbose_name='Resumen')

    # Notificación Tipo
    RAP_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES, null=True, blank=True, verbose_name='Tipo de Notificación')
    RAP_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a /Dirección/Periódico')
    RAP_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    RAP_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    class Meta:
        db_table            = 'rap'
        verbose_name        = 'Recurso de Apelación (RAP)'
        verbose_name_plural = 'Recursos de Apelación (RAP)'
        ordering            = ['-RAP_FEC']

    def __str__(self):
        return f"{self.RAP_NUM or 'Sin número'} — {self.ID_SIM.SIM_COD}"
    
    def save(self, *args, **kwargs):
        self.RAP_OFI   = self.RAP_OFI.upper()   if self.RAP_OFI   else self.RAP_OFI
        self.RAP_NUM   = self.RAP_NUM.upper()   if self.RAP_NUM   else self.RAP_NUM
        self.RAP_RESOL = self.RAP_RESOL.upper() if self.RAP_RESOL else self.RAP_RESOL
        self.RAP_RESUM = self.RAP_RESUM.upper() if self.RAP_RESUM else self.RAP_RESUM
        self.RAP_NOT   = self.RAP_NOT.upper()   if self.RAP_NOT   else self.RAP_NOT
        super().save(*args, **kwargs)

    def get_alerta_plazo(self):
        """Devuelve color de alerta según proximidad a RAP_FECLIMITE."""
        if not self.RAP_FECLIMITE:
            return 'secondary'
        hoy = timezone.now().date()
        diff = (self.RAP_FECLIMITE - hoy).days
        if diff < 0:
            return 'danger'
        elif diff <= 2:
            return 'warning'
        return 'success'


# ============================================================
# MODELO 9: RAEE — Recurso de Aclaración, Explicación y Enmienda
# ============================================================
class RAEE(models.Model):

    NOTIF_CHOICES = [
        ('FIRMA',   'Firma'),
        ('EDICTO',  'Edicto'),
        ('CEDULON', 'Cedulón'),
    ]

    ID_RAP = models.ForeignKey(RAP, on_delete=models.SET_NULL, null=True, blank=True,
                                db_column='ID_RAP', verbose_name='Recurso de Apelación')
    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE,
                                db_column='ID_SIM', verbose_name='Sumario')

    RAE_OFI    = models.CharField(max_length=15, null=True, blank=True, verbose_name='N° Oficio')
    RAE_FECOFI = models.DateField(null=True, blank=True, verbose_name='Fecha del Oficio')

    RAE_NUM   = models.CharField(max_length=15,  null=True, blank=True, verbose_name='Número Resolución')
    RAE_FEC   = models.DateField(null=True, blank=True, verbose_name='Fecha Resolución')
    RAE_RESOL = models.TextField(null=True, blank=True, verbose_name='Resolución')
    RAE_RESUM = models.CharField(max_length=200, null=True, blank=True, verbose_name='Resumen')

    # Notificación Tipo
    RAE_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES, null=True, blank=True, verbose_name='Tipo de Notificación')
    RAE_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a /Dirección/Periódico')
    RAE_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    RAE_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # Agenda
    RAE_AGENDA  = models.CharField(max_length=15, null=True, blank=True, verbose_name='Agenda')
    RAE_FECAGEN = models.DateField(null=True, blank=True, verbose_name='Fecha Agenda')

    class Meta:
        db_table            = 'raee'
        verbose_name        = 'RAEE — Aclaración, Explicación y Enmienda'
        verbose_name_plural = 'RAEE — Aclaración, Explicación y Enmienda'
        ordering            = ['-RAE_FEC']

    def __str__(self):
        return f"{self.RAE_NUM or 'Sin número'} — {self.ID_SIM.SIM_COD}"
    def save(self, *args, **kwargs):
        self.RAE_OFI   = self.RAE_OFI.upper()   if self.RAE_OFI   else self.RAE_OFI
        self.RAE_NUM   = self.RAE_NUM.upper()   if self.RAE_NUM   else self.RAE_NUM
        self.RAE_RESOL = self.RAE_RESOL.upper() if self.RAE_RESOL else self.RAE_RESOL
        self.RAE_RESUM = self.RAE_RESUM.upper() if self.RAE_RESUM else self.RAE_RESUM
        self.RAE_NOT   = self.RAE_NOT.upper()   if self.RAE_NOT   else self.RAE_NOT
        self.RAE_AGENDA= self.RAE_AGENDA.upper()if self.RAE_AGENDA else self.RAE_AGENDA
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

    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')

    TSP_NUM   = models.CharField(max_length=15,  verbose_name='Número de Auto')
    TSP_FEC   = models.DateField(verbose_name='Fecha del Auto')
    TSP_RESOL = models.TextField(verbose_name='Resolución')
    TSP_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

    # Notificación Tipo
    TSP_TIPO_NOTIF = models.CharField(max_length=20, choices=NOTIF_CHOICES, null=True, blank=True, verbose_name='Tipo de Notificación')
    TSP_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a /Dirección/Periódico')
    TSP_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    TSP_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # Auto de Ejecutoria (sin memorándum en TSP)
    TSP_EJECU_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado Ejecutoria')
    TSP_EJECU_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notif. Ejecutoria')

    class Meta:
        db_table            = 'autotsp'
        verbose_name        = 'Auto TSP'
        verbose_name_plural = 'Autos TSP'
        ordering            = ['-TSP_FEC']

    def __str__(self):
        return f"{self.TSP_NUM} — {self.get_TSP_TIPO_display()}"
    def save(self, *args, **kwargs):
        self.TSP_NUM          = self.TSP_NUM.upper()          if self.TSP_NUM          else self.TSP_NUM
        self.TSP_RESOL        = self.TSP_RESOL.upper()        if self.TSP_RESOL        else self.TSP_RESOL
        self.TSP_NOT          = self.TSP_NOT.upper()          if self.TSP_NOT          else self.TSP_NOT
        self.TSP_EDICTO_PERIOD= self.TSP_EDICTO_PERIOD.upper()if self.TSP_EDICTO_PERIOD else self.TSP_EDICTO_PERIOD
        self.TSP_EJECU_NOT    = self.TSP_EJECU_NOT.upper()    if self.TSP_EJECU_NOT    else self.TSP_EJECU_NOT
        super().save(*args, **kwargs)

# ============================================================
# MODELO 11: DocumentoAdjunto — PDFs escaneados (2013–2026)
# ✅ NUEVO v1.2
# ============================================================
class DocumentoAdjunto(models.Model):

    TABLA_CHOICES = [
        ('sim',     'Sumario SIM'),
        ('res',     'Resolución TPE'),
        ('rr',      'Segunda Resolución RR'),
        ('rap',     'Recurso de Apelación RAP'),
        ('raee',    'RAEE'),
        ('autotpe', 'Auto TPE'),
        ('autotsp', 'Auto TSP'),
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
