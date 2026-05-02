# CLAUDE.md — Sistema TPE (Tribunal de Personal del Ejército)
# Este archivo es leído automáticamente por Claude Code en cada sesión.
# Actualízalo cada vez que aprendas algo nuevo sobre el flujo militar.

---

## ¿Qué es este sistema?

Sistema de gestión de **Sumarios Informativos Militares (SIM)** del
**Tribunal de Personal del Ejército (TPE)** de Bolivia.
Tecnología: Django + MySQL + Bootstrap 5.

**VERSIÓN ACTUAL: v4.0** (Abril 2026)
- v3.0: Rediseño completo (Admin1/2/3, Abogados diferenciados)
- v3.1: Custodia de carpetas entre actores
- v3.2: Gestión de agendas (Admin1)
- v3.3: Rol AYUDANTE, Ejecutoria, mejoras en Buscador
- v3.4: Votos y Asistencia del tribunal, Rol ASESOR_JEFE, Miembros TPE
- v3.5: Búsqueda por lotes de antecedentes militares
- v3.5.1: Grado histórico por sumario, año de egreso y cálculo automático de ascensos
- **v4.0: Estandarización completa de nombres de campos a snake_case (sin prefijos), auditoría de seguridad, índices y correcciones de integridad**

---

## Flujo del proceso militar (orden cronológico)

```
1. Ingresa el SIM (Sumario) al TPE
         ↓
2. Se asigna un Abogado al sumario (ABOG_SIM)
         ↓
3. Se programa una AGENDA (sesión ordinaria o extraordinaria)
         ↓
4. El Abogado emite un DICTAMEN en esa agenda
   → El Secretario de Actas confirma/modifica el dictamen
         ↓
5. El Tribunal resuelve. Puede emitir:
   ├── Resolucion (Primera Resolución TPE)   ← caso disciplinario normal
   └── AUTOTPE (Auto TPE)                    ← sobreseído, nulidad, excusa, etc.
         ↓
6. Si el implicado apela:
   ├── RR    (Recurso de Reconsideración)  ← ante el TPE  [instancia='RECONSIDERACION']
   │         ↓
   │   Resolucion (Segunda Resolución)    [instancia='RECONSIDERACION']
   │         ↓
   └── RAP   (Recurso de Apelación al TSP) ← ante el Tribunal Supremo Policial
             ↓  [RecursoTSP, instancia='APELACION']
         AUTOTSP (Auto del TSP: confirma/revoca/modifica)
             ↓
         RAEE  (Aclaración, Explicación y Enmienda — RecursoTSP, instancia='ACLARACION_ENMIENDA')
             ↓
         AUTOTPE de Ejecutoria o Cumplimiento
```

**Regla importante:** Para archivos históricos (casos anteriores a esta gestión),
muchos campos pueden ser `null`. El sistema debe tolerarlo sin errores.

---

## Plazos legales automatizados

| Documento | Plazo | Campo calculado automáticamente |
|-----------|-------|----------------------------------|
| RR (Reconsideración) | 15 días hábiles desde `fecha_presentacion` | `fecha_limite` en Resolucion |
| RAP (Apelación TSP)  | 3 días hábiles desde `fecha_oficio`        | `fecha_limite` en RecursoTSP |

La función `add_business_days(fecha, dias)` en `models.py` calcula días hábiles
excluyendo fines de semana y feriados de Bolivia 2026.

---

## Modelos de la base de datos

### Tabla central y actores

| Modelo       | Tabla BD      | PK    | Descripción |
|--------------|---------------|-------|-------------|
| `PM`         | `pm`          | `id`  | Personal Militar (incluye abogados — tabla unificada desde v4.0) |
| `VOCAL_TPE`  | `vocal_tpe`   | `id`  | Vocales (Presidente, Vicepresidente, Vocal, Secretario de Actas) |
| `SIM`        | `sim`         | `id`  | Sumario Informativo Militar (tabla central) |

### Tablas puente (relaciones N:M)

| Modelo    | Tabla BD  | Relación |
|-----------|-----------|----------|
| `PM_SIM`  | `pm_sim`  | Militares investigados en un sumario (varios PM → varios SIM) |
| `ABOG_SIM`| `abog_sim`| Abogados asignados a un sumario |

### Documentos generados por el proceso

| Modelo         | Tabla BD          | Descripción |
|----------------|-------------------|-------------|
| `AGENDA`       | `agenda`          | Sesión del tribunal (ordinaria/extraordinaria) |
| `DICTAMEN`     | `dictamen`        | Dictamen del abogado en una agenda para un SIM |
| `Resolucion`   | `resolucion`      | Primera Resolución (instancia='PRIMERA') y RR (instancia='RECONSIDERACION') |
| `AUTOTPE`      | `autotpe`         | Auto del TPE (sobreseído, nulidad, excusa, ejecutoria, etc.) |
| `RecursoTSP`   | `recurso_tsp`     | Recurso Apelación (instancia='APELACION') y RAEE (instancia='ACLARACION_ENMIENDA') |
| `AUTOTSP`      | `autotsp`         | Auto del TSP (respuesta a la apelación) |
| `DocumentoAdjunto` | `documentos_adjuntos` | PDFs escaneados adjuntos a cualquier tabla |

---

## Convenciones de nombres (v4.0 — IMPORTANTE)

### Campos en BD
- Todos los campos usan **snake_case sin prefijos de tabla** (estándar Django).
- Ejemplos: `sim.codigo`, `pm.grado`, `pm.paterno`, `agenda.fecha_prog`, `resolucion.numero`
- NO existe `SIM_COD`, `PM_GRADO`, `AG_FECPROG` ni ningún prefijo en mayúscula.

### Datos almacenados
- Todos los campos de texto se guardan en **MAYÚSCULAS** (el método `save()` de cada modelo lo hace automáticamente).

### Campos clave por modelo (referencia rápida)

| Modelo | Campos principales |
|--------|-------------------|
| `PM` | `ci`, `escalafon`, `grado`, `arma`, `especialidad`, `nombre`, `paterno`, `materno`, `estado`, `anio_promocion`, `no_ascendio`, `foto` (incluye abogados desde v4.0 — tabla unificada) |
| `SIM` | `codigo`, `version`, `origen` (FK self), `motivo_reapertura`, `fecha_ingreso`, `estado`, `fase`, `objeto`, `resumen`, `auto_final`, `tipo` |
| `PM_SIM` | `pm`, `sim`, `grado_en_fecha` |
| `AGENDA` | `numero`, `tipo`, `estado`, `fecha_prog`, `fecha_real` |
| `DICTAMEN` | `sim`, `agenda`, `abogado`, `pm`, `secretario`, `numero`, `conclusion`, `conclusion_secretario`, `fecha_confirmacion` |
| `Resolucion` | `instancia`, `sim`, `abogado`, `agenda`, `pm`, `dictamen`, `resolucion_origen`, `numero`, `fecha`, `texto`, `tipo`, `resumen`, `fecha_presentacion`, `fecha_limite`, `tipo_notif`, `notif_a`, `fecha_notif`, `hora_notif` |
| `AUTOTPE` | `sim`, `abogado`, `agenda`, `pm`, `resolucion`, `recurso_tsp`, `numero`, `fecha`, `texto`, `tipo`, `tipo_notif`, `notif_a`, `fecha_notif`, `hora_notif`, `memo_numero`, `memo_fecha`, `memo_fecha_entrega` |
| `RecursoTSP` | `instancia`, `sim`, `abogado`, `pm`, `resolucion`, `recurso_origen`, `fecha_presentacion`, `numero_oficio`, `fecha_oficio`, `fecha_limite`, `tipo`, `numero`, `fecha`, `texto`, `tipo_notif`, `notif_a`, `fecha_notif`, `hora_notif` |
| `DocumentoAdjunto` | `tabla`, `registro_id`, `tipo`, `archivo`, `nombre`, `fecha_registro` |

---

## Roles de usuario del sistema

> **IMPORTANTE:** Los nombres de rol son exactamente como aparecen en `PerfilUsuario.ROL_CHOICES` y en los decoradores `@rol_requerido(...)`. Usar estos nombres exactos al buscar en el código.

| Rol (nombre en código)  | Vista principal          | Responsabilidades |
|-------------------------|--------------------------|-------------------|
| `ADMIN1_AGENDADOR`      | `admin1_views.py`        | Ingresa SIM, asigna abogados, crea agendas, ordena ejecutoria |
| `ADMIN2_ARCHIVO`        | `admin2_views.py`        | Gestiona custodia/entrega de carpetas entre actores |
| `ADMIN3_NOTIFICADOR`    | `admin3_views.py`        | Envía notificaciones a terceros |
| `ABOG1_ASESOR`          | `abogado_views.py`       | Crea dictámenes, resoluciones (1ra instancia y RR) |
| `ABOG2_AUTOS`           | `abogado_views.py`       | Crea autos sin agenda previa (Excusa, Ejecutoria) |
| `ABOG3_BUSCADOR`        | `abogado_views.py`       | Búsqueda de antecedentes, confirma entrega de carpetas |
| `SECRETARIO_ACTAS`      | `vocal_views.py`         | Modifica dictámenes, registra votos y asistencia del tribunal |
| `ASESOR_JEFE`           | `asesor_jefe_views.py`   | Monitoreo de agendas y estadísticas (solo lectura) |
| `ASESOR_JURIDICO`       | `buscador_views.py`      | Consulta historial de personal (sin voto ni firma) |
| `AYUDANTE`              | `ayudante_views.py`      | Registra resoluciones históricas, notificaciones, RAEE |
| `BUSCADOR`              | `buscador_views.py`      | Consulta historial de personal (requiere login) |
| `MASTER`                | `admin1_views.py`        | Control total del sistema |
| `ADMINISTRADOR`         | `admin1_views.py`        | Administrador de sistemas |

> **Rol eliminado:** `ADMINISTRATIVO` fue eliminado en la limpieza v4.0. Ya no existe en ROL_CHOICES ni en ningún decorador.

### Seguridad de vistas
- Todas las vistas usan `@rol_requerido` o `@login_required` (decorators.py).
- `buscador_views.py` y `export_views.py`: todas las vistas tienen `@login_required`.
- Ninguna vista es pública — el buscador también requiere autenticación.

---

## Flujo de Custodia de Carpetas

El sistema controla la **trazabilidad** de carpetas entre actores mediante `CustodiaSIM`.

### Modelo CustodiaSIM — Campos clave:
- `fase` (en SIM): PARA_DICTAMEN, PARA_AGENDA, PARA_RESOLUCION, EN_APELACION, PARA_EJECUTORIA
- `estado`: **ACTIVA** (en poder del custodio), **PENDIENTE_CONFIRMACION** (entregada, aguardando confirmación)
- `tipo_custodio`: ADMIN2_ARCHIVO, ABOG_ASESOR, ABOG_RR, ABOG_AUTOS, VOCAL_SESION, ADMIN1_AGENDADOR

**Regla cardinal:** Admin2 **SIEMPRE** crea la custodia cuando **ENTREGA**. NO cuando se registra o agenda.

### Flujo resumido:
```
ADMIN1 registra SIM → ADMIN2 recibe (CustodiaSIM ACTIVA)
    ↓
ADMIN2 entrega a ABOGADO (estado='PENDIENTE_CONFIRMACION')
    ↓
ABOGADO confirma recepción (estado='ACTIVA') → puede crear DICTAMEN
    ↓
ABOGADO devuelve a ADMIN2 → ADMIN2 entrega a VOCAL (sesión)
    ↓
VOCAL devuelve a ADMIN2 → ciclo continúa según resolución
```

### Dashboard de ADMIN2 (3 secciones):
1. Carpetas en su poder → `estado='ACTIVA'`
2. Pendiente confirmar recepción → `estado='PENDIENTE_CONFIRMACION'`
3. Carpetas prestadas → Custodias activas de otros actores

---

## Flujo de Ejecutoria

```
ADMIN1: "Entregar para Ejecutoria" (botón en RES)
    ↓
ADMIN2: confirma entrega a ABOG2
    ↓
ABOG2: crea Auto de Ejecutoria (sin agenda previa)
    → sim.fase = 'EN_EJECUTORIA'
    ↓
ADMIN3: notifica Auto → sim.fase = 'EJECUTORIA_NOTIFICADA'
    ↓
ADMIN1: "Ordenar Archivo a SPRODA" → sim.fase = 'PENDIENTE_ARCHIVO'
    ↓
ADMIN2: confirma archivo → sim.fase = 'CONCLUIDO' → sim.estado = 'PROCESO_CONCLUIDO_TPE'
    ↓
Si hay memorándum (autotpe.memo_numero): ADMIN2 registra retorno
    → sim.estado = 'PROCESO_EJECUTADO'
```

Los Autos de Ejecutoria NO requieren agenda previa (a diferencia de RES).

---

## Numeración automática de documentos

El sistema genera números automáticamente con formato `NN/AA` (ej: `05/26`).

| Documento | Campo | Función |
|-----------|-------|---------|
| Dictamen | `dictamen.numero` | en la vista al crear |
| Resolución | `resolucion.numero` | `next_resolucion_num()` en models.py |
| Recurso TSP | `recurso_tsp.numero` | `next_recurso_tsp_num()` en models.py |
| Auto TPE | `autotpe.numero` | en la vista al crear |

Las funciones usan `select_for_update()` dentro de `transaction.atomic()` para evitar duplicados concurrentes.

**Restricción BD:** `Resolucion` tiene `unique_together = [('numero', 'instancia')]` — no puede repetirse el mismo número dentro de la misma instancia (PRIMERA o RECONSIDERACION).

---

## Grados militares (jerarquía de mayor a menor)

**Generales:** GRAL. EJTO. → GRAL. DIV. → GRAL. BRIG.
**Oficiales Superiores:** CNL. → TCNL. → MY.
**Oficiales Subalternos:** CAP. → TTE. → SBTTE.
**Suboficiales:** SOF. MTRE. → SOF. MY. → SOF. 1RO. → SOF. 2DO. → SOF. INCL.
**Sargentos:** SGTO. 1RO. → SGTO. 2DO. → SGTO. INCL.
**Tropa:** CABO → DGTE. → SLDO.
**Empleados Civiles:** PROF. / TEC. / ADM. / APAD. (niveles I al V)

---

## Armas del Ejército registradas

INF. | CAB. | ART. | ING. | COM. | INT. | SAN. | TGRAFO. | AV. | MÚS.

**Pendiente agregar:** LOGÍSTICA (está en TO_DO.py)

---

## Estados del SIM

### Jerarquía (nivel — impide retroceder al hacer `sim.save()`)

| Nivel | Estado | Significado | Disparado por |
|:-----:|--------|-------------|---------------|
| 0 | `PARA_AGENDA` | **Estado inicial**. SIM ingresa, pendiente agendar | ADMIN1 registra SIM |
| 0 | `OBSERVADO` | Sumario con observaciones pendientes | Correcciones manuales |
| 1 | `PROCESO_EN_EL_TPE` | Abogado trabajando (1ra RES, RR, ejecutoria) | ADMIN1 al agendar + asignar ABOG |
| 2 | `PROCESO_EN_EL_TSP` | RAP elevado. Caso **físicamente en el TSP** (puede durar años) | ABOGADO o AYUDANTE al crear RecursoTSP |
| 3 | `CUMPLIMIENTO_EN_TPE` | TSP devolvió pronunciamiento. TPE elabora auto de cumplimiento | Admin2 recibe doc TSP → Admin1 ordena a ABOG2 |
| 4 | `PROCESO_CONCLUIDO_TPE` | Ejecutoria notificada y archivada en SPRODA (ruta sin TSP) | ADMIN2 al confirmar archivo |
| 4 | `PROCESO_CONCLUIDO_TSP_TPE` | Auto de cumplimiento/ejecutoria notificado y archivado (ruta TSP) | ADMIN2 al confirmar archivo |
| 5 | `PROCESO_EJECUTADO` | Memorándum retornó. Solo aplica ruta sin TSP | ADMIN2 al registrar retorno de memo |

### Fases por estado

**PROCESO_EN_EL_TPE (nivel 1) — Ruta sin RAP:**
```
PARA_AGENDA → EN_DICTAMEN_1RA → 1RA_RESOLUCION → NOTIFICACION_1RA → NOTIFICADO_1RA
→ EN_ESPERA_RR → PARA_AGENDA_RR → EN_DICTAMEN_RR → 2DA_RESOLUCION
→ NOTIFICACION_RR → NOTIFICADO_RR → EN_ESPERA_RAP
→ EN_AGENDA_EJECUTORIA → EN_EJECUTORIA → EJECUTORIA_NOTIFICADA
→ PENDIENTE_ARCHIVO → CONCLUIDO → MEMORANDUM_RETORNADO
```

**PROCESO_EN_EL_TSP (nivel 2) — RAP presentado:**
```
ELEVADO_TSP   (único estado mientras el caso está en el TSP)
              [se pueden registrar docs RAEE y AUTOTSP sin cambiar fase]
```

**CUMPLIMIENTO_EN_TPE (nivel 3) — TSP devolvió pronunciamiento:**
```
RECIBIDO_TSP → EN_CUMPLIMIENTO → EN_AGENDA_CUMPLIMIENTO
→ CUMPLIMIENTO_EMITIDO → CUMPLIMIENTO_NOTIFICADO
```
- `NULIDAD_TSP`: fase especial si el TSP revocó y anuló obrados (proceso puede reiniciarse como nueva versión SIM)

**PROCESO_CONCLUIDO_TSP_TPE (nivel 4):**
```
CONCLUIDO_TSP_TPE
```

### Colores de badge de fase (admin1_dashboard):
- Azul `#3b82f6`: fases `PARA_*`
- Naranja `#f97316`: fases `EN_*` (EN_DICTAMEN, EN_EJECUTORIA, EN_CUMPLIMIENTO...)
- Verde `#16a34a`: resoluciones (`1RA_*`, `2DA_*`) y fases `CONCLUIDO*`
- Cian `#0ea5e9`: notificaciones (`*NOTIFICACION*`, `*NOTIFICADO*`)
- Rojo `#dc2626`: esperas y elevación (`*ESPERA*`, `*ELEVADO*`, `NULIDAD_TSP`)
- Violeta `#7c3aed`: recepción TSP (`*RECIBIDO*`)
- Teal `#0d9488`: cumplimiento TPE (`*CUMPLIMIENTO*`)

---

## Tipos de Resolución (`resolucion.tipo`)

ARCHIVO_OBRADOS, ADMINISTRATIVO, SANCIONES_DISCIPLINARIAS,
SANCION_ARRESTO, SANCION_LETRA_B, SANCION_RETIRO_OBLIGATORIO, SANCION_BAJA,
SOLICITUD_LETRA_D, SOLICITUD_LICENCIA_MAXIMA, SOLICITUD_ASCENSO,
SOLICITUD_RESTITUCION_ANTIGUEDAD, SOLICITUD_RESTITUCION_DE_DERECHOS_PROFESIONALES,
SOLICITUD_ART_114, SOLICITUD_ART_117, SOLICITUD_ART_118, OTRO.

---

## Tipos de Auto TPE (`autotpe.tipo`)

SOBRESEIDO | NULIDAD_OBRADOS | SANCION_ARRESTO | SANCION_LETRA_B |
SANCION_RETIRO_OBLIGATORIO | AUTO_CUMPLIMIENTO | AUTO_EJECUTORIA |
AUTO_EXCUSA | AUTO_RECHAZO_RECURSO

---

## Grados Históricos y Años de Servicio (v3.5.1)

El sistema distingue dos conceptos de grado:

- **`pm.grado`**: grado **actual** del militar. Editable desde `/ayudante/pm/<id>/editar/`.
- **`pm_sim.grado_en_fecha`**: grado que tenía el militar **al momento de ese sumario**. Extraído del documento escaneado, no cambia.

### Campos de PM para carrera

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `anio_promocion` | IntegerField | Año de egreso (ej: `2000`). Base para todos los cálculos. **CRÍTICO: sin este dato no se puede calcular grado esperado.** |
| `no_ascendio` | BooleanField | Marcar cuando el militar no ascendió al grado que le correspondía. |

### Propiedades calculadas (sin columna en BD)

```python
pm.años_servicio             # año_actual - anio_promocion → None si falta anio_promocion
pm.grado_esperado            # grado según escalafón y años (None si no_ascendio=True o si falta anio_promocion)
pm.estado_carrera_calculado  # ACTIVO / SERVICIO ACTIVO / LETRA A / SERVICIO PASIVO → None si falta anio_promocion
```

### ⚠️ IMPORTANTE: Cuando falta Año de Egreso

Si **NO hay `anio_promocion`** registrado (casos históricos):

| Situación | Comportamiento | En pantalla |
|-----------|---|---|
| Cálculo de carrera | No se puede calcular | `grado_esperado` = None |
| Años de servicio | No se puede calcular | `años_servicio` = None |
| Grado mostrado | Se usa el `pm.grado` actual | Badge **"DOC"** indica grado del documento |
| En reportes | Grado del sumario histórico | Con advertencia si falta año |
| Campo "No ascendió" | DESHABILITADO | Requiere `anio_promocion` para funcionar |

**Recomendación:** El campo `Año de Egreso` tiene una advertencia visual en la interfaz de edición (`/ayudante/pm/<id>/editar/`) cuando falta este dato crítico.

### Tabla de ascensos (regla: N años completos + 1 día)

| Sargentos / Suboficiales | Año | Oficiales | Año |
|--------------------------|-----|-----------|-----|
| SGTO. INCL. | 0  | SBTTE. | 0  |
| SGTO. 2DO.  | 4  | TTE.   | 6  |
| SGTO. 1RO.  | 7  | CAP.   | 11 |
| SOF. INCL.  | 11 | MY.    | 16 |
| SOF. 2DO.   | 16 | TCNL.  | 21 |
| SOF. 1RO.   | 21 | CNL.   | 26 |
| SOF. MY.    | 26 | GRAL. (postulación) | 31 |
| SOF. MTRE. (si califica) | 31 | | |

---

## Buscador — Reportes de Historial

- Requiere `@login_required` (no es público).
- **PDF directo** (no ZIP): Reporte unificado con toda la información del militar.
- **Búsqueda por lotes**: múltiples militares por apellido paterno + materno.
- **Exportación**: PDF individual, Excel individual, PDF lote, Excel lote.
- El historial usa `PM.objects.get(id=personal_id)` y `SIM.objects.filter(militares__id=personal_id)`.

**Archivos:** `buscador_views.py`, `export_views.py`, `dashboard_buscador.html`

---

## Correcciones y decisiones de diseño aplicadas (historial)

1. **v4.0 — Estandarización snake_case**: Todos los campos renombrados de `PREFIJO_CAMPO` a `campo`. Ejemplo: `PM_GRADO` → `grado`, `SIM_COD` → `codigo`, `AG_FECPROG` → `fecha_prog`. Las 28 migraciones antiguas fueron eliminadas y se creó una sola `0001_initial` limpia.
2. **v4.0 — Seguridad**: Todas las vistas de buscador y exportación protegidas con `@login_required`. `DEBUG` default cambiado a `False`. `ALLOWED_HOSTS` con fallback.
3. **v4.0 — Integridad**: `max_length` de nombre/paterno/materno aumentado de 25→50; especialidad 15→30. `ABOG.ci` ahora `unique=True`. Índices en `SIM.estado`, `SIM.fase`, `SIM.fecha_ingreso`, `PM.paterno`. `Resolucion` tiene `unique_together = [('numero', 'instancia')]`. `resolucion_origen` FK cambiada de CASCADE a PROTECT.
4. **v4.0 — Bug fix**: `_obtener_historial_completo()` usaba `pm_id=` (incorrecto) → corregido a `id=`.
5. **Campo `TSP_RESUM` eliminado** del modelo RecursoTSP.
6. **Admin nativo de Django**: Panel al estilo Django estándar. Dashboard `/panel-admin/dashboard/` es el panel principal del sistema.
7. **Abogado NO va en SIM**: Va en `ABOG_SIM` (tabla puente).
8. **DICTAMEN tiene FK a PM**: Para mostrar el nombre del implicado.
9. **Todos los textos en MAYÚSCULAS**: El método `save()` de cada modelo lo hace automáticamente.
10. **Reaperturas de SIM**: `sim.version` (int), `sim.origen` (FK self, PROTECT), `sim.motivo_reapertura` para manejar reaperturas tras nulidad.
11. **Memorándum ejecutoria**: `autotpe.memo_numero`, `autotpe.memo_fecha`, `autotpe.memo_fecha_entrega`. Al registrar retorno → `sim.estado = 'PROCESO_EJECUTADO'`.

---

## Pendientes / Mejoras Futuras

### Buscador
- [ ] Dashboard buscador: mostrar filtro por fecha de ingreso del SIM
- [ ] Historial: agregar opción de descarga en formato CSV
- [ ] Reportes: agregar gráficas de estadísticas por año/mes

### Modelos y Base de Datos
- [ ] Agregar arma LOGÍSTICA en `ARMA_CHOICES` de PM
- [ ] Campo `causa_especifica` en SIM para detallar causa más allá del tipo

### Dashboards
- [ ] Dashboard Abogado: mostrar todos los militares implicados en cada sumario
- [ ] Dashboard Admin1: vista de "Sumarios Pendientes de Ejecutoria"
- [ ] Dashboard Admin2: Indicador de "Carpetas con Demora en Entrega"

### Mejoras en Flujo
- [ ] Notificación automática cuando demora custodia > 7 días
- [ ] Recordatorio de plazos legales (RR, RAP)
- [ ] Auditoría: registrar quién cambió qué y cuándo

---

## Estructura de archivos clave

```
TPEsystem/
├── CLAUDE.md                          ← ESTE ARCHIVO
├── TO_DO.py                           ← Lista de tareas pendientes
├── tpe_app/
│   ├── models.py                      ← Modelos: PM, SIM, AUTOTPE, Resolucion, RecursoTSP, etc.
│   ├── forms.py                       ← Formularios (SIM, Resoluciones, Autos, Wizards)
│   ├── urls.py                        ← Rutas por rol
│   ├── decorators.py                  ← @rol_requerido para control de acceso
│   ├── views/
│   │   ├── admin1_views.py            ← Ingresa SIM, asigna abogados, crea agendas
│   │   ├── admin2_views.py            ← Custodia: entrega/recepción de carpetas
│   │   ├── admin3_views.py            ← Notificaciones
│   │   ├── abogado_views.py           ← Dictámenes, Resoluciones, Autos (ABOG1/2/3)
│   │   ├── abogado_documentos_views.py ← Crear RES, RR, AUTOTPE, Auto Excusa, Ejecutoria
│   │   ├── vocal_views.py             ← Confirmar dictámenes (Secretario de Actas)
│   │   ├── asesor_jefe_views.py       ← Dashboard supervisor (solo lectura)
│   │   ├── buscador_views.py          ← Historial personal (requiere @login_required)
│   │   ├── ayudante_views.py          ← Registrar RES/RR/RAP/RAEE históricas
│   │   ├── export_views.py            ← PDF y Excel del buscador (requiere @login_required)
│   │   ├── ejecutoria_views.py        ← Auto de Ejecutoria
│   │   └── auth_views.py              ← Login/Logout
│   ├── templates/
│   │   ├── dashboard_*.html           ← Dashboards por rol
│   │   └── buscador/                  ← Templates del buscador
│   ├── migrations/
│   │   ├── 0001_initial.py            ← Esquema completo limpio (v4.0)
│   │   └── 0002_*.py                  ← Mejoras de integridad (índices, max_length, constraints)
│   └── queries/
│       └── historial_personal.py      ← Consultas ORM reutilizables
├── config/
│   └── settings.py                    ← Django config. DEBUG default=False. ALLOWED_HOSTS con fallback.
├── .env                               ← Credenciales (no subir a Git)
└── manage.py
```

**Accesos rápidos por rol:**
- **ADMIN1**: `admin1_dashboard`
- **ADMIN2**: `admin2_dashboard`
- **ADMIN3**: `admin3_dashboard`
- **ABOG**: `abogado_dashboard`
- **VOCAL**: `vocal_dashboard`
- **ASESOR_JEFE**: `asesor_jefe_dashboard`
- **AYUDANTE**: `ayudante_dashboard`
- **BUSCADOR**: `buscador_dashboard`

---

---

## Coordinación de Reportes (v4.0+)

### Tres modelos de reportes coordinados

Los reportes PDF y Excel están coordinados para mantener **formato y contenido consistente**:

#### 1. **Reportes Individuales** (export_person_historial_pdf)
- **Función**: `export_views.py:export_person_historial_pdf()`
- **Tabla**: TIPO | N° | FECHA | RESOLUTIVA | NOTIF.
- **Documentos incluidos**: RES, RR, AUTO TPE, RAP, RAEE, AUTO TSP
- **Resolutiva**: En MAYÚSCULA (captura del texto o tipo_display())
- **Memorándum**: Se muestra debajo del tipo si existe

#### 2. **Reportes por Lotes** (búsqueda por lotes)
- **Funciones**: `buscador_views.py:export_batch_pdf()` y `export_batch_excel()`
- **Estructura**: GRADO | NOMBRES | PATERNO | MATERNO | SIM | OBJETO | ACTUADOS | ESTADO
- **Actuados**: Compilados con tipo, número, fecha y resolutiva (coordinado)
- **Memorándum**: Agregado al tipo con formato `[MEMO N° ...]`
- **Formato**: TODO EN MAYÚSCULA

#### 3. **Reportes por Sumario** (detalles SIM)
- **Funciones**: `export_views.py:export_sim_pdf()` y `export_sim_excel()`
- **Tabla PDF**: TIPO | N° | FECHA | RESOLUTIVA | NOTIF.
- **Excel**: Columnas separadas para MEMO N°, MEMO FECHA, MEMO ENTREGA
- **Documentos**: Compilados con función coordinada

### Funciones helpers

**`_compilar_documentos(sim, historial)`** — export_views.py
- Compila lista coordinada de documentos para reportes individual/sumario
- Retorna: `dict` con `tipo`, `numero`, `fecha_doc`, `resolutiva`, `notificacion`, `memo`
- Incluye: RES, RR, AUTO TPE, RAP, RAEE, AUTO TSP

**`_compilar_documentos_lotes(sim, historial)`** — buscador_views.py
- Compila documentos para reportes por lotes
- Retorna: tuplas `(tipo, numero, fecha, resolutiva)`
- Más compacto para PDF/Excel lote

### Requisitos de formato

✅ **Todo en mayúscula**: nombres, apellidos, grado, especialidad, objeto, estado, resolutiva
✅ **Parte resolutiva en todos los documentos**: campo `texto` de RES/RR o `get_tipo_display()` de Autos
✅ **Columnas estándar**: Documento | Número | Fecha | Resolutiva | Notificación
✅ **Memorándum en autos**: número, fecha y fecha de entrega

---

## Notas de desarrollo

- Base de datos: MySQL (credenciales en .env — DB: `db_sumarios_militares`, usuario: `root`)
- ORM: siempre usar Django ORM, nunca SQL crudo
- Las migraciones van en `tpe_app/migrations/`
- Para importación masiva de datos: usar `generar_plantilla_historico.py` → genera Excel
- Feriados Bolivia 2026 ya configurados en `models.py` para cálculo de días hábiles
- Superusuario inicial: `admin` / `admin123` (cambiar en producción)
