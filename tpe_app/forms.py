# tpe_app/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import SIM, PM, PM_SIM, CustodiaSIM, AGENDA, AUTOTPE, AUTOTSP, Resolucion, RecursoTSP, Notificacion, Memorandum
from .widgets import ResumenConOpcionesWidget
from .resumen_choices import RESUMEN_CHOICES


class SIMForm(forms.ModelForm):

    class Meta:
        model = SIM
        fields = ['codigo', 'fecha_ingreso', 'numero_carpeta', 'tipo', 'objeto', 'resumen', 'auto_final']
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ejemplo: DJE-123/25, SASJUR-25/25, SDISCAPE-86/25',
                'autocomplete': 'off',
                'spellcheck': 'false'
            }),
            'fecha_ingreso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_carpeta': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 85',
                'min': '1',
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'objeto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Establecer las circunstancias que motivaron...'
            }),
            'resumen': ResumenConOpcionesWidget(opciones=RESUMEN_CHOICES),
            'auto_final': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dictamen o auto final del sumario (opcional)'
            }),
        }
        labels = {
            'codigo':          'Código del Sumario',
            'fecha_ingreso':   'Fecha de Ingreso al TPE',
            'numero_carpeta':  'N° Carpeta Física',
            'tipo':            'Tipo de Sumario',
            'objeto':          'Objeto del Sumario',
            'resumen':         'Resumen',
            'auto_final':      'Auto Final / Dictamen',
        }

    def clean_codigo(self):
        cod = self.cleaned_data.get('codigo')
        if cod:
            cod = cod.upper()
            version = self.cleaned_data.get('version', 1)
            if self.instance and self.instance.pk:
                existentes = SIM.objects.filter(codigo=cod, version=version).exclude(pk=self.instance.pk)
            else:
                existentes = SIM.objects.filter(codigo=cod, version=version)
            if existentes.exists():
                raise forms.ValidationError(
                    f'El código {cod} versión {version} ya existe. '
                    'Para reaperturas, use una versión diferente.'
                )
        return cod


class PMSIMForm(forms.ModelForm):

    ci = forms.CharField(
        label='CI del Militar', max_length=13, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese CI', 'list': 'pm_list'})
    )
    nombre = forms.CharField(
        label='Nombre', max_length=25, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre(s)', 'autocomplete': 'off'})
    )
    paterno = forms.CharField(
        label='Apellido Paterno', max_length=25, required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido paterno', 'autocomplete': 'off'})
    )
    materno = forms.CharField(
        label='Apellido Materno', max_length=25, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido materno (opcional)'})
    )
    escalafon = forms.ChoiceField(
        label='Escalafón', required=False,
        choices=[('', '---------')] + list(PM.ESCALAFON_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    grado = forms.ChoiceField(
        label='Grado', required=False,
        choices=[('', '---------')] + list(PM.GRADO_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    arma = forms.ChoiceField(
        label='Arma', required=False,
        choices=[('', '---------')] + list(PM.ARMA_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    especialidad = forms.CharField(
        label='Especialidad', max_length=15, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: INFANTERÍA, BLINDADOS...'})
    )
    foto = forms.ImageField(
        label='Foto', required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )
    anio_promocion = forms.IntegerField(
        label='Año de Egreso', required=False, min_value=1950, max_value=2100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 2000'})
    )
    grado_en_fecha = forms.ChoiceField(
        label='Grado al momento del sumario', required=False,
        choices=[('', '---------')] + list(PM.GRADO_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    no_ascendio = forms.BooleanField(
        label='No ascendió al grado correspondiente', required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = PM_SIM
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and getattr(self.instance, 'pk', None):
            pm = self.instance.pm
            self.fields['ci'].initial          = '' if pm.ci is None else str(pm.ci)
            self.fields['nombre'].initial      = pm.nombre
            self.fields['paterno'].initial     = pm.paterno
            self.fields['materno'].initial     = pm.materno
            self.fields['escalafon'].initial   = pm.escalafon
            self.fields['grado'].initial       = pm.grado
            self.fields['arma'].initial        = pm.arma
            self.fields['especialidad'].initial = pm.especialidad
            self.fields['anio_promocion'].initial = pm.anio_promocion
            self.fields['no_ascendio'].initial = pm.no_ascendio
            self.fields['grado_en_fecha'].initial = self.instance.grado_en_fecha

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('DELETE'):
            return cleaned_data

        ci          = (cleaned_data.get('ci') or '').strip()
        nombre      = (cleaned_data.get('nombre') or '').strip().upper()
        paterno     = (cleaned_data.get('paterno') or '').strip().upper()
        materno     = (cleaned_data.get('materno') or '').strip().upper()
        escalafon   = cleaned_data.get('escalafon') or None
        grado       = cleaned_data.get('grado') or None
        arma        = cleaned_data.get('arma') or None
        especialidad = (cleaned_data.get('especialidad') or '').strip() or None
        anio_promocion = cleaned_data.get('anio_promocion') or None
        no_ascendio = cleaned_data.get('no_ascendio') or False
        grado_fecha = cleaned_data.get('grado_en_fecha') or None

        cleaned_data['pmsim_grado_en_fecha'] = grado_fecha

        if not any([ci, nombre, paterno, materno, escalafon, grado, arma]):
            return cleaned_data

        if not nombre:
            self.add_error('nombre', 'Ingrese el nombre del militar.')
        if not paterno:
            self.add_error('paterno', 'Ingrese el apellido paterno del militar.')

        if self.errors:
            return cleaned_data

        pm = None
        if ci:
            if not ci.isdigit():
                self.add_error('ci', 'El CI debe contener solo números.')
                return cleaned_data
            pm = PM.objects.filter(ci=ci).first()

        if not pm:
            query = PM.objects.filter(nombre=nombre, paterno=paterno)
            if materno:
                query = query.filter(materno=materno)
            pm = query.first()

        if pm:
            cleaned_data['pm'] = pm
            return cleaned_data

        cleaned_data['pm_data'] = {
            'ci':          ci or None,
            'escalafon':   escalafon,
            'grado':       grado,
            'arma':        arma,
            'especialidad': especialidad,
            'nombre':      nombre,
            'paterno':     paterno,
            'materno':     materno or None,
            'anio_promocion': anio_promocion,
            'no_ascendio': no_ascendio,
        }
        return cleaned_data


PMSIMFormSet = inlineformset_factory(
    SIM, PM_SIM, form=PMSIMForm,
    extra=0, can_delete=True, min_num=1, validate_min=True
)


class AgendarSumarioForm(forms.Form):

    agenda = forms.ModelChoiceField(
        queryset=AGENDA.objects.filter(estado='PROGRAMADA').order_by('fecha_prog'),
        label='Agenda',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione una agenda...'
    )
    sumario = forms.ModelChoiceField(
        queryset=SIM.objects.filter(estado='PARA_AGENDA', abogados__isnull=True),
        label='Sumario a Agendar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione un sumario...'
    )
    abogados = forms.ModelMultipleChoiceField(
        queryset=PM.objects.filter(perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR']).order_by('paterno', 'nombre'),
        label='Abogado(s) Asignado(s)',
        widget=forms.CheckboxSelectMultiple(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def sumario_display(obj):
            militares = ", ".join([f"{pm.grado} {pm.paterno}" for pm in obj.militares.all()[:2]])
            return f"{obj.codigo} — {militares} — {obj.resumen[:40]}"

        self.fields['sumario'].label_from_instance = sumario_display
        self.fields['abogados'].label_from_instance = lambda obj: f"{obj.grado} {obj.nombre} {obj.paterno}"
        self.fields['agenda'].label_from_instance = lambda obj: f"[{obj.numero}] {obj.get_tipo_display()} — {obj.fecha_prog.strftime('%d/%m/%Y') if obj.fecha_prog else '—'}"


class GestionarAbogadosSIMForm(forms.Form):

    abogados = forms.ModelMultipleChoiceField(
        queryset=PM.objects.filter(perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR']).order_by('paterno', 'nombre'),
        label='Abogados asignados',
        widget=forms.CheckboxSelectMultiple(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['abogados'].label_from_instance = lambda obj: f"{obj.grado} {obj.nombre} {obj.paterno}"


class AgendaForm(forms.ModelForm):

    numero = forms.CharField(
        max_length=50, label='Número de Agenda',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1ra. Reunión/26 o AG-001/26',
        }),
        help_text='Número único de la agenda (ej: "1ra. Reunión/26")'
    )

    class Meta:
        model = AGENDA
        fields = ['numero', 'tipo', 'fecha_prog']
        widgets = {
            'tipo':       forms.Select(attrs={'class': 'form-control'}),
            'fecha_prog': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'tipo':       'Tipo de Agenda',
            'fecha_prog': 'Fecha Programada',
        }


class AgendaResultadoForm(forms.ModelForm):

    estado = forms.ChoiceField(
        choices=[
            ('REALIZADA',    'Realizada (sesión se realizó)'),
            ('SUSPENDIDA',   'Suspendida (sin nueva fecha aún)'),
            ('REPROGRAMADA', 'Reprogramada (nueva fecha)'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input', 'style': 'display: block; margin: 0;'}),
        label='¿Qué pasó con esta agenda?'
    )

    class Meta:
        model = AGENDA
        fields = ['estado', 'fecha_real']
        widgets = {
            'fecha_real': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'fecha_real': 'Fecha Realizada (si aplica)',
        }

    def clean(self):
        cleaned_data = super().clean()
        estado   = cleaned_data.get('estado')
        fecha_real = cleaned_data.get('fecha_real')
        if estado == 'REALIZADA' and not fecha_real:
            raise forms.ValidationError('La fecha realizada es obligatoria si la sesión fue realizada.')
        return cleaned_data


class RegistrarRRForm(forms.ModelForm):

    resolucion_origen = forms.ModelChoiceField(
        queryset=Resolucion.objects.filter(instancia='PRIMERA').order_by('-fecha'),
        label='Primera Resolución a Apelar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione la Resolución original...'
    )

    class Meta:
        model = Resolucion
        fields = ['resolucion_origen', 'tipo', 'fecha_presentacion']
        widgets = {
            'tipo':               forms.Select(attrs={'class': 'form-control'}),
            'fecha_presentacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'tipo':               'Resultado (PROCEDENCIA/IMPROCEDENCIA)',
            'fecha_presentacion': 'Fecha de Presentación del Recurso',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def res_label(obj):
            pm_info = f" - {obj.pm.grado} {obj.pm.paterno}" if obj.pm else ""
            return f"RES {obj.numero}{pm_info} (SIM: {obj.sim.codigo})"
        self.fields['resolucion_origen'].label_from_instance = res_label


class AgendarRRForm(forms.Form):

    rr = forms.ModelChoiceField(
        queryset=Resolucion.objects.filter(instancia='RECONSIDERACION', agenda__isnull=True),
        label='Recurso de Reconsideración a Agendar',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione un recurso...'
    )
    abogado = forms.ModelChoiceField(
        queryset=PM.objects.filter(perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR']).order_by('paterno', 'nombre'),
        label='Abogado Asignado',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Seleccione un abogado...'
    )
    fecha_agenda = forms.DateField(
        label='Fecha de Agenda/Reunión',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def rr_label(obj):
            origen = obj.resolucion_origen
            pm_info = f" - {origen.pm.grado} {origen.pm.paterno}" if (origen and origen.pm) else ""
            origen_num = origen.numero if origen else 'S/N'
            return f"RR sobre RES {origen_num}{pm_info} (SIM: {obj.sim.codigo})"
        self.fields['rr'].label_from_instance = rr_label
        self.fields['abogado'].label_from_instance = lambda obj: f"{obj.grado} {obj.nombre} {obj.paterno}"


# ============================================================
# FORMULARIOS DE CUSTODIA
# ============================================================

class CustodiaSIMForm(forms.ModelForm):

    class Meta:
        model = CustodiaSIM
        fields = ['tipo_custodio', 'abogado', 'observacion']
        widgets = {
            'tipo_custodio': forms.Select(attrs={'class': 'form-control'}),
            'abogado':       forms.Select(attrs={'class': 'form-control'}),
            'observacion':   forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                   'placeholder': 'Notas sobre la entrega (opcional)'}),
        }
        labels = {
            'tipo_custodio': 'Tipo de Custodio',
            'abogado':       'Abogado (si aplica)',
            'observacion':   'Observación',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['abogado'].queryset = PM.objects.filter(perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR']).order_by('paterno', 'nombre')
        self.fields['abogado'].label_from_instance = lambda obj: f"{obj.grado} {obj.nombre} {obj.paterno}"
        self.fields['abogado'].required = False


class EntregarCarpetaAbogadoForm(forms.Form):
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
            'placeholder': 'Ej: "Carpeta completa con dictamen y resolución"'}),
        label='Observaciones al entregar'
    )


class EntregarCarpetaForm(forms.Form):
    tipo_custodio = forms.ChoiceField(
        choices=[
            ('ABOG_ASESOR', 'Abogado Asesor (1ra. Resolución)'),
            ('ABOG_RR',     'Abogado (Recurso de Reconsideración)'),
            ('ABOG_AUTOS',  'Abogado Autos (Ejecutoria)'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tipo de Custodia'
    )
    abogado = forms.ModelChoiceField(
        queryset=PM.objects.filter(perfilusuario__rol__in=['ABOG1_ASESOR', 'ABOG2_AUTOS', 'ABOG3_BUSCADOR']).order_by('paterno', 'nombre'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Abogado que recibe'
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
            'placeholder': 'Notas sobre la entrega (opcional)'}),
        label='Observación'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['abogado'].label_from_instance = lambda obj: f"{obj.grado} {obj.nombre} {obj.paterno}"


class RecibirCarpetaForm(forms.Form):
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
            'placeholder': 'Estado de la carpeta, notas (opcional)'}),
        label='Observación',
        help_text='Ej: carpeta completa, falta documento, etc.'
    )


# ============================================================
# FORMULARIOS PARA AYUDANTE — Registro de datos históricos
# ============================================================

class RESForm(forms.ModelForm):

    class Meta:
        model = Resolucion
        fields = ['sim', 'pm', 'numero', 'fecha', 'tipo', 'texto']
        widgets = {
            'sim':    forms.Select(attrs={'class': 'form-control'}),
            'pm':     forms.Select(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 05/26'}),
            'fecha':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo':   forms.Select(attrs={'class': 'form-control'}),
            'texto':  forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                            'placeholder': 'Texto de la resolución'}),
        }
        labels = {
            'sim':    'Sumario',
            'pm':     'Personal Militar Implicado',
            'numero': 'Número de Resolución',
            'fecha':  'Fecha de Resolución',
            'tipo':   'Tipo de Resolución',
            'texto':  'Texto de la Resolución',
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.instancia = 'PRIMERA'
        if commit:
            obj.save()
        return obj


class NotificacionForm(forms.ModelForm):
    """Formulario unificado para registrar la notificación de cualquier documento."""

    class Meta:
        model = Notificacion
        fields = ['tipo', 'notificado_a', 'fecha', 'hora']
        widgets = {
            'fecha':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hora':         forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'notificado_a': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Persona / dirección notificada'}),
            'tipo':         forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'fecha':        'Fecha de Notificación',
            'hora':         'Hora de Notificación',
            'notificado_a': 'Notificado a (persona / dirección)',
            'tipo':         'Tipo de Notificación',
        }


# Alias por compatibilidad con imports existentes
RESNotificacionForm = NotificacionForm


class RAPForm(forms.ModelForm):

    class Meta:
        model = RecursoTSP
        fields = [
            'sim', 'pm', 'resolucion', 'fecha_presentacion', 'numero_oficio', 'fecha_oficio',
            'numero', 'fecha', 'texto', 'tipo'
        ]
        widgets = {
            'sim':                forms.Select(attrs={'class': 'form-control'}),
            'pm':                 forms.Select(attrs={'class': 'form-control'}),
            'resolucion':         forms.Select(attrs={'class': 'form-control'}),
            'fecha_presentacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_oficio':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de oficio'}),
            'fecha_oficio':       forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 03/26'}),
            'fecha':              forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'texto':              forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                       'placeholder': 'Texto del recurso'}),
            'tipo':               forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'sim':                'Sumario',
            'pm':                 'Personal Militar',
            'resolucion':         'Resolución RR impugnada (opcional)',
            'fecha_presentacion': 'Fecha de Presentación',
            'numero_oficio':      'Número de Oficio',
            'fecha_oficio':       'Fecha de Oficio',
            'numero':             'Número del RAP',
            'fecha':              'Fecha del RAP',
            'texto':              'Texto del RAP',
            'tipo':               'Tipo de RAP',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolucion'].queryset = Resolucion.objects.filter(instancia='RECONSIDERACION')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.instancia = 'APELACION'
        if commit:
            instance.save()
        return instance


class RAEEForm(forms.ModelForm):

    class Meta:
        model = RecursoTSP
        fields = ['sim', 'pm', 'recurso_origen', 'numero', 'fecha', 'texto']
        widgets = {
            'sim':           forms.Select(attrs={'class': 'form-control'}),
            'pm':            forms.Select(attrs={'class': 'form-control'}),
            'recurso_origen': forms.Select(attrs={'class': 'form-control'}),
            'numero':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 02/26'}),
            'fecha':         forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'texto':         forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                   'placeholder': 'Texto de la aclaración/enmienda'}),
        }
        labels = {
            'sim':           'Sumario',
            'pm':            'Personal Militar',
            'recurso_origen': 'Recurso de Apelación (RAP) origen',
            'numero':        'Número del RAEE',
            'fecha':         'Fecha del RAEE',
            'texto':         'Texto del RAEE',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recurso_origen'].queryset = RecursoTSP.objects.filter(instancia='APELACION')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.instancia = 'ACLARACION_ENMIENDA'
        if commit:
            instance.save()
        return instance


class AUTOTPEHistoricoForm(forms.ModelForm):

    class Meta:
        model = AUTOTPE
        fields = ['sim', 'pm', 'numero', 'fecha', 'tipo', 'texto']
        widgets = {
            'sim':    forms.Select(attrs={'class': 'form-control'}),
            'pm':     forms.Select(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04/26'}),
            'fecha':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo':   forms.Select(attrs={'class': 'form-control'}),
            'texto':  forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Texto del auto'}),
        }
        labels = {
            'sim':    'Sumario',
            'pm':     'Personal Militar',
            'numero': 'Número del Auto',
            'fecha':  'Fecha del Auto',
            'tipo':   'Tipo de Auto',
            'texto':  'Texto del Auto',
        }


class MemorandumForm(forms.ModelForm):
    """Registra el memorándum asociado a un Auto de Ejecutoria."""

    class Meta:
        model = Memorandum
        fields = ['numero', 'fecha']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° Memorándum'}),
            'fecha':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'numero': 'Número de Memorándum',
            'fecha':  'Fecha del Memorándum',
        }


class AutoEjecutoriaForm(forms.ModelForm):

    class Meta:
        model = AUTOTPE
        fields = ['numero', 'fecha', 'texto', 'abogado']
        widgets = {
            'numero':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 07/26'}),
            'fecha':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'texto':   forms.Textarea(attrs={'class': 'form-control', 'rows': 5,
                                             'placeholder': 'Texto del Auto de Ejecutoria...'}),
            'abogado': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'numero':  'Número del Auto',
            'fecha':   'Fecha del Auto',
            'texto':   'Texto del Auto de Ejecutoria',
            'abogado': 'Abogado',
        }


# Alias por compatibilidad con imports existentes
AUTOTPENotificacionForm = NotificacionForm


# ============================================================
# FORMULARIOS EXTENDIDOS CON NOTIFICACIÓN INTEGRADA (AYUDANTE)
# ============================================================

class ResolucionConNotificacionForm(forms.Form):
    """Formulario que incluye Resolución + Notificación opcional (para registro histórico)"""

    # Campos de Resolución
    sim = forms.ModelChoiceField(queryset=SIM.objects.all(),
                                 widget=forms.Select(attrs={'class': 'form-control'}),
                                 label='Sumario')
    pm = forms.ModelChoiceField(queryset=PM.objects.all(),
                                widget=forms.Select(attrs={'class': 'form-control'}),
                                label='Personal Militar Implicado')
    numero = forms.CharField(max_length=15,
                            widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 05/26'}),
                            label='Número de Resolución')
    fecha = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                           label='Fecha de Resolución')
    tipo = forms.ChoiceField(choices=Resolucion.TIPO_CHOICES,
                            widget=forms.Select(attrs={'class': 'form-control'}),
                            label='Tipo de Resolución')
    texto = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                         'placeholder': 'Texto de la resolución'}),
                           label='Texto de la Resolución')

    # Campos de Notificación (opcionales)
    notif_tipo = forms.ChoiceField(choices=[('', 'Sin notificación')] + list(Notificacion.NOTIF_CHOICES),
                                   widget=forms.Select(attrs={'class': 'form-control'}),
                                   required=False, label='Tipo de Notificación')
    notif_notificado_a = forms.CharField(max_length=100, required=False,
                                        widget=forms.TextInput(attrs={'class': 'form-control',
                                                                     'placeholder': 'Persona / dirección notificada'}),
                                        label='Notificado a')
    notif_fecha = forms.DateField(required=False,
                                 widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                                 label='Fecha de Notificación')
    notif_hora = forms.TimeField(required=False,
                                widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
                                label='Hora de Notificación')


class RAPConNotificacionForm(forms.Form):
    """Recurso de Apelación + Notificación opcional"""

    sim = forms.ModelChoiceField(queryset=SIM.objects.all(),
                                 widget=forms.Select(attrs={'class': 'form-control'}),
                                 label='Sumario')
    pm = forms.ModelChoiceField(queryset=PM.objects.all(),
                                widget=forms.Select(attrs={'class': 'form-control'}),
                                label='Personal Militar')
    resolucion = forms.ModelChoiceField(queryset=Resolucion.objects.filter(instancia='PRIMERA'),
                                       widget=forms.Select(attrs={'class': 'form-control'}),
                                       label='Resolución Recurrida')
    fecha_presentacion = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                                        label='Fecha de Presentación')
    numero_oficio = forms.CharField(max_length=30, required=False,
                                   widget=forms.TextInput(attrs={'class': 'form-control'}),
                                   label='Número de Oficio')
    fecha_oficio = forms.DateField(required=False,
                                  widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                                  label='Fecha de Oficio')
    numero = forms.CharField(max_length=15,
                            widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 03/26'}),
                            label='Número del RAP')
    fecha = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                           label='Fecha del RAP')
    texto = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
                           label='Texto del RAP')
    tipo = forms.ChoiceField(choices=RecursoTSP.TIPO_CHOICES,
                            widget=forms.Select(attrs={'class': 'form-control'}),
                            label='Tipo de RAP')

    # Notificación opcional
    notif_tipo = forms.ChoiceField(choices=[('', 'Sin notificación')] + list(Notificacion.NOTIF_CHOICES),
                                   widget=forms.Select(attrs={'class': 'form-control'}),
                                   required=False, label='Tipo de Notificación')
    notif_notificado_a = forms.CharField(max_length=100, required=False,
                                        widget=forms.TextInput(attrs={'class': 'form-control'}),
                                        label='Notificado a')
    notif_fecha = forms.DateField(required=False,
                                 widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                                 label='Fecha de Notificación')
    notif_hora = forms.TimeField(required=False,
                                widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
                                label='Hora de Notificación')


class AUTOTPEHistoricoConNotificacionForm(forms.Form):
    """Auto TPE + Notificación + Memorándum opcionales"""

    sim = forms.ModelChoiceField(queryset=SIM.objects.all(),
                                 widget=forms.Select(attrs={'class': 'form-control'}),
                                 label='Sumario')
    pm = forms.ModelChoiceField(queryset=PM.objects.all(),
                                widget=forms.Select(attrs={'class': 'form-control'}),
                                label='Personal Militar')
    numero = forms.CharField(max_length=15,
                            widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04/26'}),
                            label='Número del Auto')
    fecha = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                           label='Fecha del Auto')
    tipo = forms.ChoiceField(choices=AUTOTPE.TIPO_CHOICES,
                            widget=forms.Select(attrs={'class': 'form-control'}),
                            label='Tipo de Auto')
    texto = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
                           label='Texto del Auto')

    # Notificación opcional
    notif_tipo = forms.ChoiceField(choices=[('', 'Sin notificación')] + list(Notificacion.NOTIF_CHOICES),
                                   widget=forms.Select(attrs={'class': 'form-control'}),
                                   required=False, label='Tipo de Notificación')
    notif_notificado_a = forms.CharField(max_length=100, required=False,
                                        widget=forms.TextInput(attrs={'class': 'form-control'}),
                                        label='Notificado a')
    notif_fecha = forms.DateField(required=False,
                                 widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                                 label='Fecha de Notificación')
    notif_hora = forms.TimeField(required=False,
                                widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
                                label='Hora de Notificación')

    # Memorándum (solo para AUTOTPE tipo EJECUTORIA)
    memo_numero = forms.CharField(max_length=60, required=False,
                                 widget=forms.TextInput(attrs={'class': 'form-control'}),
                                 label='Número de Memorándum (si ejecutoria)')
    memo_fecha = forms.DateField(required=False,
                                widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
                                label='Fecha del Memorándum')


# ============================================================
# FORMULARIOS WIZARD AYUDANTE
# ============================================================

class WizardSIMForm(SIMForm):
    codigo = forms.CharField(
        label='Código del Sumario', max_length=25, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ejemplo: DJE-123/25, SASJUR-25/25, SDISCAPE-86/25',
            'autocomplete': 'off', 'spellcheck': 'false'
        })
    )
    objeto = forms.CharField(
        label='Objeto del Sumario', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
            'placeholder': 'Establecer las circunstancias que motivaron...'})
    )
    resumen = forms.CharField(
        label='Resumen', max_length=200, required=False,
        widget=ResumenConOpcionesWidget(opciones=RESUMEN_CHOICES),
    )
    tipo = forms.ChoiceField(
        label='Tipo de Sumario', required=False,
        choices=[('', '---------')] + list(SIM.TIPO_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    fase = forms.ChoiceField(
        choices=[('', '---------')] + list(SIM.FASE_CHOICES),
        required=False, label='Fase del Sumario',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Seleccione la fase en que quedó este sumario histórico'
    )

    class Meta(SIMForm.Meta):
        fields = SIMForm.Meta.fields + ['fase']

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.objeto:   obj.objeto = ''
        if not obj.resumen:  obj.resumen = ''
        if not obj.tipo:     obj.tipo = 'DISCIPLINARIO'
        fase = self.cleaned_data.get('fase')
        if fase:
            obj.fase = fase
        if commit:
            obj.save()
        return obj


class WizardRESForm(RESForm):
    numero = forms.CharField(
        label='Número de Resolución', max_length=10, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 05/26 (opcional)'})
    )

    class Meta(RESForm.Meta):
        fields = ['pm', 'numero', 'fecha', 'tipo', 'texto']

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.instancia = 'PRIMERA'
        if commit:
            obj.save()
        return obj


class WizardRRForm(forms.ModelForm):
    numero = forms.CharField(
        label='Número de RR', max_length=10, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 07/24 (opcional)'})
    )

    class Meta:
        model = Resolucion
        fields = ['numero', 'fecha', 'texto', 'tipo', 'fecha_presentacion']
        widgets = {
            'numero':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 07/24 (opcional)'}),
            'fecha':              forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'texto':              forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'tipo':               forms.Select(attrs={'class': 'form-control'}),
            'fecha_presentacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'numero':             'Número del RR',
            'fecha':              'Fecha del RR',
            'texto':              'Texto del RR',
            'tipo':               'Resultado (PROCEDENCIA/IMPROCEDENCIA)',
            'fecha_presentacion': 'Fecha de Presentación del Recurso',
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.instancia = 'RECONSIDERACION'
        if commit:
            obj.save()
        return obj


class WizardAUTOTPEForm(AUTOTPEHistoricoForm):

    class Meta(AUTOTPEHistoricoForm.Meta):
        fields = ['pm', 'numero', 'fecha', 'tipo', 'texto']


class WizardRAPForm(RAPForm):

    class Meta(RAPForm.Meta):
        fields = ['pm', 'resolucion', 'fecha_presentacion', 'numero_oficio', 'fecha_oficio', 'numero', 'fecha', 'tipo', 'texto']

    def __init__(self, *args, sim=None, **kwargs):
        super().__init__(*args, **kwargs)
        if sim:
            self.fields['pm'].queryset = sim.militares.all()
            self.fields['resolucion'].queryset = Resolucion.objects.filter(sim=sim, instancia='RECONSIDERACION')

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.instancia = 'APELACION'
        if commit:
            obj.save()
        return obj


class WizardRAEEForm(RAEEForm):

    class Meta(RAEEForm.Meta):
        fields = ['pm', 'recurso_origen', 'numero', 'fecha', 'texto']

    def __init__(self, *args, sim=None, **kwargs):
        super().__init__(*args, **kwargs)
        if sim:
            self.fields['pm'].queryset = sim.militares.all()
            self.fields['recurso_origen'].queryset = RecursoTSP.objects.filter(sim=sim, instancia='APELACION')

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.instancia = 'ACLARACION_ENMIENDA'
        if commit:
            obj.save()
        return obj


class WizardAUTOTSPForm(forms.ModelForm):
    class Meta:
        model = AUTOTSP
        fields = ['numero', 'fecha', 'tipo', 'texto']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 03/24'}),
            'fecha':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tipo':   forms.Select(attrs={'class': 'form-control'}),
            'texto':  forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
        labels = {
            'numero': 'Número del Auto TSP',
            'fecha':  'Fecha del Auto TSP',
            'tipo':   'Tipo de Auto TSP',
            'texto':  'Texto del Auto TSP',
        }

    def __init__(self, *args, sim=None, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].required = False
