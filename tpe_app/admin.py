# ============================================================
#  ADMIN DJANGO — SISTEMA DE SUMARIOS INFORMATIVOS MILITARES
#  Versión 1.0
# ============================================================

from django.contrib import admin
from django.utils.html import format_html
from .models import PM, ABOG, SIM, PM_SIM, AUTOTPE, AUTOTSP, RES, RR, RAP, RAEE, DocumentoAdjunto


# ============================================================
# ADMIN: PM — Personal Militar
# ============================================================
@admin.register(PM)
class PMAdmin(admin.ModelAdmin):
    list_display    = ('PM_CI', 'PM_PATERNO', 'PM_NOMBRE', 'PM_GRADO', 'PM_ARMA', 'PM_ESTADO')
    list_filter     = ('PM_ESCALAFON', 'PM_ARMA', 'PM_ESTADO')
    search_fields   = ('PM_CI', 'PM_PATERNO', 'PM_NOMBRE')
    ordering        = ('PM_PATERNO', 'PM_NOMBRE')
    
    class Media:
        js = ('js/filtro_grado.js',)

    fieldsets = (
        ('Datos Personales', {
            'fields': ('PM_CI', 'PM_NOMBRE', 'PM_PATERNO', 'PM_MATERNO')
        }),
        ('Datos Militares', {
            'fields': ('PM_ESCALAFON', 'PM_GRADO', 'PM_ARMA', 'PM_ESPEC', 'PM_ESTADO', 'PM_PROMOCION')
        }),
    )


# ============================================================
# ADMIN: ABOG — Abogados del Tribunal
# ============================================================
@admin.register(ABOG)
class ABOGAdmin(admin.ModelAdmin):
    list_display  = ('AB_CI', 'AB_PATERNO', 'AB_NOMBRE', 'AB_GRADO', 'AB_ARMA')
    search_fields = ('AB_CI', 'AB_PATERNO', 'AB_NOMBRE')
    ordering      = ('AB_PATERNO', 'AB_NOMBRE')


# ============================================================
# INLINE: PM_SIM dentro de SIM
# ============================================================
class PM_SIMInline(admin.TabularInline):
    model      = PM_SIM
    extra      = 1
    verbose_name = 'Militar involucrado'
    verbose_name_plural = 'Militares involucrados'


# ============================================================
# INLINE: RES dentro de SIM
# ============================================================
class RESInline(admin.StackedInline):
    model   = RES
    extra   = 0
    show_change_link = True
    fields  = ('RES_NUM', 'RES_FEC', 'RES_TIPO', 'RES_RESUM', 'RES_FECNOT')


# ============================================================
# INLINE: AUTOTPE dentro de SIM
# ============================================================
class AUTOTPEInline(admin.StackedInline):
    model   = AUTOTPE
    extra   = 0
    show_change_link = True
    fields  = ('TPE_NUM', 'TPE_FEC', 'TPE_TIPO', 'TPE_FECNOT')


# ============================================================
# ADMIN: SIM — Sumario Informativo Militar (tabla central)
# ============================================================
@admin.register(SIM)
class SIMAdmin(admin.ModelAdmin):
    list_display  = ('SIM_COD', 'SIM_RESUM', 'SIM_TIPO', 'estado_badge', 'SIM_FECING', 'ID_ABOG')
    list_filter   = ('SIM_TIPO', 'SIM_ESTADO')
    search_fields = ('SIM_COD', 'SIM_RESUM', 'SIM_OBJETO')
    ordering      = ('-SIM_FECREG',)
    readonly_fields = ('SIM_FECREG',)
    inlines       = [PM_SIMInline, RESInline, AUTOTPEInline]

    fieldsets = (
        ('Identificación', {
            'fields': ('SIM_COD', 'SIM_TIPO', 'SIM_ESTADO', 'SIM_FECING', 'ID_ABOG')
        }),
        ('Contenido', {
            'fields': ('SIM_OBJETO', 'SIM_RESUM', 'SIM_AUTOFINAL')
        }),
        ('Sistema', {
            'fields': ('SIM_FECREG',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colores = {
            'RADICADO_TPE':    ('blue',   '🔵'),
            'PARA_AGENDA':     ('orange', '🟡'),
            'EN_APELACION_TSP':('red',    '🔴'),
        }
        color, icono = colores.get(obj.SIM_ESTADO, ('gray', '⚪'))
        return format_html(
            '<span style="color:{}; font-weight:bold">{} {}</span>',
            color, icono, obj.get_SIM_ESTADO_display()
        )


# ============================================================
# ADMIN: RES — Primera Resolución
# ============================================================
class RRInline(admin.StackedInline):
    model   = RR
    extra   = 0
    show_change_link = True
    fields  = ('RR_FECPRESEN', 'RR_FECLIMITE', 'RR_NUM', 'RR_FEC', 'RR_RESUM', 'alerta_plazo')
    readonly_fields = ('alerta_plazo',)

    @admin.display(description='Alerta plazo')
    def alerta_plazo(self, obj):
        color_map = {'success': 'green', 'warning': 'orange', 'danger': 'red', 'secondary': 'gray'}
        color = color_map.get(obj.get_alerta_plazo(), 'gray')
        texto = {
            'success':   '🟢 En plazo',
            'warning':   '🟡 Por vencer',
            'danger':    '🔴 Vencido',
            'secondary': '⚪ Sin fecha',
        }.get(obj.get_alerta_plazo(), '⚪')
        return format_html('<span style="color:{};font-weight:bold">{}</span>', color, texto)


@admin.register(RES)
class RESAdmin(admin.ModelAdmin):
    list_display  = ('RES_NUM', 'RES_FEC', 'RES_TIPO', 'RES_RESUM', 'ID_SIM')
    list_filter   = ('RES_TIPO',)
    search_fields = ('RES_NUM', 'ID_SIM__SIM_COD')
    ordering      = ('-RES_FEC',)
    inlines       = [RRInline]

    fieldsets = (
        ('Resolución', {
            'fields': ('ID_SIM', 'RES_NUM', 'RES_FEC', 'RES_TIPO', 'RES_RESOL', 'RES_RESUM')
        }),
        ('Agenda', {
            'fields': ('RES_AGENDA', 'RES_FECAGEN')
        }),
        ('Notificación por Firma', {
            'fields': ('RES_NOT', 'RES_FECNOT', 'RES_HORNOT')
        }),
        ('Notificación por Edicto', {
            'fields': ('RES_EDICTO_PERIOD', 'RES_EDICTO_FEC'),
            'classes': ('collapse',)
        }),
    )


# ============================================================
# ADMIN: RR — Segunda Resolución
# ============================================================
class RAPInline(admin.StackedInline):
    model   = RAP
    extra   = 0
    show_change_link = True
    fields  = ('RAP_OFI', 'RAP_FECOFI', 'RAP_FECLIMITE', 'RAP_NUM', 'RAP_FEC')


@admin.register(RR)
class RRAdmin(admin.ModelAdmin):
    list_display  = ('RR_NUM', 'RR_FEC', 'RR_FECLIMITE', 'alerta_plazo', 'RR_RESUM', 'ID_SIM')
    search_fields = ('RR_NUM', 'ID_SIM__SIM_COD')
    ordering      = ('-RR_FEC',)
    inlines       = [RAPInline]

    fieldsets = (
        ('Recurso', {
            'fields': ('ID_SIM', 'ID_RES', 'RR_FECPRESEN', 'RR_FECLIMITE')
        }),
        ('Resolución', {
            'fields': ('RR_NUM', 'RR_FEC', 'RR_RESOL', 'RR_RESUM')
        }),
        ('Agenda', {
            'fields': ('RR_AGENDA', 'RR_FECAGEN')
        }),
        ('Notificación', {
            'fields': ('RR_NOT', 'RR_FECNOT', 'RR_HORNOT')
        }),
    )

    @admin.display(description='Alerta')
    def alerta_plazo(self, obj):
        texto = {
            'success':   '🟢 En plazo',
            'warning':   '🟡 Por vencer',
            'danger':    '🔴 Vencido',
            'secondary': '⚪ Sin fecha',
        }.get(obj.get_alerta_plazo(), '⚪')
        return format_html('<b>{}</b>', texto)


# ============================================================
# ADMIN: RAP — Recurso de Apelación
# ============================================================
@admin.register(RAP)
class RAPAdmin(admin.ModelAdmin):
    list_display  = ('RAP_NUM', 'RAP_FEC', 'RAP_FECLIMITE', 'alerta_plazo', 'ID_SIM')
    search_fields = ('RAP_NUM', 'ID_SIM__SIM_COD')
    ordering      = ('-RAP_FEC',)

    fieldsets = (
        ('Elevación al TSP', {
            'fields': ('ID_SIM', 'ID_RR', 'RAP_OFI', 'RAP_FECOFI', 'RAP_FECLIMITE')
        }),
        ('Resolución TSP', {
            'fields': ('RAP_NUM', 'RAP_FEC', 'RAP_RESOL', 'RAP_RESUM')
        }),
        ('Notificación', {
            'fields': ('RAP_NOT', 'RAP_FECNOT', 'RAP_HORNOT')
        }),
    )

    @admin.display(description='Alerta')
    def alerta_plazo(self, obj):
        texto = {
            'success':   '🟢 En plazo',
            'warning':   '🟡 Por vencer',
            'danger':    '🔴 Vencido',
            'secondary': '⚪ Sin fecha',
        }.get(obj.get_alerta_plazo(), '⚪')
        return format_html('<b>{}</b>', texto)


# ============================================================
# ADMIN: RAEE
# ============================================================
@admin.register(RAEE)
class RAEEAdmin(admin.ModelAdmin):
    list_display  = ('RAE_NUM', 'RAE_FEC', 'RAE_RESUM', 'ID_SIM')
    search_fields = ('RAE_NUM', 'ID_SIM__SIM_COD')
    ordering      = ('-RAE_FEC',)

    fieldsets = (
        ('Datos', {
            'fields': ('ID_SIM', 'ID_RAP', 'RAE_OFI', 'RAE_FECOFI')
        }),
        ('Resolución', {
            'fields': ('RAE_NUM', 'RAE_FEC', 'RAE_RESOL', 'RAE_RESUM')
        }),
        ('Agenda', {
            'fields': ('RAE_AGENDA', 'RAE_FECAGEN')
        }),
        ('Notificación', {
            'fields': ('RAE_NOT', 'RAE_FECNOT', 'RAE_HORNOT')
        }),
    )


# ============================================================
# ADMIN: AUTOTPE
# ============================================================
@admin.register(AUTOTPE)
class AUTOTPEAdmin(admin.ModelAdmin):
    list_display  = ('TPE_NUM', 'TPE_FEC', 'TPE_TIPO', 'ID_SIM')
    list_filter   = ('TPE_TIPO',)
    search_fields = ('TPE_NUM', 'ID_SIM__SIM_COD')
    ordering      = ('-TPE_FEC',)

    fieldsets = (
        ('Auto', {
            'fields': ('ID_SIM', 'TPE_NUM', 'TPE_FEC', 'TPE_TIPO', 'TPE_RESOL')
        }),
        ('Notificación por Firma', {
            'fields': ('TPE_NOT', 'TPE_FECNOT', 'TPE_HORNOT')
        }),
        ('Notificación por Edicto', {
            'fields': ('TPE_EDICTO_PERIOD', 'TPE_EDICTO_FEC'),
            'classes': ('collapse',)
        }),
        ('Auto de Ejecutoria', {
            'fields': ('TPE_EJECU_NOT', 'TPE_EJECU_FECNOT'),
            'classes': ('collapse',)
        }),
        ('Memorándum', {
            'fields': ('TPE_MEMO_NUM', 'TPE_MEMO_FEC', 'TPE_MEMO_ENTREGA'),
            'classes': ('collapse',)
        }),
    )


# ============================================================
# ADMIN: AUTOTSP
# ============================================================
@admin.register(AUTOTSP)
class AUTOTSPAdmin(admin.ModelAdmin):
    list_display  = ('TSP_NUM', 'TSP_FEC', 'TSP_TIPO', 'ID_SIM')
    list_filter   = ('TSP_TIPO',)
    search_fields = ('TSP_NUM', 'ID_SIM__SIM_COD')
    ordering      = ('-TSP_FEC',)

    fieldsets = (
        ('Auto', {
            'fields': ('ID_SIM', 'TSP_NUM', 'TSP_FEC', 'TSP_TIPO', 'TSP_RESOL')
        }),
        ('Notificación por Firma', {
            'fields': ('TSP_NOT', 'TSP_FECNOT', 'TSP_HORNOT')
        }),
        ('Notificación por Edicto', {
            'fields': ('TSP_EDICTO_PERIOD', 'TSP_EDICTO_FEC'),
            'classes': ('collapse',)
        }),
        ('Auto de Ejecutoria', {
            'fields': ('TSP_EJECU_NOT', 'TSP_EJECU_FECNOT'),
            'classes': ('collapse',)
        }),
    )


# ============================================================
# ADMIN: DocumentoAdjunto
# ============================================================
@admin.register(DocumentoAdjunto)
class DocumentoAdjuntoAdmin(admin.ModelAdmin):
    list_display  = ('DOC_NOMBRE', 'DOC_TABLA', 'DOC_ID_REG', 'DOC_TIPO', 'DOC_FECREG')
    list_filter   = ('DOC_TABLA', 'DOC_TIPO')
    search_fields = ('DOC_NOMBRE',)
    ordering      = ('-DOC_FECREG',)
    readonly_fields = ('DOC_FECREG',)
