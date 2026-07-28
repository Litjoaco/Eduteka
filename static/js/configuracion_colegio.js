document.addEventListener('DOMContentLoaded', () => {
    // Inputs
    const nombreInput = document.getElementById('nombre_oficial');
    const cortoInput = document.getElementById('nombre_corto');
    const esloganInput = document.getElementById('eslogan');
    
    // Preview Elements
    const prevNombre = document.getElementById('prev-nombre');
    const prevCorto = document.getElementById('prev-corto');
    const prevEslogan = document.getElementById('prev-eslogan');
    
    // Live text updates
    if (nombreInput && prevNombre) {
        nombreInput.addEventListener('input', (e) => {
            prevNombre.textContent = e.target.value || 'Colegio Bilingüe Los Andes';
        });
        // Forzar actualización inicial
        nombreInput.dispatchEvent(new Event('input'));
    }
    
    if (cortoInput && prevCorto) {
        cortoInput.addEventListener('input', (e) => {
            prevCorto.textContent = e.target.value || 'CLA';
            prevCorto.style.display = e.target.value ? 'inline-block' : (e.target.placeholder ? 'inline-block' : 'none');
        });
        cortoInput.dispatchEvent(new Event('input'));
    }
    
    if (esloganInput && prevEslogan) {
        esloganInput.addEventListener('input', (e) => {
            prevEslogan.textContent = e.target.value ? `"${e.target.value}"` : '"Formamos líderes para el futuro"';
        });
        esloganInput.dispatchEvent(new Event('input'));
    }

    // File Uploads
    setupFileUpload('logo_input', 'logo_block', 'prev-logo-container');
    setupFileUpload('img_input', 'img_block', 'prev-image-container');
});

function setupFileUpload(inputId, blockId, previewContainerId) {
    const fileInput = document.getElementById(inputId);
    const block = document.getElementById(blockId);
    const previewContainer = document.getElementById(previewContainerId);
    
    block.addEventListener('click', () => {
        fileInput.click();
    });
    
    // Drag and drop
    block.addEventListener('dragover', (e) => {
        e.preventDefault();
        block.style.borderColor = 'var(--purple-main)';
        block.style.background = 'var(--soft-lilac)';
    });
    
    block.addEventListener('dragleave', (e) => {
        e.preventDefault();
        block.style.borderColor = '';
        block.style.background = '';
    });
    
    block.addEventListener('drop', (e) => {
        e.preventDefault();
        block.style.borderColor = '';
        block.style.background = '';
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            updatePreview(fileInput, previewContainer);
        }
    });

    fileInput.addEventListener('change', () => {
        updatePreview(fileInput, previewContainer);
    });
}

function updatePreview(fileInput, container) {
    if (fileInput.files && fileInput.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            // Clear container
            container.innerHTML = '';
            
            // Create image element
            const img = document.createElement('img');
            img.src = e.target.result;
            container.appendChild(img);
        }
        
        reader.readAsDataURL(fileInput.files[0]);
    }
}
