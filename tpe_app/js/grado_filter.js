// ============================================================
// tpe_app/static/tpe_app/js/grado_filter.js
// Filtra el campo Grado según el Escalafón seleccionado
// ============================================================

const GRADOS_POR_ESCALAFON = {
    'GENERAL': [
        ['GENERAL_EJERCITO',  'General de Ejército'],
        ['GENERAL_DIVISION',  'General de División'],
        ['GENERAL_BRIGADA',   'General de Brigada'],
    ],
    'OFICIAL_SUPERIOR': [
        ['CORONEL',  'Coronel'],
        ['TCNEL',    'Teniente Coronel'],
        ['MAYOR',    'Mayor'],
    ],
    'OFICIAL_SUBALTERNO': [
        ['CAPITAN',     'Capitán'],
        ['TENIENTE',    'Teniente'],
        ['SUBTENIENTE', 'Subteniente'],
    ],
    'SUBOFICIAL': [
        ['SUBOFICIAL_MAYOR',   'Suboficial Mayor'],
        ['SUBOFICIAL_MAESTRE', 'Suboficial Maestre'],
        ['SUBOFICIAL_1RO',     'Suboficial Primero'],
        ['SUBOFICIAL_2DO',     'Suboficial Segundo'],
        ['SUBOFICIAL_INICIAL', 'Suboficial Inicial'],
    ],
    'SARGENTO': [
        ['SARGENTO_1RO',     'Sargento Primero'],
        ['SARGENTO_2DO',     'Sargento Segundo'],
        ['SARGENTO_INICIAL', 'Sargento Inicial'],
        ['CABO',             'Cabo'],
        ['SOLDADO',          'Soldado'],
    ],
    'EMPLEADO_CIVIL': [
        ['PROF_V',   'Prof. V'],  ['PROF_IV',  'Prof. IV'],
        ['PROF_III', 'Prof. III'],['PROF_II',  'Prof. II'],  ['PROF_I',   'Prof. I'],
        ['TEC_V',    'Tec. V'],   ['TEC_IV',   'Tec. IV'],
        ['TEC_III',  'Tec. III'], ['TEC_II',   'Tec. II'],   ['TEC_I',    'Tec. I'],
        ['ADM_V',    'Adm. V'],   ['ADM_IV',   'Adm. IV'],
        ['ADM_III',  'Adm. III'], ['ADM_II',   'Adm. II'],   ['ADM_I',    'Adm. I'],
        ['APAD_V',   'Apad. V'],  ['APAD_IV',  'Apad. IV'],
        ['APAD_III', 'Apad. III'],['APAD_II',  'Apad. II'],  ['APAD_I',   'Apad. I'],
    ],
};

document.addEventListener('DOMContentLoaded', function () {
    const escalafon = document.getElementById('id_PM_ESCALAFON');
    const grado     = document.getElementById('id_PM_GRADO');

    if (!escalafon || !grado) return;

    function filtrarGrados() {
        const seleccionado = escalafon.value;
        const grados       = GRADOS_POR_ESCALAFON[seleccionado] || [];
        const valorActual  = grado.value;

        grado.innerHTML = '<option value="">---------</option>';

        grados.forEach(function ([valor, texto]) {
            const opt    = document.createElement('option');
            opt.value    = valor;
            opt.textContent = texto;
            if (valor === valorActual) opt.selected = true;
            grado.appendChild(opt);
        });
    }

    escalafon.addEventListener('change', filtrarGrados);
    filtrarGrados(); // ejecutar al cargar la página
});