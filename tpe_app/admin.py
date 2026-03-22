from django.contrib import admin
from .models import PM, ABOG, SIM, PM_SIM, AUTOTPE, RES, RR, RAP, RAEE, AUTOTSP

# ============================================================
#  Configuración general del panel admin
# ============================================================
admin.site.site_header = "Sistema TPE — Tribunal de Personal del Ejército"
admin.site.site_title  = "TPE Sistema"
admin.site.index_title = "Panel de Administración"


# ============================================================
#  SECCIÓN 1: SUMARIO INFORMATIVO MILITAR
#  Color azul — agrupa PM, ABOG y SIM
# ============================================================

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


@admin.register(ABOG)
class ABOGAdmin(admin.ModelAdmin):
    list_display  = ('AB_CI', 'AB_GRADO', 'AB_NOMBRE', 'AB_PATERNO', 'AB_ARMA')
    search_fields = ('AB_CI', 'AB_NOMBRE', 'AB_PATERNO')


# ── Inline: militares dentro del formulario SIM ──────────────
class PM_SIM_Inline(admin.TabularInline):
    model               = PM_SIM
    extra               = 1
    verbose_name        = "Militar investigado"
    verbose_name_plural = "Militares investigados"


@admin.register(SIM)
class SIMAdmin(admin.ModelAdmin):
    list_display  = ('SIM_COD', 'SIM_TIPO', 'ID_ABOG', 'SIM_RESUM', 'SIM_FECREG')
    search_fields = ('SIM_COD', 'SIM_RESUM')
    list_filter   = ('SIM_TIPO',)
    inlines       = [PM_SIM_Inline]


# ============================================================
#  SECCIÓN 2: TRIBUNAL DE PERSONAL DEL EJÉRCITO (TPE)
#  Agrupa RES, RR y AUTOTPE
# ============================================================

@admin.register(RES)
class RESAdmin(admin.ModelAdmin):
    list_display  = ('RES_NUM', 'ID_SIM', 'RES_TIPO', 'RES_FEC', 'RES_NOT', 'RES_FECNOT')
    search_fields = ('RES_NUM', 'ID_SIM__SIM_COD')
    list_filter   = ('RES_TIPO',)


@admin.register(RR)
class RRAdmin(admin.ModelAdmin):
    list_display  = ('RR_NUM', 'ID_SIM', 'ID_RES', 'RR_FEC', 'RR_FECPRESEN', 'RR_NOT')
    search_fields = ('RR_NUM', 'ID_SIM__SIM_COD')


@admin.register(AUTOTPE)
class AUTOTPEAdmin(admin.ModelAdmin):
    list_display  = ('TPE_NUM', 'ID_SIM', 'TPE_TIPO', 'TPE_FEC', 'TPE_NOT', 'TPE_FECNOT')
    search_fields = ('TPE_NUM', 'ID_SIM__SIM_COD')
    list_filter   = ('TPE_TIPO',)


# ============================================================
#  SECCIÓN 3: TRIBUNAL SUPERIOR DE PERSONAL FF. AA. (TSP)
#  Agrupa RAP, RAEE y AUTOTSP
# ============================================================

@admin.register(RAP)
class RAPAdmin(admin.ModelAdmin):
    list_display  = ('RAP_NUM', 'ID_SIM', 'RAP_OFI', 'RAP_FECOFI', 'RAP_FEC', 'RAP_NOT')
    search_fields = ('RAP_NUM', 'ID_SIM__SIM_COD')


@admin.register(RAEE)
class RAEEAdmin(admin.ModelAdmin):
    list_display  = ('RAE_NUM', 'ID_SIM', 'RAE_OFI', 'RAE_FECOFI', 'RAE_FEC', 'RAE_NOT')
    search_fields = ('RAE_NUM', 'ID_SIM__SIM_COD')


@admin.register(AUTOTSP)
class AUTOTSPAdmin(admin.ModelAdmin):
    list_display  = ('TSP_NUM', 'ID_SIM', 'TSP_TIPO', 'TSP_FEC', 'TSP_NOT', 'TSP_FECNOT')
    search_fields = ('TSP_NUM', 'ID_SIM__SIM_COD')
    list_filter   = ('TSP_TIPO',)



