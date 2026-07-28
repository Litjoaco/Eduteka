from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import SolicitudAcceso, MiembroColegio
from .forms import SolicitudAccesoForm
from colegios.models import RolColegio
from django.contrib import messages

@login_required
def solicitar_acceso_view(request):
    if request.method == 'POST':
        form = SolicitudAccesoForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user
            # Verificar si ya tiene una solicitud pendiente
            if SolicitudAcceso.objects.filter(usuario=request.user, colegio=solicitud.colegio, estado='pendiente').exists():
                messages.error(request, "Ya tienes una solicitud pendiente para este colegio.")
                return render(request, 'solicitar_acceso.html', {'form': form})
            
            solicitud.save()
            return redirect('solicitud_enviada')
        else:
            # Capturar errores del formulario para mostrarlos como mensajes de Django
            for field, errors in form.errors.items():
                for error in errors:
                    mensaje = f"{error}" if field == '__all__' else f"{form.fields[field].label or field.capitalize()}: {error}"
                    messages.error(request, mensaje)
    else:
        form = SolicitudAccesoForm()
    return render(request, 'solicitar_acceso.html', {'form': form})

@login_required
def solicitud_enviada_view(request):
    return render(request, 'solicitud_enviada.html')


