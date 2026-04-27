# 📋 Búsqueda por Lotes - v3.5

## ¿Qué es?

Nueva funcionalidad para generar **reportes de antecedentes de múltiples militares** en PDF y Excel, optimizando el trabajo administrativo cuando necesitas antecedentes de 10+ personas.

## Problema que resuelve

**Antes:** Búsqueda individual → reporte de 3/4 de hoja por persona → impresión de 10 hojas para 10 personas.

**Ahora:** Ingresa lista de 10+ apellidos → genera 1 PDF compacto (1-2 hojas) + Excel filtrable.

---

## Cómo usar

### 1. Acceder a Búsqueda por Lotes

Desde el **Buscador** (🔍 Panel Principal → 📋 Búsqueda por Lotes)

### 2. Ingresar lista de militares

**Formato: APELLIDO_PATERNO, APELLIDO_MATERNO** (uno por línea)

```
VARGAS, FLORES
RODRIGUEZ, LOPEZ
GUTIERREZ, SANTOS
HERNANDEZ, MARTINEZ
```

### 3. Buscar militares

Botón "🔍 Buscar Militares" → el sistema busca y muestra resultados

### 4. Descargar reportes

- **📄 Descargar PDF** → Tabla compacta en PDF
- **📊 Descargar Excel** → Tabla filtrable/ordenable

---

## Formato del Reporte

### PDF (Tabla Compacta - 1-2 hojas)

```
═══════════════════════════════════════════════════════════════════════════════════════════════════════════
                    TRIBUNAL DE PERSONAL DEL EJÉRCITO — REPORTE DE ANTECEDENTES POR LOTES
═══════════════════════════════════════════════════════════════════════════════════════════════════════════

GRADO        │ NOMBRE           │ AP           │ AM        │ SIM    │ OBJETO (resumen)      │ ACTUADOS      │ ESTADO
───────────────────────────────────────────────────────────────────────────────────────────────────────────
CAP.         │ Juan Carlos      │ VARGAS       │ FLORES    │ 045/26 │ Abuso de autoridad    │ RES 02/26     │ CONCLUIDO
             │                  │              │           │ 046/26 │ Falsificación de doc  │ RES 03/26     │ EN APELACIÓN
             │                  │              │           │        │                       │ RAP 02/26     │
───────────────────────────────────────────────────────────────────────────────────────────────────────────
TTE.         │ Roberto          │ RODRIGUEZ    │ LOPEZ     │ 048/26 │ Insubordinación       │ PENDIENTE     │ EN PROCESO
───────────────────────────────────────────────────────────────────────────────────────────────────────────
```

**Estructura:**
- Encabezado institucional (COMANDO GENERAL DEL EJÉRCITO)
- Tabla con 8 columnas: Grado, Nombre, AP, AM, SIM, Objeto, Actuados, Estado
- Pie de página con usuario, fecha y número de página
- **Agrupación:** Una fila por sumario (si militar tiene 2 SIM → 2 filas)

### Excel (Tabla Filtrable)

Mismo contenido que PDF pero en hoja de Excel con:
- Encabezados en azul (#185FA5)
- Columnas redimensionadas
- Posibilidad de filtros y ordenamiento

---

## Características

✅ **Búsqueda por AP + AM** (no requiere CI ni nombre exacto)
✅ **Una fila por sumario** (si militar tiene múltiples SIM, los ve todos)
✅ **Actuados comprimidos** (RES 02/26, AUTO 1/26, etc.)
✅ **Estado actual del SIM** (CONCLUIDO, EN PROCESO, EN APELACIÓN, etc.)
✅ **PDF compacto** (10 militares ≈ 1-2 hojas)
✅ **Excel filtrable** (ordenar por grado, estado, etc.)

---

## Archivos Modificados

### Vistas
- **tpe_app/views/buscador_views.py**
  - `busqueda_por_lotes()` → Búsqueda y listado
  - `export_batch_pdf()` → Generación de PDF
  - `export_batch_excel()` → Generación de Excel

### Templates
- **tpe_app/templates/tpe_app/buscador/dashboard_buscador.html**
  - Agregados tabs: "🔍 Búsqueda Individual" | "📋 Búsqueda por Lotes"
  - Sidebar actualizado con ambas opciones

- **tpe_app/templates/tpe_app/buscador/busqueda_lotes.html** (NUEVO)
  - Formulario de ingreso de lista
  - Listado de militares encontrados
  - Botones de exportación

### URLs
- **tpe_app/urls.py**
  - `buscador/lotes/` → Vista principal
  - `buscador/lotes/exportar/pdf/` → Descarga PDF
  - `buscador/lotes/exportar/excel/` → Descarga Excel

### Imports
- **tpe_app/views/__init__.py**
  - Agregadas: `busqueda_por_lotes`, `export_batch_pdf`, `export_batch_excel`

---

## Ejemplos de Uso

### Caso 1: Reporte de 3 militares
```
Ingreso:
VARGAS, FLORES
RODRIGUEZ, LOPEZ
GUTIERREZ, SANTOS

Resultado:
PDF: 1 hoja con tabla (0-3 filas según sumarios por militar)
Excel: Tabla filtrable con mismos datos
```

### Caso 2: Militar con 2 sumarios
```
VARGAS, FLORES
→ Resulta en 2 filas (una por SIM):
  • CAP. Juan Carlos VARGAS FLORES | 045/26 | Abuso | RES 02/26 | CONCLUIDO
  • CAP. Juan Carlos VARGAS FLORES | 046/26 | Falsificación | RES 03/26 | EN APELACIÓN
```

---

## Ventajas

| Aspecto | Individual | Por Lotes |
|--------|-----------|-----------|
| **Tiempo por persona** | 3/4 hoja | 1/8 hoja |
| **10 personas** | 10 hojas | 1-2 hojas |
| **Impresión** | 10 documentos | 1 documento |
| **Filtrado en Excel** | No disponible | ✅ Sí |
| **Archivamiento** | Carpetas separadas | 1 archivo |

---

## Notas Técnicas

- **Búsqueda:** Case-insensitive, por `PM_PATERNO` + `PM_MATERNO`
- **Actuados:** Agrupados por SIM (RES, AUTO, RAP, RAEE)
- **Estado:** Mostrado en última columna (SIM_ESTADO)
- **Objeto:** Truncado a 50 caracteres en PDF para legibilidad
- **Formato:** PDF con fuentes Arial (soporte acentos + ñ)

---

## Próximas mejoras (si aplica)

- [ ] Filtro por rango de fechas (ingreso SIM)
- [ ] Exportación a CSV
- [ ] Búsqueda por CI (si disponible)
- [ ] Búsqueda por Grado
- [ ] Reporte estadístico por estado (CONCLUIDO, EN PROCESO, etc.)

---

**Versión:** 3.5  
**Fecha:** Abril 2026  
**Estado:** ✅ Completado
