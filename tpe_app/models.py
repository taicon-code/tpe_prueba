# ============================================================
#  MODELOS DJANGO — SISTEMA DE SUMARIOS INFORMATIVOS MILITARES
#  Versión 3.0 — Sincronizado con db_sumarios_v1.2
#  Correcciones: SIM_FECING, SIM_ESTADO, RES_EDICTO, RR_FECLIMITE,
#                RAP_FECLIMITE, RES_TIPO completo, DocumentoAdjunto
# ============================================================

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
        ('SUBOFICIAL_MAYOR',   'Suboficial Mayor'),
        ('SUBOFICIAL_MAESTRE', 'Suboficial Maestre'),
        ('SUBOFICIAL_1RO',     'Suboficial Primero'),
        ('SUBOFICIAL_2DO',     'Suboficial Segundo'),
        ('SUBOFICIAL_INICIAL', 'Suboficial Inicial'),
        # Sargentos y tropa
        ('SARGENTO_1RO',       'Sargento Primero'),
        ('SARGENTO_2DO',       'Sargento Segundo'),
        ('SARGENTO_INICIAL',   'Sargento Inicial'),
        ('CABO',               'Cabo'),
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
        ('JAM',             'JAM'),
        ('AVIACION',        'Aviación del Ejército'),
        ('POLICIA_MILITAR', 'Policía Militar'),
    ]
    ESTADO_CHOICES = [
        ('ACTIVO',         'Activo'),
        ('BAJA',           'Baja'),
        ('FALLECIDO',      'Fallecido'),
        ('RESERVA_ACTIVA', 'Reserva Activa'),
    ]

    PM_CI        = models.DecimalField(max_digits=8, decimal_places=0, unique=True, verbose_name='Cédula de Identidad')
    PM_ESCALAFON = models.CharField(max_length=20, choices=ESCALAFON_CHOICES, null=True, blank=True, verbose_name='Escalafón')
    PM_GRADO     = models.CharField(max_length=20, choices=GRADO_CHOICES,     null=True, blank=True, verbose_name='Grado')
    PM_ARMA      = models.CharField(max_length=20, choices=ARMA_CHOICES,      null=True, blank=True, verbose_name='Arma')
    PM_ESPEC     = models.CharField(max_length=15, null=True, blank=True, verbose_name='Especialidad')
    PM_NOMBRE    = models.CharField(max_length=25, verbose_name='Nombre')
    PM_PATERNO   = models.CharField(max_length=25, verbose_name='Apellido Paterno')
    PM_MATERNO   = models.CharField(max_length=25, null=True, blank=True, verbose_name='Apellido Materno')
    PM_ESTADO    = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='ACTIVO', verbose_name='Estado')
    PM_PROMOCION = models.DateField(null=True, blank=True, verbose_name='Fecha de Promoción')

    class Meta:
        db_table            = 'pm'
        verbose_name        = 'Personal Militar'
        verbose_name_plural = 'Personal Militar'
        ordering            = ['PM_PATERNO', 'PM_NOMBRE']

    def __str__(self):
        return f"{self.get_PM_GRADO_display()} {self.PM_NOMBRE} {self.PM_PATERNO}"


# ============================================================
# MODELO 2: ABOG — Abogados del Tribunal
# ============================================================
class ABOG(models.Model):

    AB_CI      = models.DecimalField(max_digits=8, decimal_places=0, unique=True, verbose_name='Cédula de Identidad')
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
        return f"{self.AB_GRADO} {self.AB_NOMBRE} {self.AB_PATERNO}"


# ============================================================
# MODELO 3: SIM — Sumario Informativo Militar (tabla central)
# ============================================================
class SIM(models.Model):

    TIPO_CHOICES = [
        ('DISCIPLINARIO',  'Disciplinario'),
        ('ADMINISTRATIVO', 'Administrativo'),
        ('PENAL',          'Penal'),
    ]

    # ✅ CORREGIDO v1.2: estados del sumario
    ESTADO_CHOICES = [
        ('RADICADO_TPE',      'Radicado en el TPE'),
        ('PARA_AGENDA',       'Para Agenda'),
        ('EN_APELACION_TSP',  'En Apelación TSP'),
    ]

    ID_ABOG   = models.ForeignKey(
                    ABOG, on_delete=models.RESTRICT,
                    db_column='ID_ABOG', verbose_name='Abogado')
    militares = models.ManyToManyField(
                    PM, through='PM_SIM', verbose_name='Militares investigados')

    SIM_COD       = models.CharField(max_length=10,  unique=True, verbose_name='Código SIM')
    # ✅ CORREGIDO v1.2: renombrado de SIM_FECTPE → SIM_FECING
    SIM_FECING    = models.DateField(null=True, blank=True, verbose_name='Fecha de Ingreso al TPE')
    # ✅ NUEVO v1.2: estado del sumario
    SIM_ESTADO    = models.CharField(
                        max_length=20, choices=ESTADO_CHOICES,
                        default='RADICADO_TPE', verbose_name='Estado del Sumario')
    SIM_OBJETO    = models.TextField(verbose_name='Objeto del sumario')
    SIM_RESUM     = models.CharField(max_length=200, verbose_name='Resumen')
    SIM_AUTOFINAL = models.TextField(null=True, blank=True, verbose_name='Auto Final / Dictamen')
    SIM_TIPO      = models.CharField(max_length=50, choices=TIPO_CHOICES, verbose_name='Tipo')
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
            'RADICADO_TPE':     'primary',
            'PARA_AGENDA':      'warning',
            'EN_APELACION_TSP': 'danger',
        }
        return colores.get(self.SIM_ESTADO, 'secondary')


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
    ]

    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')

    TPE_NUM   = models.CharField(max_length=15,  verbose_name='Número de Auto')
    TPE_FEC   = models.DateField(verbose_name='Fecha del Auto')
    TPE_RESOL = models.TextField(verbose_name='Resolución')
    TPE_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

    # Notificación por Firma
    TPE_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a')
    TPE_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    TPE_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # Notificación por Edicto
    TPE_EDICTO_PERIOD = models.CharField(max_length=100, null=True, blank=True, verbose_name='Periódico del Edicto')
    TPE_EDICTO_FEC    = models.DateField(null=True, blank=True, verbose_name='Fecha del Edicto')

    # Auto de Ejecutoria
    TPE_EJECU_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado Ejecutoria')
    TPE_EJECU_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notif. Ejecutoria')

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


# ============================================================
# MODELO 6: RES — Primera Resolución del TPE
# ============================================================
class RES(models.Model):

    # ✅ CORREGIDO v1.2: lista completa de tipos de resolución
    TIPO_CHOICES = [
        ('SANCIONES_DISCIPLINARIAS',       'Sanciones Disciplinarias'),
        ('SANCION_ARRESTO',                'Sanción Arresto (Ejecutiva)'),
        ('SANCION_LETRA_B',                'Sanción Letra B (Pérdida de Antigüedad)'),
        ('SANCION_RETIRO_OBLIGATORIO',     'Sanción Retiro Obligatorio'),
        ('SANCION_BAJA',                   'Sanción Baja'),
        ('SOLICITUD_LETRA_D',              'Solicitud Letra D (Permiso Médico)'),
        ('SOLICITUD_LICENCIA_MAXIMA',      'Solicitud Licencia Máxima'),
        ('SOLICITUD_ASCENSO',              'Solicitud de Ascenso'),
        ('SOLICITUD_RESTITUCION_ANTIGUEDAD','Solicitud de Restitución de Antigüedad'),
        ('ARCHIVO_OBRADOS',                'Archivo de Obrados'),
        ('OTRO',                           'Otro'),
    ]

    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')

    RES_NUM   = models.CharField(max_length=15,  verbose_name='Número de Resolución')
    RES_FEC   = models.DateField(verbose_name='Fecha')
    RES_RESOL = models.TextField(verbose_name='Resolución')
    RES_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo')
    RES_RESUM = models.CharField(max_length=200, null=True, blank=True, verbose_name='Resumen')

    # Notificación por Firma
    RES_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a')
    RES_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    RES_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # ✅ NUEVO v1.2: Notificación por Edicto en resoluciones
    RES_EDICTO_PERIOD = models.CharField(max_length=100, null=True, blank=True, verbose_name='Periódico del Edicto')
    RES_EDICTO_FEC    = models.DateField(null=True, blank=True, verbose_name='Fecha del Edicto')

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


# ============================================================
# MODELO 7: RR — Segunda Resolución (Recurso de Reconsideración)
# ============================================================
class RR(models.Model):

    ID_RES = models.ForeignKey(RES, on_delete=models.CASCADE, db_column='ID_RES', verbose_name='Primera Resolución')
    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')

    RR_FECPRESEN = models.DateField(null=True, blank=True, verbose_name='Fecha de Presentación del Recurso')
    # ✅ NUEVO v1.2: fecha límite para alertas (15 días hábiles)
    RR_FECLIMITE = models.DateField(null=True, blank=True, verbose_name='Fecha Límite (15 días hábiles)')

    RR_NUM   = models.CharField(max_length=10,  verbose_name='Número')
    RR_FEC   = models.DateField(verbose_name='Fecha')
    RR_RESOL = models.TextField(verbose_name='Resolución')
    RR_RESUM = models.CharField(max_length=200, null=True, blank=True, verbose_name='Resumen')

    # Notificación
    RR_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a')
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

    # Notificación
    RAP_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a')
    RAP_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    RAP_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    class Meta:
        db_table            = 'rap'
        verbose_name        = 'Recurso de Apelación (RAP)'
        verbose_name_plural = 'Recursos de Apelación (RAP)'
        ordering            = ['-RAP_FEC']

    def __str__(self):
        return f"{self.RAP_NUM or 'Sin número'} — {self.ID_SIM.SIM_COD}"

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

    # Notificación
    RAE_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a')
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

    ID_SIM = models.ForeignKey(SIM, on_delete=models.CASCADE, db_column='ID_SIM', verbose_name='Sumario')

    TSP_NUM   = models.CharField(max_length=15,  verbose_name='Número de Auto')
    TSP_FEC   = models.DateField(verbose_name='Fecha del Auto')
    TSP_RESOL = models.TextField(verbose_name='Resolución')
    TSP_TIPO  = models.CharField(max_length=100, choices=TIPO_CHOICES, verbose_name='Tipo de Auto')

    # Notificación por Firma
    TSP_NOT    = models.CharField(max_length=100, null=True, blank=True, verbose_name='Notificado a')
    TSP_FECNOT = models.DateField(null=True, blank=True, verbose_name='Fecha Notificación')
    TSP_HORNOT = models.TimeField(null=True, blank=True, verbose_name='Hora Notificación')

    # Notificación por Edicto
    TSP_EDICTO_PERIOD = models.CharField(max_length=100, null=True, blank=True, verbose_name='Periódico del Edicto')
    TSP_EDICTO_FEC    = models.DateField(null=True, blank=True, verbose_name='Fecha del Edicto')

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
