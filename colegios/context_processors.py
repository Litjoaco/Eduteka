from django.utils import timezone
from colegios.models import Colegio, ColegioModulo, ConfiguracionAcademica, RolPermiso
from solicitudes.models import MiembroColegio
from colegios.views import obtener_colegio_usuario

def colegio_context(request):
    if not request.user.is_authenticated:
        return {'hoy': timezone.now()}

    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return {'hoy': timezone.now()}

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).select_related('rol').first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()

    rol_nombre = ''
    if miembro and miembro.rol:
        rol_nombre = miembro.rol.nombre.strip()
    elif request.user.colegios_administrados.filter(id=colegio.id).exists() or request.user.is_superuser:
        rol_nombre = 'Administrador'
    else:
        rol_nombre = 'Usuario'

    rol_lower = rol_nombre.lower().strip()
    is_admin = (
        request.user.is_superuser
        or request.user.colegios_administrados.filter(id=colegio.id).exists()
        or any(r in rol_lower for r in ['administrador', 'director', 'sostenedor', 'rector'])
    )
    is_utp = any(r in rol_lower for r in ['utp', 'pedagogic', 'pedagógic', 'coordinador', 'evaluador', 'curriculum'])
    is_profesor = any(r in rol_lower for r in ['profesor', 'docente', 'educador', 'maestro'])
    is_inspector = any(r in rol_lower for r in ['inspector', 'inspectora'])
    is_convivencia = any(r in rol_lower for r in ['convivencia', 'psicolog', 'psicólog', 'orientad', 'dupla', 'pie', 'social', 'psicopedagog'])
    is_secretario = any(r in rol_lower for r in ['secretari', 'administrativ', 'recepcion', 'asistente'])
    is_apoderado = any(r in rol_lower for r in ['apoderado', 'padre', 'madre', 'tutor'])
    is_estudiante = any(r in rol_lower for r in ['alumno', 'alumna', 'estudiante'])

    modulos_qs = ColegioModulo.objects.filter(colegio=colegio, activo=True).select_related('modulo')
    modulos_activos = set(m.modulo.nombre.lower().strip() for m in modulos_qs)

    permisos_ver = set()
    if is_admin:
        permisos_ver = set(modulos_activos)
    elif miembro:
        if miembro.rol:
            rps = RolPermiso.objects.filter(rol=miembro.rol, puede_ver=True).select_related('modulo')
            for rp in rps:
                mod_name = rp.modulo.nombre.lower().strip()
                permisos_ver.add(mod_name)
        
        # Integrar permisos individuales del personal
        from colegios.models import MiembroPermiso
        mps = MiembroPermiso.objects.filter(miembro=miembro).select_related('modulo')
        for mp in mps:
            mod_name = mp.modulo.nombre.lower().strip()
            if mp.puede_ver:
                permisos_ver.add(mod_name)
            elif mod_name in permisos_ver:
                permisos_ver.remove(mod_name)

    # Nombre display limpio (nunca correo)
    user_display_name = ''
    if request.user.first_name:
        user_display_name = f"{request.user.first_name} {request.user.last_name or ''}".strip()
    elif getattr(request.user, 'perfil', None) and request.user.perfil.nombre_completo:
        user_display_name = request.user.perfil.nombre_completo.strip()
    elif colegio and colegio.administrador == request.user and colegio.nombre_administrador:
        user_display_name = colegio.nombre_administrador.strip()
    elif '@' in request.user.username:
        user_display_name = request.user.username.split('@')[0].replace('.', ' ').replace('_', ' ').title()
    else:
        user_display_name = request.user.username

    return {
        'colegio': colegio,
        'periodo': periodo,
        'miembro': miembro,
        'rol_nombre': rol_nombre,
        'is_admin': is_admin,
        'is_utp': is_utp,
        'is_profesor': is_profesor,
        'is_inspector': is_inspector,
        'is_convivencia': is_convivencia,
        'is_secretario': is_secretario,
        'is_apoderado': is_apoderado,
        'is_estudiante': is_estudiante,
        'permisos_ver': permisos_ver,
        'nombre_display': user_display_name,
        'hoy': timezone.now(),
    }
