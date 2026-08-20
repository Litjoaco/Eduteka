from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from solicitudes.models import SolicitudAcceso, MiembroColegio
from colegios.models import Colegio, ColegioModulo, RolColegio, Estudiante, CursoColegio

from django.contrib.auth.models import User
from django.utils import timezone

@login_required
def dashboard_view(request):
    return redirect('dashboard_usuario')




@login_required
def aprobar_solicitud(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAcceso, id=solicitud_id)
        # Verificamos por seguridad que el usuario logueado es el administrador del colegio
        if request.user == solicitud.colegio.administrador:
            solicitud.estado = 'aprobada'
            solicitud.save()
            
            # Buscar el rol correspondiente en el colegio
            # Si el rol solicitado no existe, podríamos asignar uno por defecto o el que solicitó si es base
            rol_nombre = solicitud.rol_solicitado.capitalize()
            rol_obj = RolColegio.objects.filter(colegio=solicitud.colegio, nombre__iexact=rol_nombre).first()
            
            if not rol_obj:
                # Si no existe, usamos el primer rol activo o Administrador por defecto (aunque mejor uno menor)
                rol_obj = RolColegio.objects.filter(colegio=solicitud.colegio, activo=True).exclude(nombre='Administrador').first()

            MiembroColegio.objects.get_or_create(
                usuario=solicitud.usuario,
                colegio=solicitud.colegio,
                defaults={'rol': rol_obj, 'activo': True}
            )
            
            messages.success(request, f"Acceso aprobado para {solicitud.usuario.perfil.nombre_completo}.")
        else:
            messages.error(request, "No tienes permiso para aprobar esta solicitud.")
    return redirect('dashboard_profesor')

@login_required
def rechazar_solicitud(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAcceso, id=solicitud_id)
        if request.user == solicitud.colegio.administrador:
            solicitud.estado = 'rechazada'
            solicitud.save()
            messages.success(request, f"Solicitud de {solicitud.usuario.perfil.nombre_completo} rechazada.")
        else:
            messages.error(request, "No tienes permiso para rechazar esta solicitud.")
    return redirect('dashboard_profesor')
