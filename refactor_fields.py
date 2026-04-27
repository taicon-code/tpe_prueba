"""
Script de refactorización: reemplaza todos los nombres de campos antiguos
por los nuevos nombres snake_case en todos los .py y .html del proyecto.
Ejecutar UNA SOLA VEZ desde la raíz del proyecto.
"""

import os
import re

# Directorio raíz del proyecto (ajustar si se ejecuta desde otro lugar)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(BASE_DIR, 'tpe_app')

# ============================================================
# MAPEO COMPLETO: viejo → nuevo
# IMPORTANTE: ordenar de más largo a más corto para evitar
# sustituciones parciales (ej: TPE_TIPO_NOTIF antes que TPE_TIPO)
# ============================================================
REPLACEMENTS = [
    # ── SIM ──
    ('SIM_MOTIVO_REAPERTURA', 'motivo_reapertura'),
    ('SIM_AUTOFINAL',         'auto_final'),
    ('SIM_FECREG',            'fecha_registro'),
    ('SIM_FECING',            'fecha_ingreso'),
    ('SIM_ESTADO',            'estado'),
    ('SIM_FASE',              'fase'),
    ('SIM_OBJETO',            'objeto'),
    ('SIM_RESUM',             'resumen'),
    ('SIM_TIPO',              'tipo'),
    ('SIM_VERSION',           'version'),
    ('SIM_ORIGEN',            'origen'),
    ('SIM_COD',               'codigo'),

    # ── PM ──
    ('PM_ESCALAFON',   'escalafon'),
    ('PM_NO_ASCENDIO', 'no_ascendio'),
    ('PM_PROMOCION',   'anio_promocion'),
    ('PM_NOMBRE',      'nombre'),
    ('PM_PATERNO',     'paterno'),
    ('PM_MATERNO',     'materno'),
    ('PM_ESTADO',      'estado'),
    ('PM_GRADO',       'grado'),
    ('PM_ARMA',        'arma'),
    ('PM_ESPEC',       'especialidad'),
    ('PM_FOTO',        'foto'),
    ('PM_CI',          'ci'),

    # ── ABOG ──
    ('AB_GRADO',    'grado'),
    ('AB_NOMBRE',   'nombre'),
    ('AB_PATERNO',  'paterno'),
    ('AB_MATERNO',  'materno'),
    ('AB_ARMA',     'arma'),
    ('AB_ESPEC',    'especialidad'),
    ('AB_CI',       'ci'),

    # ── PM_SIM ──
    ('PMSIM_GRADO_EN_FECHA', 'grado_en_fecha'),

    # ── AGENDA ──
    ('AG_FECPROG', 'fecha_prog'),
    ('AG_FECREAL', 'fecha_real'),
    ('AG_ESTADO',  'estado'),
    ('AG_TIPO',    'tipo'),
    ('AG_NUM',     'numero'),

    # ── DICTAMEN ──
    ('DIC_CONCL_SEC',   'conclusion_secretario'),
    ('DIC_CONFIR_FEC',  'fecha_confirmacion'),
    ('DIC_ESTADO',      'estado'),
    ('DIC_CONCL',       'conclusion'),
    ('DIC_NUM',         'numero'),

    # ── AUTOTPE ──
    ('TPE_MEMO_ENTREGA', 'memo_fecha_entrega'),
    ('TPE_MEMO_NUM',     'memo_numero'),
    ('TPE_MEMO_FEC',     'memo_fecha'),
    ('TPE_TIPO_NOTIF',   'tipo_notif'),
    ('TPE_FECNOT',       'fecha_notif'),
    ('TPE_HORNOT',       'hora_notif'),
    ('TPE_RESOL',        'texto'),
    ('TPE_TIPO',         'tipo'),
    ('TPE_FEC',          'fecha'),
    ('TPE_NUM',          'numero'),
    ('TPE_NOT',          'notif_a'),

    # ── AUTOTSP ──
    ('TSP_TIPO_NOTIF',   'tipo_notif'),
    ('TSP_FECNOT',       'fecha_notif'),
    ('TSP_HORNOT',       'hora_notif'),
    ('TSP_RESOL',        'texto'),
    ('TSP_TIPO',         'tipo'),
    ('TSP_FEC',          'fecha'),
    ('TSP_NUM',          'numero'),
    ('TSP_NOT',          'notif_a'),

    # ── Resolucion ──
    ('RES_FECLIMITE',    'fecha_limite'),
    ('RES_FECPRESEN',    'fecha_presentacion'),
    ('RES_TIPO_NOTIF',   'tipo_notif'),
    ('RES_FECNOT',       'fecha_notif'),
    ('RES_HORNOT',       'hora_notif'),
    ('RES_INSTANCIA',    'instancia'),
    ('RES_RESOL',        'texto'),
    ('RES_RESUM',        'resumen'),
    ('RES_TIPO',         'tipo'),
    ('RES_FEC',          'fecha'),
    ('RES_NUM',          'numero'),
    ('RES_NOT',          'notif_a'),

    # ── RecursoTSP ──
    ('TSP_INSTANCIA',    'instancia'),
    ('TSP_FECLIMITE',    'fecha_limite'),
    ('TSP_FECPRESEN',    'fecha_presentacion'),
    ('TSP_FECOFI',       'fecha_oficio'),
    ('TSP_OFI',          'numero_oficio'),
    ('TSP_RESUM',        'resumen'),   # se eliminó del modelo pero puede quedar en templates

    # ── DocumentoAdjunto ──
    ('DOC_ID_REG',    'registro_id'),
    ('DOC_FECREG',    'fecha_registro'),
    ('DOC_TABLA',     'tabla'),
    ('DOC_RUTA',      'archivo'),
    ('DOC_NOMBRE',    'nombre'),
    ('DOC_TIPO',      'tipo'),

    # ── PKs explícitos ──
    ('.pm_id',   '.id'),    # acceso al PK de PM como atributo
    ('.abog_id', '.id'),    # acceso al PK de ABOG como atributo

    # ── get_* helpers de display (Django autogenera estos con nuevos nombres) ──
    ('get_PM_GRADO_display',   'get_grado_display'),
    ('get_AG_TIPO_display',    'get_tipo_display'),
    ('get_AG_ESTADO_display',  'get_estado_display'),
    ('get_TPE_TIPO_display',   'get_tipo_display'),
    ('get_TSP_TIPO_display',   'get_tipo_display'),
    ('get_RES_INSTANCIA_display', 'get_instancia_display'),
    ('get_TSP_INSTANCIA_display', 'get_instancia_display'),
    ('get_DOC_TABLA_display',  'get_tabla_display'),
]

# Archivos a omitir (ya reescritos o no deben tocarse)
SKIP_FILES = {
    'models.py',
    'forms.py',
    'refactor_fields.py',
}

# Extensiones a procesar
EXTENSIONS = {'.py', '.html'}


def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    changed = []
    skipped = []

    for root, dirs, files in os.walk(TARGET_DIR):
        # Omitir directorios de migraciones
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git')]

        for fname in files:
            ext = os.path.splitext(fname)[1]
            if ext not in EXTENSIONS:
                continue
            if fname in SKIP_FILES:
                skipped.append(fname)
                continue

            fpath = os.path.join(root, fname)
            try:
                if process_file(fpath):
                    rel = os.path.relpath(fpath, BASE_DIR)
                    changed.append(rel)
            except Exception as e:
                print(f'  ERROR en {fpath}: {e}')

    # También procesar el directorio queries/ si existe
    queries_dir = os.path.join(BASE_DIR, 'tpe_app', 'queries')
    if os.path.isdir(queries_dir):
        for fname in os.listdir(queries_dir):
            if fname.endswith('.py') and fname not in SKIP_FILES:
                fpath = os.path.join(queries_dir, fname)
                try:
                    if process_file(fpath):
                        changed.append(os.path.relpath(fpath, BASE_DIR))
                except Exception as e:
                    print(f'  ERROR en {fpath}: {e}')

    print(f'\nArchivos modificados: {len(changed)}')
    for f in sorted(changed):
        print(f'   {f}')

    if skipped:
        print(f'\nOmitidos (ya reescritos): {", ".join(skipped)}')


if __name__ == '__main__':
    main()
