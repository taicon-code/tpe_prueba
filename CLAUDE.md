# CLAUDE.md — Sistema TPE (Tribunal de Personal del Ejército)
# Este archivo es leído automáticamente por Claude Code en cada sesión.
# Actualízalo cada vez que aprendas algo nuevo sobre el flujo militar.

---

## ¿Qué es este sistema?

Sistema de gestión de **Sumarios Informativos Militares (SIM)** del
**Tribunal de Personal del Ejército (TPE)** de Bolivia.
Tecnología: Django + MySQL + Bootstrap 5.

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

## Roles de usuario del sistema

| Rol            | Vista principal | Descripción |
|----------------|-----------------|-------------|
| Administrador  | `admin_views.py` | Control total del sistema |
| Abogado        | `abogado_views.py` | Gestiona dictámenes, resoluciones, autos de sus sumarios asignados |
| Vocal TPE      | `vocal_views.py` | Secretario de Actas confirma dictámenes |
| Administrativo | `administrativo_views.py` | Ingreso de SIM, PM, agenda |
| Buscador       | `buscador_views.py` | Consulta historial de personal |

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

## Estados del SIM

| Estado | Significado |
|--------|-------------|
| `PARA_AGENDA` | Esperando ser incluido en una agenda (color: azul/primary) |
| `PROCESO_EN_EL_TPE` | En proceso activo (color: amarillo/warning) |
| `EN_APELACION_TSP` | Apelado ante el TSP (color: rojo/danger) |
| `CONCLUIDO` | Proceso terminado |
| `OBSERVADO` | Observado/pendiente de corrección |

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

## Correcciones importantes ya aplicadas

1. **SIM_FECTPE → SIM_FECING**: El campo de fecha se renombró correctamente.
2. **id_abog sacado de SIM**: El abogado NO va directo en el SIM, va en `ABOG_SIM` (tabla puente), porque un abogado no realiza cada sumario, sino las resoluciones y autos.
3. **Secretario de Actas**: Se agregó como cargo en `VOCAL_TPE` y como FK en `DICTAMEN` para que confirme o modifique el dictamen.
4. **DICTAMEN tiene FK a PM**: Para mostrar el nombre del implicado (no del abogado) al crear el dictamen.
5. **RR y AUTOTPE tienen FK a ABOG**: El abogado del RR puede ser diferente al de la RES.
6. **Todos los textos en MAYÚSCULAS**: El método `save()` de cada modelo convierte automáticamente.
7. **Grados y armas en MAYÚSCULAS**: Importación masiva con Excel (`generar_plantilla_historico.py`).

---

## Pendientes (TO_DO.py — actualizar aquí cuando se completen)

- [ ] Agregar arma LOGÍSTICA en `ARMA_CHOICES` de PM
- [ ] Dashboard abogado: en panel de sumarios asignados mostrar todos los militares implicados
- [ ] Al crear dictamen: mostrar nombre de los implicados, no del abogado
- [ ] Botón "crear dictamen" en el dashboard del abogado: sacar el botón de la parte superior
- [ ] Resolución con auto-numeración (botón que genere número automático ej: 52/26)
- [ ] Tipo de Resolución: agregar ART. 118 y ADMINISTRATIVO para ascenso/frontera
- [ ] Tipo de Auto: agregar REHABILITACION DE DERECHOS PROFESIONALES

---

## Estructura de archivos clave

```
tpe_prueba/
├── CLAUDE.md                    ← ESTE ARCHIVO (memoria de Claude)
├── TO_DO.py                     ← Lista de tareas pendientes
├── EJEMPLOS_CONSULTAS.txt       ← Ejemplos de uso del Django shell
├── tpe_app/
│   ├── models.py                ← Modelos Django (fuente de verdad de la BD)
│   ├── resumen_choices.py       ← Tipos de causa del sumario
│   ├── forms.py                 ← Formularios Django
│   ├── urls.py                  ← URLs de la app
│   ├── views/
│   │   ├── abogado_views.py     ← Vistas del abogado
│   │   ├── admin_views.py       ← Vistas del administrador
│   │   ├── vocal_views.py       ← Vistas del secretario de actas/vocales
│   │   ├── administrativo_views.py
│   │   ├── buscador_views.py
│   │   └── auth_views.py
│   ├── queries/
│   │   └── historial_personal.py ← Consultas de historial (ver EJEMPLOS_CONSULTAS.txt)
│   └── templates/               ← Templates HTML Bootstrap 5
├── config/
│   └── settings.py              ← Configuración Django
└── requirements.txt
```

---

## Notas de desarrollo

- Base de datos: MySQL (configurada en settings.py, credenciales en .env)
- ORM: siempre usar Django ORM, nunca SQL crudo
- Las migraciones van en `tpe_app/migrations/`
- Para importación masiva de datos: usar `generar_plantilla_historico.py` → genera Excel
- Feriados Bolivia 2026 ya configurados en `models.py` para cálculo de días hábiles
