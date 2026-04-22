from django.contrib import admin
from django import forms
from django.utils.html import mark_safe
from .models import DICTAMEN, PM, ABOG, SIM, PM_SIM, AGENDA, AUTOTPE, AUTOTSP, DocumentoAdjunto, PerfilUsuario, VOCAL_TPE, Resolucion, RecursoTSP
from .widgets import ResumenConOpcionesWidget


# ============================================================
#  Configuración general del panel admin
# ============================================================
# Usando estilo Django estándar (sin personalizaciones)


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
        ('MALVERSACION Y COBROS INDEBIDOS REITERADOS','MALVERSACION Y COBROS INDEBIDOS REITERADOS'),
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
#  ADMIN: Vocales del Tribunal
# ════════════════════════════════════════════════════════════════════════════
@admin.register(VOCAL_TPE)
class VocalTPEAdmin(admin.ModelAdmin):
    list_display  = ('pm', 'cargo', 'activo')
    list_filter   = ('cargo', 'activo')
    search_fields = ('pm__PM_NOMBRE', 'pm__PM_PATERNO')


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
    list_display  = ('AG_NUM', 'AG_FECPROG', 'AG_FECREAL', 'AG_TIPO')
    search_fields = ('AG_NUM',)
    list_filter   = ('AG_TIPO',)

    fieldsets = (
        ('Datos de la Reunión', {
            'fields': ('AG_NUM', 'AG_FECPROG', 'AG_FECREAL', 'AG_TIPO',)
        }),
    )

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: DICTAMEN
#  Se registra ANTES que la RES Y/o el AUTOTPE
# ════════════════════════════════════════════════════════════════════════════
@admin.register(DICTAMEN)
class DICTAMENAdmin(admin.ModelAdmin):

    list_display  = ('DIC_NUM', 'sim', 'agenda', 'abog', 'DIC_CONCL')
    search_fields = ('DIC_NUM', 'sim__SIM_COD', 'agenda__AG_NUM')
    list_filter   = ('abog',)

    fieldsets = (
        ('Datos del Dictamen', {
            'fields': ('agenda', 'sim', 'abog', 'DIC_NUM', 'DIC_CONCL')
        }),
    )


# ============================================================
#  SECCIÓN 2: TRIBUNAL DE PERSONAL DEL EJÉRCITO (TPE)
#  Agrupa RES, RR y AUTOTPE
# ============================================================

@admin.register(Resolucion)
class ResolucionAdmin(admin.ModelAdmin):
    list_display  = ('RES_NUM', 'RES_INSTANCIA', 'sim', 'abog', 'RES_TIPO', 'RES_RESUM', 'RES_FEC',
                     'alerta_plazo', 'RES_TIPO_NOTIF', 'RES_NOT', 'RES_FECNOT', 'RES_HORNOT')
    search_fields = ('RES_NUM', 'sim__SIM_COD', 'abog__AB_PATERNO')
    list_filter   = ('RES_INSTANCIA', 'RES_TIPO', 'RES_RESUM')

    fieldsets = (
        ('INSTANCIA', {
            'fields': ('RES_INSTANCIA',)
        }),
        ('RELACIONES', {
            'fields': ('sim', 'pm', 'abog', 'agenda', 'dictamen', 'resolucion_origen',)
        }),
        ('DISPOSICIÓN RESOLUTIVA', {
            'fields': ('RES_NUM', 'RES_FEC', 'RES_RESOL', 'RES_TIPO', 'RES_RESUM',)
        }),
        ('PLAZOS (RECONSIDERACION)', {
            'fields': ('RES_FECPRESEN', 'RES_FECLIMITE',)
        }),
        ('NOTIFICACIÓN', {
            'fields': ('RES_TIPO_NOTIF', 'RES_NOT', 'RES_FECNOT', 'RES_HORNOT',)
        }),
    )

    @mark_safe
    def alerta_plazo(self, obj):
        color = obj.get_alerta_plazo()
        etiquetas = {
            'success':   'En plazo',
            'warning':   'Por vencer',
            'danger':    'Vencido',
            'secondary': '-',
        }
        colores_css = {
            'success':   '#28a745',
            'warning':   '#e67e00',
            'danger':    '#dc3545',
            'secondary': '#6c757d',
        }
        label = etiquetas.get(color, '-')
        css = colores_css.get(color, '#6c757d')
        fecha = obj.RES_FECLIMITE.strftime('%d/%m/%Y') if obj.RES_FECLIMITE else '-'
        return (
            f'<span style="color:{css};font-weight:700;">'
            f'{label}</span><br><small style="color:#555;">{fecha}</small>'
        )
    alerta_plazo.short_description = 'Plazo RR'

@admin.register(AUTOTPE)
class AUTOTPEAdmin(admin.ModelAdmin):
    list_display  = ('TPE_NUM', 'sim', 'abog', 'TPE_TIPO', 'TPE_FEC', 'TPE_TIPO_NOTIF', 'TPE_NOT', 'TPE_FECNOT','TPE_HORNOT')
    search_fields = ('TPE_NUM', 'sim__SIM_COD','abog__AB_PATERNO')
    list_filter   = ('TPE_TIPO',)

    fieldsets = (
        ('AGENDA', {
            'fields': ('sim', 'abog', 'agenda',)
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

@admin.register(RecursoTSP)
class RecursoTSPAdmin(admin.ModelAdmin):
    list_display  = ('TSP_NUM', 'TSP_INSTANCIA', 'sim', 'TSP_FECPRESEN', 'TSP_OFI',
                     'TSP_FECOFI', 'alerta_plazo', 'TSP_FEC',
                     'TSP_TIPO_NOTIF', 'TSP_NOT', 'TSP_FECNOT', 'TSP_HORNOT')
    search_fields = ('TSP_NUM', 'sim__SIM_COD')
    list_filter   = ('TSP_INSTANCIA', 'TSP_TIPO')

    @mark_safe
    def alerta_plazo(self, obj):
        if obj.TSP_INSTANCIA != 'APELACION':
            return '<span style="color:#6c757d;">—</span>'
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
        fecha = obj.TSP_FECLIMITE.strftime('%d/%m/%Y') if obj.TSP_FECLIMITE else '-'
        return (
            f'<span style="color:{css};font-weight:700;">'
            f'{label}</span><br><small style="color:#555;">{fecha}</small>'
        )
    alerta_plazo.short_description = 'Límite 3 días'

    fieldsets = (
        ('INSTANCIA', {
            'fields': ('TSP_INSTANCIA',),
        }),
        ('REGISTRO DEL RECURSO', {
            'fields': ('sim', 'pm', 'resolucion', 'recurso_origen',
                       'TSP_FECPRESEN', 'TSP_FECLIMITE',)
        }),
        ('REGISTRO DE ENVÍO AL TSP', {
            'fields': ('TSP_OFI', 'TSP_FECOFI',)
        }),
        ('PARTE RESOLUTIVA', {
            'fields': ('TSP_NUM', 'TSP_FEC', 'TSP_RESOL', 'TSP_TIPO', 'TSP_RESUM',)
        }),
        ('NOTIFICACIÓN', {
            'fields': ('TSP_TIPO_NOTIF', 'TSP_NOT', 'TSP_FECNOT', 'TSP_HORNOT',)
        }),
    )


@admin.register(AUTOTSP)
class AUTOTSPAdmin(admin.ModelAdmin):
    list_display  = ('TSP_NUM', 'sim', 'TSP_TIPO', 'TSP_FEC', 'TSP_TIPO_NOTIF', 'TSP_NOT', 'TSP_FECNOT','TSP_HORNOT')
    search_fields = ('TSP_NUM', 'sim__SIM_COD')
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

# Agregar al FINAL de admin.py

from .models import PerfilUsuario
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Gestión de Usuarios y Roles
# ════════════════════════════════════════════════════════════════════════════

# Anular el UserAdmin por defecto para agregar PerfilUsuario inline
class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    verbose_name = "Asignación de Rol"
    verbose_name_plural = "Asignación de Rol"
    fields = ('rol', 'abogado', 'activo')
    extra = 0
    can_delete = True


# Registrar un UserAdmin mejorado
admin.site.unregister(User)

@admin.register(User)
class UsuarioTPEAdmin(UserAdmin):
    inlines = (PerfilUsuarioInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol_display', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff', 'date_joined')

    def rol_display(self, obj):
        """Muestra el rol del usuario si existe"""
        try:
            perfil = PerfilUsuario.objects.get(user=obj)
            return f"{perfil.get_rol_display()}" + (" ✓" if perfil.activo else " ✗")
        except PerfilUsuario.DoesNotExist:
            return "Sin asignar"
    rol_display.short_description = "Rol/Estado"


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display  = ('usuario_completo', 'rol_badge', 'abogado_asignado', 'activo', 'acciones')
    list_filter   = ('rol', 'activo', 'user__date_joined')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'abogado__AB_PATERNO')
    readonly_fields = ('user_info',)

    fieldsets = (
        ('Información de usuario', {
            'fields': ('user', 'user_info', 'rol', 'activo')
        }),
        ('Vinculación (solo para rol ABOGADO)', {
            'fields': ('abogado',),
            'description': '⚠️ Complete este campo SOLO si asignó el rol "Abogado" arriba'
        }),
    )

    def usuario_completo(self, obj):
        """Muestra username y email del usuario"""
        return f"{obj.user.username} ({obj.user.email})"
    usuario_completo.short_description = "Usuario"

    def rol_badge(self, obj):
        """Muestra el rol con color"""
        colores = {
            'ADMINISTRADOR': '#dc3545',  # Rojo
            'ABOGADO': '#0066cc',         # Azul
            'ADMINISTRATIVO': '#28a745',  # Verde
            'BUSCADOR': '#ffc107',        # Amarillo
        }
        color = colores.get(obj.rol, '#6c757d')
        return f'<span style="background-color:{color};color:white;padding:3px 8px;border-radius:3px;font-weight:bold;">{obj.get_rol_display()}</span>'
    rol_badge.allow_tags = True
    rol_badge.short_description = "Rol"

    def abogado_asignado(self, obj):
        """Muestra si hay abogado asignado"""
        if obj.abogado:
            return f"✓ {obj.abogado.AB_PATERNO} {obj.abogado.AB_MATERNO}"
        return "—"
    abogado_asignado.short_description = "Abogado Vinculado"

    def acciones(self, obj):
        """Muestra estado visual"""
        if obj.activo:
            return '<span style="color:green;font-weight:bold;">✓ Activo</span>'
        return '<span style="color:red;font-weight:bold;">✗ Inactivo</span>'
    acciones.allow_tags = True
    acciones.short_description = "Estado"

    def user_info(self, obj):
        """Información de referencia del usuario"""
        return f"""
            <strong>Username:</strong> {obj.user.username}<br>
            <strong>Email:</strong> {obj.user.email}<br>
            <strong>Nombre:</strong> {obj.user.first_name} {obj.user.last_name}<br>
            <strong>Miembro desde:</strong> {obj.user.date_joined.strftime('%d/%m/%Y')}
        """
    user_info.allow_tags = True
    user_info.short_description = "Información del Usuario"

    def save_model(self, request, obj, form, change):
        """Validar que abogados tengan un abogado asignado"""
        if obj.rol == 'ABOGADO' and not obj.abogado:
            raise ValueError('⚠️ Los usuarios con rol ABOGADO deben tener un abogado vinculado')
        super().save_model(request, obj, form, change)
