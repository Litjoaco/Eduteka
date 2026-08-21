/* ==========================================================================
   EDUTEKA - SOLICITAR ACCESO JS (BUSCADOR ENRIQUECIDO & PREVIEW CARD)
   ========================================================================== */

let colegiosCache = [];
const busquedaInput = document.getElementById('busqueda_colegio');
const dropdown = document.getElementById('suggestionsDropdown');
const colegioIdHidden = document.getElementById('colegio_id_hidden');
const searchWrapper = document.getElementById('searchWrapper');
const selectedPreview = document.getElementById('selectedSchoolPreview');
let searchTimeout;

document.addEventListener('DOMContentLoaded', function() {
    // Buscar colegios al escribir o hacer focus
    if (busquedaInput) {
        busquedaInput.addEventListener('focus', function() {
            if (this.value.trim().length === 0) {
                cargarColegios('');
            }
        });

        busquedaInput.addEventListener('input', function() {
            const q = this.value.trim();
            colegioIdHidden.value = '';
            busquedaInput.classList.remove('error');
            clearTimeout(searchTimeout);
            
            searchTimeout = setTimeout(() => {
                cargarColegios(q);
            }, 250);
        });
    }

    // Cerrar dropdown al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (searchWrapper && !searchWrapper.contains(e.target) && dropdown && !dropdown.contains(e.target)) {
            cerrarDropdown();
        }
    });

    // Validación y animación al enviar formulario
    const form = document.getElementById('solicitudForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!colegioIdHidden.value) {
                e.preventDefault();
                alert('Por favor, busca y selecciona tu colegio de la lista.');
                if (searchWrapper.style.display === 'none') {
                    cambiarColegio();
                }
                busquedaInput.classList.add('error');
                busquedaInput.focus();
                return false;
            }

            const rol = document.getElementById('rol_seleccionado').value;
            if (!rol) {
                e.preventDefault();
                alert('Por favor, selecciona tu rol en la institución.');
                const rolesGrid = document.querySelector('.roles-grid');
                rolesGrid.classList.add('error');
                rolesGrid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return false;
            }

            const btn = document.getElementById('btnSubmitSolicitud');
            const txt = document.getElementById('btnSubmitText');
            const icon = document.getElementById('btnSubmitIcon');
            const spinner = document.getElementById('btnSubmitSpinner');

            btn.disabled = true;
            txt.textContent = 'Enviando solicitud...';
            icon.classList.add('d-none');
            spinner.classList.remove('d-none');
        });
    }
});

/* ── Cargar Colegios vía API ── */
function cargarColegios(query) {
    fetch(`/api/buscar-colegios/?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            colegiosCache = data;
            renderSugerencias(data, query);
        })
        .catch(err => {
            console.error("Error al buscar colegios:", err);
            cerrarDropdown();
        });
}

/* ── Renderizar Sugerencias con Tarjetas Enriquecidas ── */
function renderSugerencias(colegios, query) {
    if (!dropdown) return;

    if (!colegios || colegios.length === 0) {
        dropdown.innerHTML = `
            <div class="p-3 text-center text-muted" style="font-size:0.88rem;">
                <i class="bi bi-building-slash fs-4 d-block mb-1 text-secondary"></i>
                No se encontraron colegios con "<strong>${esc(query)}</strong>".<br>
                <span class="extra-small">Verifica el nombre o contacta a tu sostenedor.</span>
            </div>
        `;
        dropdown.style.display = 'block';
        return;
    }

    let html = `
        <div class="suggestion-header-hint">
            <i class="bi bi-buildings me-1"></i> ${query ? 'Resultados de búsqueda' : 'Colegios disponibles'} (${colegios.length})
        </div>
    `;

    colegios.forEach(c => {
        const logoHtml = c.logo_url 
            ? `<img src="${esc(c.logo_url)}" alt="${esc(c.nombre)}" class="school-logo-avatar">`
            : `<div class="school-logo-avatar" style="background:${esc(c.color_principal || '#7C5CFC')};">${esc(c.nombre.charAt(0).toUpperCase())}</div>`;

        const shortNameBadge = c.nombre_corto ? `<span class="badge bg-light text-dark border">${esc(c.nombre_corto)}</span>` : '';
        const typeBadge = c.tipo_institucion ? `<span class="school-type-pill">${esc(c.tipo_institucion)}</span>` : '';
        const sloganHtml = c.eslogan ? `<div class="school-item-slogan">"${esc(c.eslogan)}"</div>` : '';
        
        const locParts = [];
        if (c.ciudad_comuna) locParts.push(c.ciudad_comuna);
        if (c.region) locParts.push(c.region);
        const locationStr = locParts.join(', ') || 'Chile';

        html += `
            <div class="suggestion-item-pro" onclick="seleccionarColegioPorId(${c.id})">
                ${logoHtml}
                <div class="school-info-body">
                    <div class="school-item-name">
                        <span>${esc(c.nombre)}</span>
                        ${shortNameBadge}
                        ${typeBadge}
                    </div>
                    ${sloganHtml}
                    <div class="school-item-location">
                        <i class="bi bi-geo-alt"></i> ${esc(locationStr)}
                    </div>
                </div>
            </div>
        `;
    });

    dropdown.innerHTML = html;
    dropdown.style.display = 'block';
}

/* ── Seleccionar Colegio y Mostrar Preview Card ── */
function seleccionarColegioPorId(id) {
    const colegio = colegiosCache.find(c => c.id === id);
    if (!colegio) return;

    colegioIdHidden.value = colegio.id;
    busquedaInput.value = colegio.nombre;
    cerrarDropdown();

    // Actualizar Previsualización
    const previewLogo = document.getElementById('selectedLogoContainer');
    const previewTitle = document.getElementById('selectedTitle');
    const previewSlogan = document.getElementById('selectedSlogan');
    const previewLocation = document.getElementById('selectedLocation');
    const previewType = document.getElementById('selectedType');

    if (colegio.logo_url) {
        previewLogo.innerHTML = `<img src="${esc(colegio.logo_url)}" alt="${esc(colegio.nombre)}" class="selected-logo">`;
    } else {
        previewLogo.innerHTML = `<div class="selected-logo" style="background:${esc(colegio.color_principal || '#7C5CFC')};">${esc(colegio.nombre.charAt(0).toUpperCase())}</div>`;
    }

    previewTitle.textContent = colegio.nombre;
    if (colegio.nombre_corto) {
        previewTitle.textContent += ` (${colegio.nombre_corto})`;
    }

    if (colegio.eslogan) {
        previewSlogan.textContent = `"${colegio.eslogan}"`;
        previewSlogan.style.display = 'block';
    } else {
        previewSlogan.style.display = 'none';
    }

    const locParts = [];
    if (colegio.ciudad_comuna) locParts.push(colegio.ciudad_comuna);
    if (colegio.region) locParts.push(colegio.region);
    previewLocation.innerHTML = `<i class="bi bi-geo-alt text-primary"></i> ${esc(locParts.join(', ') || 'Chile')}`;
    previewType.textContent = colegio.tipo_institucion || 'Establecimiento Educacional';

    // Ocultar input y mostrar preview card
    searchWrapper.style.display = 'none';
    selectedPreview.style.display = 'block';
}

/* ── Cambiar Colegio Seleccionado ── */
function cambiarColegio() {
    colegioIdHidden.value = '';
    busquedaInput.value = '';
    selectedPreview.style.display = 'none';
    searchWrapper.style.display = 'block';
    busquedaInput.focus();
    cargarColegios('');
}

/* ── Cerrar Dropdown ── */
function cerrarDropdown() {
    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.innerHTML = '';
    }
}

/* ── Selección de Rol ── */
function seleccionarRol(card) {
    document.querySelectorAll('.role-card').forEach(c => c.classList.remove('selected'));
    card.classList.add('selected');
    document.getElementById('rol_seleccionado').value = card.dataset.rol;
    document.querySelector('.roles-grid').classList.remove('error');
}

function esc(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}