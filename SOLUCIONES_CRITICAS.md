# 🔧 SOLUCIONES PARA PROBLEMAS CRÍTICOS
## Sistema TPE v4.0 — Código Específico para Remediación

---

## 1. SOLUCIÓN: Campos Deprecated en import_actuados_historicos.py

**Archivo:** `tpe_app/management/commands/import_actuados_historicos.py`  
**Problema:** Intenta asignar `tipo_notif`, `notif_a`, `fecha_notif`, `hora_notif` que no existen en los modelos.

### Código Corregido para Resoluciones:

```python
def _importar_resoluciones(self, xls):
    """Importa Resoluciones (1RA y RR)."""
    self.stdout.write('4️⃣  Importando Resoluciones...')

    df = pd.read_excel(xls, sheet_name='4_Resoluciones')
    df = df.dropna(how='all')

    for idx, row in df.iterrows():
        try:
            sim = SIM.objects.get(id=int(row['sim_id']))
            pm = PM.objects.get(ci=str(row['pm_ci']).strip())

            numero = str(row['numero']).strip() if pd.notna(row['numero']) else ''
            instancia = str(row['instancia']).strip() if pd.notna(row['instancia']) else 'PRIMERA'

            # Primero: Crear o actualizar Resolucion SIN campos de notificación
            defaults = {
                'sim': sim,
                'pm': pm,
                'numero': numero,
                'instancia': instancia,
                'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                'fecha': pd.to_datetime(row['fecha']).date() if pd.notna(row['fecha']) else None,
                'fecha_presentacion': pd.to_datetime(row['fecha_presentacion']).date() if pd.notna(row['fecha_presentacion']) else None,
                'fecha_limite': pd.to_datetime(row['fecha_limite']).date() if pd.notna(row['fecha_limite']) else None,
                'texto': str(row['texto']).strip().upper() if pd.notna(row['texto']) else '',
            }

            resolucion, _ = Resolucion.objects.update_or_create(
                numero=numero,
                instancia=instancia,
                defaults=defaults
            )

            # Segundo: Crear Notificacion SEPARADAMENTE si hay datos
            if pd.notna(row.get('tipo_notif')) or pd.notna(row.get('fecha_notif')):
                from tpe_app.models import Notificacion
                
                notif_tipo = str(row['tipo_notif']).strip() if pd.notna(row['tipo_notif']) else 'FIRMA'
                # Validar que el tipo sea válido
                valid_tipos = ['FIRMA', 'EDICTO', 'CEDULON']
                if notif_tipo not in valid_tipos:
                    notif_tipo = 'FIRMA'
                
                notif_fecha = pd.to_datetime(row['fecha_notif']).date() if pd.notna(row['fecha_notif']) else None
                notif_a = str(row['notif_a']).strip() if pd.notna(row['notif_a']) else ''
                
                # Nota: hora_notif se ignora (no existe en modelo Notificacion actual)
                
                Notificacion.objects.update_or_create(
                    resolucion=resolucion,
                    defaults={
                        'tipo': notif_tipo,
                        'notificado_a': notif_a,
                        'fecha': notif_fecha,
                        'hora': None,  # Si en futuro se requiere, agregar campo TimeField
                    }
                )

        except (SIM.DoesNotExist, PM.DoesNotExist) as e:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

    self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Resoluciones importadas'))
```

### Código Corregido para Autos TPE:

```python
def _importar_autos_tpe(self, xls):
    """Importa Autos TPE."""
    self.stdout.write('5️⃣  Importando Autos TPE...')

    df = pd.read_excel(xls, sheet_name='5_Autos_TPE')
    df = df.dropna(how='all')

    for idx, row in df.iterrows():
        try:
            sim = SIM.objects.get(id=int(row['sim_id']))
            pm = PM.objects.get(ci=str(row['pm_ci']).strip())

            numero_auto = str(row['numero']).strip() if pd.notna(row['numero']) else ''

            # Crear/actualizar Auto TPE SIN campos de notificación
            autotpe, _ = AUTOTPE.objects.update_or_create(
                sim=sim,
                pm=pm,
                numero=numero_auto,
                defaults={
                    'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                    'fecha': pd.to_datetime(row['fecha']).date() if pd.notna(row['fecha']) else None,
                    'texto': str(row['texto']).strip().upper() if pd.notna(row['texto']) else '',
                    'memo_numero': str(row['memo_numero']).strip() if pd.notna(row['memo_numero']) else '',
                    'memo_fecha': pd.to_datetime(row['memo_fecha']).date() if pd.notna(row['memo_fecha']) else None,
                    'memo_fecha_entrega': pd.to_datetime(row['memo_fecha_entrega']).date() if pd.notna(row['memo_fecha_entrega']) else None,
                }
            )

            # Crear Notificacion por separado
            if pd.notna(row.get('tipo_notif')) or pd.notna(row.get('fecha_notif')):
                from tpe_app.models import Notificacion
                
                notif_tipo = str(row['tipo_notif']).strip() if pd.notna(row['tipo_notif']) else 'FIRMA'
                valid_tipos = ['FIRMA', 'EDICTO', 'CEDULON']
                if notif_tipo not in valid_tipos:
                    notif_tipo = 'FIRMA'
                
                Notificacion.objects.update_or_create(
                    autotpe=autotpe,
                    defaults={
                        'tipo': notif_tipo,
                        'notificado_a': str(row['notif_a']).strip() if pd.notna(row['notif_a']) else '',
                        'fecha': pd.to_datetime(row['fecha_notif']).date() if pd.notna(row['fecha_notif']) else None,
                        'hora': None,
                    }
                )

        except (SIM.DoesNotExist, PM.DoesNotExist) as e:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

    self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Autos TPE importados'))
```

### Código Corregido para Recursos TSP:

```python
def _importar_recursos_tsp(self, xls):
    """Importa Recursos TSP (RAP y RAEE)."""
    self.stdout.write('6️⃣  Importando Recursos TSP...')

    df = pd.read_excel(xls, sheet_name='6_Recursos_TSP')
    df = df.dropna(how='all')

    for idx, row in df.iterrows():
        try:
            sim = SIM.objects.get(id=int(row['sim_id']))
            pm = PM.objects.get(ci=str(row['pm_ci']).strip())

            numero_oficio = str(row['numero_oficio']).strip() if pd.notna(row['numero_oficio']) else ''

            # Crear/actualizar Recurso TSP SIN campos de notificación
            recurso, _ = RecursoTSP.objects.update_or_create(
                sim=sim,
                pm=pm,
                numero_oficio=numero_oficio,
                defaults={
                    'instancia': str(row['instancia']).strip() if pd.notna(row['instancia']) else 'APELACION',
                    'fecha_oficio': pd.to_datetime(row['fecha_oficio']).date() if pd.notna(row['fecha_oficio']) else None,
                    'fecha_presentacion': pd.to_datetime(row['fecha_presentacion']).date() if pd.notna(row['fecha_presentacion']) else None,
                    'fecha_limite': pd.to_datetime(row['fecha_limite']).date() if pd.notna(row['fecha_limite']) else None,
                    'tipo': str(row['tipo']).strip().upper() if pd.notna(row['tipo']) else '',
                    'numero': str(row['numero']).strip() if pd.notna(row['numero']) else '',
                    'fecha': pd.to_datetime(row['fecha']).date() if pd.notna(row['fecha']) else None,
                    'texto': str(row['texto']).strip().upper() if pd.notna(row['texto']) else '',
                }
            )

            # Crear Notificacion por separado
            if pd.notna(row.get('tipo_notif')) or pd.notna(row.get('fecha_notif')):
                from tpe_app.models import Notificacion
                
                notif_tipo = str(row['tipo_notif']).strip() if pd.notna(row['tipo_notif']) else 'FIRMA'
                valid_tipos = ['FIRMA', 'EDICTO', 'CEDULON']
                if notif_tipo not in valid_tipos:
                    notif_tipo = 'FIRMA'
                
                Notificacion.objects.update_or_create(
                    recurso_tsp=recurso,
                    defaults={
                        'tipo': notif_tipo,
                        'notificado_a': str(row['notif_a']).strip() if pd.notna(row['notif_a']) else '',
                        'fecha': pd.to_datetime(row['fecha_notif']).date() if pd.notna(row['fecha_notif']) else None,
                        'hora': None,
                    }
                )

        except (SIM.DoesNotExist, PM.DoesNotExist) as e:
            self.stdout.write(self.style.WARNING(f'  ⚠️  Fila {idx + 2}: {e}'))

    self.stdout.write(self.style.SUCCESS(f'   ✓ {len(df)} Recursos TSP importados'))
```

---

## 2. SOLUCIÓN: Cambiar CASCADE → PROTECT en Modelos

**Archivo:** `tpe_app/models.py`

### Migración Django:

```python
# tpe_app/migrations/0007_fix_on_delete_cascade.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('tpe_app', '0006_memorandum_add_resolucion_fk'),
    ]

    operations = [
        # 1. DocumentoAdjunto: Cambiar CASCADE → PROTECT
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='sim',
            field=models.ForeignKey('SIM', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Sumario SIM'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='resolucion',
            field=models.ForeignKey('Resolucion', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Resolución'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='autotpe',
            field=models.ForeignKey('AUTOTPE', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Auto TPE'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='autotsp',
            field=models.ForeignKey('AUTOTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Auto TSP'),
        ),
        migrations.AlterField(
            model_name='documentoAdjunto',
            name='recurso_tsp',
            field=models.ForeignKey('RecursoTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='documentos', verbose_name='Recurso TSP'),
        ),

        # 2. Memorandum: Cambiar CASCADE → PROTECT
        migrations.AlterField(
            model_name='Memorandum',
            name='resolucion',
            field=models.ForeignKey('Resolucion', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='memorandums', verbose_name='Resolución vinculada'),
        ),
        migrations.AlterField(
            model_name='Memorandum',
            name='autotpe',
            field=models.ForeignKey('AUTOTPE', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='memorandums', verbose_name='Auto TPE vinculado'),
        ),

        # 3. Notificacion: Cambiar CASCADE → PROTECT (o SET_NULL si prefieres)
        migrations.AlterField(
            model_name='Notificacion',
            name='resolucion',
            field=models.OneToOneField('Resolucion', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Resolución'),
        ),
        migrations.AlterField(
            model_name='Notificacion',
            name='autotpe',
            field=models.OneToOneField('AUTOTPE', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Auto TPE'),
        ),
        migrations.AlterField(
            model_name='Notificacion',
            name='autotsp',
            field=models.OneToOneField('AUTOTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Auto TSP'),
        ),
        migrations.AlterField(
            model_name='Notificacion',
            name='recurso_tsp',
            field=models.OneToOneField('RecursoTSP', null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='notificacion', verbose_name='Recurso TSP'),
        ),

        # 4. RecursoTSP.recurso_origen: CASCADE → PROTECT
        migrations.AlterField(
            model_name='RecursoTSP',
            name='recurso_origen',
            field=models.ForeignKey('self', on_delete=django.db.models.deletion.PROTECT, null=True, blank=True, related_name='aclaraciones', verbose_name='Recurso origen (solo ACLARACION_ENMIENDA)'),
        ),

        # 5. PM_SIM: Validar y normalizar (si es necesario)
        # En este caso, el cambio es más complejo porque requiere migración de datos
        # Ver solución 3 abajo
    ]
```

### Modificar models.py directamente:

```python
# En tpe_app/models.py, actualizar:

class DocumentoAdjunto(models.Model):
    # ...
    sim         = models.ForeignKey('SIM', null=True, blank=True, on_delete=models.PROTECT, ...)
    resolucion  = models.ForeignKey('Resolucion', null=True, blank=True, on_delete=models.PROTECT, ...)
    autotpe     = models.ForeignKey('AUTOTPE', null=True, blank=True, on_delete=models.PROTECT, ...)
    autotsp     = models.ForeignKey('AUTOTSP', null=True, blank=True, on_delete=models.PROTECT, ...)
    recurso_tsp = models.ForeignKey('RecursoTSP', null=True, blank=True, on_delete=models.PROTECT, ...)

class Memorandum(models.Model):
    # ...
    resolucion = models.ForeignKey('Resolucion', on_delete=models.PROTECT, ...)
    autotpe    = models.ForeignKey('AUTOTPE', on_delete=models.PROTECT, ...)

class Notificacion(models.Model):
    # ...
    resolucion  = models.OneToOneField('Resolucion', on_delete=models.PROTECT, ...)
    autotpe     = models.OneToOneField('AUTOTPE', on_delete=models.PROTECT, ...)
    autotsp     = models.OneToOneField('AUTOTSP', on_delete=models.PROTECT, ...)
    recurso_tsp = models.OneToOneField('RecursoTSP', on_delete=models.PROTECT, ...)

class RecursoTSP(models.Model):
    # ...
    recurso_origen = models.ForeignKey('self', on_delete=models.PROTECT, ...)
```

---

## 3. SOLUCIÓN: Corregir PerfilUsuario.DoesNotExist

**Archivo:** `tpe_app/views/abogado_views.py` (y similares en otras vistas)

### Antes (línea 12):
```python
perfil = request.user.perfilusuario  # ⚠️ Crash si no existe
```

### Después:
```python
try:
    perfil = request.user.perfilusuario
except PerfilUsuario.DoesNotExist:
    context = {'error': 'Tu usuario no tiene un perfil asignado. Contacta al administrador.'}
    return render(request, 'tpe_app/error.html', context)
```

**O mejor aún, en el decorador:**

```python
# tpe_app/decorators.py
def rol_requerido(*roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            from tpe_app.models import PerfilUsuario

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                perfil = PerfilUsuario.objects.get(user=request.user)
                if perfil.rol == 'MASTER':
                    if not perfil.activo:
                        raise PermissionDenied("Tu cuenta está desactivada")
                    return view_func(request, *args, **kwargs)
                if perfil.rol not in roles_permitidos:
                    raise PermissionDenied(
                        f"Tu rol ({perfil.get_rol_display()}) no tiene acceso a esta página. "
                        f"Se requiere uno de: {', '.join(roles_permitidos)}"
                    )
                if not perfil.activo:
                    raise PermissionDenied("Tu cuenta está desactivada")
                return view_func(request, *args, **kwargs)
            except PerfilUsuario.DoesNotExist:
                raise PermissionDenied(
                    "Tu usuario no tiene un perfil asignado. Contacta al administrador del sistema."
                )
            except AttributeError:
                raise PermissionDenied("Error en la configuración del usuario")
        return wrapper
    return decorator
```

---

## 4. SOLUCIÓN: Validaciones en Models

**Archivo:** `tpe_app/models.py`

### Validación para Resolucion (evitar RR→RR):

```python
class Resolucion(models.Model):
    # ... campos existentes ...

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validación 1: RR solo puede apuntar a PRIMERA
        if self.instancia == 'RECONSIDERACION' and self.resolucion_origen:
            if self.resolucion_origen.instancia != 'PRIMERA':
                raise ValidationError({
                    'resolucion_origen': 'Un Recurso de Reconsideración solo puede apuntar a una Resolución PRIMERA.'
                })
        
        # Validación 2: PRIMERA no debe tener resolucion_origen
        if self.instancia == 'PRIMERA' and self.resolucion_origen:
            raise ValidationError({
                'resolucion_origen': 'Una Resolución PRIMERA no puede tener resolución de origen.'
            })

    def save(self, *args, **kwargs):
        self.clean()  # Ejecutar validaciones
        if self.instancia == 'RECONSIDERACION' and self.fecha_presentacion and not self.fecha_limite:
            self.fecha_limite = add_business_days(self.fecha_presentacion, 15)
        self.numero = self.numero.upper() if self.numero else self.numero
        self.texto = self.texto.upper() if self.texto else self.texto
        super().save(*args, **kwargs)
```

### Validación para Memorandum (evitar memorandums huérfanos):

```python
class Memorandum(models.Model):
    # ... campos existentes ...

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Exactamente uno debe ser no-nulo
        vinculados = sum([
            bool(self.resolucion_id),
            bool(self.autotpe_id),
        ])
        if vinculados != 1:
            raise ValidationError(
                f'Memorandum debe estar vinculado a exactamente un documento '
                f'(resolucion o autotpe). Actualmente: {vinculados}.'
            )

    def save(self, *args, **kwargs):
        self.clean()
        self.numero = self.numero.upper() if self.numero else self.numero
        super().save(*args, **kwargs)
```

### Validación para CustodiaSIM:

```python
class CustodiaSIM(models.Model):
    # ... campos existentes ...

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validación: Si estado es PENDIENTE_CONFIRMACION, debe haber un abogado destino
        if self.estado == 'PENDIENTE_CONFIRMACION' and not self.abogado_destino:
            raise ValidationError({
                'abogado_destino': 'El abogado destino es obligatorio cuando la custodia está pendiente de confirmación.'
            })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
```

---

## 5. SOLUCIÓN: Agregar Índices Faltantes

**Archivo:** `tpe_app/models.py` o migración

### En models.py:

```python
class Resolucion(models.Model):
    # ... campos ...
    class Meta:
        db_table = 'resolucion'
        verbose_name = 'Resolución'
        verbose_name_plural = 'Resoluciones'
        ordering = ['-fecha']
        unique_together = [('numero', 'instancia')]
        indexes = [
            models.Index(fields=['instancia']),  # ← AGREGAR
            models.Index(fields=['sim', 'instancia']),  # ← AGREGAR
            models.Index(fields=['fecha']),  # ← AGREGAR
        ]

class RecursoTSP(models.Model):
    # ... campos ...
    class Meta:
        db_table = 'recurso_tsp'
        verbose_name = 'Recurso TSP'
        verbose_name_plural = 'Recursos TSP'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['instancia']),  # ← AGREGAR
            models.Index(fields=['sim', 'instancia']),  # ← AGREGAR
            models.Index(fields=['fecha']),  # ← AGREGAR
        ]

class AUTOTPE(models.Model):
    # ... campos ...
    class Meta:
        db_table = 'autotpe'
        verbose_name = 'Auto TPE'
        verbose_name_plural = 'Autos TPE'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['tipo']),  # ← AGREGAR
            models.Index(fields=['sim', 'tipo']),  # ← AGREGAR
            models.Index(fields=['fecha']),  # ← AGREGAR
        ]
```

### Crear migración:

```bash
python manage.py makemigrations --name add_indexes_for_performance
python manage.py migrate
```

---

## 6. SOLUCIÓN: Actualizar MAX_LENGTH en Forms

**Archivo:** `tpe_app/forms.py`

### Antes (líneas 131-141):
```python
nombre = forms.CharField(
    label='Nombre', max_length=25, ...  # ❌ Antiguo (modelo tiene 50)
)
paterno = forms.CharField(
    label='Apellido Paterno', max_length=25, ...  # ❌ Antiguo
)
materno = forms.CharField(
    label='Apellido Materno', max_length=25, ...  # ❌ Antiguo
)
```

### Después:
```python
nombre = forms.CharField(
    label='Nombre', max_length=50, ...  # ✅ Sincronizado con modelo
)
paterno = forms.CharField(
    label='Apellido Paterno', max_length=50, ...  # ✅ Sincronizado
)
materno = forms.CharField(
    label='Apellido Materno', max_length=50, ...  # ✅ Sincronizado
)
```

---

## Plan de Implementación

1. **Crear migración** para cambios de `on_delete` (solución 2)
2. **Actualizar import_actuados_historicos.py** (solución 1)
3. **Mejorar decorador** en decorators.py (solución 3)
4. **Agregar validaciones** en models.py (solución 4)
5. **Agregar índices** (solución 5)
6. **Actualizar forms.py** (solución 6)
7. **Testear** con datos históricos

---

## Testing

```bash
# 1. Verificar que no hay campos sin manejo en import
python manage.py import_actuados_historicos --file plantilla_test.xlsx

# 2. Verificar validaciones
python manage.py shell
>>> from tpe_app.models import Resolucion, Memorandum
>>> # Intentar crear RR→RR (debe fallar)
>>> # Intentar crear Memorandum huérfano (debe fallar)

# 3. Verificar que PROTECT funciona
>>> from tpe_app.models import SIM
>>> sim = SIM.objects.first()
>>> sim.delete()  # Debe fallar si hay documentos adjuntos
```

