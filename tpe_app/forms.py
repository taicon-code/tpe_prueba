# tpe_app/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import SIM, PM, PM_SIM, ABOG, CustodiaSIM, AGENDA, AUTOTPE, Resolucion, RecursoTSP
from .widgets import ResumenConOpcionesWidget
from .resumen_choices import RESUMEN_CHOICES

class SIMForm(forms.ModelForm):
    """Formulario para crear un nuevo sumario"""
    
    class Meta:
        model = SIM
        fields = [
            'SIM_COD', 'SIM_FECING', 'SIM_TIPO', 
            'SIM_OBJETO', 'SIM_RESUM', 'SIM_AUTOFINAL'
        ]
        widgets = {
            'SIM_COD': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ejemplo: DJE-123/25, SASJUR-25/25, SDISCAPE-86/25',
                'pattern': '[A-Z]+-[0-9]{1,4}/[0-9]{2}',
                'title': 'Formato: PREFIJO-NUM/AÑO (ej: DJE-95/25, SASJUR-25/25)'
            }),
            'SIM_FECING': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'SIM_TIPO': forms.Select(attrs={'class': 'form-control'}),
            'SIM_OBJETO': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Establecer las circunstancias que motivaron...'
            }),
            'SIM_RESUM': ResumenConOpcionesWidget(opciones=RESUMEN_CHOICES),
            'SIM_AUTOFINAL': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dictamen o auto final del sumario (opcional)'
            }),
        }
        labels = {
            'SIM_COD': 'Código del Sumario',
            'SIM_FECING': 'Fecha de Ingreso al TPE',
            'SIM_TIPO': 'Tipo de Sumario',
            'SIM_OBJETO': 'Objeto del Sumario',
            'SIM_RESUM': 'Resumen',
            'SIM_AUTOFINAL': 'Auto Final / Dictamen',
        }

    def clean_SIM_COD(self):
        """Validar que el código no exista ya (considera SIM_VERSION para reaperturas)"""
        cod = self.cleaned_data.get('SIM_COD')
        if cod:
            cod = cod.upper()
            version = self.cleaned_data.get('SIM_VERSION', 1)

            # Si es edición de un SIM existente, permitir el mismo código
            if self.instance and self.instance.pk:
                existentes = SIM.objects.filter(SIM_COD=cod, SIM_VERSION=version).exclude(pk=self.instance.pk)
            else:
                # Si es nuevo SIM, verificar si (SIM_COD, SIM_VERSION) ya existe
                existentes = SIM.objects.filter(SIM_COD=cod, SIM_VERSION=version)

            if existentes.exists():
                raise forms.ValidationError(
                    f'El código {cod} versión {version} ya existe. '
                    'Para reaperturas, use una versión diferente.'
                )
        return cod


class PMSIMForm(forms.ModelForm):
    """Formulario para agregar militares investigados al sumario"""
    
    PM_CI = forms.CharField(
        label='CI del Militar',
        max_length=13,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese CI',
            'list': 'pm_list'
        })
    )

    PM_NOMBRE = forms.CharField(
        label='Nombre',
        max_length=25,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre(s)',
            'autocomplete': 'off'
        })
    )

    PM_PATERNO = forms.CharField(
        label='Apellido Paterno',
        max_length=25,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido paterno',
            'autocomplete': 'off'
        })
    )

    PM_MATERNO = forms.CharField(
        label='Apellido Materno',
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido materno (opcional)'
        })
    )

    PM_ESCALAFON = forms.ChoiceField(
        label='Escalafón',
        required=False,
        choices=[('', '---------')] + list(PM.ESCALAFON_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    PM_GRADO = forms.ChoiceField(
        label='Grado',
        required=False,
        choices=[('', '---------')] + list(PM.GRADO_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    PM_ARMA = forms.ChoiceField(
        label='Arma',
        required=False,
        choices=[('', '---------')] + list(PM.ARMA_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    PM_ESPEC = forms.CharField(
        label='Especialidad',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: INFANTERÍA, BLINDADOS...'
        })
    )

    PM_FOTO = forms.ImageField(
        label='Foto',
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = PM_SIM
        fields = []  # Solo usamos los campos personalizados

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si ya tiene PM asignado, precargar datos (para edición/errores)
        if self.instance and getattr(self.instance, 'pm_id', None):
            pm = self.instance.pm
            self.fields['PM_CI'].initial = '' if pm.PM_CI is None else str(pm.PM_CI)
            self.fields['PM_NOMBRE'].initial = pm.PM_NOMBRE
            self.fields['PM_PATERNO'].initial = pm.PM_PATERNO
            self.fields['PM_MATERNO'].initial = pm.PM_MATERNO
            self.fields['PM_ESCALAFON'].initial = pm.PM_ESCALAFON
            self.fields['PM_GRADO'].initial = pm.PM_GRADO
            self.fields['PM_ARMA'].initial = pm.PM_ARMA
            self.fields['PM_ESPEC'].initial = pm.PM_ESPEC
    
    def clean(self):
        cleaned_data = super().clean()

        # Si es un form marcado para eliminar, no validar más
        if cleaned_data.get('DELETE'):
            return cleaned_data

        ci = (cleaned_data.get('PM_CI') or '').strip()
        nombre = (cleaned_data.get('PM_NOMBRE') or '').strip().upper()
        paterno = (cleaned_data.get('PM_PATERNO') or '').strip().upper()
        materno = (cleaned_data.get('PM_MATERNO') or '').strip().upper()
        escalafon = cleaned_data.get('PM_ESCALAFON') or None
        grado = cleaned_data.get('PM_GRADO') or None
        arma = cleaned_data.get('PM_ARMA') or None
        espec = (cleaned_data.get('PM_ESPEC') or '').strip() or None

        # Form vacío: permitirlo (útil cuando agregas/quitas filas dinámicamente)
        if not any([ci, nombre, paterno, materno, escalafon, grado, arma]):
            return cleaned_data

        # Exigir nombre y paterno como mínimo
        if not nombre:
            self.add_error('PM_NOMBRE', 'Ingrese el nombre del militar.')
        if not paterno:
            self.add_error('PM_PATERNO', 'Ingrese el apellido paterno del militar.')

        if self.errors:
            return cleaned_data

        # PRIORIDAD 1: Buscar por CI (si se ingresó)
        pm = None
        if ci:
            if not ci.isdigit():
                self.add_error('PM_CI', 'El CI debe contener solo números.')
                return cleaned_data
            pm = PM.objects.filter(PM_CI=ci).first()

        # PRIORIDAD 2: Buscar por Nombre + Paterno + Materno (si no encontró por CI)
        if not pm:
            query = PM.objects.filter(PM_NOMBRE=nombre, PM_PATERNO=paterno)
            if materno:
                query = query.filter(PM_MATERNO=materno)
            pm = query.first()

        # Si encontró PM existente, reutilizarlo
        if pm:
            cleaned_data['pm'] = pm
            return cleaned_data

        # Si no encontró, preparar datos para crear nuevo PM
        cleaned_data['pm_data'] = {
            'PM_CI': ci or None,
            'PM_ESCALAFON': escalafon,
            'PM_GRADO': grado,
            'PM_ARMA': arma,
            'PM_ESPEC': espec,
            'PM_NOMBRE': nombre,
            'PM_PATERNO': paterno,
            'PM_MATERNO': materno or None,
        }
        return cleaned_data


# Formset para agregar múltiples militares al sumario
PMSIMFormSet = inlineformset_factory(
    SIM,                    # Modelo padre
    PM_SIM,                 # Modelo hijo
    form=PMSIMForm,
    extra=0,                # Mostrar 1 formulario vacío por defecto (lo fuerza min_num)
    can_delete=True,        # Permitir eliminar militares
    min_num=1,              # Al menos 1 militar es obligatorio
    validate_min=True
)


class AgendarSumarioForm(forms.Form):
    """Formulario para agendar un sumario a una agenda existente"""

    # ✅ NUEVO v3.2: Seleccionar agenda existente (en lugar de fecha suelta)
    agenda = forms.ModelChoiceField(
        queryset=AGENDA.objects.filter(AG_ESTADO='PROGRAMADA').order_by('AG_FECPROG'),
        label='Agenda',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione una agenda...'
    )

    sumario = forms.ModelChoiceField(
        queryset=SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True),
        label='Sumario a Agendar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione un sumario...'
    )

    abogados = forms.ModelMultipleChoiceField(
        queryset=ABOG.objects.all().order_by('AB_PATERNO', 'AB_NOMBRE'),
        label='Abogado(s) Asignado(s)',
        widget=forms.CheckboxSelectMultiple(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar displays
        # ✅ Mostrar sumario con código, militares involucrados y resumen
        def sumario_display(obj):
            militares = ", ".join([f"{pm.PM_GRADO} {pm.PM_PATERNO}" for pm in obj.militares.all()[:2]])
            return f"{obj.SIM_COD} — {militares} — {obj.SIM_RESUM[:40]}"

        self.fields['sumario'].label_from_instance = sumario_display
        self.fields['abogados'].label_from_instance = lambda obj: f"{obj.AB_GRADO} {obj.AB_NOMBRE} {obj.AB_PATERNO}"
        # ✅ Mostrar número, tipo y fecha en el dropdown de agendas
        self.fields['agenda'].label_from_instance = lambda obj: f"[{obj.AG_NUM}] {obj.get_AG_TIPO_display()} — {obj.AG_FECPROG.strftime('%d/%m/%Y') if obj.AG_FECPROG else '—'}"


class GestionarAbogadosSIMForm(forms.Form):
    """Agregar o quitar abogados de un sumario ya agendado"""

    abogados = forms.ModelMultipleChoiceField(
        queryset=ABOG.objects.all().order_by('AB_PATERNO', 'AB_NOMBRE'),
        label='Abogados asignados',
        widget=forms.CheckboxSelectMultiple(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['abogados'].label_from_instance = lambda obj: f"{obj.AB_GRADO} {obj.AB_NOMBRE} {obj.AB_PATERNO}"


# ✅ NUEVO v3.2: Formularios para gestionar agendas
class AgendaForm(forms.ModelForm):
    """Crear o editar una agenda"""

    AG_NUM = forms.CharField(
        max_length=50,
        label='Número de Agenda',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1ra. Reunión/26 o AG-001/26',
        }),
        help_text='Número único de la agenda (ej: "1ra. Reunión/26")'
    )

    class Meta:
        model = AGENDA
        fields = ['AG_NUM', 'AG_TIPO', 'AG_FECPROG']
        widgets = {
            'AG_TIPO': forms.Select(attrs={'class': 'form-control'}),
            'AG_FECPROG': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'AG_TIPO': 'Tipo de Agenda',
            'AG_FECPROG': 'Fecha Programada',
        }


class AgendaResultadoForm(forms.ModelForm):
    """Registrar resultado de una agenda (realizada/suspendida/reprogramada)"""

    # Opciones limitadas: no se puede volver a PROGRAMADA
    AG_ESTADO = forms.ChoiceField(
        choices=[
            ('REALIZADA', 'Realizada (sesión se realizó)'),
            ('SUSPENDIDA', 'Suspendida (sin nueva fecha aún)'),
            ('REPROGRAMADA', 'Reprogramada (nueva fecha)'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input', 'style': 'display: block; margin: 0;'}),
        label='¿Qué pasó con esta agenda?'
    )

    class Meta:
        model = AGENDA
        fields = ['AG_ESTADO', 'AG_FECREAL']
        widgets = {
            'AG_FECREAL': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'AG_FECREAL': 'Fecha Realizada (si aplica)',
        }

    def clean(self):
        cleaned_data = super().clean()
        estado = cleaned_data.get('AG_ESTADO')
        fecreal = cleaned_data.get('AG_FECREAL')

        # Si es REALIZADA, AG_FECREAL es obligatoria
        if estado == 'REALIZADA' and not fecreal:
            raise forms.ValidationError('La fecha realizada es obligatoria si la sesión fue realizada.')

        return cleaned_data

class RegistrarRRForm(forms.ModelForm):
    """Formulario para registrar un Recurso de Reconsideración (Resolucion con INSTANCIA=RECONSIDERACION)"""

    resolucion_origen = forms.ModelChoiceField(
        queryset=Resolucion.objects.filter(RES_INSTANCIA='PRIMERA').order_by('-RES_FEC'),
        label='Primera Resolución a Apelar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione la Resolución original...'
    )

    class Meta:
        model = Resolucion
        fields = ['resolucion_origen', 'RES_RESUM', 'RES_FECPRESEN']
        widgets = {
            'RES_RESUM': forms.Select(attrs={'class': 'form-control'}),
            'RES_FECPRESEN': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'RES_RESUM': 'Tipo de Recurso',
            'RES_FECPRESEN': 'Fecha de Presentación del Recurso',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def res_label(obj):
            pm_info = f" - {obj.pm.PM_GRADO} {obj.pm.PM_PATERNO}" if obj.pm else ""
            return f"RES {obj.RES_NUM}{pm_info} (SIM: {obj.sim.SIM_COD})"
        self.fields['resolucion_origen'].label_from_instance = res_label


class AgendarRRForm(forms.Form):
    """Formulario para agendar un Recurso de Reconsideración"""

    rr = forms.ModelChoiceField(
        queryset=Resolucion.objects.filter(RES_INSTANCIA='RECONSIDERACION', agenda__isnull=True),
        label='Recurso de Reconsideración a Agendar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione un recurso...'
    )

    abogado = forms.ModelChoiceField(
        queryset=ABOG.objects.all().order_by('AB_PATERNO', 'AB_NOMBRE'),
        label='Abogado Asignado',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione un abogado...'
    )

    fecha_agenda = forms.DateField(
        label='Fecha de Agenda/Reunión',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def rr_label(obj):
            origen = obj.resolucion_origen
            pm_info = f" - {origen.pm.PM_GRADO} {origen.pm.PM_PATERNO}" if (origen and origen.pm) else ""
            origen_num = origen.RES_NUM if origen else 'S/N'
            return f"RR sobre RES {origen_num}{pm_info} (SIM: {obj.sim.SIM_COD})"
        self.fields['rr'].label_from_instance = rr_label
        self.fields['abogado'].label_from_instance = lambda obj: f"{obj.AB_GRADO} {obj.AB_NOMBRE} {obj.AB_PATERNO}"


# ============================================================
# FORMULARIOS DE CUSTODIA
# ============================================================

class CustodiaSIMForm(forms.ModelForm):
    """Formulario para registrar custodia de una carpeta SIM"""

    class Meta:
        model = CustodiaSIM
        fields = ['tipo_custodio', 'abog', 'observacion']
        widgets = {
            'tipo_custodio': forms.Select(attrs={'class': 'form-control'}),
            'abog': forms.Select(attrs={'class': 'form-control'}),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas sobre la entrega (opcional)'
            }),
        }
        labels = {
            'tipo_custodio': 'Tipo de Custodio',
            'abog': 'Abogado (si aplica)',
            'observacion': 'Observación',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Listar todos los abogados disponibles
        self.fields['abog'].queryset = ABOG.objects.all()
        self.fields['abog'].label_from_instance = lambda obj: f"{obj.AB_GRADO} {obj.AB_NOMBRE} {obj.AB_PATERNO}"
        # Campo opcional
        self.fields['abog'].required = False


class EntregarCarpetaAbogadoForm(forms.Form):
    """Formulario para que el ABOGADO entregue carpeta a Archivo SIM"""

    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Ej: "Carpeta completa con dictamen y resolución", "Documentos en buen estado", etc.'
        }),
        label='Observaciones al entregar'
    )


class EntregarCarpetaForm(forms.Form):
    """Formulario para que ADMIN2 entregue carpeta a un abogado"""

    tipo_custodio = forms.ChoiceField(
        choices=[
            ('ABOG_ASESOR', 'Abogado Asesor (1ra. Resolución)'),
            ('ABOG_RR', 'Abogado (Recurso de Reconsideración)'),
            ('ABOG_AUTOS', 'Abogado Autos (Ejecutoria)'),
            ('ABOG_RAP', 'Abogado 3 (RAP/Búsqueda)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tipo de Custodia'
    )

    abogado = forms.ModelChoiceField(
        queryset=ABOG.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Abogado que recibe'
    )

    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Notas sobre la entrega (opcional)'
        }),
        label='Observación'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['abogado'].label_from_instance = lambda obj: f"{obj.AB_GRADO} {obj.AB_NOMBRE} {obj.AB_PATERNO}"


class RecibirCarpetaForm(forms.Form):
    """Formulario para recibir carpeta de vuelta de un abogado (Admin2)"""

    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Estado de la carpeta, notas (opcional)'
        }),
        label='Observación',
        help_text='Ej: carpeta completa, falta documento, etc.'
    )


# ============================================================
# FORMULARIOS PARA AYUDANTE — Registro de datos históricos
# ============================================================

class RESForm(forms.ModelForm):
    """Formulario para registrar una Resolución PRIMERA histórica sin dictamen previo"""

    class Meta:
        model = Resolucion
        fields = [
            'sim', 'pm', 'RES_NUM', 'RES_FEC', 'RES_TIPO', 'RES_RESOL'
        ]
        widgets = {
            'sim': forms.Select(attrs={'class': 'form-control'}),
            'pm': forms.Select(attrs={'class': 'form-control'}),
            'RES_NUM': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 05/26',
                'pattern': '[0-9]{1,4}/[0-9]{2}'
            }),
            'RES_FEC': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'RES_TIPO': forms.Select(attrs={'class': 'form-control'}),
            'RES_RESOL': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Texto de la resolución'
            }),
        }
        labels = {
            'sim': 'Sumario',
            'pm': 'Personal Militar Implicado',
            'RES_NUM': 'Número de Resolución',
            'RES_FEC': 'Fecha de Resolución',
            'RES_TIPO': 'Tipo de Resolución',
            'RES_RESOL': 'Texto de la Resolución',
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.RES_INSTANCIA = 'PRIMERA'
        if commit:
            obj.save()
        return obj


class RESNotificacionForm(forms.ModelForm):
    """Formulario para registrar notificación de una Resolución existente (PRIMERA o RECONSIDERACION)"""

    class Meta:
        model = Resolucion
        fields = [
            'RES_FECNOT', 'RES_HORNOT', 'RES_NOT', 'RES_TIPO_NOTIF'
        ]
        widgets = {
            'RES_FECNOT': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'RES_HORNOT': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'RES_NOT': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quién notificó'
            }),
            'RES_TIPO_NOTIF': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'RES_FECNOT': 'Fecha de Notificación',
            'RES_HORNOT': 'Hora de Notificación',
            'RES_NOT': 'Notificado a (persona)',
            'RES_TIPO_NOTIF': 'Tipo de Notificación',
        }


class RAPForm(forms.ModelForm):
    """Formulario para registrar un Recurso de Apelación al TSP histórico (RecursoTSP.APELACION)"""

    class Meta:
        model = RecursoTSP
        fields = [
            'sim', 'pm', 'resolucion', 'TSP_FECPRESEN', 'TSP_OFI', 'TSP_FECOFI',
            'TSP_NUM', 'TSP_FEC', 'TSP_RESOL', 'TSP_TIPO'
        ]
        widgets = {
            'sim': forms.Select(attrs={'class': 'form-control'}),
            'pm': forms.Select(attrs={'class': 'form-control'}),
            'resolucion': forms.Select(attrs={'class': 'form-control'}),
            'TSP_FECPRESEN': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'TSP_OFI': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de oficio'}),
            'TSP_FECOFI': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'TSP_NUM': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 03/26',
                'pattern': '[0-9]{1,4}/[0-9]{2}'
            }),
            'TSP_FEC': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'TSP_RESOL': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                'placeholder': 'Texto del recurso'}),
            'TSP_TIPO': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'sim': 'Sumario',
            'pm': 'Personal Militar',
            'resolucion': 'Resolución RR impugnada (opcional)',
            'TSP_FECPRESEN': 'Fecha de Presentación',
            'TSP_OFI': 'Número de Oficio',
            'TSP_FECOFI': 'Fecha de Oficio',
            'TSP_NUM': 'Número del RAP',
            'TSP_FEC': 'Fecha del RAP',
            'TSP_RESOL': 'Texto del RAP',
            'TSP_TIPO': 'Tipo de RAP',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolucion'].queryset = Resolucion.objects.filter(
            RES_INSTANCIA='RECONSIDERACION'
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.TSP_INSTANCIA = 'APELACION'
        if commit:
            instance.save()
        return instance


class RAEEForm(forms.ModelForm):
    """Formulario para registrar un RAEE (RecursoTSP.ACLARACION_ENMIENDA) histórico"""

    class Meta:
        model = RecursoTSP
        fields = [
            'sim', 'pm', 'recurso_origen', 'TSP_NUM', 'TSP_FEC', 'TSP_RESOL', 'TSP_RESUM'
        ]
        widgets = {
            'sim': forms.Select(attrs={'class': 'form-control'}),
            'pm': forms.Select(attrs={'class': 'form-control'}),
            'recurso_origen': forms.Select(attrs={'class': 'form-control'}),
            'TSP_NUM': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 02/26',
                'pattern': '[0-9]{1,4}/[0-9]{2}'
            }),
            'TSP_FEC': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'TSP_RESOL': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                'placeholder': 'Texto de la aclaración/enmienda'}),
            'TSP_RESUM': forms.TextInput(attrs={'class': 'form-control',
                'placeholder': 'Resumen breve'}),
        }
        labels = {
            'sim': 'Sumario',
            'pm': 'Personal Militar',
            'recurso_origen': 'Recurso de Apelación (RAP) origen',
            'TSP_NUM': 'Número del RAEE',
            'TSP_FEC': 'Fecha del RAEE',
            'TSP_RESOL': 'Texto del RAEE',
            'TSP_RESUM': 'Resumen',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recurso_origen'].queryset = RecursoTSP.objects.filter(
            TSP_INSTANCIA='APELACION'
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.TSP_INSTANCIA = 'ACLARACION_ENMIENDA'
        if commit:
            instance.save()
        return instance


class AUTOTPEHistoricoForm(forms.ModelForm):
    """Formulario para registrar un Auto del TPE histórico (incluyendo memorándum)"""

    class Meta:
        model = AUTOTPE
        fields = [
            'sim', 'pm', 'TPE_NUM', 'TPE_FEC', 'TPE_TIPO', 'TPE_RESOL',
            'TPE_MEMO_NUM', 'TPE_MEMO_FEC', 'TPE_MEMO_ENTREGA'
        ]
        widgets = {
            'sim': forms.Select(attrs={'class': 'form-control'}),
            'pm': forms.Select(attrs={'class': 'form-control'}),
            'TPE_NUM': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 04/26',
                'pattern': '[0-9]{1,4}/[0-9]{2}'
            }),
            'TPE_FEC': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'TPE_TIPO': forms.Select(attrs={'class': 'form-control'}),
            'TPE_RESOL': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Texto del auto'
            }),
            'TPE_MEMO_NUM': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de memorándum (opcional)'
            }),
            'TPE_MEMO_FEC': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'TPE_MEMO_ENTREGA': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'sim': 'Sumario',
            'pm': 'Personal Militar',
            'TPE_NUM': 'Número del Auto',
            'TPE_FEC': 'Fecha del Auto',
            'TPE_TIPO': 'Tipo de Auto',
            'TPE_RESOL': 'Texto del Auto',
            'TPE_MEMO_NUM': 'Número de Memorándum',
            'TPE_MEMO_FEC': 'Fecha del Memorándum',
            'TPE_MEMO_ENTREGA': 'Fecha de Entrega del Memorándum',
        }


class AutoEjecutoriaForm(forms.ModelForm):
    """Formulario para crear Auto de Ejecutoria desde caso pendiente (RES sin RR o RR sin RAP)"""

    class Meta:
        model = AUTOTPE
        fields = ['TPE_NUM', 'TPE_FEC', 'TPE_RESOL', 'abog']
        widgets = {
            'TPE_NUM': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 07/26',
                'pattern': '[0-9]{1,4}/[0-9]{2}',
            }),
            'TPE_FEC': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'TPE_RESOL': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Texto del Auto de Ejecutoria...',
            }),
            'abog': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'TPE_NUM': 'Número del Auto',
            'TPE_FEC': 'Fecha del Auto',
            'TPE_RESOL': 'Texto del Auto de Ejecutoria',
            'abog': 'Abogado',
        }


class AUTOTPENotificacionForm(forms.ModelForm):
    """Formulario para registrar notificación de un Auto TPE existente"""

    class Meta:
        model = AUTOTPE
        fields = [
            'TPE_FECNOT', 'TPE_HORNOT', 'TPE_NOT', 'TPE_TIPO_NOTIF'
        ]
        widgets = {
            'TPE_FECNOT': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'TPE_HORNOT': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'TPE_NOT': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Quién notificó'
            }),
            'TPE_TIPO_NOTIF': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'TPE_FECNOT': 'Fecha de Notificación',
            'TPE_HORNOT': 'Hora de Notificación',
            'TPE_NOT': 'Notificado a (persona)',
            'TPE_TIPO_NOTIF': 'Tipo de Notificación',
        }

