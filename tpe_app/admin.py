from django.contrib import admin
from django import forms
from .models import PM, ABOG, SIM, PM_SIM, AUTOTPE, RES, RR, RAP, RAEE, AUTOTSP
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
            'fields': ('ID_SIM','ID_ABOG', 'RES_AGENDA','RES_FEC', 'RES_NUM',)
        }),
        ('DISPOSICIÒN RESOLUTIVA', {
            'fields': ('RES_RESOL','RES_TIPO','RES_RESUM',)
        }),
        ('NOTIFICACIÓN', {
            'fields': ('RES_TIPO_NOTIF','RES_NOT','RES_FECNOT','RES_HORNOT',)
        }),
    )

@admin.register(RR)
class RRAdmin(admin.ModelAdmin):
    list_display  = ('RR_NUM', 'ID_SIM', 'ID_RES', 'ID_ABOG', 'RR_FEC', 'RR_FECPRESEN', 'RR_TIPO_NOTIF', 'RR_NOT', 'RR_FECNOT','RR_HORNOT')
    search_fields = ('RR_NUM', 'ID_SIM__SIM_COD','ID_ABOG__AB_PATERNO')


@admin.register(AUTOTPE)
class AUTOTPEAdmin(admin.ModelAdmin):
    list_display  = ('TPE_NUM', 'ID_SIM', 'ID_ABOG', 'TPE_TIPO', 'TPE_FEC', 'TPE_TIPO_NOTIF', 'TPE_NOT', 'TPE_FECNOT','TPE_HORNOT')
    search_fields = ('TPE_NUM', 'ID_SIM__SIM_COD','ID_ABOG__AB_PATERNO')
    list_filter   = ('TPE_TIPO',)


# ============================================================
#  SECCIÓN 3: TRIBUNAL SUPERIOR DE PERSONAL FF. AA. (TSP)
#  Agrupa RAP, RAEE y AUTOTSP
# ============================================================

@admin.register(RAP)
class RAPAdmin(admin.ModelAdmin):
    list_display  = ('RAP_NUM', 'ID_SIM', 'RAP_OFI', 'RAP_FECOFI', 'RAP_FEC', 'RAP_TIPO_NOTIF', 'RAP_NOT', 'RAP_FECNOT','RAP_HORNOT')
    search_fields = ('RAP_NUM', 'ID_SIM__SIM_COD')


@admin.register(RAEE)
class RAEEAdmin(admin.ModelAdmin):
    list_display  = ('RAE_NUM', 'ID_SIM', 'RAE_OFI', 'RAE_FECOFI', 'RAE_FEC', 'RAE_TIPO_NOTIF', 'RAE_NOT', 'RAE_FECNOT','RAE_HORNOT')
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

