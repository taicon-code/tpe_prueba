from django.contrib import admin
from django import forms
from django.utils.html import mark_safe
from .models import DICTAMEN, PM, SIM, PM_SIM, AGENDA, AUTOTPE, AUTOTSP, DocumentoAdjunto, PerfilUsuario, VOCAL_TPE, Resolucion, RecursoTSP, Notificacion, Memorandum
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
            'resumen': ResumenConOpcionesWidget(opciones=RESUMEN_CHOICES),
        }


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Personal Militar
# ════════════════════════════════════════════════════════════════════════════
@admin.register(PM)
class PMAdmin(admin.ModelAdmin):
    list_display  = ('ci', 'escalafon', 'grado', 'nombre', 'paterno', 'arma', 'estado')
    search_fields = ('ci', 'nombre', 'paterno')
    list_filter   = ('estado', 'escalafon', 'arma')

    class Meta:
        verbose_name        = "Personal Militar"
        verbose_name_plural = "Personal Militar"

    class Media:
        js = ('tpe_app/js/grado_filter.js',)

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Vocales del Tribunal
# ════════════════════════════════════════════════════════════════════════════
@admin.register(VOCAL_TPE)
class VocalTPEAdmin(admin.ModelAdmin):
    list_display  = ('pm', 'cargo', 'cargo_em', 'activo')
    list_filter   = ('cargo', 'activo')
    search_fields = ('pm__nombre', 'pm__paterno', 'cargo_em')
    fields        = ('pm', 'cargo', 'cargo_em', 'activo')


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
    list_display  = ('codigo', 'tipo', 'resumen', 'fecha_registro')
    search_fields = ('codigo', 'resumen')
    list_filter   = ('tipo',)
    inlines       = [PM_SIM_Inline]
# ESTO ORDENA LOS CAMPOS EN EL FORMULARIO PARA LA VISUALIZACIÓN DENTRO DEL SUMARIO INFORMATIVO MILITAR
    fieldsets = (
        ('Datos principales', {
            'fields': ('codigo','fecha_ingreso', 'objeto','resumen', 'auto_final','tipo')
        }),
        ('Situación Actual', {
            'fields': ('estado',)
        }),
    )

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Agenda — Reunión del Tribunal
#  Se registra ANTES que la RES o el AUTOTPE
# ════════════════════════════════════════════════════════════════════════════
@admin.register(AGENDA)
class AGENDAAdmin(admin.ModelAdmin):
    list_display  = ('numero', 'fecha_prog', 'fecha_real', 'tipo')
    search_fields = ('numero',)
    list_filter   = ('tipo',)

    fieldsets = (
        ('Datos de la Reunión', {
            'fields': ('numero', 'fecha_prog', 'fecha_real', 'tipo',)
        }),
    )

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: DICTAMEN
#  Se registra ANTES que la RES Y/o el AUTOTPE
# ════════════════════════════════════════════════════════════════════════════
@admin.register(DICTAMEN)
class DICTAMENAdmin(admin.ModelAdmin):

    list_display  = ('numero', 'sim', 'agenda', 'abogado', 'conclusion')
    search_fields = ('numero', 'sim__codigo', 'agenda__numero')
    list_filter   = ('abogado',)

    fieldsets = (
        ('Datos del Dictamen', {
            'fields': ('agenda', 'sim', 'abogado', 'numero', 'conclusion')
        }),
    )


# ============================================================
#  SECCIÓN 2: TRIBUNAL DE PERSONAL DEL EJÉRCITO (TPE)
#  Agrupa RES, RR y AUTOTPE
# ============================================================

class NotificacionInline(admin.StackedInline):
    model = Notificacion
    extra = 0
    max_num = 1
    verbose_name = "Notificación"
    fields = ('tipo', 'notificado_a', 'fecha', 'hora')


class MemorandumInline(admin.StackedInline):
    model = Memorandum
    extra = 0
    max_num = 1
    verbose_name = "Memorándum"
    fields = ('numero', 'fecha', 'fecha_entrega')


@admin.register(Resolucion)
class ResolucionAdmin(admin.ModelAdmin):
    list_display  = ('numero', 'instancia', 'sim', 'abogado', 'tipo', 'resumen', 'fecha', 'alerta_plazo')
    search_fields = ('numero', 'sim__codigo', 'abogado__paterno')
    list_filter   = ('instancia', 'tipo', 'resumen')
    inlines       = [NotificacionInline]

    fieldsets = (
        ('INSTANCIA', {
            'fields': ('instancia',)
        }),
        ('RELACIONES', {
            'fields': ('sim', 'pm', 'abogado', 'agenda', 'dictamen', 'resolucion_origen',)
        }),
        ('DISPOSICIÓN RESOLUTIVA', {
            'fields': ('numero', 'fecha', 'texto', 'tipo', 'resumen',)
        }),
        ('PLAZOS (RECONSIDERACION)', {
            'fields': ('fecha_presentacion', 'fecha_limite',)
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
        fecha = obj.fecha_limite.strftime('%d/%m/%Y') if obj.fecha_limite else '-'
        return (
            f'<span style="color:{css};font-weight:700;">'
            f'{label}</span><br><small style="color:#555;">{fecha}</small>'
        )
    alerta_plazo.short_description = 'Plazo RR'

class NotificacionAUTOTPEInline(admin.StackedInline):
    model = Notificacion
    extra = 0
    max_num = 1
    verbose_name = "Notificación"
    fields = ('tipo', 'notificado_a', 'fecha', 'hora')
    fk_name = 'autotpe'


@admin.register(AUTOTPE)
class AUTOTPEAdmin(admin.ModelAdmin):
    list_display  = ('numero', 'sim', 'abogado', 'tipo', 'fecha')
    search_fields = ('numero', 'sim__codigo', 'abogado__paterno')
    list_filter   = ('tipo',)
    inlines       = [NotificacionAUTOTPEInline, MemorandumInline]

    fieldsets = (
        ('AGENDA', {
            'fields': ('sim', 'abogado', 'agenda',)
        }),
        ('DISPOSICIÓN DEL AUTO', {
            'fields': ('numero', 'fecha', 'texto', 'tipo',)
        }),
    )


# ============================================================
#  SECCIÓN 3: TRIBUNAL SUPERIOR DE PERSONAL FF. AA. (TSP)
#  Agrupa RAP, RAEE y AUTOTSP
# ============================================================

class NotificacionRecursoTSPInline(admin.StackedInline):
    model = Notificacion
    extra = 0
    max_num = 1
    verbose_name = "Notificación"
    fields = ('tipo', 'notificado_a', 'fecha', 'hora')
    fk_name = 'recurso_tsp'


@admin.register(RecursoTSP)
class RecursoTSPAdmin(admin.ModelAdmin):
    list_display  = ('numero', 'instancia', 'sim', 'fecha_presentacion', 'numero_oficio',
                     'fecha_oficio', 'alerta_plazo', 'fecha')
    search_fields = ('numero', 'sim__codigo')
    list_filter   = ('instancia', 'tipo')
    inlines       = [NotificacionRecursoTSPInline]

    @mark_safe
    def alerta_plazo(self, obj):
        if obj.instancia != 'APELACION':
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
        fecha = obj.fecha_limite.strftime('%d/%m/%Y') if obj.fecha_limite else '-'
        return (
            f'<span style="color:{css};font-weight:700;">'
            f'{label}</span><br><small style="color:#555;">{fecha}</small>'
        )
    alerta_plazo.short_description = 'Límite 3 días'

    fieldsets = (
        ('INSTANCIA', {
            'fields': ('instancia',),
        }),
        ('REGISTRO DEL RECURSO', {
            'fields': ('sim', 'pm', 'resolucion', 'recurso_origen',
                       'fecha_presentacion', 'fecha_limite',)
        }),
        ('REGISTRO DE ENVÍO AL TSP', {
            'fields': ('numero_oficio', 'fecha_oficio',)
        }),
        ('PARTE RESOLUTIVA', {
            'fields': ('numero', 'fecha', 'texto', 'tipo',)
        }),
    )


class NotificacionAUTOTSPInline(admin.StackedInline):
    model = Notificacion
    extra = 0
    max_num = 1
    verbose_name = "Notificación"
    fields = ('tipo', 'notificado_a', 'fecha', 'hora')
    fk_name = 'autotsp'


@admin.register(AUTOTSP)
class AUTOTSPAdmin(admin.ModelAdmin):
    list_display  = ('numero', 'sim', 'tipo', 'fecha')
    search_fields = ('numero', 'sim__codigo')
    list_filter   = ('tipo',)
    inlines       = [NotificacionAUTOTSPInline]

# ════════════════════════════════════════════════════════════════════════════
#  ADMIN: Documentos Adjuntos
# ════════════════════════════════════════════════════════════════════════════
@admin.register(DocumentoAdjunto)
class DocumentoAdjuntoAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'tipo', 'sim', 'resolucion', 'autotpe', 'autotsp', 'recurso_tsp', 'fecha_registro')
    search_fields = ('nombre',)
    list_filter   = ('tipo',)
    raw_id_fields = ('sim', 'resolucion', 'autotpe', 'autotsp', 'recurso_tsp')
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
    fields = ('rol', 'pm', 'activo')
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
    list_display  = ('usuario_completo', 'rol_badge', 'pm_asignado', 'activo', 'acciones')
    list_filter   = ('rol', 'activo', 'user__date_joined')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'pm__paterno')
    readonly_fields = ('user_info',)

    fieldsets = (
        ('Información de usuario', {
            'fields': ('user', 'user_info', 'rol', 'activo')
        }),
        ('Personal Militar vinculado', {
            'fields': ('pm', 'vocal'),
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

    def pm_asignado(self, obj):
        """Muestra si hay PM asignado"""
        if obj.pm:
            return f"{obj.pm.grado} {obj.pm.paterno} {obj.pm.nombre}"
        return "—"
    pm_asignado.short_description = "Personal Militar"

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
        super().save_model(request, obj, form, change)
