from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse

from django.contrib.auth import login, logout
from django.contrib.auth.models import User
import json
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from usuarios.models import PerfilUsuario

from .models import Colegio, Suscripcion, ColegioModulo, ConfiguracionAcademica, RolColegio, Permiso, RolPermiso, CursoColegio, SeccionCurso, Asignatura

from .forms import RegistroColegioPaso1Form, RegistroColegioPaso2Form
from solicitudes.models import MiembroColegio
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime



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
                                defaults={'nombre': f"{curso_obj.nombre} {letra}"[:150], 'activo': True}
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


from django.db.models import Q
from .models import Estudiante, Asignatura

def obtener_colegio_usuario(user):
    colegio = user.colegios_administrados.order_by('-fecha_creacion').first()
    if not colegio:
        miembro = MiembroColegio.objects.filter(usuario=user, activo=True).order_by('-fecha_ingreso').first()
        if miembro:
            colegio = miembro.colegio
    if colegio:
        asegurar_roles_base_colegio(colegio, user)
    return colegio


@login_required
def listar_estudiantes_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    # Filtrado por curso/seccion
    seccion_id = request.GET.get('seccion')
    busqueda = request.GET.get('q', '').strip()

    estudiantes = Estudiante.objects.filter(colegio=colegio).order_by('seccion__curso__nombre', 'nombre_completo')

    if seccion_id and seccion_id.isdigit():
        estudiantes = estudiantes.filter(seccion_id=int(seccion_id))

    if busqueda:
        estudiantes = estudiantes.filter(
            Q(nombre_completo__icontains=busqueda) | 
            Q(rut__icontains=busqueda)
        )

    # Secciones para el dropdown de filtros
    secciones = SeccionCurso.objects.filter(curso__colegio=colegio, activo=True).order_by('curso__nombre', 'nombre')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])

    paginator = Paginator(estudiantes, 10)
    page_number = request.GET.get('page', 1)
    estudiantes_page = paginator.get_page(page_number)

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'estudiantes': estudiantes_page,
        'secciones': secciones,
        'seccion_seleccionada': int(seccion_id) if seccion_id and seccion_id.isdigit() else None,
        'busqueda': busqueda,
    }
    return render(request, 'colegios/listar_estudiantes.html', context)



@login_required
def matricular_estudiante_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No tienes permisos de administrador.")
        return redirect('dashboard_usuario')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para matricular estudiantes.")
        return redirect('listar_estudiantes')

    if request.method == 'POST':
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        rut = request.POST.get('rut', '').strip()
        seccion_id = request.POST.get('seccion')

        if not nombre_completo or not seccion_id:
            messages.error(request, "El nombre completo y el curso/sección son requeridos.")
        else:
            seccion = get_object_or_404(SeccionCurso, id=seccion_id, curso__colegio=colegio)
            Estudiante.objects.create(
                colegio=colegio,
                seccion=seccion,
                nombre_completo=nombre_completo,
                rut=rut,
                activo=True
            )
            messages.success(request, f"Estudiante {nombre_completo} matriculado con éxito.")
            return redirect('listar_estudiantes')

    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    secciones = SeccionCurso.objects.filter(curso__colegio=colegio, activo=True).order_by('curso__nombre', 'nombre')
    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'secciones': secciones,
        'titulo_pagina': 'Matricular Estudiante',
        'boton_texto': 'Matricular',
    }
    return render(request, 'colegios/matricular_estudiante.html', context)


@login_required
def editar_estudiante_view(request, estudiante_id):
    colegio = obtener_colegio_usuario(request.user)
    estudiante = get_object_or_404(Estudiante, id=estudiante_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para editar estudiantes.")
        return redirect('listar_estudiantes')

    if request.method == 'POST':
        nombre_completo = request.POST.get('nombre_completo', '').strip()
        rut = request.POST.get('rut', '').strip()
        seccion_id = request.POST.get('seccion')
        activo = request.POST.get('activo') == 'true'

        if not nombre_completo or not seccion_id:
            messages.error(request, "El nombre completo y el curso/sección son requeridos.")
        else:
            seccion = get_object_or_404(SeccionCurso, id=seccion_id, curso__colegio=colegio)
            estudiante.nombre_completo = nombre_completo
            estudiante.rut = rut
            estudiante.seccion = seccion
            estudiante.activo = activo
            estudiante.save()
            messages.success(request, f"Ficha de {nombre_completo} modificada con éxito.")
            return redirect('listar_estudiantes')

    secciones = SeccionCurso.objects.filter(curso__colegio=colegio, activo=True).order_by('curso__nombre', 'nombre')
    context = {
        'colegio': colegio,
        'estudiante': estudiante,
        'secciones': secciones,
        'titulo_pagina': 'Editar Ficha de Estudiante',
        'boton_texto': 'Guardar Cambios',
    }
    return render(request, 'colegios/matricular_estudiante.html', context)

@login_required
def baja_estudiante_view(request, estudiante_id):
    colegio = obtener_colegio_usuario(request.user)
    estudiante = get_object_or_404(Estudiante, id=estudiante_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para dar de baja estudiantes.")
        return redirect('listar_estudiantes')

    estudiante.activo = not estudiante.activo
    estudiante.save()
    estado = "activado" if estudiante.activo else "desactivado (baja)"
    messages.success(request, f"Estudiante {estudiante.nombre_completo} ha sido {estado} correctamente.")
    return redirect('listar_estudiantes')

@login_required
def listar_asignaturas_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    
    plan_estudios = []
    for cur in cursos:
        asignaturas = Asignatura.objects.filter(curso=cur).order_by('nombre')
        plan_estudios.append({
            'curso': cur,
            'asignaturas': asignaturas,
            'cantidad': asignaturas.count()
        })

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'plan_estudios': plan_estudios,
        'is_admin': is_admin,
    }
    return render(request, 'colegios/listar_asignaturas.html', context)


@login_required
def crear_asignatura_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No tienes permisos.")
        return redirect('dashboard_usuario')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para crear asignaturas.")
        return redirect('listar_asignaturas')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        cursos_ids = request.POST.getlist('cursos')
        docente_id = request.POST.get('docente')

        if not nombre or not any(cursos_ids):
            messages.error(request, "El nombre de la asignatura y al menos un curso son requeridos.")
        else:
            docente = None
            if docente_id:
                docente = get_object_or_404(User, id=docente_id)
            
            created_count = 0
            for curso_id in cursos_ids:
                curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)
                exists = Asignatura.objects.filter(curso=curso, nombre=nombre).exists()
                if not exists:
                    Asignatura.objects.create(
                        colegio=colegio,
                        curso=curso,
                        nombre=nombre,
                        docente=docente,
                        activo=True
                    )
                    created_count += 1
            
            if created_count > 0:
                messages.success(request, f"Asignatura '{nombre}' creada con éxito en {created_count} curso(s).")
            else:
                messages.info(request, f"La asignatura '{nombre}' ya existía en los cursos seleccionados.")
            return redirect('listar_asignaturas')

    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    profesores_miembros = MiembroColegio.objects.filter(colegio=colegio, rol__nombre='Profesor', activo=True).select_related('usuario')
    profesores = [m.usuario for m in profesores_miembros]

    context = {
        'colegio': colegio,
        'cursos': cursos,
        'profesores': profesores,
        'titulo_pagina': 'Crear Nueva Asignatura',
        'boton_texto': 'Crear Asignatura',
        'es_creacion': True,
    }
    return render(request, 'colegios/crear_asignatura.html', context)

@login_required
def editar_asignatura_view(request, asignatura_id):
    colegio = obtener_colegio_usuario(request.user)
    asignatura = get_object_or_404(Asignatura, id=asignatura_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para editar asignaturas.")
        return redirect('listar_asignaturas')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        curso_id = request.POST.get('curso')
        docente_id = request.POST.get('docente')
        activo = request.POST.get('activo') == 'true'

        if not nombre or not curso_id:
            messages.error(request, "El nombre de la asignatura y el curso son requeridos.")
        else:
            curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)
            docente = None
            if docente_id:
                docente = get_object_or_404(User, id=docente_id)
            
            asignatura.nombre = nombre
            asignatura.curso = curso
            asignatura.docente = docente
            asignatura.activo = activo
            asignatura.save()
            
            messages.success(request, f"Asignatura '{nombre}' modificada con éxito.")
            return redirect('listar_asignaturas')

    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    profesores_miembros = MiembroColegio.objects.filter(colegio=colegio, rol__nombre='Profesor', activo=True).select_related('usuario')
    profesores = [m.usuario for m in profesores_miembros]

    context = {
        'colegio': colegio,
        'asignatura': asignatura,
        'cursos': cursos,
        'profesores': profesores,
        'titulo_pagina': 'Editar Asignatura',
        'boton_texto': 'Guardar Cambios',
        'es_creacion': False,
    }
    return render(request, 'colegios/crear_asignatura.html', context)

@login_required
def eliminar_asignatura_view(request, asignatura_id):
    colegio = obtener_colegio_usuario(request.user)
    asignatura = get_object_or_404(Asignatura, id=asignatura_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para eliminar asignaturas.")
        return redirect('listar_asignaturas')

    nombre = asignatura.nombre
    asignatura.delete()
    messages.success(request, f"La asignatura '{nombre}' ha sido eliminada correctamente.")
    return redirect('listar_asignaturas')

@login_required
def precargar_asignaturas_base_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No tienes permisos.")
        return redirect('dashboard_usuario')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect('listar_asignaturas')

    if request.method == 'POST':
        asignaturas_seleccionadas = request.POST.getlist('asignaturas_base')
        cursos_seleccionados = request.POST.getlist('cursos_destino')

        if not asignaturas_seleccionadas or not cursos_seleccionados:
            messages.error(request, "Debes seleccionar al menos una asignatura y al menos un curso.")
            return redirect('listar_asignaturas')

        created_count = 0
        for curso_id in cursos_seleccionados:
            curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)
            for nombre_asig in asignaturas_seleccionadas:
                exists = Asignatura.objects.filter(curso=curso, nombre=nombre_asig).exists()
                if not exists:
                    Asignatura.objects.create(
                        colegio=colegio,
                        curso=curso,
                        nombre=nombre_asig,
                        docente=None,
                        activo=True
                    )
                    created_count += 1

        if created_count > 0:
            messages.success(request, f"Se crearon exitosamente {created_count} asignaturas en los cursos seleccionados.")
        else:
            messages.info(request, "Todas las asignaturas seleccionadas ya existían en los cursos correspondientes.")

    return redirect('listar_asignaturas')

@login_required
def listar_cursos_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No tienes un establecimiento asociado.")
        return redirect('dashboard_usuario')
        
    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "Acceso denegado. Se requieren permisos de administrador.")
        return redirect('dashboard_usuario')

    cursos_db = CursoColegio.objects.filter(colegio=colegio).order_by('nombre')
    cursos_con_secciones = []
    for c in cursos_db:
        secciones = SeccionCurso.objects.filter(curso=c).order_by('nombre')
        cursos_con_secciones.append({
            'curso': c,
            'secciones': secciones,
            'cantidad_secciones': secciones.count()
        })

    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    paginator = Paginator(cursos_con_secciones, 10)
    page_number = request.GET.get('page', 1)
    cursos_page = paginator.get_page(page_number)

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'cursos_con_secciones': cursos_page,
        'hoy': timezone.now(),
        'is_admin': is_admin
    }

    return render(request, 'colegios/listar_cursos.html', context)


@login_required
def crear_curso_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos.")
        return redirect('listar_cursos')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, "El nombre del curso es requerido.")
        else:
            exists = CursoColegio.objects.filter(colegio=colegio, nombre=nombre).exists()
            if exists:
                curso = CursoColegio.objects.filter(colegio=colegio, nombre=nombre).first()
                if not curso.activo:
                    curso.activo = True
                    curso.save()
                    messages.success(request, f"El curso '{nombre}' ha sido reactivado.")
                else:
                    messages.error(request, f"El curso '{nombre}' ya existe.")
            else:
                CursoColegio.objects.create(
                    colegio=colegio,
                    nombre=nombre,
                    activo=True
                )
                messages.success(request, f"Curso '{nombre}' creado con éxito.")
    return redirect('listar_cursos')

@login_required
def editar_curso_view(request, curso_id):
    colegio = obtener_colegio_usuario(request.user)
    curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos.")
        return redirect('listar_cursos')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, "El nombre no puede estar vacío.")
        else:
            curso.nombre = nombre
            curso.save()
            messages.success(request, f"Curso actualizado a '{nombre}' correctamente.")
    return redirect('listar_cursos')

@login_required
def baja_curso_view(request, curso_id):
    colegio = obtener_colegio_usuario(request.user)
    curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos.")
        return redirect('listar_cursos')

    curso.activo = not curso.activo
    curso.save()
    
    SeccionCurso.objects.filter(curso=curso).update(activo=curso.activo)
    
    estado = "activado" if curso.activo else "desactivado (baja lógica)"
    messages.success(request, f"El curso '{curso.nombre}' ha sido {estado} correctamente.")
    return redirect('listar_cursos')

@login_required
def crear_seccion_view(request, curso_id):
    colegio = obtener_colegio_usuario(request.user)
    curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos.")
        return redirect('listar_cursos')

    if request.method == 'POST':
        secciones_nuevas = request.POST.getlist('secciones_nuevas')
        if not secciones_nuevas:
            messages.error(request, "Debes seleccionar al menos una sección.")
        else:
            created_count = 0
            ya_existen = []
            for valor in secciones_nuevas:
                valor = valor.strip()
                # El valor viene como "Sección A" - extraemos la letra (último carácter)
                letra = valor[-1].upper() if valor else ''
                if not letra or len(letra) != 1:
                    continue
                nombre_seccion = f"{curso.nombre} {letra}"
                secc, created = SeccionCurso.objects.get_or_create(
                    curso=curso,
                    letra=letra,
                    defaults={'nombre': nombre_seccion, 'activo': True}
                )
                if created:
                    created_count += 1
                elif not secc.activo:
                    secc.activo = True
                    secc.nombre = nombre_seccion
                    secc.save()
                    created_count += 1
                else:
                    ya_existen.append(letra)
            if created_count > 0:
                messages.success(request, f"Se agregaron {created_count} secciones correctamente a {curso.nombre}.")
            if ya_existen:
                messages.warning(request, f"Las secciones {', '.join(ya_existen)} ya existen en {curso.nombre}.")
    return redirect('listar_cursos')


@login_required
def baja_seccion_view(request, seccion_id):
    colegio = obtener_colegio_usuario(request.user)
    seccion = get_object_or_404(SeccionCurso, id=seccion_id, curso__colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos.")
        return redirect('listar_cursos')

    from colegios.models import Estudiante
    if Estudiante.objects.filter(seccion=seccion).exists():
        messages.error(request, f"No se puede eliminar la sección '{seccion.nombre}' porque contiene alumnos matriculados.")
    else:
        nombre = seccion.nombre
        seccion.delete()
        messages.success(request, f"La sección '{nombre}' ha sido eliminada correctamente.")
    return redirect('listar_cursos')

def asegurar_roles_base_colegio(colegio, usuario=None):

    if not RolColegio.objects.filter(colegio=colegio).exists():
        roles_base = RolColegio.objects.filter(es_base=True, colegio=None)
        if not roles_base.exists():
            nombres_base = [
                ('Administrador', 'Acceso total a la administración y gestión institucional.'),
                ('Director', 'Dirección académica, reportes y políticas de evaluación.'),
                ('Profesor', 'Gestión de clases, calificaciones, asistencia y observaciones.'),
                ('Inspector', 'Control de asistencia general y convivencia escolar.'),
                ('Secretario', 'Administración de matrículas y documentación de estudiantes.'),
                ('Contabilidad', 'Gestión de cobros, facturación y finanzas.'),
                ('Apoderado', 'Visualización de notas, asistencia y comunicados de pupilos.')
            ]
            for nombre, desc in nombres_base:
                RolColegio.objects.get_or_create(
                    colegio=None,
                    nombre=nombre,
                    defaults={'descripcion': desc, 'es_base': True, 'activo': True}
                )
            roles_base = RolColegio.objects.filter(es_base=True, colegio=None)

        for rb in roles_base:
            nuevo_rol = RolColegio.objects.create(
                colegio=colegio,
                nombre=rb.nombre,
                descripcion=rb.descripcion,
                es_base=False,
                activo=True
            )
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
            if usuario and rb.nombre == 'Administrador':
                MiembroColegio.objects.get_or_create(
                    usuario=usuario,
                    colegio=colegio,
                    defaults={'rol': nuevo_rol, 'activo': True}
                )


@login_required
def listar_personal_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No tienes un establecimiento asociado.")
        return redirect('dashboard_usuario')
        
    asegurar_roles_base_colegio(colegio, request.user)

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "Acceso denegado. Se requieren permisos de administrador.")
        return redirect('dashboard_usuario')

    personal = MiembroColegio.objects.filter(colegio=colegio).select_related('usuario', 'rol').order_by('usuario__first_name')
    roles = RolColegio.objects.filter(colegio=colegio).order_by('nombre')
    asignaturas_colegio = Asignatura.objects.filter(colegio=colegio, activo=True).select_related('curso')

    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    paginator = Paginator(personal, 10)
    page_number = request.GET.get('page', 1)
    personal_page = paginator.get_page(page_number)

    context = {
        'colegio': colegio,
        'miembro': miembro_solicitante,
        'periodo': periodo,
        'personal': personal_page,
        'roles': roles,
        'asignaturas_colegio': asignaturas_colegio,
        'hoy': timezone.now(),
        'is_admin': is_admin
    }
    return render(request, 'colegios/listar_personal.html', context)



@login_required
def crear_rol_personalizado_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "Acceso denegado. Se requieren permisos de Administrador.")
        return redirect('listar_personal')

    if request.method == 'POST':
        nombre_rol = request.POST.get('nombre_rol', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not nombre_rol:
            messages.error(request, "El nombre del rol es obligatorio.")
            return redirect('listar_personal')

        rol_existente = RolColegio.objects.filter(colegio=colegio, nombre__iexact=nombre_rol).first()
        if rol_existente:
            messages.warning(request, f"El rol '{nombre_rol}' ya existe en tu colegio.")
            return redirect('listar_personal')

        nuevo_rol = RolColegio.objects.create(
            colegio=colegio,
            nombre=nombre_rol,
            descripcion=descripcion,
            es_base=False,
            activo=True
        )
        messages.success(request, f"¡El rol personalizado '{nuevo_rol.nombre}' fue creado exitosamente!")

    return redirect('listar_personal')



@login_required
def asignar_asignaturas_docente_view(request, miembro_id):
    colegio = obtener_colegio_usuario(request.user)
    miembro = get_object_or_404(MiembroColegio, id=miembro_id, colegio=colegio)

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "Acceso denegado. Se requieren permisos de administrador.")
        return redirect('listar_personal')

    if request.method == 'POST':
        asignaturas_ids = request.POST.getlist('asignaturas')
        # Limpiar asignaciones previas de este docente en este colegio
        Asignatura.objects.filter(colegio=colegio, docente=miembro.usuario).update(docente=None)
        # Asignar seleccionadas
        if asignaturas_ids:
            Asignatura.objects.filter(colegio=colegio, id__in=asignaturas_ids).update(docente=miembro.usuario)

        docente_nombre = miembro.usuario.get_full_name() or miembro.usuario.username
        messages.success(request, f"Se actualizaron exitosamente las asignaturas asignadas a {docente_nombre}.")

    return redirect('listar_personal')



@login_required
def editar_personal_view(request, miembro_id):
    colegio = obtener_colegio_usuario(request.user)
    miembro = get_object_or_404(MiembroColegio, id=miembro_id, colegio=colegio)

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos.")
        return redirect('listar_personal')

    if request.method == 'POST':
        rol_id = request.POST.get('rol')
        if rol_id:
            nuevo_rol = get_object_or_404(RolColegio, id=rol_id, colegio=colegio)
            miembro.rol = nuevo_rol
            miembro.save()
            messages.success(request, f"El rol de {miembro.usuario.username} ha sido cambiado a {nuevo_rol.nombre}.")
    return redirect('listar_personal')

@login_required
def baja_personal_view(request, miembro_id):
    colegio = obtener_colegio_usuario(request.user)
    miembro = get_object_or_404(MiembroColegio, id=miembro_id, colegio=colegio)

    if miembro.usuario == request.user:
        messages.error(request, "No puedes cambiar tu propio estado de acceso.")
        return redirect('listar_personal')

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos.")
        return redirect('listar_personal')

    miembro.activo = not miembro.activo
    miembro.save()
    
    estado = "reactivado" if miembro.activo else "desactivado (baja de acceso)"
    messages.success(request, f"El acceso para {miembro.usuario.username} ha sido {estado}.")
    return redirect('listar_personal')


@login_required
def centro_reportes_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    secciones_count = SeccionCurso.objects.filter(curso__colegio=colegio, activo=True).count()
    estudiantes_count = Estudiante.objects.filter(colegio=colegio, activo=True).count()

    from asistencia.utils import calcular_alumnos_en_riesgo
    alumnos_riesgo_asistencia = len(calcular_alumnos_en_riesgo(colegio))

    from calificaciones.models import Nota
    alumnos_riesgo_notas = Nota.objects.filter(evaluacion__colegio=colegio, valor__lt=4.0).values('estudiante').distinct().count()

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'secciones_count': secciones_count,
        'estudiantes_count': estudiantes_count,
        'alumnos_riesgo_asistencia': alumnos_riesgo_asistencia,
        'alumnos_riesgo_notas': alumnos_riesgo_notas,
        'hoy': timezone.now(),
    }
    return render(request, 'colegios/reportes_hub.html', context)


@login_required
def configuracion_politicas_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )
    if not is_admin:
        messages.error(request, "Acceso denegado. Se requieren permisos de Administrador.")
        return redirect('dashboard_usuario')

    periodo, _ = ConfiguracionAcademica.objects.get_or_create(
        colegio=colegio,
        defaults={
            'anio_academico': timezone.now().year,
            'fecha_inicio': timezone.now().date(),
            'fecha_termino': timezone.now().date(),
        }
    )

    if request.method == 'POST':
        periodo.modalidad_asistencia = request.POST.get('modalidad_asistencia', 'asignatura')
        try:
            periodo.porcentaje_asistencia_minima = int(request.POST.get('porcentaje_asistencia_minima', 85))
        except ValueError:
            periodo.porcentaje_asistencia_minima = 85

        periodo.tipo_calificacion = request.POST.get('tipo_calificacion', 'numerica')
        try:
            periodo.nota_minima_aprobacion = float(request.POST.get('nota_minima_aprobacion', 4.0))
        except ValueError:
            periodo.nota_minima_aprobacion = 4.0

        try:
            periodo.porcentaje_exigencia = int(request.POST.get('porcentaje_exigencia', 60))
        except ValueError:
            periodo.porcentaje_exigencia = 60

        periodo.regla_redondeo = request.POST.get('regla_redondeo', 'un_decimal')
        periodo.tipo_calculo_promedio = request.POST.get('tipo_calculo_promedio', 'ponderado')
        periodo.visibilidad_notas_apoderados = request.POST.get('visibilidad_notas_apoderados', 'inmediata')
        periodo.notificar_ausencias = (request.POST.get('notificar_ausencias') == 'on')
        periodo.notificar_notas_rojas = (request.POST.get('notificar_notas_rojas') == 'on')

        periodo.save()
        messages.success(request, "¡Configuración de Políticas Académicas actualizada exitosamente!")
        return redirect('configuracion_politicas')

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'hoy': timezone.now(),
    }
    return render(request, 'colegios/configuracion_politicas.html', context)


@login_required
def hoja_vida_estudiante_view(request, estudiante_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    estudiante = get_object_or_404(Estudiante, id=estudiante_id, colegio=colegio)
    seccion = estudiante.seccion
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    if request.method == 'POST':
        tipo = request.POST.get('tipo', 'neutra')
        gravedad = request.POST.get('gravedad', 'leve')
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        asignatura_id = request.POST.get('asignatura_id')

        if not titulo or not descripcion:
            messages.error(request, "El título y la descripción son obligatorios.")
            return redirect('hoja_vida_estudiante', estudiante_id=estudiante.id)

        asig_obj = None
        if asignatura_id:
            asig_obj = Asignatura.objects.filter(id=asignatura_id, colegio=colegio).first()

        from colegios.models import AnotacionEstudiante
        AnotacionEstudiante.objects.create(
            colegio=colegio,
            estudiante=estudiante,
            asignatura=asig_obj,
            docente=request.user,
            tipo=tipo,
            gravedad=gravedad,
            titulo=titulo,
            descripcion=descripcion,
            fecha=timezone.now().date()
        )
        messages.success(request, f"¡Anotación agregada exitosamente a la hoja de vida de {estudiante.nombre_completo}!")
        return redirect('hoja_vida_estudiante', estudiante_id=estudiante.id)

    from colegios.models import AnotacionEstudiante
    anotaciones = AnotacionEstudiante.objects.filter(estudiante=estudiante).select_related('docente', 'asignatura')

    positivas_cnt = anotaciones.filter(tipo='positiva').count()
    negativas_cnt = anotaciones.filter(tipo='negativa').count()
    citaciones_cnt = anotaciones.filter(tipo='citacion').count()
    neutras_cnt = anotaciones.filter(tipo='neutra').count()

    if negativas_cnt == 0:
        semaforo_estado = 'excelente'
        semaforo_texto = 'Excelente Conducta'
        semaforo_color = 'success'
    elif negativas_cnt <= 2:
        semaforo_estado = 'atencion'
        semaforo_texto = 'Atención Requerida'
        semaforo_color = 'warning'
    else:
        semaforo_estado = 'alerta'
        semaforo_texto = 'Alerta Convivencia Escolar'
        semaforo_color = 'danger'

    asignaturas_curso = []
    estudiantes_seccion = []
    if seccion:
        asignaturas_curso = Asignatura.objects.filter(curso=seccion.curso, activo=True).order_by('nombre')
        estudiantes_seccion = Estudiante.objects.filter(seccion=seccion, activo=True).order_by('nombre_completo')

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'convivencia',
        'estudiante': estudiante,
        'seccion': seccion,
        'estudiantes_seccion': estudiantes_seccion,
        'anotaciones': anotaciones,
        'positivas_cnt': positivas_cnt,
        'negativas_cnt': negativas_cnt,
        'citaciones_cnt': citaciones_cnt,
        'neutras_cnt': neutras_cnt,
        'semaforo_estado': semaforo_estado,
        'semaforo_texto': semaforo_texto,
        'semaforo_color': semaforo_color,
        'asignaturas_curso': asignaturas_curso,
        'hoy': timezone.now(),
    }
    return render(request, 'colegios/hoja_vida_estudiante.html', context)



@login_required
def eliminar_anotacion_view(request, anotacion_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    from colegios.models import AnotacionEstudiante
    anotacion = get_object_or_404(AnotacionEstudiante, id=anotacion_id, colegio=colegio)
    estudiante_id = anotacion.estudiante.id

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    if not is_admin and anotacion.docente != request.user:
        messages.error(request, "No tienes permiso para eliminar esta anotación.")
        return redirect('hoja_vida_estudiante', estudiante_id=estudiante_id)

    anotacion.delete()
    messages.success(request, "Anotación eliminada correctamente.")
    return redirect('hoja_vida_estudiante', estudiante_id=estudiante_id)


@login_required
def convivencia_hub_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    secciones = SeccionCurso.objects.filter(curso__colegio=colegio, activo=True).select_related('curso').order_by('curso__nombre', 'nombre')

    seccion_id = request.GET.get('seccion')
    busqueda = request.GET.get('q', '').strip()

    estudiantes_qs = Estudiante.objects.filter(colegio=colegio, activo=True).select_related('seccion', 'seccion__curso').order_by('seccion__curso__nombre', 'nombre_completo')

    if seccion_id and seccion_id.isdigit():
        estudiantes_qs = estudiantes_qs.filter(seccion_id=int(seccion_id))

    if busqueda:
        from django.db.models import Q
        estudiantes_qs = estudiantes_qs.filter(
            Q(nombre_completo__icontains=busqueda) | Q(rut__icontains=busqueda)
        )

    from colegios.models import AnotacionEstudiante
    estudiantes_data = []
    total_alertas_count = 0

    for est in estudiantes_qs:
        anotaciones = AnotacionEstudiante.objects.filter(estudiante=est)
        pos_cnt = anotaciones.filter(tipo='positiva').count()
        neg_cnt = anotaciones.filter(tipo='negativa').count()
        cit_cnt = anotaciones.filter(tipo='citacion').count()

        if neg_cnt == 0:
            semaforo_color = 'success'
            semaforo_text = 'Excelente'
        elif neg_cnt <= 2:
            semaforo_color = 'warning'
            semaforo_text = 'Atención'
        else:
            semaforo_color = 'danger'
            semaforo_text = 'Alerta'
            total_alertas_count += 1

        estudiantes_data.append({
            'estudiante': est,
            'pos_cnt': pos_cnt,
            'neg_cnt': neg_cnt,
            'cit_cnt': cit_cnt,
            'semaforo_color': semaforo_color,
            'semaforo_text': semaforo_text,
        })

    paginator = Paginator(estudiantes_data, 10)
    page_number = request.GET.get('page', 1)
    estudiantes_data_page = paginator.get_page(page_number)

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'convivencia',
        'secciones': secciones,
        'seccion_seleccionada': int(seccion_id) if (seccion_id and seccion_id.isdigit()) else None,
        'busqueda': busqueda,
        'estudiantes_data': estudiantes_data_page,
        'total_alertas_count': total_alertas_count,
        'hoy': timezone.now(),
    }
    return render(request, 'colegios/convivencia_hub.html', context)



@login_required
def calendario_escolar_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    from colegios.models import EventoAgenda
    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        tipo = request.POST.get('tipo', 'actividad')
        fecha_str = request.POST.get('fecha_inicio')
        hora_str = request.POST.get('hora_inicio', '08:00')
        lugar = request.POST.get('lugar', '').strip()
        curso_id = request.POST.get('curso_id')

        asignado_a_id = request.POST.get('asignado_a_id')
        es_para_todos = (request.POST.get('es_para_todos') in ['on', '1', 'true'])
        es_recurrente = (request.POST.get('es_recurrente') in ['on', '1', 'true'])

        descripcion = request.POST.get('descripcion', '').strip()

        if titulo and fecha_str:
            try:
                dt_str = f"{fecha_str} {hora_str}"
                fecha_inicio = timezone.make_aware(datetime.strptime(dt_str, '%Y-%m-%d %H:%M'))
            except ValueError:
                fecha_inicio = timezone.now()

            dia_semana = fecha_inicio.weekday() if es_recurrente else None
            curso_obj = CursoColegio.objects.filter(id=curso_id, colegio=colegio).first() if (curso_id and curso_id.isdigit()) else None
            asignado_obj = User.objects.filter(id=asignado_a_id).first() if (asignado_a_id and asignado_a_id.isdigit()) else None

            EventoAgenda.objects.create(
                colegio=colegio,
                creado_por=request.user,
                asignado_a=asignado_obj,
                es_para_todos=es_para_todos,
                es_recurrente=es_recurrente,
                dia_semana=dia_semana,
                titulo=titulo,
                tipo=tipo,
                fecha_inicio=fecha_inicio,
                lugar=lugar if lugar else None,
                curso=curso_obj,
                descripcion=descripcion if descripcion else None
            )
            messages.success(request, f"¡Evento '{titulo}' guardado en la agenda!")
            return redirect('calendario_escolar')

    hoy_date = timezone.now().date()
    eventos_hoy = EventoAgenda.objects.filter(colegio=colegio, fecha_inicio__date=hoy_date).order_by('fecha_inicio')
    proximos_eventos = EventoAgenda.objects.filter(colegio=colegio, fecha_inicio__date__gte=hoy_date).order_by('fecha_inicio')[:20]
    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nivel', 'nombre')
    personal = MiembroColegio.objects.filter(colegio=colegio, activo=True).select_related('usuario', 'rol').order_by('usuario__first_name')

    abs_ical_url = request.build_absolute_uri(reverse('exportar_ical_agenda')) + f"?colegio_id={colegio.id}"
    webcal_url = abs_ical_url.replace('https://', 'webcal://').replace('http://', 'webcal://')
    google_cal_feed_url = f"https://calendar.google.com/calendar/r?cid={webcal_url}"


    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'calendario',
        'eventos_hoy': eventos_hoy,
        'proximos_eventos': proximos_eventos,
        'cursos': cursos,
        'personal': personal,
        'hoy': timezone.now(),
        'abs_ical_url': abs_ical_url,
        'webcal_url': webcal_url,
        'google_cal_feed_url': google_cal_feed_url,
    }
    return render(request, 'colegios/calendario_escolar.html', context)



@login_required
def api_eventos_calendario_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return JsonResponse([], safe=False)

    docente_id = request.GET.get('docente_id')
    from colegios.models import EventoAgenda
    from django.db.models import Q

    qs = EventoAgenda.objects.filter(colegio=colegio)

    if docente_id and docente_id.isdigit():
        target_uid = int(docente_id)
        qs = qs.filter(Q(asignado_a_id=target_uid) | Q(creado_por_id=target_uid) | Q(es_para_todos=True))

    events_list = []
    color_map = {
        'clase': '#7C5CFC',       # Morado
        'evaluacion': '#E11D48',  # Rojo
        'reunion': '#D97706',     # Naranja
        'actividad': '#059669',   # Verde
    }

    for ev in qs:
        item = {
            'id': ev.id,
            'title': ev.titulo,
            'backgroundColor': color_map.get(ev.tipo, '#7C5CFC'),
            'borderColor': color_map.get(ev.tipo, '#7C5CFC'),
            'extendedProps': {
                'tipo': ev.get_tipo_display(),
                'lugar': ev.lugar or 'Sin definir',
                'curso': ev.curso.nombre if ev.curso else 'General',
                'docente': ev.asignado_a.get_full_name() if ev.asignado_a else ('Todos' if ev.es_para_todos else (ev.creado_por.get_full_name() if ev.creado_por else 'Institución')),
                'descripcion': ev.descripcion or '',
                'es_recurrente': ev.es_recurrente,
            }
        }
        if ev.es_recurrente and ev.dia_semana is not None:
            fc_dow = (ev.dia_semana + 1) % 7
            item['daysOfWeek'] = [fc_dow]
            item['startTime'] = ev.fecha_inicio.strftime('%H:%M:%S')
        else:
            item['start'] = ev.fecha_inicio.isoformat()
            if ev.fecha_fin:
                item['end'] = ev.fecha_fin.isoformat()

        events_list.append(item)

    return JsonResponse(events_list, safe=False)



def exportar_ical_agenda_view(request):
    from django.http import HttpResponse
    from colegios.models import Colegio, EventoAgenda

    colegio = None
    if request.user.is_authenticated:
        colegio = obtener_colegio_usuario(request.user)

    colegio_id = request.GET.get('colegio_id')
    if not colegio and colegio_id and colegio_id.isdigit():
        colegio = Colegio.objects.filter(id=colegio_id).first()

    if not colegio:
        return HttpResponse("Colegio no encontrado.", status=404)

    eventos = EventoAgenda.objects.filter(colegio=colegio).order_by('fecha_inicio')

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Eduteka//Agenda Escolar//ES",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:Agenda {colegio.nombre}",
    ]

    for ev in eventos:
        dtstart = ev.fecha_inicio.strftime('%Y%m%dT%H%M%SZ')
        dtstamp = ev.fecha_creacion.strftime('%Y%m%dT%H%M%SZ')
        summary = ev.titulo.replace('\n', ' ')
        desc = (ev.descripcion or '').replace('\n', ' ')
        location = (ev.lugar or '').replace('\n', ' ')

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:eduteka-event-{ev.id}@{colegio.id}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"LOCATION:{location}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ics_content = "\r\n".join(lines)

    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="agenda_{colegio.id}.ics"'
    return response



@login_required
def eliminar_evento_agenda_view(request, evento_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No estás asociado a ningún colegio.")
        return redirect('solicitar_acceso')

    from colegios.models import EventoAgenda
    evento = get_object_or_404(EventoAgenda, id=evento_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    if not is_admin and evento.creado_por != request.user:
        messages.error(request, "No tienes permiso para eliminar este evento.")
        return redirect('calendario_escolar')

    evento.delete()
    messages.success(request, "Evento eliminado de la agenda.")
    return redirect('calendario_escolar')







