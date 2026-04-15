# tpe_app/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import SIM, PM, PM_SIM, ABOG, RES, RR, CustodiaSIM
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
                'placeholder': 'Ejemplo: DJE-123/25',
                'pattern': 'DJE-[0-9]{1,4}/[0-9]{2}',
                'title': 'Formato: DJE-###/AA'
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
        """Validar que el código no exista ya"""
        cod = self.cleaned_data.get('SIM_COD')
        if cod:
            cod = cod.upper()
            if SIM.objects.filter(SIM_COD=cod).exists():
                raise forms.ValidationError(f'El código {cod} ya existe en el sistema')
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
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre(s)'
        })
    )

    PM_PATERNO = forms.CharField(
        label='Apellido Paterno',
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido paterno'
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
    
    class Meta:
        model = PM_SIM
        fields = []  # Solo usamos el campo personalizado PM_CI
    
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
    
    def clean(self):
        cleaned_data = super().clean()

        # Si es un form marcado para eliminar, no validar más
        if cleaned_data.get('DELETE'):
            return cleaned_data

        ci = (cleaned_data.get('PM_CI') or '').strip()
        nombre = (cleaned_data.get('PM_NOMBRE') or '').strip()
        paterno = (cleaned_data.get('PM_PATERNO') or '').strip()
        materno = (cleaned_data.get('PM_MATERNO') or '').strip()
        escalafon = cleaned_data.get('PM_ESCALAFON') or None
        grado = cleaned_data.get('PM_GRADO') or None
        arma = cleaned_data.get('PM_ARMA') or None

        # Form vacío: permitirlo (útil cuando agregas/quitas filas dinámicamente)
        if not any([ci, nombre, paterno, materno, escalafon, grado, arma]):
            return cleaned_data

        # Validación CI (si viene)
        pm = None
        if ci:
            if not ci.isdigit():
                self.add_error('PM_CI', 'El CI debe contener solo números.')
                return cleaned_data

            pm = PM.objects.filter(PM_CI=ci).first()
            if pm:
                cleaned_data['pm'] = pm
                return cleaned_data

        # Si no existe por CI (o no se ingresó), exigir datos mínimos para crear
        if not nombre:
            self.add_error('PM_NOMBRE', 'Ingrese el nombre del militar.')
        if not paterno:
            self.add_error('PM_PATERNO', 'Ingrese el apellido paterno del militar.')

        if self.errors:
            return cleaned_data

        cleaned_data['pm_data'] = {
            'PM_CI': ci or None,
            'PM_ESCALAFON': escalafon,
            'PM_GRADO': grado,
            'PM_ARMA': arma,
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
    """Formulario para agendar un sumario (asignar abogado)"""
    
    sumario = forms.ModelChoiceField(
        queryset=SIM.objects.filter(SIM_ESTADO='PARA_AGENDA', abogados__isnull=True),
        label='Sumario a Agendar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione un sumario...'
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
        # Personalizar el label del queryset de sumarios
        self.fields['sumario'].label_from_instance = lambda obj: f"{obj.SIM_COD} - {obj.SIM_RESUM[:50]}"
        self.fields['abogado'].label_from_instance = lambda obj: f"{obj.AB_GRADO} {obj.AB_NOMBRE} {obj.AB_PATERNO}"

class RegistrarRRForm(forms.ModelForm):
    """Formulario para registrar un nuevo Recurso de Reconsideración"""
    
    res = forms.ModelChoiceField(
        queryset=RES.objects.all().order_by('-RES_FEC'),
        label='Primera Resolución a Apelar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione la Resolución original...'
    )

    class Meta:
        model = RR
        fields = ['res', 'RR_FECPRESEN']
        widgets = {
            'RR_FECPRESEN': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'RR_FECPRESEN': 'Fecha de Presentación del Recurso',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['res'].label_from_instance = lambda obj: f"RES {obj.RES_NUM} (Sumario: {obj.sim.SIM_COD})"


class AgendarRRForm(forms.Form):
    """Formulario para agendar un Recurso de Reconsideración"""
    
    rr = forms.ModelChoiceField(
        queryset=RR.objects.filter(agenda__isnull=True),
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
        self.fields['rr'].label_from_instance = lambda obj: f"Sumario {obj.sim.SIM_COD} - RES {obj.res.RES_NUM} ({obj.RR_RESUM or 'Sin resumen'})"
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


class EntregarCarpetaForm(forms.Form):
    """Formulario para entregar carpeta a un abogado (Admin2)"""

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

