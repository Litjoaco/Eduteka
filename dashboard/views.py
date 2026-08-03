from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from solicitudes.models import SolicitudAcceso, MiembroColegio
from colegios.models import Colegio, ColegioModulo, RolColegio, Estudiante, CursoColegio

from django.contrib.auth.models import User
from django.utils import timezone

@login_required
def dashboard_view(request):
    # Obtenemos el colegio que administra el usuario logueado o del cual es miembro con permiso
    colegio = request.user.colegios_administrados.order_by('-fecha_creacion').first()
    
    # Si no administra ninguno, buscamos si es miembro
    if not colegio:
        miembro = MiembroColegio.objects.filter(usuario=request.user, activo=True).order_by('-fecha_ingreso').first()
        if miembro:
            colegio = miembro.colegio

    if colegio:
        solicitudes_pendientes = SolicitudAcceso.objects.filter(colegio=colegio, estado='pendiente')
        modulos_activos_count = ColegioModulo.objects.filter(colegio=colegio, activo=True).count()
        usuarios_colegio_count = MiembroColegio.objects.filter(colegio=colegio, activo=True).count()
        ultimas_solicitudes = SolicitudAcceso.objects.filter(colegio=colegio).order_by('-fecha_solicitud')[:5]
        
        # Suscripción actual
        suscripcion = getattr(colegio, 'suscripcion', None)
        
        # Alumnos en riesgo
        from asistencia.utils import calcular_alumnos_en_riesgo
        alumnos_en_riesgo = calcular_alumnos_en_riesgo(colegio)
        alumnos_en_riesgo_count = len(alumnos_en_riesgo)
        # Total Estudiantes y Cursos
        total_estudiantes_count = Estudiante.objects.filter(colegio=colegio, activo=True).count()
        total_cursos_count = CursoColegio.objects.filter(colegio=colegio, activo=True).count()
    else:
        # Si no tiene colegio, redirigir a solicitar acceso o registro
        return redirect('solicitar_acceso')

    from colegios.models import ConfiguracionAcademica

    # Obtener miembro actual (puede ser None si es el administrador directo del colegio)
    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()

    # is_admin: True para administradores del colegio y roles directivos
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'inicio',
        'suscripcion': suscripcion,
        'solicitudes_pendientes_count': solicitudes_pendientes.count(),
        'modulos_activos_count': modulos_activos_count,
        'usuarios_colegio_count': usuarios_colegio_count,
        'total_estudiantes_count': total_estudiantes_count,
        'total_cursos_count': total_cursos_count,
        'solicitudes_pendientes': solicitudes_pendientes,
        'ultimas_solicitudes': ultimas_solicitudes,
        'alumnos_en_riesgo': alumnos_en_riesgo,
        'alumnos_en_riesgo_count': alumnos_en_riesgo_count,
        'hoy': timezone.now(),
    }
    return render(request, 'dashboard_profesor.html', context)



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
