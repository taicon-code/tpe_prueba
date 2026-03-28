from django.contrib import admin
from django import forms
from django.utils.html import mark_safe
from .models import DICTAMEN, PM, ABOG, SIM, PM_SIM, AGENDA, AUTOTPE, RES, RR, RAP, RAEE, AUTOTSP, DocumentoAdjunto
from .widgets import ResumenConOpcionesWidget


# ============================================================
#  Configuración general del panel admin
# ============================================================
admin.site.site_header = "Sistema TPE — Tribunal de Personal del Ejército"
admin.site.site_title  = "TPE Sistema"
admin.site.index_title = "Panel de Administración"


RESUMEN_CHOICES = [
        ('ADMINISTRACIÓN IRREGULAR DE INSTITUCIÓN PUBLICA MILITAR','ADMINISTRACIÓN IRREGULAR DE INSTITUCIÓN PUBLICA MILITAR'),
        ('ALLANAMIENTO FALTA DE RESPETO Y AMENAZAS AL SUPERIOR','ALLANAMIENTO, FALTA DE RESPETO Y AMENAZAS AL SUPERIOR'),
        ('COBROS IRREGULARES','COBROS IRREGULARES'),
        ('CONSUMO DE BEBIDAS ALCOHOLICAS EN INSTALACIONES ','CONSUMO DE BEBIDAS ALCOHOLICAS EN INSTALACIONES '),
        ('CONSUMO DE BEBIDAS ALCOHOLICAS PMA.','CONSUMO DE BEBIDAS ALCOHOLICAS PMA.'),
        ('CONSUMO DE BEBIDAS ALCOHOLICAS PMA. Y ACCIDENTE DE TRANSITO','CONSUMO DE BEBIDAS ALCOHOLICAS PMA. Y ACCIDENTE DE TRANSITO'),
        ('CONSUMO DE BEBIDAS ALCOHOLICAS PMA. Y MALTRATO A SLDOS.','CONSUMO DE BEBIDAS ALCOHOLICAS PMA. Y MALTRATO A SLDOS.'),
        ('CONSUMO DE BEBIDAS ALCOHOLICAS Y HOMICIDIO','CONSUMO DE BEBIDAS ALCOHOLICAS Y HOMICIDIO'),
        ('CONSUMO DE SUSTANCIAS CONTROLADAS EN SERVICIO','CONSUMO DE SUSTANCIAS CONTROLADAS EN SERVICIO'),
        ('DELITOS SEXUALES','DELITOS SEXUALES'),
        ('DESTRUCCIÓN ILEGAL DE BIENES ESTATALES','DESTRUCCIÓN ILEGAL DE BIENES ESTATALES'),
        ('EMPLEO DE SOLDADO','EMPLEO DE SOLDADO'),
        ('FALSIFICACIÓN Y USO DE DOCUMENTO FALSO','FALSIFICACIÓN Y USO DE DOCUMENTO FALSO'),
        ('FALTA LISTA','FALTA LISTA'),
        ('FAVORECIMIENTO AL CONTRABANDO','FAVORECIMIENTO AL CONTRABANDO'),
        ('FAVORECIMIENTO AL ROBO DE MINERAL','FAVORECIMIENTO AL ROBO DE MINERAL'),
        ('HURTO DE ARMAMENTO','HURTO DE ARMAMENTO'),
        ('INDISCIPLINA PROFESIONAL','INDISCIPLINA PROFESIONAL'),
        ('MALOS TRATOS AL PERSONAL','MALOS TRATOS AL PERSONAL'),
        ('MALOS TRATOS AL PERSONAL Y COBROS','MALOS TRATOS AL PERSONAL Y COBROS'),
        ('MALTRATO A SLDOS.','MALTRATO A SLDOS.'),
        ('MALVERSACIÓN Y COBROS INDEBIDOS REITERADOS','MALVERSACIÓN Y COBROS INDEBIDOS REITERADOS'),
        ('REINCORPORACION AL SERVICIO ACTIVO','REINCORPORACION AL SERVICIO ACTIVO'),
        ('RELACION EXTRAMATRIMONIAL','RELACION EXTRAMATRIMONIAL'),
        ('TENENCIA DE MUNICIÓN ','TENENCIA DE MUNICIÓN '),
        ('SOLICITUD DE ASCENSO AL GRADO INMEDIATO SUPERIOR','SOLICITUD DE ASCENSO AL GRADO INMEDIATO SUPERIOR'),
        ('SOLICITUD DE EXIMIR CURSO CONDOR','SOLICITUD DE EXIMIR CURSO CONDOR'),
        ('SOLICITUD RESTITUCIÓN DE ANTIGÜEDAD','SOLICITUD RESTITUCIÓN DE ANTIGÜEDAD'),
        ('SOLICITUD ASCENSO POSTUMO','SOLICITUD ASCENSO POSTUMO'),
        ('SOLICITUD LICENCIA MAXIMA','SOLICITUD LICENCIA MAXIMA'),
        ('SOLICITUD LETRA "D"','SOLICITUD LETRA "D"'),
        ('SOLICITUD ART. 118 LOFA','SOLICITUD ART. 118 LOFA'),
        ('SOLICITUD ART. 114 LOFA','SOLICITUD ART. 114 LOFA'),
        ('OTRO','OTRO'),
    ]

# ============================================================
#  SECCIÓN 1: SUMARIO INFORMATIVO MILITAR
#  Color azul — agrupa PM, ABOG y SIM
# ============================================================
class SIMAdminForm(forms.ModelForm):
    """
    Formulario personalizado para SIM que usa el widget ResumenConOpcionesWidget.
    
    El widget permite:
    - Seleccionar opciones predefinidas
    - Escribir texto personalizado
    - Sin crear nuevas columnas en la BD
    """
    
    class Meta:
        model = SIM
        fields = '__all__'
        widgets = {
            'SIM_RESUM': ResumenConOpcionesWidget(opciones=RESUMEN_CHOICES),
        }


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Personal Militar
# ════════════════════════════════════════════════════════════════════════════
@admin.register(PM)
class PMAdmin(admin.ModelAdmin):
    list_display  = ('PM_CI', 'PM_ESCALAFON', 'PM_GRADO', 'PM_NOMBRE', 'PM_PATERNO', 'PM_ARMA', 'PM_ESTADO')
    search_fields = ('PM_CI', 'PM_NOMBRE', 'PM_PATERNO')
    list_filter   = ('PM_ESTADO', 'PM_ESCALAFON', 'PM_ARMA')

    class Meta:
        verbose_name        = "Personal Militar"
        verbose_name_plural = "Personal Militar"

    class Media:
        js = ('tpe_app/js/grado_filter.js',)

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Abogados
# ════════════════════════════════════════════════════════════════════════════
@admin.register(ABOG)
class ABOGAdmin(admin.ModelAdmin):
    list_display  = ('AB_CI', 'AB_GRADO', 'AB_NOMBRE', 'AB_PATERNO', 'AB_MATERNO')
    search_fields = ('AB_CI', 'AB_NOMBRE', 'AB_PATERNO')


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Sumarios Informativos Militares
# ════════════════════════════════════════════════════════════════════════════

# ── Inline: militares dentro del formulario SIM ──────────────
class PM_SIM_Inline(admin.TabularInline):
    model               = PM_SIM
    extra               = 1
    verbose_name        = "Militar investigado"
    verbose_name_plural = "Militares investigados"


@admin.register(SIM)
class SIMAdmin(admin.ModelAdmin):
    form          = SIMAdminForm
    list_display  = ('SIM_COD', 'SIM_TIPO', 'SIM_RESUM', 'SIM_FECREG')
    search_fields = ('SIM_COD', 'SIM_RESUM')
    list_filter   = ('SIM_TIPO',)
    inlines       = [PM_SIM_Inline]
# ESTO ORDENA LOS CAMPOS EN EL FORMULARIO PARA LA VISUALIZACIÓN DENTRO DEL SUMARIO INFORMATIVO MILITAR
    fieldsets = (
        ('Datos principales', {
            'fields': ('SIM_COD','SIM_FECING', 'SIM_OBJETO','SIM_RESUM', 'SIM_AUTOFINAL','SIM_TIPO')
        }),
        ('Situación Actual', {
            'fields': ('SIM_ESTADO',)
        }),
    )

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Agenda — Reunión del Tribunal
#  Se registra ANTES que la RES o el AUTOTPE
# ════════════════════════════════════════════════════════════════════════════
@admin.register(AGENDA)
class AGENDAAdmin(admin.ModelAdmin):
    list_display  = ('AG_NUM', 'AG_FECPROG', 'AG_FECREAL', 'ID_SIM','AG_TIPO')
    search_fields = ('AG_NUM', 'ID_SIM__SIM_COD')
    list_filter   = ()

    fieldsets = (
        ('Datos de la Reunión', {
            'fields': ('ID_SIM', 'AG_NUM', 'AG_FECPROG', 'AG_FECREAL','AG_TIPO',)
        }),

    )

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: DICTAMEN
#  Se registra ANTES que la RES Y/o el AUTOTPE
# ════════════════════════════════════════════════════════════════════════════
@admin.register(DICTAMEN)
class DICTAMENAdmin(admin.ModelAdmin):

    list_display  = ('DIC_NUM', 'DIC_CONCL', 'ID_AGENDA', 'ID_ABOG')
    search_fields = ('DIC_NUM', 'ID_AGENDA__ID_SIM__SIM_COD')
    list_filter   = ('ID_ABOG', 'ID_AGENDA',)

    fieldsets = (
        ('Datos de la Reunión', {
            'fields': ('ID_AGENDA', 'ID_ABOG', 'DIC_NUM', 'DIC_CONCL')
        }),
    )


# ============================================================
#  SECCIÓN 2: TRIBUNAL DE PERSONAL DEL EJÉRCITO (TPE)
#  Agrupa RES, RR y AUTOTPE
# ============================================================

@admin.register(RES)
class RESAdmin(admin.ModelAdmin):
    list_display  = ('RES_NUM', 'ID_SIM', 'ID_ABOG', 'RES_TIPO', 'RES_FEC', 'RES_TIPO_NOTIF', 'RES_NOT', 'RES_FECNOT','RES_HORNOT')
    search_fields = ('RES_NUM', 'ID_SIM__SIM_COD','ID_ABOG__AB_PATERNO')
    list_filter   = ('RES_TIPO',)

# ESTO ORDENA LOS CAMPOS EN EL FORMULARIO PARA LA VISUALIZACIÓN DENTRO DE LA RESOLUCIÓN DEL TPE
    fieldsets = (
        ('AGENDA', {
            'fields': ('ID_SIM', 'ID_ABOG', 'ID_AGENDA',)
        }),
        ('DISPOSICIÒN RESOLUTIVA', {
            'fields': ('RES_NUM','RES_FEC','RES_RESOL','RES_TIPO',)
        }),
        ('NOTIFICACIÓN', {
            'fields': ('RES_TIPO_NOTIF','RES_NOT','RES_FECNOT','RES_HORNOT',)
        }),
    )

@admin.register(RR)
class RRAdmin(admin.ModelAdmin):
    list_display  = ('RR_NUM', 'ID_SIM', 'ID_RES', 'ID_ABOG', 'RR_FEC', 'RR_FECPRESEN', 'alerta_plazo', 'RR_TIPO_NOTIF', 'RR_NOT', 'RR_FECNOT','RR_HORNOT')
    search_fields = ('RR_NUM', 'ID_SIM__SIM_COD','ID_ABOG__AB_PATERNO')
# ESTO ORDENA LOS CAMPOS EN EL FORMULARIO PARA LA VISUALIZACION DENTRO DE LA RESOLUCION DEL TPE
    fieldsets = (
        ('PLAZOS', {
            'fields': ('ID_SIM', 'ID_RES', 'ID_ABOG', 'ID_AGENDA', 'RR_FECPRESEN', 'RR_FECLIMITE',)
        }),
        ('DISPOSICION RESOLUTIVA', {
            'fields': ('RR_NUM','RR_FEC','RR_RESOL','RR_RESUM',)
        }),
        ('NOTIFICACION', {
            'fields': ('RR_TIPO_NOTIF','RR_NOT','RR_FECNOT','RR_HORNOT',)
        }),
    )

    @mark_safe
    def alerta_plazo(self, obj):
        color = obj.get_alerta_plazo()
        etiquetas = {
            'success':   ('verde',   'En plazo'),
            'warning':   ('amarillo','Por vencer'),
            'danger':    ('rojo',    'Vencido'),
            'secondary': ('gris',    'Sin fecha'),
        }
        colores_css = {
            'success':   '#28a745',
            'warning':   '#e67e00',
            'danger':    '#dc3545',
            'secondary': '#6c757d',
        }
        _, label = etiquetas.get(color, ('gris', '-'))
        css = colores_css.get(color, '#6c757d')
        fecha = obj.RR_FECLIMITE.strftime('%d/%m/%Y') if obj.RR_FECLIMITE else '-'
        return (
            f'<span style="color:{css};font-weight:700;">'
            f'{label}</span><br><small style="color:#555;">{fecha}</small>'
        )
    alerta_plazo.short_description = 'Limite 15 dias'

@admin.register(AUTOTPE)
class AUTOTPEAdmin(admin.ModelAdmin):
    list_display  = ('TPE_NUM', 'ID_SIM', 'ID_ABOG', 'TPE_TIPO', 'TPE_FEC', 'TPE_TIPO_NOTIF', 'TPE_NOT', 'TPE_FECNOT','TPE_HORNOT')
    search_fields = ('TPE_NUM', 'ID_SIM__SIM_COD','ID_ABOG__AB_PATERNO')
    list_filter   = ('TPE_TIPO',)

    fieldsets = (
        ('AGENDA', {
            'fields': ('ID_SIM', 'ID_ABOG', 'ID_AGENDA',)
        }),
        ('DISPOSICIÓN DEL AUTO', {
            'fields': ('TPE_NUM', 'TPE_FEC', 'TPE_RESOL', 'TPE_TIPO',)
        }),
        ('NOTIFICACIÓN', {
            'fields': ('TPE_TIPO_NOTIF', 'TPE_NOT', 'TPE_FECNOT', 'TPE_HORNOT',)
        }),
        ('MEMORÁNDUM', {
            'fields': ('TPE_MEMO_NUM', 'TPE_MEMO_FEC', 'TPE_MEMO_ENTREGA',),
            'classes': ('collapse',),
        }),
    )


# ============================================================
#  SECCIÓN 3: TRIBUNAL SUPERIOR DE PERSONAL FF. AA. (TSP)
#  Agrupa RAP, RAEE y AUTOTSP
# ============================================================

@admin.register(RAP)
class RAPAdmin(admin.ModelAdmin):
    list_display  = ('RAP_NUM', 'ID_SIM', 'RAP_FECPRESEN','RAP_OFI', 'RAP_FECOFI', 'alerta_plazo_rap', 'RAP_FEC', 'RAP_TIPO_NOTIF', 'RAP_NOT', 'RAP_FECNOT','RAP_HORNOT')
    search_fields = ('RAP_NUM', 'ID_SIM__SIM_COD')

    @mark_safe
    def alerta_plazo_rap(self, obj):
        color = obj.get_alerta_plazo()
        etiquetas = {
            'success':   'En plazo',
            'warning':   'Por vencer',
            'danger':    'Vencido',
            'secondary': 'Sin fecha',
        }
        colores_css = {
            'success':   '#28a745',
            'warning':   '#e67e00',
            'danger':    '#dc3545',
            'secondary': '#6c757d',
        }
        label = etiquetas.get(color, '-')
        css = colores_css.get(color, '#6c757d')
        fecha = obj.RAP_FECLIMITE.strftime('%d/%m/%Y') if obj.RAP_FECLIMITE else '-'
        return (
            f'<span style="color:{css};font-weight:700;">'
            f'{label}</span><br><small style="color:#555;">{fecha}</small>'
        )
    alerta_plazo_rap.short_description = 'Limite 3 dias'
# ESTO ORDENA LOS CAMPOS EN EL FORMULARIO PARA LA VISUALIZACION DEL RAP DENTRO DEL TSP

    fieldsets = (
        ('REGISTRO DEL RECURSO DE APELACION', {
            'fields': ('RAP_FECPRESEN', 'RAP_FECLIMITE','ID_SIM','ID_RR',)
        }),
        ('REGISTRO DE ENVIO DE DOCUMENTOS AL TSP. FF. AA.', {
            'fields': ('RAP_OFI', 'RAP_FECOFI',)
        }),
        ('PARTE RESOLUTIVA', {
            'fields': ('RAP_NUM','RAP_FEC','RAP_RESOL','RAP_TIPO',)
        }),
        ('NOTIFICACION', {
            'fields': ('RAP_TIPO_NOTIF','RAP_NOT','RAP_FECNOT','RAP_HORNOT',)
        }),
    )

@admin.register(RAEE)
class RAEEAdmin(admin.ModelAdmin):
    list_display  = ('RAE_NUM', 'ID_SIM', 'RAE_FEC', 'RAE_TIPO_NOTIF', 'RAE_NOT', 'RAE_FECNOT','RAE_HORNOT')
    search_fields = ('RAE_NUM', 'ID_SIM__SIM_COD')


@admin.register(AUTOTSP)
class AUTOTSPAdmin(admin.ModelAdmin):
    list_display  = ('TSP_NUM', 'ID_SIM', 'TSP_TIPO', 'TSP_FEC', 'TSP_TIPO_NOTIF', 'TSP_NOT', 'TSP_FECNOT','TSP_HORNOT')
    search_fields = ('TSP_NUM', 'ID_SIM__SIM_COD')
    list_filter   = ('TSP_TIPO',)

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Documentos Adjuntos
# ════════════════════════════════════════════════════════════════════════════
# @admin.register(DocumentoAdjunto)
# class DocumentoAdjuntoAdmin(admin.ModelAdmin):
    # list_display  = ('DOC_NOMBRE', 'DOC_TABLA', 'DOC_TIPO', 'DOC_FECREG')
    # search_fields = ('DOC_NOMBRE', 'DOC_TABLA')
    # list_filter   = ('DOC_TABLA', 'DOC_TIPO')
# ════════════════════════════════════════════════════════════════════════════
#  FIN DE ARCHIVO
# ════════════════════════════════════════════════════════════════════════════