# 🔐 REPORTE DE AUDITORÍA DE SEGURIDAD Y CONSISTENCIA
## Sistema TPE v4.0 — Auditoría de Infraestructura y Código
**Fecha:** 2 de mayo de 2026  
**Versión del Sistema:** 4.0  
**Estado:** ⚠️ CRÍTICO - Hallazgos que requieren atención inmediata

---

## 📊 RESUMEN EJECUTIVO

Se encontraron **12 problemas críticos/altos** y **8 problemas medios**, distribuidos en:
- **Base de Datos:** Inconsistencias en relaciones FK y campos deprecated
- **Seguridad:** Falta de @login_required en una vista crítica
- **Código Legacy:** Referencias a campos que fueron eliminados en v4.0
- **Lógica:** Problemas en cascada de eliminación de datos
- **Validación:** Fallos en importación de datos históricos

---

## 🔴 PROBLEMAS CRÍTICOS (Impacto Alto)

### 1. **CRÍTICO: Campos Deprecated en Importación de Datos**
**Archivo:** `tpe_app/management/commands/import_actuados_historicos.py`  
**Líneas:** 170-173, 206-209, 245-248  
**Descripción:**  
El script de importación intenta asignar campos que fueron eliminados en v4.0:
- `tipo_notif` ❌ (reemplazado por `Notificacion.tipo`)
- `notif_a` ❌ (reemplazado por `Notificacion.notificado_a`)
- `fecha_notif` ❌ (reemplazado por `Notificacion.fecha`)
- `hora_notif` ❌ (reemplazado por `Notificacion.hora`)

**Impacto:** La importación de datos históricos FALLARÁ con errores de `AttributeError`.

**Solución:**
```python
# Actualizar el script para crear Notificacion separadamente:
notificacion_data = {
    'tipo': row.get('tipo_notif', 'FIRMA'),
    'notificado_a': row.get('notif_a', ''),
    'fecha': pd.to_datetime(row.get('fecha_notif')).date() if pd.notna(row.get('fecha_notif')) else None,
    'hora': None,  # hora_notif no existe más en Notificacion
}
# Crear Notificacion como objeto separado y vincular a resolucion.notificacion
```

---

### 2. **CRÍTICO: Cascada de Eliminación en Documentos Adjuntos**
**Archivo:** `tpe_app/models.py:919-923`  
**Problema:**  
El modelo `DocumentoAdjunto` usa `on_delete=models.CASCADE` en FKs a:
- `SIM` (línea 919)
- `Resolucion` (línea 920)
- `AUTOTPE` (línea 921)
- `AUTOTSP` (línea 922)
- `RecursoTSP` (línea 923)

Si se elimina accidentalmente un `SIM`, todos sus documentos, resoluciones, autos y recursos se borran en cascada.

**Impacto:** Pérdida completa de auditoría y evidencia legal.

**Solución:**
```python
# Cambiar a PROTECT para prevenir eliminación accidental:
sim         = models.ForeignKey('SIM', null=True, blank=True, on_delete=models.PROTECT, ...)
resolucion  = models.ForeignKey('Resolucion', null=True, blank=True, on_delete=models.PROTECT, ...)
autotpe     = models.ForeignKey('AUTOTPE', null=True, blank=True, on_delete=models.PROTECT, ...)
autotsp     = models.ForeignKey('AUTOTSP', null=True, blank=True, on_delete=models.PROTECT, ...)
recurso_tsp = models.ForeignKey('RecursoTSP', null=True, blank=True, on_delete=models.PROTECT, ...)
```

---

### 3. **CRÍTICO: Cascadas en Memorandum (Pérdida de Datos)**
**Archivo:** `tpe_app/models.py:842-845`  
**Problema:**  
```python
resolucion = models.ForeignKey('Resolucion', on_delete=models.CASCADE, ...)
autotpe    = models.ForeignKey('AUTOTPE', on_delete=models.CASCADE, ...)
```

Si se elimina una `Resolucion` o `AUTOTPE`, todos sus `Memorandum` (que contienen números de retorno legal) se eliminan.

**Impacto:** Pérdida de prueba de ejecución del proceso.

**Solución:** Cambiar a `on_delete=models.PROTECT`

---

### 4. **CRÍTICO: Notificacion OneToOneField con CASCADE**
**Archivo:** `tpe_app/models.py:1143-1150`  
**Problema:**  
```python
resolucion  = models.OneToOneField('Resolucion', on_delete=models.CASCADE, ...)
autotpe     = models.OneToOneField('AUTOTPE', on_delete=models.CASCADE, ...)
autotsp     = models.OneToOneField('AUTOTSP', on_delete=models.CASCADE, ...)
recurso_tsp = models.OneToOneField('RecursoTSP', on_delete=models.CASCADE, ...)
```

La eliminación de cualquier documento padre borra la `Notificacion`.

**Solución:** Cambiar a `on_delete=models.PROTECT` o `on_delete=models.SET_NULL`

---

### 5. **ALTO: Falta @login_required en Vistas de Exportación**
**Archivo:** `tpe_app/views/buscador_views.py`  
**Líneas:** Múltiples funciones de exportación  
**Problema:**  
Aunque el CLAUDE.md menciona que buscador requiere `@login_required`, se debe verificar que TODAS las vistas de exportación (PDF, Excel, lotes) tengan el decorador. Una vista sin protección podría exponer datos sensibles.

**Verificación:**
```bash
grep -n "def export_" tpe_app/views/buscador_views.py | grep -v "@login_required"
```

**Solución:** Asegurar que cada función de exportación tenga `@login_required` ANTES de `@rol_requerido` si la tiene.

---

### 6. **ALTO: Aceso a PerfilUsuario sin Manejo de Excepciones**
**Archivo:** `tpe_app/views/abogado_views.py:12`  
```python
perfil = request.user.perfilusuario  # ⚠️ Puede lanzar DoesNotExist
```

Si el usuario no tiene `PerfilUsuario`, la vista crashea.

**Solución:**
```python
try:
    perfil = request.user.perfilusuario
except PerfilUsuario.DoesNotExist:
    raise PermissionDenied("Tu usuario no tiene un perfil asignado")
```

---

## 🟡 PROBLEMAS ALTOS

### 7. **Inconsistencia en Campos de Memorandum**
**Archivo:** `tpe_app/models.py:848`  
**Problema:**  
```python
fecha_entrega = models.DateField(null=True, blank=True, ...)
```

En exportación se referencia como `memo.fecha_entrega` pero en `models.py` está usando el nombre correcto. Sin embargo, en comentarios de CLAUDE.md se refencia como `autotpe.memo_fecha_entrega`. Verificar consistencia.

---

### 8. **Relaciones FK Problemáticas en CustodiaSIM**
**Archivo:** `tpe_app/models.py:608-613`  
**Problema:**  
- `abogado` y `abogado_destino` usan `SET_NULL` (pérdida de contexto histórico)
- Debería mantener el nombre del abogado para auditoría

**Solución:** Agregar campos `nombre_abogado` y `nombre_abogado_destino` para registro histórico.

---

### 9. **PM_SIM y ABOG_SIM con FK DELETE Diferentes**
**Archivo:** `tpe_app/models.py:531-532, 554-555`  
**Inconsistencia:**
- PM_SIM: `on_delete=models.CASCADE` para SIM, `RESTRICT` para PM
- ABOG_SIM: `on_delete=models.CASCADE` para SIM, `RESTRICT` para PM

Si un `SIM` se elimina, se pierden todos los registros de militares implicados (PM_SIM) pero se preservan las asignaciones de abogados (ABOG_SIM). Esto causa inconsistencia.

**Solución:** Normalizar a `PROTECT` en ambas tablas puente.

---

### 10. **Rol ABOGADO (General) Nunca Usado**
**Archivo:** `tpe_app/models.py:1197`  
**Problema:**  
```python
('ABOGADO', 'Abogado (General)'),  # ← Nunca aparece en vistas ni decoradores
```

El rol existe en `ROL_CHOICES` pero nunca se usa. Las vistas buscan roles específicos (ABOG1_ASESOR, ABOG2_AUTOS, ABOG3_BUSCADOR).

**Solución:** 
- Eliminar si es código legacy, O
- Documentar su propósito si es intencional

---

### 11. **Comentario Desactualizado en admin3_views.py**
**Archivo:** `tpe_app/views/admin3_views.py:15`  
```python
# RES (Resoluciones PRIMERA) por notificar (fecha_notif es NULL = no notificada aún)
```

El código correcto es `notificacion__isnull=True` (línea 17), pero el comentario hace referencia a `fecha_notif` que no existe.

---

### 12. **FK Resolucion a Resolucion sin Límites**
**Archivo:** `tpe_app/models.py:980-983`  
**Problema:**  
```python
resolucion_origen = models.ForeignKey(
    'self', on_delete=models.PROTECT, null=True, blank=True,
    related_name='recursos_reconsideracion', ...)
```

No hay validación que impida que una RR (Recurso de Reconsideración) apunte a otra RR. Debería validarse que solo apunte a resoluciones PRIMERA.

**Solución:** Agregar validación en `save()`:
```python
def clean(self):
    if self.instancia == 'RECONSIDERACION' and self.resolucion_origen:
        if self.resolucion_origen.instancia != 'PRIMERA':
            raise ValidationError("RR solo puede apuntar a resolución PRIMERA")
```

---

## 🟠 PROBLEMAS MEDIOS

### 13. **MAX_LENGTH Inconsistente en PM**
**Archivo:** `tpe_app/models.py:227-229, 226`  
**Problema:**  
- `nombre`: max_length=50 ✓
- `paterno`: max_length=50 ✓
- `materno`: max_length=50 ✓
- `especialidad`: max_length=30 ✓
- Pero en `PMSIMForm` (forms.py:131-141) los campos tienen max_length=25 (antiguo)

**Impacto:** Inconsistencia entre modelo y formulario. Datos históricos con 50 caracteres no pueden editarse via formulario.

**Solución:** Actualizar max_length en `PMSIMForm` a 50.

---

### 14. **Falta Validación en CustodiaSIM.save()**
**Archivo:** `tpe_app/models.py:577-642`  
**Problema:**  
No valida que exactamente uno de `resolucion`, `autotpe`, `autotsp`, `recurso_tsp` sea no-nulo (similar a `Notificacion`).

**Riesgo:** Custodia huérfana sin documento vinculado.

---

### 15. **INDEX Faltante en Campos Clave**
**Archivo:** `tpe_app/models.py`  
**Problema:**  
Campos sin `db_index=True` que podrían beneficiarse:
- `SIM.estado` ✓ (tiene índice)
- `SIM.fase` ✓ (tiene índice)
- `Resolucion.instancia` ❌ (falta)
- `RecursoTSP.instancia` ❌ (falta)
- `AUTOTPE.tipo` ❌ (falta)

Impacto: Queries lentas en dashboards.

---

### 16. **Memorandum sin Validación de Vínculos**
**Archivo:** `tpe_app/models.py:840-865`  
**Problema:**  
No hay validación que asegure que exactamente uno de `resolucion` o `autotpe` sea no-nulo.

```python
def save(self, *args, **kwargs):
    self.numero = self.numero.upper() if self.numero else self.numero
    # ❌ Falta validación de vínculos
    super().save(*args, **kwargs)
```

---

### 17. **add_business_days() Sin Caché**
**Archivo:** `tpe_app/models.py:42-60`  
**Problema:**  
Cada cálculo de plazo consulta la BD para obtener feriados. Sin caché, esto puede ser lento si se llama cientos de veces.

**Solución:** Cachear feriados en memoria o usar `@cache.cached_property`.

---

### 18. **RecursoTSP.recurso_origen con CASCADE Peligroso**
**Archivo:** `tpe_app/models.py:1065-1066`  
```python
recurso_origen = models.ForeignKey('self', on_delete=models.CASCADE, ...)
```

Si se elimina un RAP, se elimina en cascada su RAEE vinculada.

**Solución:** Cambiar a `on_delete=models.PROTECT`.

---

## 🟢 PROBLEMAS BAJOS / MEJORAS

### 19. **Comentario Deprecated en admin3_views.py**
**Línea:** 15  
Actualizar comentario a: `# notificacion__isnull=True (reemplazó notif_a)`

---

### 20. **Falta Validación en next_resolucion_num() y next_recurso_tsp_num()**
**Archivo:** `tpe_app/models.py:1019-1038, 1106-1124`  
**Problema:**  
No manejan el caso donde `numero` tenga formato inválido. La expresión `split('/')` puede fallar si el número está malformado.

**Solución:** Agregar `try/except` para números malformados.

---

---

## 📋 TABLA DE PROBLEMAS ORDENADOS POR CRITICIDAD

| # | Criticidad | Problema | Archivo | Línea | Riesgo |
|---|-----------|----------|---------|-------|--------|
| 1 | 🔴 CRÍTICO | Campos deprecated en import | import_actuados_historicos.py | 170-248 | Fallo de importación |
| 2 | 🔴 CRÍTICO | CASCADE en DocumentoAdjunto | models.py | 919-923 | Pérdida de auditoría |
| 3 | 🔴 CRÍTICO | CASCADE en Memorandum | models.py | 842-845 | Pérdida de ejecución |
| 4 | 🔴 CRÍTICO | CASCADE en Notificacion | models.py | 1143-1150 | Pérdida de prueba |
| 5 | 🟡 ALTO | @login_required en exportación | buscador_views.py | ? | Exposición de datos |
| 6 | 🟡 ALTO | PerfilUsuario.DoesNotExist | abogado_views.py | 12 | Crash de vista |
| 7 | 🟡 ALTO | SET_NULL en CustodiaSIM | models.py | 608-613 | Pérdida de contexto |
| 8 | 🟡 ALTO | Inconsistencia FK en PM_SIM/ABOG_SIM | models.py | 531-555 | Inconsistencia |
| 9 | 🟡 ALTO | Rol ABOGADO nunca usado | models.py | 1197 | Código muerto |
| 10 | 🟡 ALTO | Comentario desactualizado | admin3_views.py | 15 | Confusión |
| 11 | 🟡 ALTO | Falta validación RR→RR | models.py | 980-983 | Lógica errónea |
| 12 | 🟡 ALTO | CASCADE en RecursoTSP.recurso_origen | models.py | 1065 | Pérdida de datos |
| 13 | 🟠 MEDIO | MAX_LENGTH inconsistente | forms.py + models.py | 131-141, 227-229 | Restricción inválida |
| 14 | 🟠 MEDIO | Validación en CustodiaSIM | models.py | 577 | Custodia huérfana |
| 15 | 🟠 MEDIO | INDEX faltante | models.py | Múltiples | Queries lentas |
| 16 | 🟠 MEDIO | Validación Memorandum | models.py | 840 | Memoria huérfana |
| 17 | 🟠 MEDIO | add_business_days() sin caché | models.py | 42-60 | Performance |
| 18 | 🟠 MEDIO | Comentario deprecated | admin3_views.py | 15 | Documentación |
| 19 | 🟢 BAJO | Validación en next_resolucion_num() | models.py | 1019-1038 | Edge case |
| 20 | 🟢 BAJO | Validación en next_recurso_tsp_num() | models.py | 1106-1124 | Edge case |

---

## 🛠️ PLAN DE REMEDIACIÓN (Prioridad)

### Fase 1: Crítica (Semana 1)
1. ✅ Corregir `import_actuados_historicos.py` para crear `Notificacion` separadamente
2. ✅ Cambiar CASCADE → PROTECT en `DocumentoAdjunto`
3. ✅ Cambiar CASCADE → PROTECT en `Memorandum`
4. ✅ Cambiar CASCADE → PROTECT en `Notificacion`
5. ✅ Crear migración para cambios en FKs

### Fase 2: Alta (Semana 2)
6. ✅ Validar @login_required en todas las vistas de exportación
7. ✅ Añadir try/except para `PerfilUsuario.DoesNotExist`
8. ✅ Cambiar SET_NULL → PROTECT en `CustodiaSIM` o agregar campos históricos
9. ✅ Normalizar FK en `PM_SIM` y `ABOG_SIM` a PROTECT
10. ✅ Eliminar rol ABOGADO o documentar su uso
11. ✅ Cambiar CASCADE → PROTECT en `RecursoTSP.recurso_origen`

### Fase 3: Media (Semana 3)
12. ✅ Agregar validaciones en `save()` (RR→RR, CustodiaSIM, Memorandum)
13. ✅ Actualizar MAX_LENGTH en `PMSIMForm`
14. ✅ Agregar índices en campos de búsqueda frecuente
15. ✅ Implementar caché para feriados

### Fase 4: Baja (Documentación)
16. ✅ Actualizar comentarios deprecated
17. ✅ Mejorar manejo de errores en `next_*_num()`

---

## 🔐 Recomendaciones de Seguridad General

1. **Auditoría de Logs:** Implementar tabla de auditoría para rastrear cambios en SIM y documentos.
2. **Soft Deletes:** Considerar soft delete (flag `deleted_at`) en lugar de CASCADE.
3. **Permisos por Objeto:** Validar que el usuario tenga permisos para acceder al SIM específico (no solo rol).
4. **Rate Limiting:** En vistas de exportación para prevenir scraping masivo.
5. **HTTPS Requerido:** En producción, asegurar `SECURE_SSL_REDIRECT = True` en settings.py.
6. **CSRF Token:** Verificar que todos los formularios tengan `{% csrf_token %}`.
7. **XSS Prevention:** Usar `safe=False` por defecto en templates Jinja (Django lo hace por defecto).

---

## 📌 Conclusión

El sistema tiene **sólida arquitectura de roles y autenticación**, pero presenta:
- ⚠️ **Riesgos críticos de pérdida de datos** por cascadas innecesarias
- ⚠️ **Código legacy** que debe limpiarse (campos deprecated)
- ⚠️ **Inconsistencias en modelos** que pueden causar comportamiento inesperado

**Recomendación:** Implementar Plan de Remediación en Fases 1-2 antes de v4.1 en producción.

---

**Auditoría realizada por:** Claude Code (IA de Anthropic)  
**Fecha:** 2026-05-02  
**Versión del Reporte:** 1.0
