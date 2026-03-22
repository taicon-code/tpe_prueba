// ============================================================
//  filtro_grado.js — Filtra grados según escalafón
//  Versión 2.0 — Sin dependencia de jQuery
// ============================================================

const GRADOS_POR_ESCALAFON = {
    'GENERAL': [
        'GENERAL_EJERCITO', 'GENERAL_DIVISION', 'GENERAL_BRIGADA'
    ],
    'OFICIAL_SUPERIOR': [
        'CORONEL', 'TCNEL', 'MAYOR'
    ],
    'OFICIAL_SUBALTERNO': [
        'CAPITAN', 'TENIENTE', 'SUBTENIENTE'
    ],
    'SUBOFICIAL': [
        'SUBOFICIAL_MAYOR', 'SUBOFICIAL_MAESTRE',
        'SUBOFICIAL_1RO', 'SUBOFICIAL_2DO', 'SUBOFICIAL_INICIAL'
    ],
    'SARGENTO': [
        'SARGENTO_1RO', 'SARGENTO_2DO', 'SARGENTO_INICIAL'
    ],
    'TROPA': [
        'CABO', 'DRAGONEANTE', 'SOLDADO'
    ],
    'EMPLEADO_CIVIL': [
        'PROF_V','PROF_IV','PROF_III','PROF_II','PROF_I',
        'TEC_V','TEC_IV','TEC_III','TEC_II','TEC_I',
        'ADM_V','ADM_IV','ADM_III','ADM_II','ADM_I',
        'APAD_V','APAD_IV','APAD_III','APAD_II','APAD_I'
    ]
};

let todasLasOpciones = [];

function guardarOpciones() {
    const selectGrado = document.getElementById('id_PM_GRADO');
    if (!selectGrado) return;
    todasLasOpciones = [];
    for (let opt of selectGrado.options) {
        todasLasOpciones.push({ value: opt.value, text: opt.text });
    }
}

function filtrarGrados() {
    const selectEscalafon = document.getElementById('id_PM_ESCALAFON');
    const selectGrado     = document.getElementById('id_PM_GRADO');
    if (!selectEscalafon || !selectGrado) return;

    const escalafon        = selectEscalafon.value;
    const gradoActual      = selectGrado.value;
    const gradosPermitidos = GRADOS_POR_ESCALAFON[escalafon] || [];

    selectGrado.innerHTML = '';

    const optVacia = document.createElement('option');
    optVacia.value = '';
    optVacia.text  = '---------';
    selectGrado.appendChild(optVacia);

    todasLasOpciones.forEach(function(opcion) {
        if (opcion.value === '') return;
        const mostrar = escalafon === '' || gradosPermitidos.includes(opcion.value);
        if (mostrar) {
            const opt = document.createElement('option');
            opt.value    = opcion.value;
            opt.text     = opcion.text;
            if (opcion.value === gradoActual) opt.selected = true;
            selectGrado.appendChild(opt);
        }
    });
}

function iniciarFiltro() {
    const selectEscalafon = document.getElementById('id_PM_ESCALAFON');
    const selectGrado     = document.getElementById('id_PM_GRADO');
    if (!selectEscalafon || !selectGrado) return;

    guardarOpciones();
    filtrarGrados();

    selectEscalafon.addEventListener('change', function() {
        document.getElementById('id_PM_GRADO').value = '';
        filtrarGrados();
    });
}

document.addEventListener('DOMContentLoaded', iniciarFiltro);