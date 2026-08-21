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
        # Verificamos por seguridad que el usuario logueado es el administrador del colegio o directivo
        if request.user == solicitud.colegio.administrador or MiembroColegio.objects.filter(usuario=request.user, colegio=solicitud.colegio, rol__nombre__in=['Administrador', 'Director'], activo=True).exists():
            rol_id = request.POST.get('rol_id')
            rol_nombre = request.POST.get('rol_asignado')
            
            rol_obj = None
            if rol_id:
                rol_obj = RolColegio.objects.filter(colegio=solicitud.colegio, id=rol_id).first()
            elif rol_nombre:
                rol_obj = RolColegio.objects.filter(colegio=solicitud.colegio, nombre__iexact=rol_nombre).first()
                if not rol_obj:
                    rol_obj = RolColegio.objects.filter(nombre__iexact=rol_nombre).first()
            
            if not rol_obj:
                # Fallback al rol solicitado
                rol_obj = RolColegio.objects.filter(colegio=solicitud.colegio, nombre__iexact=solicitud.rol_solicitado).first()
            
            if not rol_obj:
                rol_obj = RolColegio.objects.filter(colegio=solicitud.colegio, activo=True).exclude(nombre='Administrador').first()

            solicitud.estado = 'aprobada'
            if rol_obj:
                solicitud.rol_solicitado = rol_obj.nombre.lower()
            solicitud.save()

            miembro, created = MiembroColegio.objects.update_or_create(
                usuario=solicitud.usuario,
                colegio=solicitud.colegio,
                defaults={'rol': rol_obj, 'activo': True}
            )
            
            nombre_u = getattr(solicitud.usuario, 'perfil', None)
            nombre_str = nombre_u.nombre_completo if nombre_u else (solicitud.usuario.get_full_name() or solicitud.usuario.email)
            rol_str = rol_obj.nombre if rol_obj else 'Miembro'
            messages.success(request, f"¡Solicitud aprobada! Se asignó el rol '{rol_str}' a {nombre_str}.")
        else:
            messages.error(request, "No tienes permiso para aprobar esta solicitud.")
    return redirect('dashboard_usuario')

@login_required
def rechazar_solicitud(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAcceso, id=solicitud_id)
        if request.user == solicitud.colegio.administrador or MiembroColegio.objects.filter(usuario=request.user, colegio=solicitud.colegio, rol__nombre__in=['Administrador', 'Director'], activo=True).exists():
            solicitud.estado = 'rechazada'
            solicitud.save()
            nombre_u = getattr(solicitud.usuario, 'perfil', None)
            nombre_str = nombre_u.nombre_completo if nombre_u else (solicitud.usuario.get_full_name() or solicitud.usuario.email)
            messages.success(request, f"La solicitud de {nombre_str} fue rechazada.")
        else:
            messages.error(request, "No tienes permiso para rechazar esta solicitud.")
    return redirect('dashboard_usuario')
