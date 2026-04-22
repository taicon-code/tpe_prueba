# CLAUDE.md — Sistema TPE (Tribunal de Personal del Ejército)
# Este archivo es leído automáticamente por Claude Code en cada sesión.
# Actualízalo cada vez que aprendas algo nuevo sobre el flujo militar.

---

## ¿Qué es este sistema?

Sistema de gestión de **Sumarios Informativos Militares (SIM)** del
**Tribunal de Personal del Ejército (TPE)** de Bolivia.
Tecnología: Django + MySQL + Bootstrap 5.

**VERSIÓN ACTUAL: v3.3** (Abril 2026)
- v3.0: Rediseño completo (Admin1/2/3, Abogados diferenciados)
- v3.1: Custodia de carpetas entre actores
- v3.2: Gestión de agendas (Admin1)
- v3.3: Rol AYUDANTE, Ejecutoria, mejoras en Buscador (v3.3.1)

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
   ├── RES   (Primera Resolución TPE)      ← caso disciplinario normal
   └── AUTOTPE (Auto TPE)                  ← sobreseído, nulidad, excusa, etc.
         ↓
6. Si el implicado apela:
   ├── RR    (Recurso de Reconsideración)  ← ante el TPE
   │         ↓
   │   RES2 (Segunda Resolución)
   │         ↓
   └── RAP   (Recurso de Apelación al TSP) ← ante el Tribunal Supremo Policial
             ↓
         AUTOTSP (Auto del TSP: confirma/revoca/modifica)
             ↓
         RAEE  (Aclaración, Explicación y Enmienda — si procede)
             ↓
         AUTOTPE de Ejecutoria o Cumplimiento
```

**Regla importante:** Para archivos históricos (casos anteriores a esta gestión),
muchos campos pueden ser `null`. El sistema debe tolerarlo sin errores.

---

## Plazos legales automatizados

| Documento | Plazo | Campo calculado automáticamente |
|-----------|-------|----------------------------------|
| RR        | 15 días hábiles desde `RR_FECPRESEN` | `RR_FECLIMITE` |
| RAP       | 3 días hábiles desde `RAP_FECOFI`    | `RAP_FECLIMITE` |

La función `add_business_days(fecha, dias)` en `models.py` calcula días hábiles
excluyendo fines de semana y feriados de Bolivia 2026.

---

## Modelos de la base de datos

### Tabla central y actores

| Modelo       | Tabla BD      | PK Python   | PK en BD | Descripción |
|--------------|---------------|-------------|----------|-------------|
| `PM`         | `pm`          | `pm_id`     | `id`     | Personal Militar |
| `ABOG`       | `abog`        | `abog_id`   | `id`     | Abogados del Tribunal |
| `VOCAL_TPE`  | `vocal_tpe`   | `id`        | `id`     | Vocales (Presidente, Vicepresidente, Vocal, Secretario de Actas) |
| `SIM`        | `sim`         | `id`        | `id`     | Sumario Informativo Militar (tabla central) |

### Tablas puente (relaciones N:M)

| Modelo    | Tabla BD  | Relación |
|-----------|-----------|----------|
| `PM_SIM`  | `pm_sim`  | Militares investigados en un sumario (varios PM → varios SIM) |
| `ABOG_SIM`| `abog_sim`| Abogados asignados a un sumario |

### Documentos generados por el proceso

| Modelo      | Tabla BD   | Descripción |
|-------------|------------|-------------|
| `AGENDA`    | `agenda`   | Sesión del tribunal (ordinaria/extraordinaria) |
| `DICTAMEN`  | `dictamen` | Dictamen del abogado en una agenda para un SIM |
| `RES`       | `res`      | Primera Resolución del TPE |
| `RR`        | `rr`       | Recurso de Reconsideración (Segunda Resolución) |
| `AUTOTPE`   | `autotpe`  | Auto del TPE (sobreseído, nulidad, excusa, ejecutoria, etc.) |
| `RAP`       | `rap`      | Recurso de Apelación al TSP |
| `AUTOTSP`   | `autotsp`  | Auto del TSP (respuesta a la apelación) |
| `RAEE`      | `raee`     | Recurso de Aclaración, Explicación y Enmienda |
| `DocumentoAdjunto` | `documentos_adjuntos` | PDFs escaneados adjuntos a cualquier tabla |

---

## Convenciones de nombres en los campos

- Todos los campos de texto se guardan en **MAYÚSCULAS** (el método `save()` de cada modelo lo hace automáticamente).
- Prefijos por modelo:
  - `PM_*` → Personal Militar
  - `AB_*` → Abogado
  - `SIM_*` → Sumario
  - `AG_*` → Agenda
  - `DIC_*` → Dictamen
  - `RES_*` → Resolución
  - `RR_*` → Recurso Reconsideración
  - `TPE_*` → Auto TPE
  - `RAP_*` → Recurso Apelación
  - `TSP_*` → Auto TSP
  - `RAE_*` → RAEE

---

## Roles de usuario del sistema (ACTUAL v3.3)

| Rol            | Vista principal | Responsabilidades | Flujo |
|----------------|-----------------|-------------------|-------|
| **ADMIN1**     | `admin1_views.py` | Ingresa SIM, asigna abogados, crea agendas, ordena ejecutoria | Inicio del proceso |
| **ADMIN2**     | `admin2_views.py` | Gestiona custodia/entrega de carpetas entre actores | Control de trazabilidad |
| **ADMIN3**     | `admin3_views.py` | Envía notificaciones a terceros | Comunicaciones |
| **ABOG1**      | `abogado_views.py` | Crea dictámenes, resoluciones, autos | Trabajo legal principal |
| **ABOG2**      | `abogado_views.py` | Crea autos sin agenda previa (Excusa, Ejecutoria) | Autos antes de sesión |
| **ABOG3**      | `abogado_views.py` | Confirma entrega de carpetas, suscribe autos | Recibe y valida |
| **VOCAL**      | `vocal_views.py` | Secretario de Actas: confirma/modifica dictámenes | Sesiones del tribunal |
| **AYUDANTE**   | `ayudante_views.py` | Registra resoluciones históricas, notificaciones, RAEE | Base de datos |
| **BUSCADOR**   | `buscador_views.py` | Consulta historial de personal (público) | Reportes |

---

## Flujo de Custodia de Carpetas (v3.3 — CORRECCIONES IMPORTANTES)

El sistema controla la **trazabilidad** de carpetas entre actores mediante `CustodiaSIM`.

### Modelo CustodiaSIM — Campos clave:
- `SIM_FASE`: PARA_DICTAMEN, PARA_AGENDA, PARA_RESOLUCION, EN_APELACION, PARA_EJECUTORIA
- `estado`: **ACTIVA** (en poder del custodio), **PENDIENTE_CONFIRMACION** (entregada, aguardando confirmación)
- `tipo_custodio`: ADMIN2_ARCHIVO, ABOG_ASESOR, ABOG_RR, ABOG_AUTOS, VOCAL_SESION, ADMIN1_AGENDADOR
- `custodio_a`: FK a PM (si es abogado/vocal) o NULL (si es admin)

### ⚠️ CORRECCIÓN v3.3: Flujo correcto de Admin2 (IMPORTANTE)

**Regla cardinal:** Admin2 **SIEMPRE** crea la custodia cuando **ENTREGA**. NO cuando se registra o agenda.

#### Paso 1: SIM Ingresa
```
ADMIN1: Registra SIM → estado=PARA_AGENDA
ADMIN2: Recibe SIM → crea CustodiaSIM(tipo_custodio='ADMIN2_ARCHIVO', estado='ACTIVA')
```

#### Paso 2: AGENDA y ASIGNACIÓN
```
ADMIN1: Programa AGENDA para SIM
ADMIN1: Asigna abogados (crea ABOG_SIM para cada abogado)
SIM: SIM_ESTADO='PROCESO_EN_EL_TPE'
ADMIN2: VE EN DASHBOARD que el SIM está agendado
```

#### Paso 3: ADMIN2 ENTREGA AL ABOGADO
```
ADMIN2 (Dashboard):
  ① Selecciona SIM pendiente
  ② Elige ABOGADO (consulta ABOG_SIM para ver quién está asignado)
  ③ Hace clic "Entregar Carpeta"
  
SISTEMA AUTOMÁTICO:
  ① Cierra custodia ADMIN2_ARCHIVO (fecha_entrega=now())
  ② Crea NEW custodia: CustodiaSIM(
       tipo_custodio='ABOG_ASESOR',
       abog=abogado_seleccionado,
       estado='PENDIENTE_CONFIRMACION'  ← CLAVE: No está confirmada aún
     )
  ③ ABOGADO ve SIM en su dashboard (asignado + custodia pendiente)
```

#### Paso 4: ABOGADO CONFIRMA RECEPCIÓN
```
ABOGADO (Dashboard):
  ① Ve custodia PENDIENTE_CONFIRMACION en su SIM
  ② Hace clic "Confirmar Recepción"
  
SISTEMA:
  ① Cambia custodia.estado='ACTIVA'
  ② Ahora abogado puede crear DICTAMEN
```

#### Paso 5: ABOGADO DEVUELVE A ADMIN2
```
ABOGADO (después de crear Dictamen/RES):
  ① Hace clic "Devolver Carpeta"
  
SISTEMA:
  ① Cierra custodia del abogado (fecha_entrega=now())
  ② Crea NEW custodia: CustodiaSIM(tipo_custodio='ADMIN2_ARCHIVO', estado='ACTIVA')
  ③ ADMIN2 ve SIM nuevamente en su poder
```

#### Paso 6: ADMIN2 ENTREGA A VOCAL (para sesión)
```
ADMIN2: Entrega carpeta al Secretario de Actas (VOCAL)
SISTEMA: Crea custodia con tipo_custodio='VOCAL_SESION', estado='PENDIENTE_CONFIRMACION'
VOCAL: Confirma recepción, sesiona, confirma Dictamen
VOCAL: Devuelve a ADMIN2
```

### Dashboard de ADMIN2 (3 secciones):
1. **📁 Carpetas en su poder** → `estado='ACTIVA'` (confirmadas)
2. **⏳ Pendiente confirmar recepción** → `estado='PENDIENTE_CONFIRMACION'` (entregadas pero no confirmadas aún)
3. **🔄 Carpetas prestadas** → Custodia de otros actores activas en ese momento

---

## Flujo de Ejecutoria (v3.3.1)

Nuevas resoluciones pueden generar **Autos de Ejecutoria**:

```
ADMIN1: "Entregar para Ejecutoria" (botón en RES)
    ↓
ADMIN2: confirma entrega a ABOG2
    ↓
ABOG2: crea Auto de Ejecutoria (sin agenda previa)
    ↓
ADMIN2: entrega a vocales para firmar
    ↓
VOCAL: firma el Auto
    ↓
Sumario → CONCLUIDO
```

**Nota:** Los Autos de Ejecutoria NO requieren agenda previa
(a diferencia de RES que sí la requieren)

---

## Numeración automática de documentos

El sistema genera números automáticamente con formato `NN/AA` (ej: `05/26`).
- Dictamen: `DIC_NUM`
- Resolución: `RES_NUM`
- RR: `RR_NUM`
- Auto TPE: `TPE_NUM`

La lógica de numeración está en las vistas correspondientes, no en los modelos.

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

## Estados del SIM — CORRECCIONES IMPORTANTES (v3.3)

| Estado | Significado | Transición | Disparado por |
|--------|-------------|-----------|---|
| `PARA_AGENDA` | SIM ingresa al TPE, pendiente ser agendado. ⚠️ **ESTADO INICIAL** | ADMIN1 registra SIM | ADMIN1 |
| `PROCESO_EN_EL_TPE` | SIM fue agendado en una AGENDA. Abogado está trabajando (Dictamen/RES). | `PARA_AGENDA` → `PROCESO_EN_EL_TPE` | ADMIN1 cuando lo agenda + asigna abogados |
| `EN_APELACION_TSP` | Se emitió RAP (Recurso de Apelación). El caso subió al TSP. | Cuando se crea `RAP` para el SIM | ABOGADO cuando registra RAP o AYUDANTE |
| `CONCLUIDO` | Proceso judicial terminado. Auto de Ejecutoria firmado por VOCAL. | `PROCESO_EN_EL_TPE` → `CONCLUIDO` | ADMIN1 cuando ordena ejecutoria + ABOG2 crea Auto + VOCAL firma |
| `OBSERVADO` | ⚠️ **RARO, evitar**: Sumario con observaciones pendientes. Requiere corrección. | Flujo poco común | Correcciones manuales |

### ⚠️ Correcciones de lógica de estados:

1. **NO hay transición directa** `PARA_AGENDA` → `CONCLUIDO`
   - El SIM debe pasar por `PROCESO_EN_EL_TPE` primero
   - Esto requiere: AGENDA + DICTAMEN + RES/AUTOTPE + EJECUCIÓN

2. **`PARA_AGENDA` es el ÚNICO estado inicial**
   - Cuando ADMIN1 registra un SIM nuevo, SIEMPRE comienza aquí
   - SIM_ESTADO='PARA_AGENDA' en el modelo

3. **`PROCESO_EN_EL_TPE` se activa cuando:**
   - ✅ ADMIN1 crea AGENDA para el SIM
   - ✅ ADMIN1 asigna al menos 1 ABOG a ese SIM (tabla ABOG_SIM)
   - ✅ El sistema cambia automáticamente a `PROCESO_EN_EL_TPE`

4. **`EN_APELACION_TSP` se activa solo si:**
   - ✅ Se registra un RAP para ese SIM (tabla RAP)
   - Si hay RR pero NO RAP → sigue en `PROCESO_EN_EL_TPE`
   - Si hay RAP → automáticamente pasa a `EN_APELACION_TSP`

5. **`CONCLUIDO` se activa solo cuando:**
   - ✅ Se emite RES (Primera Resolución) O AUTOTPE (Auto)
   - ✅ Se crea Auto de EJECUTORIA (paso final del proceso)
   - ✅ VOCAL firma el Auto de Ejecutoria
   - Entonces: SIM_ESTADO='CONCLUIDO'

### Visualización en dashboards:
- Color **AZUL** (`PARA_AGENDA`): Sumarios nuevos sin agendar
- Color **AMARILLO** (`PROCESO_EN_EL_TPE`): Sumarios activos en el tribunal
- Color **ROJO** (`EN_APELACION_TSP`): Sumarios apelados ante TSP
- Color **GRIS** (`CONCLUIDO`): Casos terminados (archivados)

---

## Tipos de Resolución (RES_TIPO)

Incluye: ARCHIVO_OBRADOS, ADMINISTRATIVO, SANCIONES_DISCIPLINARIAS,
SANCION_ARRESTO, SANCION_LETRA_B, SANCION_RETIRO_OBLIGATORIO, SANCION_BAJA,
SOLICITUD_LETRA_D, SOLICITUD_LICENCIA_MAXIMA, SOLICITUD_ASCENSO,
SOLICITUD_RESTITUCION_ANTIGUEDAD, SOLICITUD_RESTITUCION_DE_DERECHOS_PROFESIONALES,
SOLICITUD_ART_114, SOLICITUD_ART_117, SOLICITUD_ART_118, OTRO.

---

## Tipos de Auto TPE (TPE_TIPO)

SOBRESEIDO | NULIDAD_OBRADOS | SANCION_ARRESTO | SANCION_LETRA_B |
SANCION_RETIRO_OBLIGATORIO | AUTO_CUMPLIMIENTO | AUTO_EJECUTORIA |
AUTO_EXCUSA | AUTO_RECHAZO_RECURSO

---

## Buscador (v3.3.1) — Reportes de Historial

**Cambios recientes:**
- **PDF directo** (no ZIP): Reporte unificado con toda la información
- **Estadísticas simplificadas**: Solo Sumarios, Resoluciones, Autos TPE
- **Actuados por Sumario**: Vista detallada de cada documento:
  - Nº Resolución + link descarga
  - Fecha, Tipo, Notificación
  - Auto TPE: Disposición, Notificación, Memorandum
  - Objeto completo del sumario (no truncado)

**Archivos:** `buscador_views.py`, `dashboard_buscador.html`, `export_views.py`

---

## Correcciones importantes ya aplicadas

1. **SIM_FECTPE → SIM_FECING**: El campo de fecha se renombró correctamente.
2. **id_abog sacado de SIM**: El abogado NO va directo en el SIM, va en `ABOG_SIM` (tabla puente).
3. **Secretario de Actas**: Se agregó como cargo en `VOCAL_TPE` y como FK en `DICTAMEN`.
4. **DICTAMEN tiene FK a PM**: Para mostrar el nombre del implicado (no del abogado).
5. **RR y AUTOTPE tienen FK a ABOG**: El abogado puede ser diferente en cada documento.
6. **Todos los textos en MAYÚSCULAS**: El método `save()` de cada modelo lo hace automáticamente.
7. **Grados y armas en MAYÚSCULAS**: Importación masiva con Excel (`generar_plantilla_historico.py`).
8. **Custodia v3**: Sistema completo de trazabilidad entre Admin2, Abogados, Vocales.
9. **Ejecutoria**: Autos sin agenda previa, flujo simplificado para conclusión.
10. **AUTOTSP/RecursoTSP**: Mantienen para compatibilidad histórica pero NO se muestran en estadísticas.
11. **Admin nativo de Django (Abril 21 2026)**: Se restauró el panel de admin al estilo Django estándar (removidas personalizaciones de admin.py y desactivado admin_custom.css). El dashboard `/panel-admin/dashboard/` sigue siendo el panel principal personalizado del sistema.

---

## Pendientes / Mejoras Futuras (actualizar al completar)

### Buscador
- [ ] Dashboard buscador: mostrar filtro por fecha de ingreso del SIM
- [ ] Historial: agregar opción de descarga en formato CSV
- [ ] Reportes: agregar gráficas de estadísticas por año/mes

### Modelos y Base de Datos
- [ ] Agregar arma LOGÍSTICA en `ARMA_CHOICES` de PM
- [ ] Campo `SIM_CAUSA_ESPECIFICA` para detallar causa más allá del tipo

### Dashboards
- [ ] Dashboard Abogado: mostrar todos los militares implicados en cada sumario
- [ ] Dashboard Admin1: vista de "Sumarios Pendientes de Ejecutoria"
- [ ] Dashboard Admin2: Indicador de "Carpetas con Demora en Entrega"

### Documentación
- [ ] Crear manual de usuario para cada rol
- [ ] Documentar campos calculados automáticamente (plazos, numeración)
- [ ] Guía de migración de datos históricos con `generar_plantilla_historico.py`

### Mejoras en Flujo
- [ ] Notificación automática cuando demora custodia > 7 días
- [ ] Recordatorio de plazos legales (RR, RAP)
- [ ] Auditoria: registrar quién cambió qué y cuándo

---

## Estructura de archivos clave (v3.3)

```
TPEsystem/
├── CLAUDE.md                          ← ESTE ARCHIVO (memoria actual)
├── TO_DO.py                           ← Lista de tareas pendientes
├── EJEMPLOS_CONSULTAS.txt
├── tpe_app/
│   ├── models.py                      ← Modelos: PM, SIM, AUTOTPE, DICTAMEN, Resolucion, etc.
│   ├── forms.py                       ← Formularios (creación de SIM, Resoluciones, etc.)
│   ├── urls.py                        ← Rutas: admin1/, admin2/, admin3/, abogado/, vocal/, buscador/, ayudante/
│   ├── views/
│   │   ├── admin1_views.py            ← Ingresa SIM, asigna abogados, crea agendas
│   │   ├── admin2_views.py            ← Custodia: entrega/recepción de carpetas
│   │   ├── admin3_views.py            ← Notificaciones
│   │   ├── abogado_views.py           ← Dictámenes, Resoluciones, Autos (ABOG1/2/3)
│   │   ├── abogado_documentos_views.py ← Crear RES, RR, AUTOTPE, Auto Excusa, Ejecutoria
│   │   ├── vocal_views.py             ← Confirmar dictámenes (Secretario de Actas)
│   │   ├── buscador_views.py          ← Historial personal (reportes PDF/Excel)
│   │   ├── ayudante_views.py          ← Registrar RES/RR/RAP/RAEE históricas
│   │   ├── export_views.py            ← PDF y Excel del buscador
│   │   ├── ejecutoria_views.py        ← Auto de Ejecutoria
│   │   ├── auth_views.py              ← Login/Logout
│   ├── templates/
│   │   ├── dashboard_*.html           ← Dashboards por rol
│   │   ├── dashboard_buscador.html    ← Buscador con actuados por sumario
│   │   └── ... (otros templates)
│   ├── migrations/                    ← Cambios de BD (Django)
│   ├── queries/
│   │   └── historial_personal.py      ← Consultas ORM reutilizables
│   └── decorators.py                  ← @rol_requerido para control de acceso
├── config/
│   └── settings.py                    ← Configuración Django, BD, SECRET_KEY
├── requirements.txt
└── manage.py                          ← Django CLI
```

**Accesos rápidos por rol:**
- **ADMIN1**: `admin1_dashboard` (urls.py:24)
- **ADMIN2**: `admin2_dashboard` (urls.py:25)
- **ADMIN3**: `admin3_dashboard` (urls.py:26)
- **ABOG**: `abogado_dashboard` (urls.py:12)
- **VOCAL**: `vocal_dashboard` (urls.py:29)
- **AYUDANTE**: `ayudante_dashboard` (urls.py:34)
- **BUSCADOR**: `buscador_dashboard` (urls.py:23)

---

## Notas de desarrollo

- Base de datos: MySQL (configurada en settings.py, credenciales en .env)
- ORM: siempre usar Django ORM, nunca SQL crudo
- Las migraciones van en `tpe_app/migrations/`
- Para importación masiva de datos: usar `generar_plantilla_historico.py` → genera Excel
- Feriados Bolivia 2026 ya configurados en `models.py` para cálculo de días hábiles
