// ============================================================
//  filtro_grado.js — Filtra grados según escalafón
//  Versión 2.0 — Sin dependencia de jQuery
// ============================================================

const GRADOS_POR_ESCALAFON = {
    'GENERAL': [
        'GRAL. EJTO.', 'GRAL. DIV.', 'GRAL. BRIG.'
    ],
    'OFICIAL SUPERIOR': [
        'CNL.', 'TCNL.', 'MY.'
    ],
    'OFICIAL SUBALTERNO': [
        'CAP.', 'TTE.', 'SBTTE.'
    ],
    'SUBOFICIAL': [
        'SOF. MTRE.', 'SOF. MY.',
        'SOF. 1RO.', 'SOF. 2DO.', 'SOF. INCL.'
    ],
    'SARGENTO': [
        'SGTO. 1RO.', 'SGTO. 2DO.', 'SGTO. INCL.'
    ],
    'TROPA': [
        'CABO', 'DGTE.', 'SLDO.'
    ],
    'EMPLEADO CIVIL': [
        'PROF. V','PROF. IV','PROF. III','PROF. II','PROF. I',
        'TEC. V','TEC. IV','TEC. III','TEC. II','TEC. I',
        'ADM. V','ADM. IV','ADM. III','ADM. II','ADM. I',
        'APAD. V','APAD. IV','APAD. III','APAD. II','APAD. I'
    ]
};

let todasLasOpciones = [];

function guardarOpciones() {
    const selectGrado = document.getElementById('id_grado');
    if (!selectGrado) return;
    todasLasOpciones = [];
    for (let opt of selectGrado.options) {
        todasLasOpciones.push({ value: opt.value, text: opt.text });
    }
}

function filtrarGrados() {
    const selectEscalafon = document.getElementById('id_escalafon');
    const selectGrado     = document.getElementById('id_grado');
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
    const selectEscalafon = document.getElementById('id_escalafon');
    const selectGrado     = document.getElementById('id_grado');
    if (!selectEscalafon || !selectGrado) return;

    guardarOpciones();
    filtrarGrados();

    selectEscalafon.addEventListener('change', function() {
        document.getElementById('id_grado').value = '';
        filtrarGrados();
    });
}

document.addEventListener('DOMContentLoaded', iniciarFiltro);