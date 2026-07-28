from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
import json
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from usuarios.models import PerfilUsuario
from .models import Colegio, Suscripcion, ColegioModulo, ConfiguracionAcademica, RolColegio, Permiso, RolPermiso, CursoColegio, SeccionCurso
from .forms import RegistroColegioPaso1Form, RegistroColegioPaso2Form
from solicitudes.models import MiembroColegio

def registro_colegio_paso1_view(request):
    # Si hay un usuario logueado, cerramos su sesión inmediatamente para evitar 
    # que el colegio se asocie a una cuenta antigua por accidente.
    if request.user.is_authenticated:
        logout(request)

    if request.method == 'POST':
        form = RegistroColegioPaso1Form(request.POST)
        if form.is_valid():
            colegio = form.save(commit=False)
            
            # Como ya cerramos sesión arriba, siempre entraremos por aquí
            correo = form.cleaned_data['correo_institucional']
            password = form.cleaned_data['password']
            nombre_admin = form.cleaned_data['nombre_administrador']
            
            user = User.objects.create_user(username=correo, email=correo, password=password)
            PerfilUsuario.objects.create(
                usuario=user, 
                nombre_completo=nombre_admin,
                rut=form.cleaned_data.get('rut_administrador', ''),
                telefono=form.cleaned_data.get('telefono_administrador', '')
            )
            
            login(request, user)
            colegio.administrador = user
                
            colegio.save()
            return redirect('registro_colegio_paso2', colegio_id=colegio.id)
    else:
        form = RegistroColegioPaso1Form()
    
    return render(request, 'registrocolegio.html', {'form': form})

def registro_colegio_paso2_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)
    
    if request.method == 'POST':
        form = RegistroColegioPaso2Form(request.POST)
        if form.is_valid():
            plan = form.cleaned_data['plan']
            tipo_facturacion = form.cleaned_data['tipo_facturacion']
            
            # Calcular monto
            monto = plan.precio_anual if tipo_facturacion == 'anual' else plan.precio_mensual
            
            # 1. Crear la suscripción
            Suscripcion.objects.update_or_create(
                colegio=colegio,
                defaults={
                    'plan': plan,
                    'tipo_facturacion': tipo_facturacion,
                    'monto': monto,
                    'estado': 'pendiente_pago'
                }
            )
            
            # 2. Guardar los módulos activos
            modulos_seleccionados = form.cleaned_data['modulos']
            # Primero desactivamos todos los actuales si existen
            ColegioModulo.objects.filter(colegio=colegio).delete()
            for modulo in modulos_seleccionados:
                ColegioModulo.objects.create(colegio=colegio, modulo=modulo, activo=True)
            
            # 3. Clonar Roles Base para el colegio si no existen
            if not RolColegio.objects.filter(colegio=colegio).exists():
                roles_base = RolColegio.objects.filter(es_base=True, colegio=None)
                for rb in roles_base:
                    nuevo_rol = RolColegio.objects.create(
                        colegio=colegio,
                        nombre=rb.nombre,
                        descripcion=rb.descripcion,
                        es_base=False,
                        activo=True
                    )
                    # Clonar permisos del rol base
                    for rp in rb.permisos.all():
                        RolPermiso.objects.create(
                            rol=nuevo_rol,
                            modulo=rp.modulo,
                            puede_ver=rp.puede_ver,
                            puede_crear=rp.puede_crear,
                            puede_editar=rp.puede_editar,
                            puede_eliminar=rp.puede_eliminar,
                            puede_exportar=rp.puede_exportar,
                            puede_aprobar=rp.puede_aprobar,
                            puede_enviar_mensajes=rp.puede_enviar_mensajes,
                            puede_administrar=rp.puede_administrar
                        )
                    
                    # Si el rol es Administrador, vincular al usuario actual
                    if rb.nombre == 'Administrador':
                        MiembroColegio.objects.get_or_create(
                            usuario=request.user,
                            colegio=colegio,
                            defaults={'rol': nuevo_rol, 'activo': True}
                        )
            
            return redirect('configuracion_colegio_paso1', colegio_id=colegio.id)
    else:
        form = RegistroColegioPaso2Form()
        
    return render(request, 'registrocolegiopaso2.html', {'form': form, 'colegio': colegio})

def api_buscar_colegios(request):
    q = request.GET.get('q', '').lower()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    colegios = Colegio.objects.filter(nombre__icontains=q)[:10]
    resultados = [{'id': c.id, 'nombre': c.nombre, 'ciudad': c.ciudad_comuna} for c in colegios]
    return JsonResponse(resultados, safe=False)

def configuracion_colegio_paso1_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    # Validación de seguridad: el usuario debe ser el administrador de ESTE colegio.
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)

    if request.method == 'POST':
        nombre = request.POST.get('nombre_oficial', '').strip()
        nombre_corto = request.POST.get('nombre_corto', '').strip()

        if not nombre or not nombre_corto:
            messages.error(request, "El nombre oficial y el nombre corto son campos obligatorios.")
            return render(request, 'configuracion_colegio_paso1.html', {'colegio': colegio})
        
        colegio.nombre = nombre
        colegio.nombre_corto = nombre_corto
        colegio.eslogan = request.POST.get('eslogan', '')

        if 'logo' in request.FILES:
            colegio.logo = request.FILES['logo']
        if 'imagen' in request.FILES:
            colegio.imagen_portada = request.FILES['imagen']
        
        # Guardar colores si vienen
        if request.POST.get('color_principal'):
            colegio.color_principal = request.POST.get('color_principal')
        
        colegio.paso_configuracion_actual = 2
        colegio.save()
        return redirect('configuracion_colegio_paso2', colegio_id=colegio.id)
        
    return render(request, 'configuracion_colegio_paso1.html', {'colegio': colegio})

def configuracion_colegio_paso2_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    # Validación de seguridad
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)

    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        telefono = request.POST.get('telefono_principal', '').strip()
        comuna = request.POST.get('comuna', '').strip()

        if not correo or not direccion or not telefono or not comuna:
            messages.error(request, "Por favor complete todos los campos requeridos (*).")
            return render(request, 'configuracion_colegio_paso2.html', {'colegio': colegio})

        try:
            validate_email(correo)
        except ValidationError:
            messages.error(request, "Ingrese una dirección de correo institucional válida.")
            return render(request, 'configuracion_colegio_paso2.html', {'colegio': colegio})

        colegio.correo_institucional = correo
        colegio.direccion = direccion
        colegio.telefono = telefono
        colegio.ciudad_comuna = comuna
        colegio.telefono_alternativo = request.POST.get('telefono_alternativo', '')
        colegio.region = request.POST.get('region', '')
        colegio.sitio_web = request.POST.get('sitio_web', '')
        colegio.pais = request.POST.get('pais', '')
        colegio.referencia_direccion = request.POST.get('referencia', '')
        
        colegio.paso_configuracion_actual = 3
        colegio.save()
        return redirect('configuracion_colegio_paso3', colegio_id=colegio.id)
        
    return render(request, 'configuracion_colegio_paso2.html', {'colegio': colegio})

def configuracion_colegio_paso3_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    # Validación de seguridad
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)

    if request.method == 'POST':
        anio_academico = request.POST.get('anio_academico')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_termino = request.POST.get('fecha_termino')
        
        # Procesar cursos y secciones SIEMPRE, incluso si faltan fechas
        datos_cursos_json = request.POST.get('datos_cursos')
        if datos_cursos_json:
            try:
                lista_cursos = json.loads(datos_cursos_json)
                # Extraer cursos válidos y evitar borrar y recrear (para mantener IDs relacionales)
                cursos_mantener = []
                
                for c in lista_cursos:
                    nivel_key = 'basica'
                    if 'parvularia' in c['nivel'].lower(): nivel_key = 'parvularia'
                    elif 'media' in c['nivel'].lower(): nivel_key = 'media'
                    elif 'tp' in c['nivel'].lower() or 'téc' in c['nivel'].lower(): nivel_key = 'tecnico_profesional'
                    elif 'especial' in c['nivel'].lower(): nivel_key = 'especial'
                    
                    curso_nombre = c['curso'].strip()
                    curso_jornada = c.get('jornada', 'Mañana').strip()
                    
                    curso_obj, _ = CursoColegio.objects.update_or_create(
                        colegio=colegio, 
                        nombre=curso_nombre, 
                        jornada=curso_jornada,
                        defaults={
                            'nivel': nivel_key, 
                            'desde_letra': c['letra_desde'].upper(), 
                            'hasta_letra': c['letra_hasta'].upper(),
                            'activo': True
                        }
                    )
                    cursos_mantener.append(curso_obj.id)
                    
                    # Generar secciones
                    start = ord(curso_obj.desde_letra)
                    end = ord(curso_obj.hasta_letra)
                    
                    if start <= end:
                        # Desactivar secciones viejas que ya no estén en el rango
                        SeccionCurso.objects.filter(curso=curso_obj).update(activo=False)
                        
                        for i in range(start, end + 1):
                            letra = chr(i)
                            SeccionCurso.objects.update_or_create(
                                curso=curso_obj,
                                letra=letra,
                                defaults={'nombre': f"{curso_obj.nombre} {letra}", 'activo': True}
                            )
                
                # Eliminar cursos que el usuario quitó explícitamente de la tabla
                CursoColegio.objects.filter(colegio=colegio).exclude(id__in=cursos_mantener).delete()

            except json.JSONDecodeError:
                pass
                
        if anio_academico and fecha_inicio and fecha_termino:
            periodo, created = ConfiguracionAcademica.objects.update_or_create(
                colegio=colegio,
                defaults={
                    'anio_academico': anio_academico,
                    'fecha_inicio': fecha_inicio,
                    'fecha_termino': fecha_termino,
                    'periodo_academico': request.POST.get('tipo_periodo', 'semestres').lower(),
                    'horario_referencial': request.POST.get('horario_referencia', '')
                }
            )
            
            # Guardar flags de niveles
            niveles_raw = request.POST.get('niveles_educativos', '').lower()
            periodo.nivel_parvularia = 'parvularia' in niveles_raw
            periodo.nivel_basica = 'básica' in niveles_raw
            periodo.nivel_media = 'media' in niveles_raw
            periodo.nivel_tecnico_profesional = 'técnico' in niveles_raw
            periodo.nivel_especial = 'especial' in niveles_raw
            periodo.nivel_otro = 'otro' in niveles_raw
            
            # Guardar flags de jornadas
            jornadas_raw = request.POST.get('jornadas', '').lower()
            periodo.jornada_manana = 'mañana' in jornadas_raw
            periodo.jornada_tarde = 'tarde' in jornadas_raw
            periodo.jornada_completa = 'completa' in jornadas_raw
            periodo.jornada_vespertina = 'vespertina' in jornadas_raw
            periodo.jornada_flexible = 'flexible' in jornadas_raw
            periodo.save()
            
            colegio.paso_configuracion_actual = 4
            colegio.save()
            return redirect('configuracion_colegio_paso4', colegio_id=colegio.id)
        else:
            messages.error(request, "El año, fecha de inicio y término son obligatorios.")

    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    cursos = CursoColegio.objects.filter(colegio=colegio).order_by('nivel', 'nombre')
    
    # Preparar el JSON de cursos de forma segura para evitar errores de parseo en JS
    cursos_data = []
    for c in cursos:
        nivel_label = 'TP'
        if c.nivel == 'parvularia': nivel_label = 'Parvularia'
        elif c.nivel == 'basica': nivel_label = 'Básica'
        elif c.nivel == 'media': nivel_label = 'Media'
        
        cursos_data.append({
            'curso': c.nombre.replace('\n', ' ').replace('\r', '').strip(),
            'nivel': nivel_label,
            'jornada': c.jornada,
            'desde_letra': c.desde_letra,
            'hasta_letra': c.hasta_letra
        })

    return render(request, 'configuracion_colegio_paso3.html', {'colegio': colegio, 'periodo': periodo, 'cursos': cursos, 'cursos_data': cursos_data})

def configuracion_colegio_paso4_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    # Validación de seguridad
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)

    roles = RolColegio.objects.filter(colegio=colegio)
    modulos = ColegioModulo.objects.filter(colegio=colegio, activo=True)

    if request.method == 'POST':
        permissions_data = request.POST.get('permissions_data')
        if permissions_data:
            try:
                data = json.loads(permissions_data)
                for rol_nombre, rol_info in data.items():
                    rol_obj = RolColegio.objects.filter(colegio=colegio, nombre=rol_nombre).first()
                    if rol_obj:
                        modules_data = rol_info.get('modules', {})
                        for mod_nombre, perms in modules_data.items():
                            from planes.models import Modulo
                            modulo_obj = Modulo.objects.filter(nombre__iexact=mod_nombre).first()
                            if modulo_obj:
                                rp, _ = RolPermiso.objects.get_or_create(rol=rol_obj, modulo=modulo_obj)
                                rp.puede_ver = perms.get('view', False)
                                rp.puede_crear = perms.get('create', False)
                                rp.puede_editar = perms.get('edit', False)
                                rp.puede_exportar = perms.get('export', False)
                                rp.save()
            except json.JSONDecodeError:
                messages.error(request, "Error procesando la configuración de permisos.")
                return redirect('configuracion_colegio_paso4', colegio_id=colegio.id)

        colegio.paso_configuracion_actual = 5
        colegio.save()
        return redirect('configuracion_colegio_paso5', colegio_id=colegio.id)
        
    # Preparar permisos guardados en JSON para inicializar la vista de forma correcta
    saved_permissions = {}
    for rol in roles:
        rol_perms = {}
        for rp in rol.permisos.all():
            rol_perms[rp.modulo.nombre] = {
                'view': rp.puede_ver,
                'create': rp.puede_crear,
                'edit': rp.puede_editar,
                'export': rp.puede_exportar,
            }
        if rol_perms:
            saved_permissions[rol.nombre] = rol_perms
            
    return render(request, 'configuracion_colegio_paso4.html', {
        'colegio': colegio, 'roles': roles, 'modulos': modulos,
        'saved_permissions_json': json.dumps(saved_permissions)
    })

def configuracion_colegio_paso5_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    # Validación de seguridad
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)

    if request.method == 'POST':
        modulos_colegio = ColegioModulo.objects.filter(colegio=colegio)
        for mod_col in modulos_colegio:
            estado = request.POST.get(f'modulo_{mod_col.modulo.id}')
            mod_col.activo = True if estado else False
            mod_col.save()
        
        colegio.configuracion_completa = True
        colegio.estado = 'activo'
        colegio.save()
        return redirect('dashboard_profesor')
    
    modulos = ColegioModulo.objects.filter(colegio=colegio)
    return render(request, 'configuracion_colegio_paso5.html', {'modulos_colegio': modulos, 'colegio': colegio})
