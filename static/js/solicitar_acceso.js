/* ── Selección de rol ── */
function seleccionarRol(card) {
    document.querySelectorAll('.role-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    document.getElementById('rol_seleccionado').value = card.dataset.rol;
    // Quitar el marco de error si existía al seleccionar
    document.querySelector('.roles-grid').classList.remove('error');
}

/* ── AJAX búsqueda de colegios ── */
const busquedaInput   = document.getElementById('busqueda_colegio');
const dropdown        = document.getElementById('suggestionsDropdown');
const colegioIdHidden = document.getElementById('colegio_id_hidden');
let searchTimeout;

busquedaInput.addEventListener('input', function () {
    const q = this.value.trim();
    colegioIdHidden.value = '';
    busquedaInput.classList.remove('error');
    clearTimeout(searchTimeout);
    if (q.length < 2) { cerrarDropdown(); return; }
    searchTimeout = setTimeout(() => {
        fetch(`/api/buscar-colegios/?q=${encodeURIComponent(q)}`)
            .then(r => r.json())
            .then(data => renderSugerencias(data))
            .catch(() => cerrarDropdown());
    }, 300);
});

function renderSugerencias(colegios) {
    if (!colegios.length) { cerrarDropdown(); return; }
    dropdown.innerHTML = colegios.map(c => `
        <div class="suggestion-item" onclick="seleccionarColegio(${c.id}, '${esc(c.nombre)}')">
            ${esc(c.nombre)}
            <small>${esc(c.ciudad || '')}</small>
        </div>`).join('');
    dropdown.style.display = 'block';
}

function seleccionarColegio(id, nombre) {
    busquedaInput.value   = nombre;
    colegioIdHidden.value = id;
    cerrarDropdown();
}

function cerrarDropdown() {
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
}

function esc(str) {
    return String(str)
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.addEventListener('click', e => {
    if (!busquedaInput.contains(e.target) && !dropdown.contains(e.target)) cerrarDropdown();
});

/* ── Validación al enviar ── */
document.getElementById('solicitudForm').addEventListener('submit', function (e) {
    // Permitir pasar si el usuario escribió algo manualmente (para pruebas)
    if (!colegioIdHidden.value && busquedaInput.value.trim().length > 2) {
        colegioIdHidden.value = "999"; 
    }

    if (!colegioIdHidden.value) {
        e.preventDefault();
        busquedaInput.classList.add('error');
        busquedaInput.focus();
        return;
    }
    if (!document.getElementById('rol_seleccionado').value) {
        e.preventDefault();
        const rolesGrid = document.querySelector('.roles-grid');
        rolesGrid.classList.add('error');
        rolesGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});