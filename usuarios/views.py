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
            
            # 0. Si es superusuario -> dashboard superadmin
            if user.is_superuser:
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
    # Verificamos por seguridad que el usuario sea miembro activo para poder ver este dashboard
    miembro = MiembroColegio.objects.filter(usuario=request.user, activo=True).first()
    if not miembro:
        # Si intenta entrar por URL forzada, lo devolvemos a donde corresponde
        if SolicitudAcceso.objects.filter(usuario=request.user, estado='pendiente').exists():
            messages.warning(request, "Tu solicitud aún se encuentra en revisión.")
            return redirect('solicitud_enviada')
        else:
            messages.warning(request, "No has solicitado acceso a ningún colegio.")
            return redirect('solicitar_acceso')
        
    colegio = miembro.colegio
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    cursos_count = CursoColegio.objects.filter(colegio=colegio, activo=True).count()
    
    # Alumnos en riesgo
    from asistencia.utils import calcular_alumnos_en_riesgo
    alumnos_en_riesgo = calcular_alumnos_en_riesgo(colegio)
    alumnos_en_riesgo_count = len(alumnos_en_riesgo)
    
    # Rol del usuario para filtrar sidebar
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'cursos_count': cursos_count,
        'is_admin': is_admin,
        'hoy': timezone.now(),
        'alumnos_en_riesgo': alumnos_en_riesgo,
        'alumnos_en_riesgo_count': alumnos_en_riesgo_count,
    }
    return render(request, 'dashboard_usuarios.html', context)
