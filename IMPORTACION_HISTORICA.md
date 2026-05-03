# Importación de Datos Históricos — Sistema TPE v4.0

## 📋 ¿Qué se importa?

**SOLO ACTUADOS (documentos finales):**
- ✅ Personal Militar (PM)
- ✅ Sumarios (SIM)
- ✅ Resoluciones (1RA y RR)
- ✅ Autos TPE (Ejecutoria, Cumplimiento, Sobreseído, etc.)
- ✅ Recursos TSP (RAP y RAEE)
- ✅ Autos TSP (respuesta a RAP/RAEE)
- ✅ PDFs adjuntos

**NO se importan (se deducen de los actuados):**
- ✗ Abogados asignados
- ✗ Dictámenes
- ✗ Agendas
- ✗ Vocales TPE
- ✗ Custodia interna de carpetas

---

## 🚀 Procedimiento

### Paso 1: Generar plantilla Excel con ejemplos

```bash
python plantilla_importacion_historico.py
```

Esto crea `plantilla_importacion_historico.xlsx` con **8 hojas** ejemplificadas:

| # | Hoja | Contenido |
|---|------|----------|
| 0 | INSTRUCCIONES | Guía y reglas |
| 1 | PM_Historico | Personal Militar (ci, paterno, materno, grado, etc.) |
| 2 | SIM_Historico | Sumarios (codigo, fecha_ingreso, estado, fase, etc.) |
| 3 | PM_SIM | Relación militar ↔ sumario |
| 4 | Resoluciones | 1RA y RR con fechas, notificaciones |
| 5 | Autos_TPE | Autos TPE (con memo si aplica) |
| 6 | Recursos_TSP | RAP y RAEE (con oficio) |
| 7 | Autos_TSP | Autos TSP (respuesta a RAP/RAEE) |
| 8 | Documentos_Adjuntos | PDFs escaneados |

### Paso 2: Completar datos históricos

Abre `plantilla_importacion_historico.xlsx` en Excel/Calc y:

1. **NO edites la hoja 0 (INSTRUCCIONES)** — es solo de referencia
2. Reemplaza los ejemplos en las hojas 1-8 con tus datos reales
3. Mantén las columnas en el mismo orden
4. Rellena solo campos que tengas (otros pueden quedar vacíos)
5. **Fechas siempre en formato ISO: YYYY-MM-DD**

### Paso 3: Ejecutar importación

```bash
# En el servidor o local
python manage.py import_actuados_historicos --file plantilla_importacion_historico.xlsx
```

**Con transacción atómica:** si falla una fila, se revierte todo.

---

## 📌 Orden de Importación (respeta FK automáticamente)

El script importa en este orden:

```
1. PM ← tabla raíz
2. SIM ← contenedor, puede referenciar SIM.origen
3. PM_SIM ← relación, necesita PM + SIM
4. Resoluciones ← necesita SIM + PM
5. Autos TPE ← necesita SIM + PM + Resolucion
6. Recursos TSP ← necesita SIM + PM + Resolucion
7. Autos TSP ← necesita RecursoTSP
8. Documentos Adjuntos ← último (tabla polimórfica)
```

---

## 🔑 Reglas Críticas por Campo

### Personal Militar (PM)

| Campo | Tipo | Regla | Ejemplo |
|-------|------|-------|---------|
| **ci** | CharField(12) | **ÚNICO** — sin espacios ni guiones | `12345678` |
| **paterno, materno** | CharField(50) | Se convierte a MAYÚSCULA automático | `García` → `GARCÍA` |
| **grado** | CharField(20) | Debe estar en la lista de grados válidos | `CAP.`, `SGTO. 1RO.` |
| **anio_promocion** | IntegerField | **CRÍTICO** para cálculos de carrera (puede estar vacío en históricos) | `2005` |
| **arma** | CharField(20) | INF., CAB., ART., ING., COM., INT., SAN., etc. | `INF.` |

### Sumarios (SIM)

| Campo | Tipo | Regla | Ejemplo |
|-------|------|-------|---------|
| **codigo** | CharField(20) | **ÚNICO** — formato recomendado: SIM-AAAA-### | `SIM-2020-001` |
| **fecha_ingreso** | DateField | ISO: YYYY-MM-DD | `2020-01-15` |
| **estado** | CharField | Debe estar en enum válido (ver niveles abajo) | `PROCESO_EN_EL_TPE` |
| **fase** | CharField | Debe corresponder al estado | `EN_DICTAMEN_1RA` |
| **tipo** | CharField | De `TIPO_RESOLUCION` choices | `ADMINISTRATIVO` |
| **origen_id** | IntegerField (FK) | Si es reapertura, debe existir el SIM origen | `2` (ID del SIM original) |

### Resoluciones

| Campo | Tipo | Regla | Ejemplo |
|-------|------|-------|---------|
| **numero** | CharField(10) | Formato `NN/AA` — **ÚNICO por instancia** | `01/20` |
| **instancia** | CharField | **SOLO dos valores:** `'PRIMERA'` o `'RECONSIDERACION'` | `'PRIMERA'` |
| **tipo** | CharField | De `TIPO_RESOLUCION` choices | `SANCIONES_DISCIPLINARIAS` |
| **fecha** | DateField | Fecha de emisión | `2020-03-10` |
| **fecha_presentacion** | DateField | Fecha para cálculo de plazo RR | `2020-03-15` |
| **fecha_limite** | DateField | 15 días hábiles desde presentación | `2020-03-30` |
| **texto** | TextField | Parte resolutiva **en MAYÚSCULA** | `SE ARCHIVAN LOS OBRADOS` |
| **fecha_notif** | DateField | Cuándo se notificó | `2020-03-16` |

### Autos TPE

| Campo | Tipo | Regla | Ejemplo |
|-------|------|-------|---------|
| **numero** | CharField(10) | Formato `NN/AA` | `05/22` |
| **tipo** | CharField | De `TIPO_AUTO_TPE` choices | `AUTO_EJECUTORIA`, `AUTO_CUMPLIMIENTO` |
| **memo_numero** | CharField(20) | Memorándum entregado (puede estar vacío) | `125/2022` |
| **memo_fecha** | DateField | Fecha del memo (puede estar vacío) | `2022-08-15` |
| **memo_fecha_entrega** | DateField | Cuándo se entregó el memo (puede estar vacío) | `2022-08-30` |

### Recursos TSP

| Campo | Tipo | Regla | Ejemplo |
|-------|------|-------|---------|
| **numero_oficio** | CharField(20) | Del oficio de presentación | `0542/2020` |
| **instancia** | CharField | **DOS valores:** `'APELACION'` o `'ACLARACION_ENMIENDA'` | `'APELACION'` |
| **fecha_oficio** | DateField | Fecha del oficio | `2020-05-20` |
| **fecha_presentacion** | DateField | Cuándo se presentó | `2020-05-20` |
| **fecha_limite** | DateField | 3 días hábiles desde oficio | `2020-05-23` |
| **numero** | CharField(20) | Número del recurso (ej: RAP-001/20) | `RAP-001/20` |

---

## 📊 Ejemplos de Transiciones de Estado (para validar datos)

### Ruta SIN apelación (1RA → RR → Ejecutoria)

```
SIM.estado: PARA_AGENDA (inicial)
    ↓
SIM.estado: PROCESO_EN_EL_TPE
SIM.fase: EN_DICTAMEN_1RA
    ↓
Resolucion(instancia='PRIMERA') emitida
SIM.fase: 1RA_RESOLUCION → NOTIFICACION_1RA → NOTIFICADO_1RA
    ↓
RecursoRR presentado (Resolucion con instancia='RECONSIDERACION')
SIM.fase: EN_ESPERA_RR → EN_DICTAMEN_RR → 2DA_RESOLUCION
    ↓
SIM.fase: EN_EJECUTORIA → EJECUTORIA_NOTIFICADA
    ↓
SIM.estado: PROCESO_CONCLUIDO_TPE
SIM.fase: CONCLUIDO
```

### Ruta CON apelación al TSP

```
SIM.estado: PROCESO_EN_EL_TPE (1RA emitida)
    ↓
RecursoTSP(instancia='APELACION') creado
SIM.estado: PROCESO_EN_EL_TSP ← cambio de nivel
SIM.fase: ELEVADO_TSP
    ↓
AutoTSP emitido (confirmación/revocación)
    ↓
RecursoTSP(instancia='ACLARACION_ENMIENDA') opcional
    ↓
AutoTPE de Cumplimiento emitido
SIM.estado: CUMPLIMIENTO_EN_TPE
SIM.fase: EN_CUMPLIMIENTO
    ↓
SIM.estado: PROCESO_CONCLUIDO_TSP_TPE
SIM.fase: CONCLUIDO_TSP_TPE
```

---

## ⚠️ Validaciones Automáticas

El script **valida antes de importar:**

- [ ] PM.ci único y válido
- [ ] SIM.codigo único
- [ ] Resolucion.numero único **por instancia**
- [ ] Fechas en formato ISO
- [ ] FK: PM existe antes de referenciar
- [ ] FK: SIM existe antes de referenciar
- [ ] Estados y fases existen en enum

**Si hay error:** El script muestra la fila problemática y **revierte toda la transacción** (no queda nada importado).

---

## 📝 Ejemplo Completo: Sumario con 1RA + RR

**PM_Historico.xlsx:**
```
ci          paterno     materno     nombre      grado       anio_promocion
12345678    GARCÍA      MIRANDA     JUAN        CAP.        2005
```

**SIM_Historico.xlsx:**
```
id  codigo              fecha_ingreso   estado                tipo                    fase
1   SIM-2020-001        2020-01-15      PROCESO_EN_EL_TPE     SANCIONES_DISCIPLINARIAS    1RA_RESOLUCION
```

**PM_SIM.xlsx:**
```
sim_id  pm_ci       grado_en_fecha
1       12345678    SBTTE.
```

**Resoluciones.xlsx:**
```
sim_id  pm_ci       numero  instancia       tipo                        fecha       fecha_notif
1       12345678    01/20   PRIMERA         SANCIONES_DISCIPLINARIAS    2020-03-10  2020-03-16
1       12345678    02/20   RECONSIDERACION SANCIONES_DISCIPLINARIAS    2020-05-15  2020-05-16
```

---

## 🔧 Troubleshooting

| Error | Causa | Solución |
|-------|-------|----------|
| `KeyError: '1_PM_Historico'` | Hoja no existe en Excel | Verifica nombres exactos de hojas |
| `ValueError: not enough values to unpack` | Columnas faltantes | Revisa encabezados (orden importa) |
| `IntegrityError: Duplicate key` | PM.ci o SIM.codigo duplicados | Verifica unicidad en Excel |
| `ForeignKeyError` | PM o SIM no existe | Importa PM primero, luego SIM |
| `ValueError: invalid date` | Fecha no en YYYY-MM-DD | Reforma todas las fechas en Excel |

---

## 📞 Apoyo

- **CLAUDE.md**: Documentación del sistema
- **MEMORY.md**: Notas de desarrollo acumuladas
- **management/commands/import_actuados_historicos.py**: Código de importación
