// Lógica simple para actualizar el resumen
document.addEventListener('DOMContentLoaded', function() {
    const planRadios = document.querySelectorAll('input[name="plan"]');
    const billingRadios = document.querySelectorAll('input[name="billing"]');
    const moduleCheckboxes = document.querySelectorAll('input[name="modules"]');
    
    const summaryPlan = document.getElementById('summary-plan');
    const summaryBilling = document.getElementById('summary-billing');
    const summaryModules = document.getElementById('summary-modules');
    const summaryTotal = document.getElementById('summary-total');
    const summaryPeriod = document.getElementById('summary-period');

    const priceBasico = document.getElementById('price-basico');
    const priceProfesional = document.getElementById('price-profesional');
    const priceInstitucional = document.getElementById('price-institucional');

    const prices = {
        basico: 49900,
        profesional: 89900,
        institucional: 149900,
        personalizado: 0
    };

    const names = {
        basico: 'Básico',
        profesional: 'Profesional',
        institucional: 'Institucional',
        personalizado: 'A medida'
    };

    function updateSummary() {
        let selectedPlan = document.querySelector('input[name="plan"]:checked').value;
        let selectedBilling = document.querySelector('input[name="billing"]:checked').value;
        let activeModules = document.querySelectorAll('input[name="modules"]:checked').length;
        
        let basePrice = prices[selectedPlan];
        let isYearly = selectedBilling === 'anual';
        
        let finalPrice = basePrice;
        let periodText = '/ mes';

        if (isYearly && basePrice > 0) {
            finalPrice = basePrice * 12 * 0.85; // Precio anual total con 15% de descuento
            periodText = '/ año';
            
            priceBasico.innerHTML = '$' + new Intl.NumberFormat('es-CL').format(Math.round(prices.basico * 0.85)) + '<span style="font-weight: 500; font-size: 0.65rem;"> /mes</span>';
            priceProfesional.innerHTML = '$' + new Intl.NumberFormat('es-CL').format(Math.round(prices.profesional * 0.85)) + '<span style="font-weight: 500; font-size: 0.65rem;"> /mes</span>';
            priceInstitucional.innerHTML = '$' + new Intl.NumberFormat('es-CL').format(Math.round(prices.institucional * 0.85)) + '<span style="font-weight: 500; font-size: 0.65rem;"> /mes</span>';
        } else {
            priceBasico.innerHTML = '$' + new Intl.NumberFormat('es-CL').format(prices.basico) + '<span style="font-weight: 500; font-size: 0.65rem;"> /mes</span>';
            priceProfesional.innerHTML = '$' + new Intl.NumberFormat('es-CL').format(prices.profesional) + '<span style="font-weight: 500; font-size: 0.65rem;"> /mes</span>';
            priceInstitucional.innerHTML = '$' + new Intl.NumberFormat('es-CL').format(prices.institucional) + '<span style="font-weight: 500; font-size: 0.65rem;"> /mes</span>';
        }

        summaryPlan.textContent = names[selectedPlan];
        summaryBilling.textContent = isYearly ? 'Anual' : 'Mensual';
        summaryModules.textContent = activeModules + ' activos';
        
        if (selectedPlan === 'personalizado') {
            summaryTotal.innerHTML = 'A cotizar';
            summaryPeriod.textContent = 'Inicio sujeto a evaluación';
        } else {
            let formattedPrice = new Intl.NumberFormat('es-CL').format(Math.round(finalPrice));
            summaryTotal.innerHTML = `$${formattedPrice}`;
            summaryPeriod.textContent = `${periodText} - Inicio inmediato`;
        }
    }

    planRadios.forEach(radio => radio.addEventListener('change', updateSummary));
    billingRadios.forEach(radio => radio.addEventListener('change', updateSummary));
    moduleCheckboxes.forEach(cb => cb.addEventListener('change', updateSummary));
});