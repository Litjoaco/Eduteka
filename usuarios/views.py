from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
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


from django.contrib.auth import update_session_auth_hash

@login_required
def perfil_usuario_view(request):
    """Vista de gestión integral de Mi Perfil: Datos personales, cambio de contraseña y PIN de firma."""
    user = request.user
    perfil, _ = PerfilUsuario.objects.get_or_create(
        usuario=user,
        defaults={'nombre_completo': user.get_full_name() or user.username}
    )

    # Identificar colegio y rol activo
    colegio = None
    miembro = None
    if user.is_authenticated:
        colegio_admin = Colegio.objects.filter(administrador=user).first()
        if colegio_admin:
            colegio = colegio_admin
        else:
            miembro = MiembroColegio.objects.filter(usuario=user, activo=True).select_related('colegio', 'rol').first()
            if miembro:
                colegio = miembro.colegio

    if request.method == 'POST':
        action = request.POST.get('action')

        # 1. Actualizar Datos Personales
        if action == 'actualizar_datos':
            nombre = request.POST.get('nombre_completo', '').strip()
            email = request.POST.get('email', '').strip()
            rut = request.POST.get('rut', '').strip()
            telefono = request.POST.get('telefono', '').strip()

            if not nombre:
                messages.error(request, "El nombre completo no puede estar vacío.")
            elif not email:
                messages.error(request, "El correo electrónico es obligatorio.")
            else:
                # Comprobar si el email ya existe en otro usuario
                if User.objects.filter(email=email).exclude(pk=user.pk).exists() or User.objects.filter(username=email).exclude(pk=user.pk).exists():
                    messages.error(request, "Ese correo electrónico ya está registrado por otro usuario.")
                else:
                    perfil.nombre_completo = nombre
                    perfil.rut = rut
                    perfil.telefono = telefono
                    perfil.save()

                    user.email = email
                    user.first_name = nombre.split()[0] if nombre else ''
                    user.last_name = ' '.join(nombre.split()[1:]) if len(nombre.split()) > 1 else ''
                    user.save(update_fields=['email', 'first_name', 'last_name'])

                    messages.success(request, "¡Tus datos personales se han actualizado correctamente!")
            return redirect('perfil_usuario')

        # 2. Cambiar Contraseña de Acceso
        elif action == 'cambiar_password':
            current_pass = request.POST.get('current_password', '')
            new_pass1 = request.POST.get('new_password', '')
            new_pass2 = request.POST.get('confirm_password', '')

            if not user.check_password(current_pass):
                messages.error(request, "La contraseña actual ingresada es incorrecta.")
            elif len(new_pass1) < 6:
                messages.error(request, "La nueva contraseña debe tener al menos 6 caracteres.")
            elif new_pass1 != new_pass2:
                messages.error(request, "Las nuevas contraseñas no coinciden.")
            else:
                user.set_password(new_pass1)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, "¡Tu contraseña de acceso ha sido actualizada con éxito!")
            return redirect('perfil_usuario')

    context = {
        'perfil': perfil,
        'colegio': colegio,
        'miembro': miembro,
        'active_page': 'perfil',
        'hoy': timezone.now(),
    }
    return render(request, 'usuarios/perfil.html', context)


# =========================================================================
# RECUPERACIÓN DE CONTRASEÑA POR CORREO ELECTRÓNICO
# =========================================================================
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings

def solicitar_recuperacion_password_view(request):
    """Permite al usuario solicitar un enlace seguro para restablecer su contraseña."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, "Por favor ingresa tu correo electrónico.")
        else:
            usuarios = User.objects.filter(email__iexact=email) | User.objects.filter(username__iexact=email)
            usuarios = usuarios.distinct()
            
            for u in usuarios:
                uidb64 = urlsafe_base64_encode(force_bytes(u.pk))
                token = default_token_generator.make_token(u)
                reset_url = request.build_absolute_uri(
                    reverse('password_reset_confirmar', kwargs={'uidb64': uidb64, 'token': token})
                )
                
                perfil = getattr(u, 'perfil', None)
                nombre = perfil.nombre_completo if perfil else (u.get_full_name() or u.username)

                html_content = render_to_string('emails/reset_password_email.html', {
                    'user': u,
                    'nombre': nombre,
                    'reset_url': reset_url,
                })
                text_content = f"Hola {nombre},\n\nPara restablecer tu contraseña en Eduteka, ingresa al siguiente enlace:\n{reset_url}\n\nEste enlace expira en 15 minutos."
                
                msg = EmailMultiAlternatives(
                    subject="[Eduteka] Restablecer tu Contraseña de Acceso",
                    body=text_content,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'Eduteka <notificaciones@eduteka.cl>'),
                    to=[u.email or email],
                )
                msg.attach_alternative(html_content, "text/html")
                try:
                    msg.send(fail_silently=False)
                except Exception as e:
                    print(f"Error enviando correo de recuperación: {e}")

            messages.success(request, f"Si el correo '{email}' está registrado, te hemos enviado un enlace de recuperación con validez de 15 minutos.")
            return redirect('login')

    return render(request, 'usuarios/password_reset_solicitar.html')


def confirmar_recuperacion_password_view(request, uidb64, token):
    """Valida el token recibido y permite al usuario definir una nueva contraseña."""
    user = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "El enlace de recuperación es inválido o ha expirado. Por favor solicita uno nuevo.")
        return redirect('password_reset_solicitar')

    if request.method == 'POST':
        p1 = request.POST.get('password1', '')
        p2 = request.POST.get('password2', '')

        if not p1 or len(p1) < 6:
            messages.error(request, "La nueva contraseña debe tener al menos 6 caracteres.")
        elif p1 != p2:
            messages.error(request, "Las contraseñas ingresadas no coinciden.")
        else:
            user.set_password(p1)
            user.save()
            messages.success(request, "¡Tu contraseña ha sido restablecida exitosamente! Ya puedes iniciar sesión.")
            return redirect('login')

    return render(request, 'usuarios/password_reset_confirmar.html', {'usuario_valido': user})


# =========================================================================
# RECUPERACIÓN DE PIN DE FIRMA VÍA CÓDIGO OTP POR CORREO
# =========================================================================

@login_required
@require_POST
def api_solicitar_reset_pin(request):
    """Genera un código OTP de 6 dígitos y lo envía al correo del usuario para autorizar el cambio de PIN."""
    user = request.user
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user, defaults={'nombre_completo': user.get_full_name() or user.username})

    destinatario = user.email or request.POST.get('email', '').strip()
    if not destinatario:
        return JsonResponse({'exito': False, 'mensaje': 'Tu cuenta no tiene un correo electrónico configurado.'}, status=400)

    codigo = perfil.generar_codigo_reset_pin()

    html_content = render_to_string('emails/reset_pin_email.html', {
        'user': user,
        'nombre': perfil.nombre_completo or user.username,
        'codigo': codigo,
    })
    text_content = f"Hola {perfil.nombre_completo},\n\nTu código de verificación para recuperar tu PIN de Firma es: {codigo}\n\nVálido por 10 minutos."

    msg = EmailMultiAlternatives(
        subject="[Eduteka] Código de Recuperación de PIN de Firma",
        body=text_content,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'Eduteka <notificaciones@eduteka.cl>'),
        to=[destinatario],
    )
    msg.attach_alternative(html_content, "text/html")
    try:
        msg.send(fail_silently=False)
        return JsonResponse({
            'exito': True,
            'mensaje': f'Código de seguridad de 6 dígitos enviado exitosamente a {destinatario}. Válido por 10 minutos.'
        })
    except Exception as e:
        return JsonResponse({'exito': False, 'mensaje': f'Error al enviar el correo: {str(e)}'}, status=500)


@login_required
@require_POST
def api_verificar_reset_pin(request):
    """Valida el código OTP de 6 dígitos y establece el nuevo PIN de 4 dígitos."""
    try:
        data = json.loads(request.body) if request.body else request.POST
    except Exception:
        data = request.POST

    codigo = str(data.get('codigo', '')).strip()
    nuevo_pin = str(data.get('nuevo_pin', '')).strip()
    confirmar_pin = str(data.get('confirmar_pin', '')).strip()

    if not codigo or len(codigo) != 6:
        return JsonResponse({'exito': False, 'mensaje': 'Debes ingresar el código de verificación de 6 dígitos.'}, status=400)

    if not nuevo_pin or len(nuevo_pin) != 4 or not nuevo_pin.isdigit():
        return JsonResponse({'exito': False, 'mensaje': 'El nuevo PIN debe tener exactamente 4 dígitos numéricos.'}, status=400)

    if nuevo_pin != confirmar_pin:
        return JsonResponse({'exito': False, 'mensaje': 'Los nuevos PINs ingresados no coinciden.'}, status=400)

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=request.user, defaults={'nombre_completo': request.user.get_full_name() or request.user.username})

    valido, mensaje = perfil.verificar_codigo_reset_pin(codigo)
    if not valido:
        return JsonResponse({'exito': False, 'mensaje': mensaje}, status=400)

    # Establecer el nuevo PIN
    try:
        perfil.establecer_pin(nuevo_pin)
        # Limpiar el código OTP ya usado
        perfil.pin_reset_codigo = None
        perfil.pin_reset_expira = None
        perfil.save(update_fields=['pin_reset_codigo', 'pin_reset_expira'])

        return JsonResponse({
            'exito': True,
            'mensaje': '¡PIN de 4 dígitos restablecido y desbloqueado exitosamente! Tendrá 90 días de vigencia.',
            'dias_restantes': 90
        })
    except Exception as e:
        return JsonResponse({'exito': False, 'mensaje': str(e)}, status=500)


