from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegistroUsuarioForm
from solicitudes.models import MiembroColegio, SolicitudAcceso
from colegios.models import Colegio, ConfiguracionAcademica, CursoColegio
from django.utils import timezone

def registro_personal_view(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "¡Tu cuenta ha sido creada exitosamente!")
            return redirect('solicitar_acceso')
        else:
            # Capturar los errores del formulario y enviarlos como mensajes
            for field, errors in form.errors.items():
                for error in errors:
                    # Si es un error general (como el de contraseñas que no coinciden), no mostramos el nombre del campo
                    mensaje = f"{error}" if field == '__all__' else f"{form.fields[field].label or field.capitalize()}: {error}"
                    messages.error(request, mensaje)
    else:
        form = RegistroUsuarioForm()
    
    return render(request, 'registropersonal.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        # Copiamos el diccionario de datos para poder modificarlo
        data = request.POST.copy()
        
        # Si el HTML envía 'email' o 'correo' en lugar de 'username', lo adaptamos
        if 'email' in data and 'username' not in data:
            data['username'] = data['email']
        elif 'correo' in data and 'username' not in data:
            data['username'] = data['correo']

        # AuthenticationForm espera 'username' y 'password' en el POST request
        form = AuthenticationForm(request, data=data)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Redirigir a 'next' si existe, si no al dashboard
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            # 0. Si es superusuario o staff global -> dashboard superadmin
            if user.is_superuser or user.is_staff:
                return redirect('dashboard_superadmin')

            # 1. Si es administrador de un colegio -> dashboard admin
            if Colegio.objects.filter(administrador=user).exists():
                return redirect('dashboard_profesor')
            
            # 2. Si ya es miembro activo de un colegio -> dashboard usuario
            if MiembroColegio.objects.filter(usuario=user, activo=True).exists():
                return redirect('dashboard_usuario')
            
            # 3. Si tiene solicitud pendiente -> cámara de espera
            if SolicitudAcceso.objects.filter(usuario=user, estado='pendiente').exists():
                return redirect('solicitud_enviada')
            
            # 4. Si aún no solicita -> formulario para solicitar acceso
            return redirect('solicitar_acceso')
        else:
            messages.error(request, "Correo electrónico o contraseña incorrectos.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('landing_page')

@login_required
def dashboard_usuarios_view(request):
    # Obtenemos el colegio que administra el usuario o del cual es miembro activo
    colegio = request.user.colegios_administrados.order_by('-fecha_creacion').first()
    miembro = MiembroColegio.objects.filter(usuario=request.user, activo=True).first()
    
    if not colegio and miembro:
        colegio = miembro.colegio
    elif not colegio and not miembro:
        if SolicitudAcceso.objects.filter(usuario=request.user, estado='pendiente').exists():
            messages.warning(request, "Tu solicitud aún se encuentra en revisión.")
            return redirect('solicitud_enviada')
        else:
            messages.warning(request, "No has solicitado acceso a ningún colegio.")
            return redirect('solicitar_acceso')

    from colegios.models import ConfiguracionAcademica, Estudiante, CursoColegio, EventoAgenda, AnotacionEstudiante
    from asistencia.utils import calcular_alumnos_en_riesgo
    
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    total_estudiantes_count = Estudiante.objects.filter(colegio=colegio, activo=True).count()
    total_cursos_count = CursoColegio.objects.filter(colegio=colegio, activo=True).count()
    usuarios_colegio_count = MiembroColegio.objects.filter(colegio=colegio, activo=True).count()
    
    solicitudes_pendientes = SolicitudAcceso.objects.filter(colegio=colegio, estado='pendiente').order_by('-fecha_solicitud')
    solicitudes_pendientes_count = solicitudes_pendientes.count()
    
    alumnos_en_riesgo = calcular_alumnos_en_riesgo(colegio)
    alumnos_en_riesgo_count = len(alumnos_en_riesgo)
    
    hoy_date = timezone.now().date()
    eventos_hoy = EventoAgenda.objects.filter(colegio=colegio, fecha_inicio__date=hoy_date).order_by('fecha_inicio')
    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).prefetch_related('secciones')
    ultimas_anotaciones = AnotacionEstudiante.objects.filter(estudiante__colegio=colegio).select_related('estudiante', 'docente').order_by('-fecha')[:5]

    
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    from colegios.models import RolColegio
    roles_colegio = RolColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    if not roles_colegio.exists():
        roles_colegio = RolColegio.objects.filter(es_base=True).order_by('nombre')

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'total_estudiantes_count': total_estudiantes_count,
        'total_cursos_count': total_cursos_count,
        'cursos_count': total_cursos_count,
        'usuarios_colegio_count': usuarios_colegio_count,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_pendientes_count': solicitudes_pendientes_count,
        'roles_colegio': roles_colegio,
        'alumnos_en_riesgo': alumnos_en_riesgo[:6],
        'alumnos_en_riesgo_count': alumnos_en_riesgo_count,
        'eventos_hoy': eventos_hoy,
        'cursos': cursos,
        'ultimas_anotaciones': ultimas_anotaciones,
        'is_admin': is_admin,
        'active_page': 'inicio',
        'hoy': timezone.now(),
    }
    return render(request, 'dashboard_usuarios.html', context)


import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from .models import PerfilUsuario

@login_required
@require_GET
def api_estado_pin(request):
    """Retorna el estado de vigencia y existencia del PIN de 4 dígitos del usuario actual."""
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user, defaults={'nombre_completo': request.user.get_full_name() or request.user.username})
    return JsonResponse({
        'tiene_pin': perfil.tiene_pin(),
        'expirado': perfil.pin_expirado(),
        'bloqueado': perfil.esta_bloqueado_pin(),
        'dias_restantes': perfil.dias_restantes_pin(),
    })

@login_required
@require_POST
def api_verificar_pin(request):
    """Verifica el PIN de 4 dígitos ingresado por el usuario."""
    try:
        data = json.loads(request.body) if request.body else request.POST
        pin = data.get('pin', '').strip()
    except Exception:
        pin = request.POST.get('pin', '').strip()

    if not pin or len(pin) != 4 or not pin.isdigit():
        return JsonResponse({'valido': False, 'mensaje': 'Debes ingresar un PIN de 4 dígitos numéricos.'}, status=400)

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user, defaults={'nombre_completo': request.user.get_full_name() or request.user.username})
    
    valido, mensaje = perfil.verificar_pin(pin)
    return JsonResponse({
        'valido': valido,
        'mensaje': mensaje,
        'expirado': perfil.pin_expirado(),
        'bloqueado': perfil.esta_bloqueado_pin(),
        'dias_restantes': perfil.dias_restantes_pin()
    })

@login_required
@require_POST
def api_establecer_pin(request):
    """Crea o actualiza el PIN de 4 dígitos con expiración a 90 días."""
    try:
        data = json.loads(request.body) if request.body else request.POST
        nuevo_pin = str(data.get('nuevo_pin', '')).strip()
        confirmar_pin = str(data.get('confirmar_pin', '')).strip()
    except Exception:
        nuevo_pin = str(request.POST.get('nuevo_pin', '')).strip()
        confirmar_pin = str(request.POST.get('confirmar_pin', '')).strip()

    if not nuevo_pin or len(nuevo_pin) != 4 or not nuevo_pin.isdigit():
        return JsonResponse({'exito': False, 'mensaje': 'El PIN debe componerse de exactamente 4 números.'}, status=400)

    if nuevo_pin != confirmar_pin:
        return JsonResponse({'exito': False, 'mensaje': 'Los PINs ingresados no coinciden.'}, status=400)

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user, defaults={'nombre_completo': request.user.get_full_name() or request.user.username})
    try:
        perfil.establecer_pin(nuevo_pin)
        return JsonResponse({
            'exito': True,
            'mensaje': '¡PIN de 4 dígitos configurado exitosamente! Tendrá una vigencia de 90 días (3 meses).',
            'dias_restantes': 90
        })
    except Exception as e:
        return JsonResponse({'exito': False, 'mensaje': str(e)}, status=500)

