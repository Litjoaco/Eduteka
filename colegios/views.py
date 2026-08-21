import json
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.utils import timezone

from usuarios.models import PerfilUsuario
from solicitudes.models import MiembroColegio
from .models import (
    Colegio, Suscripcion, ColegioModulo, ConfiguracionAcademica, 
    RolColegio, Permiso, RolPermiso, CursoColegio, SeccionCurso, 
    Asignatura, ConfiguracionModulos
)
from .forms import RegistroColegioPaso1Form, RegistroColegioPaso2Form



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
        
    from planes.models import Plan, Modulo
    planes = Plan.objects.filter(activo=True).prefetch_related('modulos').order_by('precio_mensual')
    modulos = Modulo.objects.filter(activo=True).order_by('id')

    return render(request, 'registrocolegiopaso2.html', {
        'form': form, 
        'colegio': colegio,
        'planes': planes,
        'modulos': modulos,
        'modulos_disponibles': modulos
    })

def api_buscar_colegios(request):
    q = request.GET.get('q', '').strip()
    if q:
        colegios = Colegio.objects.filter(nombre__icontains=q)[:10]
    else:
        # Si no hay query, mostrar colegios activos recientes como sugerencia inicial
        colegios = Colegio.objects.all().order_by('-id')[:8]

    resultados = []
    for c in colegios:
        logo_url = c.logo.url if (c.logo and hasattr(c.logo, 'url')) else ''
        tipo_str = c.get_tipo_institucion_display() if hasattr(c, 'get_tipo_institucion_display') else (c.tipo_institucion or 'Colegio')
        resultados.append({
            'id': c.id,
            'nombre': c.nombre,
            'nombre_corto': c.nombre_corto or '',
            'eslogan': c.eslogan or '',
            'logo_url': logo_url,
            'color_principal': c.color_principal or '#7C5CFC',
            'ciudad_comuna': c.ciudad_comuna or '',
            'region': c.region or '',
            'tipo_institucion': tipo_str,
        })
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

    # Asegurar que existan los roles base institucionales
    asegurar_roles_base_colegio(colegio, request.user)

    # Asegurar módulos activos base si no existen aún
    if not ColegioModulo.objects.filter(colegio=colegio).exists():
        from planes.models import Modulo
        for mod in Modulo.objects.all():
            ColegioModulo.objects.get_or_create(colegio=colegio, modulo=mod, defaults={'activo': True})

    roles = RolColegio.objects.filter(colegio=colegio).exclude(nombre__iexact='Apoderado').order_by('id')
    modulos = ColegioModulo.objects.filter(colegio=colegio, activo=True).select_related('modulo').order_by('modulo__nombre')

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
        
    # Preparar permisos guardados en JSON para inicializar la vista de forma reactiva
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
        'colegio': colegio, 
        'roles': roles, 
        'modulos': modulos,
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
        
        colegio.paso_configuracion_actual = 6
        colegio.save()
        return redirect('configuracion_colegio_paso6', colegio_id=colegio.id)
    
    modulos = ColegioModulo.objects.filter(colegio=colegio)
    return render(request, 'configuracion_colegio_paso5.html', {'modulos_colegio': modulos, 'colegio': colegio})


def configuracion_colegio_paso6_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)

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

        # Completar la configuración institucional del colegio
        colegio.configuracion_completa = True
        colegio.estado = 'activo'
        colegio.save()

        return redirect('configuracion_colegio_finalizando', colegio_id=colegio.id)

    return render(request, 'configuracion_colegio_paso6.html', {
        'colegio': colegio,
        'periodo': periodo,
    })


def configuracion_colegio_finalizando_view(request, colegio_id):
    if not request.user.is_authenticated:
        return redirect('registro_colegio')
    colegio = get_object_or_404(Colegio, id=colegio_id, administrador=request.user)
    return render(request, 'configuracion_colegio_finalizando.html', {
        'colegio': colegio,
    })


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

    total_matriculados = estudiantes.count()
    total_activos = estudiantes.filter(activo=True).count()
    total_pie = estudiantes.filter(es_pie=True).count()
    total_baja = estudiantes.filter(activo=False).count()

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
        'total_matriculados': total_matriculados,
        'total_activos': total_activos,
        'total_pie': total_pie,
        'total_baja': total_baja,
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

        # Personal
        fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        genero = request.POST.get('genero', 'no_informa')
        nacionalidad = request.POST.get('nacionalidad', 'Chilena').strip()
        direccion = request.POST.get('direccion', '').strip()
        comuna = request.POST.get('comuna', '').strip()

        # Salud y emergencia
        prevision_salud = request.POST.get('prevision_salud', 'fonasa')
        grupo_sanguineo = request.POST.get('grupo_sanguineo', '').strip()
        alergias_enfermedades = request.POST.get('alergias_enfermedades', '').strip()
        contacto_emergencia_nombre = request.POST.get('contacto_emergencia_nombre', '').strip()
        contacto_emergencia_parentesco = request.POST.get('contacto_emergencia_parentesco', '').strip()
        contacto_emergencia_telefono = request.POST.get('contacto_emergencia_telefono', '').strip()

        # Apoderado
        nombre_apoderado = request.POST.get('nombre_apoderado', '').strip()
        rut_apoderado = request.POST.get('rut_apoderado', '').strip()
        telefono_apoderado = request.POST.get('telefono_apoderado', '').strip()
        email_apoderado = request.POST.get('email_apoderado', '').strip()
        parentesco_apoderado = request.POST.get('parentesco_apoderado', '').strip()

        # PIE
        es_pie = request.POST.get('es_pie') == 'on' or request.POST.get('es_pie') == 'true'
        tipo_pie = request.POST.get('tipo_pie', '')
        diagnostico_pie = request.POST.get('diagnostico_pie', '').strip()
        observaciones_pie = request.POST.get('observaciones_pie', '').strip()

        if not nombre_completo or not seccion_id:
            messages.error(request, "El nombre completo y el curso/sección son requeridos.")
        else:
            seccion = get_object_or_404(SeccionCurso, id=seccion_id, curso__colegio=colegio)
            Estudiante.objects.create(
                colegio=colegio,
                seccion=seccion,
                nombre_completo=nombre_completo,
                rut=rut,
                fecha_nacimiento=fecha_nacimiento,
                genero=genero,
                nacionalidad=nacionalidad,
                direccion=direccion,
                comuna=comuna,
                prevision_salud=prevision_salud,
                grupo_sanguineo=grupo_sanguineo,
                alergias_enfermedades=alergias_enfermedades,
                contacto_emergencia_nombre=contacto_emergencia_nombre,
                contacto_emergencia_parentesco=contacto_emergencia_parentesco,
                contacto_emergencia_telefono=contacto_emergencia_telefono,
                nombre_apoderado=nombre_apoderado,
                rut_apoderado=rut_apoderado,
                telefono_apoderado=telefono_apoderado,
                email_apoderado=email_apoderado,
                parentesco_apoderado=parentesco_apoderado,
                es_pie=es_pie,
                tipo_pie=tipo_pie if es_pie else None,
                diagnostico_pie=diagnostico_pie if es_pie else None,
                observaciones_pie=observaciones_pie if es_pie else None,
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
        'boton_texto': 'Matricular Estudiante',
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

        # Personal
        fecha_nacimiento = request.POST.get('fecha_nacimiento') or None
        genero = request.POST.get('genero', 'no_informa')
        nacionalidad = request.POST.get('nacionalidad', 'Chilena').strip()
        direccion = request.POST.get('direccion', '').strip()
        comuna = request.POST.get('comuna', '').strip()

        # Salud y emergencia
        prevision_salud = request.POST.get('prevision_salud', 'fonasa')
        grupo_sanguineo = request.POST.get('grupo_sanguineo', '').strip()
        alergias_enfermedades = request.POST.get('alergias_enfermedades', '').strip()
        contacto_emergencia_nombre = request.POST.get('contacto_emergencia_nombre', '').strip()
        contacto_emergencia_parentesco = request.POST.get('contacto_emergencia_parentesco', '').strip()
        contacto_emergencia_telefono = request.POST.get('contacto_emergencia_telefono', '').strip()

        # Apoderado
        nombre_apoderado = request.POST.get('nombre_apoderado', '').strip()
        rut_apoderado = request.POST.get('rut_apoderado', '').strip()
        telefono_apoderado = request.POST.get('telefono_apoderado', '').strip()
        email_apoderado = request.POST.get('email_apoderado', '').strip()
        parentesco_apoderado = request.POST.get('parentesco_apoderado', '').strip()

        # PIE
        es_pie = request.POST.get('es_pie') == 'on' or request.POST.get('es_pie') == 'true'
        tipo_pie = request.POST.get('tipo_pie', '')
        diagnostico_pie = request.POST.get('diagnostico_pie', '').strip()
        observaciones_pie = request.POST.get('observaciones_pie', '').strip()

        if not nombre_completo or not seccion_id:
            messages.error(request, "El nombre completo y el curso/sección son requeridos.")
        else:
            seccion = get_object_or_404(SeccionCurso, id=seccion_id, curso__colegio=colegio)
            estudiante.nombre_completo = nombre_completo
            estudiante.rut = rut
            estudiante.seccion = seccion
            estudiante.fecha_nacimiento = fecha_nacimiento
            estudiante.genero = genero
            estudiante.nacionalidad = nacionalidad
            estudiante.direccion = direccion
            estudiante.comuna = comuna
            estudiante.prevision_salud = prevision_salud
            estudiante.grupo_sanguineo = grupo_sanguineo
            estudiante.alergias_enfermedades = alergias_enfermedades
            estudiante.contacto_emergencia_nombre = contacto_emergencia_nombre
            estudiante.contacto_emergencia_parentesco = contacto_emergencia_parentesco
            estudiante.contacto_emergencia_telefono = contacto_emergencia_telefono
            estudiante.nombre_apoderado = nombre_apoderado
            estudiante.rut_apoderado = rut_apoderado
            estudiante.telefono_apoderado = telefono_apoderado
            estudiante.email_apoderado = email_apoderado
            estudiante.parentesco_apoderado = parentesco_apoderado
            estudiante.es_pie = es_pie
            estudiante.tipo_pie = tipo_pie if es_pie else None
            estudiante.diagnostico_pie = diagnostico_pie if es_pie else None
            estudiante.observaciones_pie = observaciones_pie if es_pie else None
            estudiante.activo = activo
            estudiante.save()
            messages.success(request, f"Ficha de {nombre_completo} modificada con éxito.")
            return redirect('listar_estudiantes')

    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    secciones = SeccionCurso.objects.filter(curso__colegio=colegio, activo=True).order_by('curso__nombre', 'nombre')
    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
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

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "Acceso restringido. Se requieren permisos de Director o Administrador para gestionar el plan de estudios.")
        return redirect('dashboard_usuario')

    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    
    plan_estudios = []
    total_asignaturas = 0
    total_con_docente = 0

    for cur in cursos:
        asignaturas = Asignatura.objects.filter(curso=cur, activo=True).select_related('docente').order_by('nombre')
        asig_count = asignaturas.count()
        asig_con_doc = asignaturas.filter(docente__isnull=False).count()
        total_asignaturas += asig_count
        total_con_docente += asig_con_doc

        plan_estudios.append({
            'curso': cur,
            'asignaturas': asignaturas,
            'cantidad': asig_count,
            'con_docente': asig_con_doc,
            'sin_docente': asig_count - asig_con_doc,
        })

    profesores_miembros = MiembroColegio.objects.filter(colegio=colegio, activo=True).select_related('usuario', 'rol').order_by('usuario__first_name')
    docentes_disponibles = [m.usuario for m in profesores_miembros]

    total_sin_docente = total_asignaturas - total_con_docente
    cobertura = round((total_con_docente / total_asignaturas * 100)) if total_asignaturas > 0 else 100

    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'plan_estudios': plan_estudios,
        'docentes_disponibles': docentes_disponibles,
        'profesores_miembros': profesores_miembros,
        'total_asignaturas': total_asignaturas,
        'total_con_docente': total_con_docente,
        'total_sin_docente': total_sin_docente,
        'cobertura': cobertura,
        'is_admin': is_admin,
    }
    return render(request, 'colegios/listar_asignaturas.html', context)


@login_required
def asignar_docente_asignatura_view(request, asignatura_id):
    colegio = obtener_colegio_usuario(request.user)
    asignatura = get_object_or_404(Asignatura, id=asignatura_id, colegio=colegio)

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'No tienes permisos'}, status=403)
        messages.error(request, "No tienes permisos para asignar docentes.")
        return redirect('listar_asignaturas')

    if request.method == 'POST':
        docente_id = request.POST.get('docente_id', '').strip()
        horas = request.POST.get('horas_semanales', '').strip()

        if horas and horas.isdigit():
            asignatura.horas_semanales = max(1, int(horas))

        if not docente_id or docente_id == 'none' or docente_id == '0':
            asignatura.docente = None
            asignatura.save()
            msg = f"Se removió el docente de la asignatura '{asignatura.nombre}' ({asignatura.curso.nombre})."
        else:
            docente = get_object_or_404(User, id=docente_id)
            asignatura.docente = docente
            asignatura.save()
            doc_nombre = docente.get_full_name() or docente.username
            msg = f"Se asignó a {doc_nombre} para '{asignatura.nombre}' ({asignatura.curso.nombre})."

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': msg})

        messages.success(request, msg)

    return redirect('listar_asignaturas')


@login_required
def crear_asignatura_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No tienes permisos.")
        return redirect('dashboard_usuario')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para crear asignaturas.")
        return redirect('listar_asignaturas')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        cursos_ids = request.POST.getlist('cursos')
        docente_id = request.POST.get('docente')
        horas_semanales = request.POST.get('horas_semanales', '4').strip()

        if not nombre or not any(cursos_ids):
            messages.error(request, "El nombre de la asignatura y al menos un curso son requeridos.")
        else:
            docente = None
            if docente_id and docente_id != 'none':
                docente = get_object_or_404(User, id=docente_id)
            
            horas = int(horas_semanales) if horas_semanales.isdigit() else 4
            created_count = 0
            for curso_id in cursos_ids:
                curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)
                asig, created = Asignatura.objects.get_or_create(
                    colegio=colegio,
                    curso=curso,
                    nombre=nombre,
                    defaults={
                        'docente': docente,
                        'horas_semanales': horas,
                        'activo': True
                    }
                )
                if created:
                    created_count += 1
                elif not asig.activo:
                    asig.activo = True
                    asig.docente = docente
                    asig.horas_semanales = horas
                    asig.save()
                    created_count += 1
            
            if created_count > 0:
                messages.success(request, f"Asignatura '{nombre}' creada con éxito en {created_count} curso(s).")
            else:
                messages.info(request, f"La asignatura '{nombre}' ya existía en los cursos seleccionados.")
            return redirect('listar_asignaturas')

    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    profesores_miembros = MiembroColegio.objects.filter(colegio=colegio, activo=True).select_related('usuario', 'rol').order_by('usuario__first_name')
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
        horas_semanales = request.POST.get('horas_semanales', '4').strip()
        activo = request.POST.get('activo') == 'true'

        if not nombre or not curso_id:
            messages.error(request, "El nombre de la asignatura y el curso son requeridos.")
        else:
            curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)
            docente = None
            if docente_id and docente_id != 'none':
                docente = get_object_or_404(User, id=docente_id)
            
            asignatura.nombre = nombre
            asignatura.curso = curso
            asignatura.docente = docente
            asignatura.horas_semanales = int(horas_semanales) if horas_semanales.isdigit() else 4
            asignatura.activo = activo
            asignatura.save()
            
            messages.success(request, f"Asignatura '{nombre}' modificada con éxito.")
            return redirect('listar_asignaturas')

    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    profesores_miembros = MiembroColegio.objects.filter(colegio=colegio, activo=True).select_related('usuario', 'rol').order_by('usuario__first_name')
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
                asig, created = Asignatura.objects.get_or_create(
                    colegio=colegio,
                    curso=curso,
                    nombre=nombre_asig,
                    defaults={'docente': None, 'horas_semanales': 4, 'activo': True}
                )
                if created:
                    created_count += 1
                elif not asig.activo:
                    asig.activo = True
                    asig.save()
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

    profesores_miembros = MiembroColegio.objects.filter(colegio=colegio, activo=True).select_related('usuario', 'rol').order_by('usuario__first_name', 'usuario__username')
    profesores = [m.usuario for m in profesores_miembros]

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'cursos_con_secciones': cursos_page,
        'profesores': profesores,
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
        messages.error(request, "Acceso restringido. Se requieren permisos de Director o Administrador para gestionar el personal y los roles.")
        return redirect('dashboard_usuario')

    personal_qs = MiembroColegio.objects.filter(colegio=colegio).select_related('usuario', 'rol').prefetch_related('permisos_individuales').order_by('usuario__first_name')
    roles = RolColegio.objects.filter(colegio=colegio).prefetch_related('permisos__modulo').order_by('nombre')
    
    modulos_colegio = ColegioModulo.objects.filter(colegio=colegio, activo=True).select_related('modulo').order_by('modulo__nombre')
    
    # Cursos con sus asignaturas para el modal de asignación rápida
    cursos_db = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    cursos_con_asignaturas = []
    for c in cursos_db:
        asigs = Asignatura.objects.filter(curso=c, activo=True).select_related('docente').order_by('nombre')
        if asigs.exists():
            cursos_con_asignaturas.append({
                'curso': c,
                'asignaturas': asigs
            })

    # Matriz de permisos de roles serializada para JS interactivo
    roles_permisos_dict = {}
    for r in roles:
        r_perms = {}
        for rp in r.permisos.all():
            r_perms[str(rp.modulo.id)] = {
                'view': rp.puede_ver,
                'create': rp.puede_crear,
                'edit': rp.puede_editar,
                'delete': rp.puede_eliminar,
                'export': rp.puede_exportar,
            }
        roles_permisos_dict[str(r.id)] = {
            'nombre': r.nombre,
            'descripcion': r.descripcion,
            'es_base': r.es_base,
            'permisos': r_perms
        }

    # Matriz de permisos individuales por personal serializada para JS
    from colegios.models import MiembroPermiso
    personal_permisos_dict = {}
    asignaturas_por_docente_dict = {}
    
    for m in personal_qs:
        m_perms = {}
        for mp in m.permisos_individuales.all():
            m_perms[str(mp.modulo.id)] = {
                'view': mp.puede_ver,
                'create': mp.puede_crear,
                'edit': mp.puede_editar,
                'delete': mp.puede_eliminar,
                'export': mp.puede_exportar,
            }
        personal_permisos_dict[str(m.id)] = {
            'usuario': m.usuario.get_full_name() or m.usuario.username,
            'rol_id': m.rol.id if m.rol else None,
            'rol_nombre': m.rol.nombre if m.rol else 'Sin Rol',
            'permisos_individuales': m_perms
        }
        # Asignaturas asignadas a este usuario
        asignaturas_por_docente_dict[str(m.id)] = list(
            Asignatura.objects.filter(colegio=colegio, docente=m.usuario, activo=True).values_list('id', flat=True)
        )

    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    paginator = Paginator(personal_qs, 10)
    page_number = request.GET.get('page', 1)
    personal_page = paginator.get_page(page_number)

    context = {
        'colegio': colegio,
        'miembro': miembro_solicitante,
        'periodo': periodo,
        'personal': personal_page,
        'roles': roles,
        'modulos_colegio': modulos_colegio,
        'cursos_con_asignaturas': cursos_con_asignaturas,
        'roles_permisos_json': json.dumps(roles_permisos_dict),
        'personal_permisos_json': json.dumps(personal_permisos_dict),
        'asignaturas_por_docente_json': json.dumps(asignaturas_por_docente_dict),
        'total_personal': personal_qs.count(),
        'total_roles': roles.count(),
        'hoy': timezone.now(),
        'is_admin': is_admin
    }
    return render(request, 'colegios/listar_personal.html', context)


@login_required
def guardar_rol_permisos_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "Acceso denegado. Se requieren permisos de Administrador.")
        return redirect('listar_personal')

    if request.method == 'POST':
        rol_id = request.POST.get('rol_id', '').strip()
        nombre_rol = request.POST.get('nombre_rol', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        if not nombre_rol:
            messages.error(request, "El nombre del rol es obligatorio.")
            return redirect('listar_personal')

        from planes.models import Modulo

        if rol_id and rol_id.isdigit():
            rol = get_object_or_404(RolColegio, id=int(rol_id), colegio=colegio)
            rol.nombre = nombre_rol
            rol.descripcion = descripcion
            rol.save()
            mensaje = f"Rol '{nombre_rol}' y sus permisos actualizados correctamente."
        else:
            rol_existente = RolColegio.objects.filter(colegio=colegio, nombre__iexact=nombre_rol).first()
            if rol_existente:
                messages.warning(request, f"Ya existe un rol con el nombre '{nombre_rol}'.")
                return redirect('listar_personal')

            rol = RolColegio.objects.create(
                colegio=colegio,
                nombre=nombre_rol,
                descripcion=descripcion,
                es_base=False,
                activo=True
            )
            mensaje = f"¡Nuevo rol '{nombre_rol}' creado exitosamente con sus permisos configurados!"

        # Procesar permisos para cada módulo activo del colegio
        modulos_colegio = ColegioModulo.objects.filter(colegio=colegio, activo=True).select_related('modulo')
        for mc in modulos_colegio:
            mod_id = mc.modulo.id
            puede_ver = request.POST.get(f'perm_view_{mod_id}') == 'on'
            puede_crear = request.POST.get(f'perm_create_{mod_id}') == 'on'
            puede_editar = request.POST.get(f'perm_edit_{mod_id}') == 'on'
            puede_eliminar = request.POST.get(f'perm_delete_{mod_id}') == 'on'
            puede_exportar = request.POST.get(f'perm_export_{mod_id}') == 'on'

            rp, _ = RolPermiso.objects.get_or_create(rol=rol, modulo=mc.modulo)
            rp.puede_ver = puede_ver
            rp.puede_crear = puede_crear
            rp.puede_editar = puede_editar
            rp.puede_eliminar = puede_eliminar
            rp.puede_exportar = puede_exportar
            rp.save()

        messages.success(request, mensaje)

    return redirect('listar_personal')


@login_required
def eliminar_rol_personalizado_view(request, rol_id):
    colegio = obtener_colegio_usuario(request.user)
    rol = get_object_or_404(RolColegio, id=rol_id, colegio=colegio)

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "No tienes permisos para eliminar roles.")
        return redirect('listar_personal')

    if rol.nombre in ['Administrador', 'Director', 'Profesor']:
        messages.error(request, f"El rol '{rol.nombre}' es un rol del sistema y no puede ser eliminado.")
        return redirect('listar_personal')

    # Verificar si hay miembros asignados a este rol
    if MiembroColegio.objects.filter(colegio=colegio, rol=rol, activo=True).exists():
        messages.error(request, f"No puedes eliminar el rol '{rol.nombre}' porque actualmente tiene funcionarios asignados. Reasigna su rol antes de continuar.")
        return redirect('listar_personal')

    nombre = rol.nombre
    rol.delete()
    messages.success(request, f"El rol '{nombre}' ha sido eliminado exitosamente.")
    return redirect('listar_personal')


@login_required
def guardar_permisos_individuales_personal_view(request, miembro_id):
    colegio = obtener_colegio_usuario(request.user)
    miembro = get_object_or_404(MiembroColegio, id=miembro_id, colegio=colegio)

    miembro_solicitante = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = request.user.colegios_administrados.filter(id=colegio.id).exists() or (miembro_solicitante and miembro_solicitante.rol and miembro_solicitante.rol.nombre in ['Administrador', 'Director'])
    if not is_admin:
        messages.error(request, "Acceso denegado. Se requieren permisos de Administrador.")
        return redirect('listar_personal')

    if request.method == 'POST':
        from colegios.models import MiembroPermiso

        limpiar_individuales = request.POST.get('limpiar_individuales') == 'true'
        if limpiar_individuales:
            MiembroPermiso.objects.filter(miembro=miembro).delete()
            messages.success(request, f"Se restauraron los permisos individuales de {miembro.usuario.username} a los valores predeterminados de su rol.")
            return redirect('listar_personal')

        modulos_colegio = ColegioModulo.objects.filter(colegio=colegio, activo=True).select_related('modulo')
        for mc in modulos_colegio:
            mod_id = mc.modulo.id
            tiene_override = request.POST.get(f'override_{mod_id}') == 'on'
            
            if tiene_override:
                puede_ver = request.POST.get(f'ind_view_{mod_id}') == 'on'
                puede_crear = request.POST.get(f'ind_create_{mod_id}') == 'on'
                puede_editar = request.POST.get(f'ind_edit_{mod_id}') == 'on'
                puede_eliminar = request.POST.get(f'ind_delete_{mod_id}') == 'on'
                puede_exportar = request.POST.get(f'ind_export_{mod_id}') == 'on'

                mp, _ = MiembroPermiso.objects.get_or_create(miembro=miembro, modulo=mc.modulo)
                mp.puede_ver = puede_ver
                mp.puede_crear = puede_crear
                mp.puede_editar = puede_editar
                mp.puede_eliminar = puede_eliminar
                mp.puede_exportar = puede_exportar
                mp.save()
            else:
                # Si no tiene override marcado, eliminar el registro para que herede del rol base
                MiembroPermiso.objects.filter(miembro=miembro, modulo=mc.modulo).delete()

        doc_nombre = miembro.usuario.get_full_name() or miembro.usuario.username
        messages.success(request, f"Permisos individuales de {doc_nombre} guardados exitosamente.")

    return redirect('listar_personal')


@login_required
def crear_rol_personalizado_view(request):
    return guardar_rol_permisos_view(request)




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
        'total_monitoreados': len(estudiantes_data),
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


    total_clases = EventoAgenda.objects.filter(colegio=colegio, tipo='clase').count()
    total_evaluaciones = EventoAgenda.objects.filter(colegio=colegio, tipo='evaluacion', fecha_inicio__gte=hoy_date).count()
    total_reuniones = EventoAgenda.objects.filter(colegio=colegio, tipo='reunion', fecha_inicio__gte=hoy_date).count()
    total_actividades = EventoAgenda.objects.filter(colegio=colegio, tipo='actividad', fecha_inicio__gte=hoy_date).count()

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
        'total_clases': total_clases,
        'total_evaluaciones': total_evaluaciones,
        'total_reuniones': total_reuniones,
        'total_actividades': total_actividades,
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


@require_POST
def actualizar_modulo_colegio(request):
    try:
        data = json.loads(request.body)
        colegio_id = data.get('colegio_id')
        modulo = data.get('modulo')
        estado = data.get('estado')

        if colegio_id:
            colegio = Colegio.objects.get(id=colegio_id)
            config, created = ConfiguracionModulos.objects.get_or_create(colegio=colegio)
            if hasattr(config, modulo):
                setattr(config, modulo, estado)
                config.save()
        else:
            from planes.models import Modulo as ModuloModel
            mod_obj = ModuloModel.objects.filter(nombre__icontains=modulo.replace('_', ' ')).first()
            if mod_obj:
                mod_obj.activo = estado
                mod_obj.save()

        return JsonResponse({'status': 'ok', 'message': f'Módulo {modulo} actualizado'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def ver_detalle_colegio(request, pk):
    colegio = get_object_or_404(Colegio, pk=pk)
    suscripcion = getattr(colegio, 'suscripcion', None)
    config_modulos, _ = ConfiguracionModulos.objects.get_or_create(colegio=colegio)
    context = {
        'colegio': colegio,
        'suscripcion': suscripcion,
        'config_modulos': config_modulos,
    }
    return render(request, 'colegios/detalle_colegio.html', context)


@login_required
def editar_colegio(request, pk):
    colegio = get_object_or_404(Colegio, pk=pk)

    if request.method == 'POST':
        colegio.nombre = request.POST.get('nombre', colegio.nombre).strip()
        colegio.nombre_corto = request.POST.get('nombre_corto', colegio.nombre_corto)
        colegio.correo_institucional = request.POST.get('correo_institucional', colegio.correo_institucional).strip()
        colegio.telefono = request.POST.get('telefono', colegio.telefono).strip()
        colegio.direccion = request.POST.get('direccion', colegio.direccion)
        colegio.ciudad_comuna = request.POST.get('ciudad_comuna', colegio.ciudad_comuna).strip()
        colegio.tipo_institucion = request.POST.get('tipo_institucion', colegio.tipo_institucion)
        colegio.cantidad_alumnos = request.POST.get('cantidad_alumnos', colegio.cantidad_alumnos)
        colegio.estado = request.POST.get('estado', colegio.estado)

        if 'logo' in request.FILES:
            colegio.logo = request.FILES['logo']

        colegio.save()
        messages.success(request, f"Datos de {colegio.nombre} actualizados con éxito.")
        return redirect('dashboard_superadmin_colegios')

    return render(request, 'colegios/editar_colegio.html', {'colegio': colegio})


@login_required
def editar_suscripcion_colegio(request, colegio_id):
    from planes.models import Plan
    colegio = get_object_or_404(Colegio, id=colegio_id)
    suscripcion = getattr(colegio, 'suscripcion', None)
    planes = Plan.objects.filter(activo=True)

    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        tipo_facturacion = request.POST.get('tipo_facturacion', 'mensual')
        estado = request.POST.get('estado', 'activa')

        if plan_id:
            plan_obj = get_object_or_404(Plan, id=plan_id)
            monto = plan_obj.precio_anual if tipo_facturacion == 'anual' else plan_obj.precio_mensual

            Suscripcion.objects.update_or_create(
                colegio=colegio,
                defaults={
                    'plan': plan_obj,
                    'tipo_facturacion': tipo_facturacion,
                    'monto': monto,
                    'estado': estado,
                }
            )
            messages.success(request, f"Plan y suscripción de {colegio.nombre} actualizados con éxito.")
            return redirect('ver_detalle_colegio', pk=colegio.id)
        else:
            messages.error(request, "Debe seleccionar un plan de suscripción.")

    context = {
        'colegio': colegio,
        'suscripcion': suscripcion,
        'planes': planes,
    }
    return render(request, 'colegios/editar_suscripcion.html', context)


@login_required
def asignar_profesor_jefe_view(request, seccion_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "No tienes un colegio asociado.")
        return redirect('dashboard_usuario')

    seccion = get_object_or_404(SeccionCurso, id=seccion_id, curso__colegio=colegio)
    if request.method == 'POST':
        profesor_jefe_id = request.POST.get('profesor_jefe_id')
        if profesor_jefe_id and profesor_jefe_id != 'none':
            docente_obj = User.objects.filter(id=profesor_jefe_id).first()
            seccion.profesor_jefe = docente_obj
            seccion.save()
            nombre_doc = docente_obj.get_full_name() or docente_obj.username
            messages.success(request, f"¡{nombre_doc} asignado/a como Profesor(a) Jefe de {seccion.curso.nombre} - {seccion.nombre}!")
        else:
            seccion.profesor_jefe = None
            seccion.save()
            messages.info(request, f"Se ha desasignado la jefatura de {seccion.curso.nombre} - {seccion.nombre}.")
    return redirect('listar_cursos')


@login_required
def mis_cursos_docente_view(request):
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

    # 1. Jefaturas de curso donde es Profesor Jefe
    jefaturas = SeccionCurso.objects.filter(
        curso__colegio=colegio,
        profesor_jefe=request.user,
        activo=True
    ).select_related('curso').prefetch_related('estudiantes', 'curso__asignaturas')

    jefaturas_data = []
    for sec in jefaturas:
        alumnos_count = sec.estudiantes.filter(activo=True).count()
        asig_count = sec.curso.asignaturas.filter(activo=True).count()
        jefaturas_data.append({
            'seccion': sec,
            'alumnos_count': alumnos_count,
            'asignaturas_count': asig_count
        })

    # 2. Asignaturas dictadas por el docente
    asignaturas_dictadas = Asignatura.objects.filter(
        colegio=colegio,
        docente=request.user,
        activo=True
    ).select_related('curso').prefetch_related('curso__secciones')

    asignaturas_data = []
    for asig in asignaturas_dictadas:
        secciones_asig = asig.curso.secciones.filter(activo=True)
        total_alumnos = Estudiante.objects.filter(seccion__in=secciones_asig, activo=True).count()
        asignaturas_data.append({
            'asignatura': asig,
            'secciones': secciones_asig,
            'total_alumnos': total_alumnos,
        })

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'mis_cursos',
        'jefaturas': jefaturas_data,
        'jefaturas_count': len(jefaturas_data),
        'asignaturas': asignaturas_data,
        'asignaturas_count': len(asignaturas_data),
        'hoy': timezone.now(),
    }
    return render(request, 'colegios/mis_cursos.html', context)


@login_required
def estadisticas_colegio_view(request):
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

    if not is_admin:
        messages.error(request, "El módulo de estadísticas institucionales está reservado para el Equipo Directivo y Administradores.")
        return redirect('dashboard_usuario')

    hoy = timezone.now().date()
    estudiantes_qs = Estudiante.objects.filter(colegio=colegio, activo=True).select_related('seccion', 'seccion__curso')
    total_estudiantes = estudiantes_qs.count()

    # 1. GÉNERO
    hombres_count = estudiantes_qs.filter(genero='masculino').count()
    mujeres_count = estudiantes_qs.filter(genero='femenino').count()
    otros_count = estudiantes_qs.filter(genero='otro').count()
    no_informa_count = total_estudiantes - (hombres_count + mujeres_count + otros_count)

    pct_hombres = round((hombres_count / total_estudiantes * 100), 1) if total_estudiantes else 0
    pct_mujeres = round((mujeres_count / total_estudiantes * 100), 1) if total_estudiantes else 0
    pct_otros = round(((otros_count + no_informa_count) / total_estudiantes * 100), 1) if total_estudiantes else 0

    # 2. RANGOS ETARIOS (EDADES)
    edad_menor_6 = 0
    edad_6_9 = 0
    edad_10_13 = 0
    edad_14_17 = 0
    edad_18_mas = 0
    edades_lista = []

    for est in estudiantes_qs:
        if est.fecha_nacimiento:
            fn = est.fecha_nacimiento
            age = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            edades_lista.append(age)
            if age < 6:
                edad_menor_6 += 1
            elif 6 <= age <= 9:
                edad_6_9 += 1
            elif 10 <= age <= 13:
                edad_10_13 += 1
            elif 14 <= age <= 17:
                edad_14_17 += 1
            else:
                edad_18_mas += 1
        else:
            # Estimación por nivel
            edad_10_13 += 1
            edades_lista.append(12)

    edad_promedio = round(sum(edades_lista) / len(edades_lista), 1) if edades_lista else 0

    # 3. PROGRAMA PIE & INCLUSIÓN
    pie_count = estudiantes_qs.filter(es_pie=True).count()
    regular_count = total_estudiantes - pie_count
    pie_neep = estudiantes_qs.filter(es_pie=True, tipo_pie='neep').count()
    pie_neet = estudiantes_qs.filter(es_pie=True, tipo_pie='neet').count()
    pie_otros = pie_count - (pie_neep + pie_neet)
    pct_pie = round((pie_count / total_estudiantes * 100), 1) if total_estudiantes else 0

    # 4. CALIFICACIONES & RANGOS DE NOTAS
    from calificaciones.models import Nota, Evaluacion
    notas_qs = Nota.objects.filter(evaluacion__colegio=colegio)
    total_notas = notas_qs.count()

    notas_sobresaliente = notas_qs.filter(valor__gte=6.0).count() # 6.0 - 7.0
    notas_bueno = notas_qs.filter(valor__gte=5.0, valor__lt=6.0).count() # 5.0 - 5.9
    notas_suficiente = notas_qs.filter(valor__gte=4.0, valor__lt=5.0).count() # 4.0 - 4.9
    notas_insuficiente = notas_qs.filter(valor__lt=4.0).count() # < 4.0

    from django.db.models import Avg
    promedio_global_val = notas_qs.aggregate(Avg('valor'))['valor__avg']
    promedio_global = round(float(promedio_global_val), 1) if promedio_global_val else 0.0

    aprobadas = notas_sobresaliente + notas_bueno + notas_suficiente
    tasa_aprobacion_global = round((aprobadas / total_notas * 100), 1) if total_notas else 0

    # Promedio por Nivel
    cursos_qs = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nivel', 'nombre')
    rendimiento_cursos = []
    for c in cursos_qs:
        n_curso = Nota.objects.filter(evaluacion__colegio=colegio, evaluacion__seccion__curso=c)
        avg_c = n_curso.aggregate(Avg('valor'))['valor__avg']
        rendimiento_cursos.append({
            'nombre': c.nombre,
            'nivel': c.get_nivel_display(),
            'promedio': round(float(avg_c), 1) if avg_c else '-',
            'total_notas': n_curso.count(),
            'aprobadas_pct': round((n_curso.filter(valor__gte=4.0).count() / n_curso.count() * 100), 1) if n_curso.exists() else 0
        })

    # 5. ASISTENCIA INSTITUCIONAL
    from asistencia.models import DetalleAsistencia
    detalles_asistencia_qs = DetalleAsistencia.objects.filter(registro__seccion__curso__colegio=colegio)
    total_asistencias = detalles_asistencia_qs.count()

    presentes = detalles_asistencia_qs.filter(estado='presente').count()
    ausentes = detalles_asistencia_qs.filter(estado='ausente').count()
    atrasados = detalles_asistencia_qs.filter(estado='tarde').count()
    justificados = detalles_asistencia_qs.filter(estado='justificado').count()

    asistencia_positiva = presentes + atrasados + justificados
    pct_asistencia_global = round((asistencia_positiva / total_asistencias * 100), 1) if total_asistencias else 0

    # 6. CONVIVENCIA ESCOLAR
    from colegios.models import AnotacionEstudiante
    anotaciones_qs = AnotacionEstudiante.objects.filter(estudiante__colegio=colegio)
    total_anotaciones = anotaciones_qs.count()

    anotaciones_pos = anotaciones_qs.filter(tipo='positiva').count()
    anotaciones_neg = anotaciones_qs.filter(tipo='negativa').count()
    anotaciones_dest = anotaciones_qs.filter(tipo='destacada').count()

    # 7. DISTRIBUCIÓN POR NIVELES
    dist_niveles = {}
    for est in estudiantes_qs:
        if est.seccion and est.seccion.curso:
            niv = est.seccion.curso.get_nivel_display()
            dist_niveles[niv] = dist_niveles.get(niv, 0) + 1

    niveles_labels = list(dist_niveles.keys())
    niveles_counts = list(dist_niveles.values())

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'estadisticas',
        'hoy': timezone.now(),
        # Totales
        'total_estudiantes': total_estudiantes,
        'total_notas': total_notas,
        'total_asistencias': total_asistencias,
        'total_anotaciones': total_anotaciones,
        'promedio_global': promedio_global,
        'tasa_aprobacion_global': tasa_aprobacion_global,
        'pct_asistencia_global': pct_asistencia_global,
        'edad_promedio': edad_promedio,
        # Género
        'hombres_count': hombres_count,
        'mujeres_count': mujeres_count,
        'otros_count': otros_count + no_informa_count,
        'pct_hombres': pct_hombres,
        'pct_mujeres': pct_mujeres,
        'pct_otros': pct_otros,
        # Rangos Etarios
        'edad_menor_6': edad_menor_6,
        'edad_6_9': edad_6_9,
        'edad_10_13': edad_10_13,
        'edad_14_17': edad_14_17,
        'edad_18_mas': edad_18_mas,
        # Notas
        'notas_sobresaliente': notas_sobresaliente,
        'notas_bueno': notas_bueno,
        'notas_suficiente': notas_suficiente,
        'notas_insuficiente': notas_insuficiente,
        'rendimiento_cursos': rendimiento_cursos,
        # PIE
        'pie_count': pie_count,
        'regular_count': regular_count,
        'pie_neep': pie_neep,
        'pie_neet': pie_neet,
        'pie_otros': pie_otros,
        'pct_pie': pct_pie,
        # Asistencia
        'presentes': presentes,
        'ausentes': ausentes,
        'atrasados': atrasados,
        'justificados': justificados,
        # Convivencia
        'anotaciones_pos': anotaciones_pos,
        'anotaciones_neg': anotaciones_neg,
        'anotaciones_dest': anotaciones_dest,
        # Niveles
        'niveles_labels': niveles_labels,
        'niveles_counts': niveles_counts,
    }
    return render(request, 'colegios/estadisticas.html', context)


@login_required
def exportar_estadisticas_excel_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "Colegio no encontrado.")
        return redirect('dashboard_usuario')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    if not is_admin:
        messages.error(request, "Acceso no autorizado.")
        return redirect('dashboard_usuario')

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.remove(wb.active) # Quitar hoja por defecto

    # Estilos Globales
    header_fill = PatternFill(start_color="7C5CFC", end_color="7C5CFC", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    sub_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # -------------------------------------------------------------
    # HOJA 1: RESUMEN EJECUTIVO
    # -------------------------------------------------------------
    ws1 = wb.create_sheet(title="Resumen Ejecutivo")
    ws1.views.sheetView[0].showGridLines = True

    ws1['A1'] = f"EDUTEKA - INFORME ESTADÍSTICO INSTITUCIONAL"
    ws1['A1'].font = title_font
    ws1['A2'] = f"Establecimiento: {colegio.nombre} | Fecha de Emisión: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
    ws1['A2'].font = sub_font

    kpis = [
        ("Métrica Institucional", "Valor Global", "Descripción / Estado"),
        ("Matrícula Total Activa", Estudiante.objects.filter(colegio=colegio, activo=True).count(), "Estudiantes matriculados"),
        ("Alumnos Programa PIE", Estudiante.objects.filter(colegio=colegio, activo=True, es_pie=True).count(), "Necesidades Educativas Especiales"),
        ("Cursos Habilitados", CursoColegio.objects.filter(colegio=colegio, activo=True).count(), "Niveles en funcionamiento"),
        ("Secciones Habilitadas", SeccionCurso.objects.filter(curso__colegio=colegio, activo=True).count(), "Aulas activas"),
        ("Asignaturas en Malla", Asignatura.objects.filter(colegio=colegio, activo=True).count(), "Cátedras impartidas"),
        ("Personal y Funcionarios", MiembroColegio.objects.filter(colegio=colegio, activo=True).count(), "Docentes y administrativos"),
    ]

    from calificaciones.models import Nota
    notas_qs = Nota.objects.filter(evaluacion__colegio=colegio)
    from django.db.models import Avg
    avg_n = notas_qs.aggregate(Avg('valor'))['valor__avg']
    prom_gral = round(float(avg_n), 1) if avg_n else 0.0
    kpis.append(("Promedio General de Notas", prom_gral, "Escala 1.0 a 7.0"))
    
    tasa_aprob = round((notas_qs.filter(valor__gte=4.0).count() / notas_qs.count() * 100), 1) if notas_qs.exists() else 0
    kpis.append(("Tasa Global de Aprobación", f"{tasa_aprob}%", "Calificaciones >= 4.0"))

    from asistencia.models import DetalleAsistencia
    detalles_asist = DetalleAsistencia.objects.filter(registro__seccion__curso__colegio=colegio)
    pct_asist = round((detalles_asist.filter(estado__in=['presente', 'tarde', 'justificado']).count() / detalles_asist.count() * 100), 1) if detalles_asist.exists() else 0
    kpis.append(("Asistencia Global del Colegio", f"{pct_asist}%", "Presentismo escolar"))

    for row_idx, row_data in enumerate(kpis, start=4):
        for col_idx, cell_value in enumerate(row_data, start=1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=cell_value)
            cell.border = thin_border
            if row_idx == 4:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center")
            else:
                cell.font = bold_font if col_idx == 1 else regular_font
                cell.alignment = Alignment(horizontal="center" if col_idx == 2 else "left", vertical="center")

    # -------------------------------------------------------------
    # HOJA 2: DEMOGRAFÍA & ESTUDIANTES
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Demografía y Alumnos")
    ws2.views.sheetView[0].showGridLines = True

    ws2['A1'] = "NÓMINA Y DEMOGRAFÍA DE ESTUDIANTES"
    ws2['A1'].font = title_font
    ws2['A2'] = f"Colegio: {colegio.nombre}"
    ws2['A2'].font = sub_font

    headers_demo = ["#", "Estudiante", "RUT", "Curso", "Sección", "Género", "Fecha Nac.", "Edad Aprox.", "PIE", "Tipo NEE"]
    for col_idx, h in enumerate(headers_demo, start=1):
        cell = ws2.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    hoy = timezone.now().date()
    estudiantes_list = Estudiante.objects.filter(colegio=colegio, activo=True).select_related('seccion', 'seccion__curso').order_by('seccion__curso__nombre', 'nombre_completo')
    
    for row_idx, est in enumerate(estudiantes_list, start=5):
        age_str = "-"
        if est.fecha_nacimiento:
            fn = est.fecha_nacimiento
            age_str = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))

        row_data = [
            row_idx - 4,
            est.nombre_completo,
            est.rut or "-",
            est.seccion.curso.nombre if est.seccion and est.seccion.curso else "-",
            est.seccion.nombre if est.seccion else "-",
            est.get_genero_display() if est.genero else "No Informa",
            est.fecha_nacimiento.strftime('%d/%m/%Y') if est.fecha_nacimiento else "-",
            age_str,
            "SÍ" if est.es_pie else "NO",
            est.get_tipo_pie_display() if est.es_pie and est.tipo_pie else "-"
        ]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx not in [2] else "left", vertical="center")

    # -------------------------------------------------------------
    # HOJA 3: RENDIMIENTO Y CALIFICACIONES
    # -------------------------------------------------------------
    ws3 = wb.create_sheet(title="Rendimiento Académico")
    ws3.views.sheetView[0].showGridLines = True

    ws3['A1'] = "ESTADÍSTICAS DE RENDIMIENTO ACADÉMICO"
    ws3['A1'].font = title_font
    ws3['A2'] = f"Colegio: {colegio.nombre}"
    ws3['A2'].font = sub_font

    headers_acad = ["Curso / Nivel", "Total Notas", "Sobresaliente (6.0-7.0)", "Bueno (5.0-5.9)", "Suficiente (4.0-4.9)", "Insuficiente (<4.0)", "Promedio", "% Aprobación"]
    for col_idx, h in enumerate(headers_acad, start=1):
        cell = ws3.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    cursos_all = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nivel', 'nombre')
    for row_idx, c in enumerate(cursos_all, start=5):
        n_c = Nota.objects.filter(evaluacion__colegio=colegio, evaluacion__seccion__curso=c)
        tot_c = n_c.count()
        sobr_c = n_c.filter(valor__gte=6.0).count()
        buen_c = n_c.filter(valor__gte=5.0, valor__lt=6.0).count()
        suf_c = n_c.filter(valor__gte=4.0, valor__lt=5.0).count()
        insuf_c = n_c.filter(valor__lt=4.0).count()
        avg_c = n_c.aggregate(Avg('valor'))['valor__avg']
        prom_c_str = round(float(avg_c), 1) if avg_c else "-"
        pct_aprob_c = f"{round((tot_c - insuf_c) / tot_c * 100, 1)}%" if tot_c > 0 else "-"

        row_data = [c.nombre, tot_c, sobr_c, buen_c, suf_c, insuf_c, prom_c_str, pct_aprob_c]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws3.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx > 1 else "left", vertical="center")

    # Autoajuste de ancho de columnas en todas las hojas
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    if len(val_str) > max_len and len(val_str) < 50:
                        max_len = len(val_str)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    import io
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"estadisticas_{colegio.nombre.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ==============================================================================
# LÓGICA Y VISTAS DEL MÓDULO DE FINANZAS, CAJA CHICA Y FACTURAS
# ==============================================================================

def inicializar_datos_finanzas(colegio):
    from .models import CuentaFinanciera, CategoriaFinanciera
    if not CuentaFinanciera.objects.filter(colegio=colegio).exists():
        CuentaFinanciera.objects.create(
            colegio=colegio,
            nombre="Caja Chica Dirección / General",
            tipo="caja_chica",
            saldo_inicial=150000.0,
            saldo_actual=150000.0
        )
        CuentaFinanciera.objects.create(
            colegio=colegio,
            nombre="Cuenta Corriente Institucional",
            tipo="cuenta_bancaria",
            banco="Banco Santander",
            numero_cuenta="0-000-00-12345-6",
            saldo_inicial=0.0,
            saldo_actual=0.0
        )

    categorias_base = [
        ("Subvención Escolar / Mineduc", "ingreso", "bi-bank", "#10B981"),
        ("Matrículas y Colegiaturas", "ingreso", "bi-cash-coin", "#3B82F6"),
        ("Aportes Centro de Padres", "ingreso", "bi-people-fill", "#8B5CF6"),
        ("Otros Ingresos", "ingreso", "bi-plus-circle", "#64748B"),
        ("Material Didáctico e Insumos", "egreso", "bi-pencil-square", "#F59E0B"),
        ("Servicios Básicos (Luz / Agua / Internet)", "egreso", "bi-lightning-charge", "#EF4444"),
        ("Mantención e Infraestructura", "egreso", "bi-tools", "#6366F1"),
        ("Sueldos y Honorarios", "egreso", "bi-person-badge", "#EC4899"),
        ("Caja Chica Gastos Menores", "egreso", "bi-wallet2", "#06B6D4"),
        ("Eventos y Actividades Extraescolares", "egreso", "bi-trophy", "#10B981"),
    ]

    for nombre, tipo, icono, color in categorias_base:
        CategoriaFinanciera.objects.get_or_create(
            colegio=colegio,
            nombre=nombre,
            tipo=tipo,
            defaults={'icono': icono, 'color': color, 'activo': True}
        )


@login_required
def finanzas_dashboard_view(request):
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

    # Inicializar cuentas y categorías si es primera vez
    inicializar_datos_finanzas(colegio)

    from .models import CuentaFinanciera, CategoriaFinanciera, MovimientoFinanciero, FacturaGasto
    from django.db.models import Sum, Q

    # Cuentas activas
    cuentas = CuentaFinanciera.objects.filter(colegio=colegio, activo=True).order_by('tipo', 'nombre')
    categorias_ingreso = CategoriaFinanciera.objects.filter(colegio=colegio, tipo='ingreso', activo=True).order_by('nombre')
    categorias_egreso = CategoriaFinanciera.objects.filter(colegio=colegio, tipo='egreso', activo=True).order_by('nombre')
    todas_categorias = CategoriaFinanciera.objects.filter(colegio=colegio, activo=True).order_by('tipo', 'nombre')

    # Filtros
    cuenta_filtro = request.GET.get('cuenta')
    tipo_filtro = request.GET.get('tipo')
    categoria_filtro = request.GET.get('categoria')
    busqueda = request.GET.get('q', '').strip()
    tab_activa = request.GET.get('tab', 'movimientos')

    movimientos_qs = MovimientoFinanciero.objects.filter(colegio=colegio).select_related('cuenta', 'categoria', 'registrado_por').order_by('-fecha', '-id')

    if cuenta_filtro and cuenta_filtro.isdigit():
        movimientos_qs = movimientos_qs.filter(cuenta_id=int(cuenta_filtro))
    if tipo_filtro in ['ingreso', 'egreso']:
        movimientos_qs = movimientos_qs.filter(tipo=tipo_filtro)
    if categoria_filtro and categoria_filtro.isdigit():
        movimientos_qs = movimientos_qs.filter(categoria_id=int(categoria_filtro))
    if busqueda:
        movimientos_qs = movimientos_qs.filter(
            Q(concepto__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(numero_comprobante__icontains=busqueda)
        )

    # Facturas
    facturas_qs = FacturaGasto.objects.filter(colegio=colegio).select_related('movimiento_asociado', 'registrado_por').order_by('-fecha_emision', '-id')

    from decimal import Decimal

    # KPIs Financieros Globales
    saldo_total_disponible = Decimal(cuentas.aggregate(Sum('saldo_actual'))['saldo_actual__sum'] or 0)
    saldo_caja_chica = Decimal(cuentas.filter(tipo='caja_chica').aggregate(Sum('saldo_actual'))['saldo_actual__sum'] or 0)
    saldo_bancos = Decimal(cuentas.filter(tipo='cuenta_bancaria').aggregate(Sum('saldo_actual'))['saldo_actual__sum'] or 0)

    hoy = timezone.now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year

    ingresos_mes = Decimal(MovimientoFinanciero.objects.filter(
        colegio=colegio, tipo='ingreso', estado='completado', fecha__year=anio_actual, fecha__month=mes_actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0)

    egresos_mes = Decimal(MovimientoFinanciero.objects.filter(
        colegio=colegio, tipo='egreso', estado='completado', fecha__year=anio_actual, fecha__month=mes_actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0)

    balance_mes = ingresos_mes - egresos_mes

    facturas_pendientes_monto = Decimal(facturas_qs.filter(estado_pago='pendiente').aggregate(Sum('monto_total'))['monto_total__sum'] or 0)
    facturas_pendientes_count = facturas_qs.filter(estado_pago='pendiente').count()

    # Datos para Gráfico de Flujo de Caja (Últimos 6 meses)
    import calendar
    flujo_labels = []
    flujo_ingresos = []
    flujo_egresos = []

    for i in range(5, -1, -1):
        m = mes_actual - i
        y = anio_actual
        if m <= 0:
            m += 12
            y -= 1
        nombre_mes = calendar.month_abbr[m].capitalize()
        flujo_labels.append(f"{nombre_mes} {y}")

        ing_m = MovimientoFinanciero.objects.filter(
            colegio=colegio, tipo='ingreso', estado='completado', fecha__year=y, fecha__month=m
        ).aggregate(Sum('monto'))['monto__sum'] or Decimal('0')
        egr_m = MovimientoFinanciero.objects.filter(
            colegio=colegio, tipo='egreso', estado='completado', fecha__year=y, fecha__month=m
        ).aggregate(Sum('monto'))['monto__sum'] or Decimal('0')

        flujo_ingresos.append(float(ing_m))
        flujo_egresos.append(float(egr_m))


    # Datos para Gráfico de Gastos por Categoría
    gastos_por_cat = MovimientoFinanciero.objects.filter(
        colegio=colegio, tipo='egreso', estado='completado', fecha__year=anio_actual
    ).values('categoria__nombre').annotate(total=Sum('monto')).order_by('-total')

    cat_labels = [item['categoria__nombre'] or 'Sin Categoría' for item in gastos_por_cat[:6]]
    cat_valores = [float(item['total']) for item in gastos_por_cat[:6]]

    # Paginación de movimientos
    paginator = Paginator(movimientos_qs, 15)
    page_number = request.GET.get('page', 1)
    movimientos_page = paginator.get_page(page_number)

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'finanzas',
        'hoy': timezone.now(),
        # Cuentas & Categorías
        'cuentas': cuentas,
        'categorias_ingreso': categorias_ingreso,
        'categorias_egreso': categorias_egreso,
        'todas_categorias': todas_categorias,
        # Listados
        'movimientos': movimientos_page,
        'facturas': facturas_qs[:30],
        'tab_activa': tab_activa,
        # Filtros seleccionados
        'cuenta_filtro': int(cuenta_filtro) if cuenta_filtro and cuenta_filtro.isdigit() else None,
        'tipo_filtro': tipo_filtro,
        'categoria_filtro': int(categoria_filtro) if categoria_filtro and categoria_filtro.isdigit() else None,
        'busqueda': busqueda,
        # KPIs
        'saldo_total_disponible': saldo_total_disponible,
        'saldo_caja_chica': saldo_caja_chica,
        'saldo_bancos': saldo_bancos,
        'ingresos_mes': ingresos_mes,
        'egresos_mes': egresos_mes,
        'balance_mes': balance_mes,
        'facturas_pendientes_monto': facturas_pendientes_monto,
        'facturas_pendientes_count': facturas_pendientes_count,
        # Gráficos
        'flujo_labels': flujo_labels,
        'flujo_ingresos': flujo_ingresos,
        'flujo_egresos': flujo_egresos,
        'cat_labels': cat_labels,
        'cat_valores': cat_valores,
    }
    return render(request, 'colegios/finanzas_dashboard.html', context)


@login_required
def crear_movimiento_financiero_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        messages.error(request, "Colegio no encontrado.")
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import CuentaFinanciera, CategoriaFinanciera, MovimientoFinanciero
        from decimal import Decimal

        tipo = request.POST.get('tipo', 'egreso')
        cuenta_id = request.POST.get('cuenta_id')
        categoria_id = request.POST.get('categoria_id')
        monto_str = request.POST.get('monto', '0').replace('.', '').replace(',', '.').replace('$', '').strip()
        concepto = request.POST.get('concepto', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        fecha_str = request.POST.get('fecha')
        metodo_pago = request.POST.get('metodo_pago', 'efectivo')
        numero_comprobante = request.POST.get('numero_comprobante', '').strip()
        comprobante_file = request.FILES.get('comprobante_adjunto')

        cuenta = get_object_or_404(CuentaFinanciera, id=cuenta_id, colegio=colegio)
        categoria = CategoriaFinanciera.objects.filter(id=categoria_id, colegio=colegio).first() if categoria_id else None

        try:
            monto = Decimal(monto_str)
        except Exception:
            messages.error(request, "El monto ingresado no es válido.")
            return redirect('finanzas_dashboard')

        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()
        except ValueError:
            fecha_obj = timezone.now().date()

        movimiento = MovimientoFinanciero.objects.create(
            colegio=colegio,
            cuenta=cuenta,
            categoria=categoria,
            tipo=tipo,
            monto=monto,
            concepto=concepto if concepto else f"Movimiento de {tipo.capitalize()}",
            descripcion=descripcion,
            fecha=fecha_obj,
            metodo_pago=metodo_pago,
            numero_comprobante=numero_comprobante,
            comprobante_adjunto=comprobante_file,
            registrado_por=request.user,
            estado='completado'
        )

        # Actualizar saldo de la cuenta
        if tipo == 'ingreso':
            cuenta.saldo_actual += monto
        else:
            cuenta.saldo_actual -= monto
        cuenta.save()

        signo_msg = 'Ingreso registrado (+${:,.0f})' if tipo == 'ingreso' else 'Egreso registrado (-${:,.0f})'
        messages.success(request, f"¡{signo_msg.format(monto)} en {cuenta.nombre}!")

    return redirect('finanzas_dashboard')


@login_required
def eliminar_movimiento_financiero_view(request, movimiento_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import MovimientoFinanciero
    mov = get_object_or_404(MovimientoFinanciero, id=movimiento_id, colegio=colegio)
    
    # Revertir saldo de la cuenta
    cuenta = mov.cuenta
    if mov.tipo == 'ingreso':
        cuenta.saldo_actual -= mov.monto
    else:
        cuenta.saldo_actual += mov.monto
    cuenta.save()

    mov.delete()
    messages.info(request, "Movimiento eliminado y saldo de la cuenta ajustado.")
    return redirect('finanzas_dashboard')


@login_required
def crear_factura_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import FacturaGasto
        from decimal import Decimal

        tipo_doc = request.POST.get('tipo_documento', 'factura_afecta')
        folio = request.POST.get('folio', '').strip()
        proveedor_nombre = request.POST.get('proveedor_nombre', '').strip()
        proveedor_rut = request.POST.get('proveedor_rut', '').strip()
        fecha_emision_str = request.POST.get('fecha_emision')
        fecha_venc_str = request.POST.get('fecha_vencimiento')
        monto_total_str = request.POST.get('monto_total', '0').replace('.', '').replace(',', '.').replace('$', '').strip()
        archivo = request.FILES.get('archivo_factura')
        observaciones = request.POST.get('observaciones', '').strip()

        try:
            monto_total = Decimal(monto_total_str)
        except Exception:
            messages.error(request, "Monto inválido.")
            return redirect('finanzas_dashboard')

        # Calcular neto e IVA estimado si es factura afecta
        if tipo_doc == 'factura_afecta':
            monto_neto = round(monto_total / Decimal('1.19'), 2)
            monto_iva = monto_total - monto_neto
        else:
            monto_neto = monto_total
            monto_iva = Decimal('0.0')

        try:
            fecha_emision = datetime.strptime(fecha_emision_str, '%Y-%m-%d').date() if fecha_emision_str else timezone.now().date()
        except ValueError:
            fecha_emision = timezone.now().date()

        fecha_venc = None
        if fecha_venc_str:
            try:
                fecha_venc = datetime.strptime(fecha_venc_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        FacturaGasto.objects.create(
            colegio=colegio,
            tipo_documento=tipo_doc,
            folio=folio if folio else f"DOC-{timezone.now().strftime('%H%M%S')}",
            proveedor_nombre=proveedor_nombre if proveedor_nombre else "Proveedor Varios",
            proveedor_rut=proveedor_rut,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_venc,
            monto_neto=monto_neto,
            monto_iva=monto_iva,
            monto_total=monto_total,
            estado_pago='pendiente',
            archivo_factura=archivo,
            observaciones=observaciones,
            registrado_por=request.user
        )

        messages.success(request, f"¡Documento #{folio} ({proveedor_nombre}) registrado exitosamente!")

    return redirect('/colegios/finanzas/?tab=facturas')


@login_required
def pagar_factura_view(request, factura_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import FacturaGasto, CuentaFinanciera, CategoriaFinanciera, MovimientoFinanciero
    factura = get_object_or_404(FacturaGasto, id=factura_id, colegio=colegio)

    if request.method == 'POST':
        cuenta_id = request.POST.get('cuenta_pago_id')
        metodo_pago = request.POST.get('metodo_pago', 'transferencia')

        cuenta = get_object_or_404(CuentaFinanciera, id=cuenta_id, colegio=colegio)
        categoria_egreso = CategoriaFinanciera.objects.filter(colegio=colegio, tipo='egreso').first()

        # Crear movimiento de egreso
        mov = MovimientoFinanciero.objects.create(
            colegio=colegio,
            cuenta=cuenta,
            categoria=categoria_egreso,
            tipo='egreso',
            monto=factura.monto_total,
            concepto=f"Pago {factura.get_tipo_documento_display()} #{factura.folio} - {factura.proveedor_nombre}",
            fecha=timezone.now().date(),
            metodo_pago=metodo_pago,
            numero_comprobante=factura.folio,
            registrado_por=request.user,
            estado='completado'
        )

        # Descontar de cuenta
        cuenta.saldo_actual -= factura.monto_total
        cuenta.save()

        factura.estado_pago = 'pagado'
        factura.movimiento_asociado = mov
        factura.save()

        messages.success(request, f"¡Factura #{factura.folio} pagada con éxito con cargo a {cuenta.nombre}!")

    return redirect('/colegios/finanzas/?tab=facturas')


@login_required
def eliminar_factura_view(request, factura_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import FacturaGasto
    factura = get_object_or_404(FacturaGasto, id=factura_id, colegio=colegio)
    factura.delete()
    messages.info(request, "Documento eliminado.")
    return redirect('/colegios/finanzas/?tab=facturas')


@login_required
def crear_cuenta_financiera_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import CuentaFinanciera
        from decimal import Decimal

        nombre = request.POST.get('nombre', '').strip()
        tipo = request.POST.get('tipo', 'caja_chica')
        banco = request.POST.get('banco', '').strip()
        numero_cuenta = request.POST.get('numero_cuenta', '').strip()
        saldo_inicial_str = request.POST.get('saldo_inicial', '0').replace('.', '').replace(',', '.').replace('$', '').strip()

        try:
            saldo_inicial = Decimal(saldo_inicial_str)
        except Exception:
            saldo_inicial = Decimal('0.0')

        CuentaFinanciera.objects.create(
            colegio=colegio,
            nombre=nombre if nombre else "Nueva Cuenta",
            tipo=tipo,
            banco=banco,
            numero_cuenta=numero_cuenta,
            saldo_inicial=saldo_inicial,
            saldo_actual=saldo_inicial,
            activo=True
        )

        messages.success(request, f"¡Cuenta / Caja '{nombre}' creada con éxito!")

    return redirect('/colegios/finanzas/?tab=cuentas')


@login_required
def crear_categoria_financiera_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import CategoriaFinanciera
        nombre = request.POST.get('nombre', '').strip()
        tipo = request.POST.get('tipo', 'egreso')
        icono = request.POST.get('icono', 'bi-tag')
        color = request.POST.get('color', '#7C5CFC')

        if nombre:
            CategoriaFinanciera.objects.get_or_create(
                colegio=colegio,
                nombre=nombre,
                tipo=tipo,
                defaults={'icono': icono, 'color': color, 'activo': True}
            )
            messages.success(request, f"Categoría '{nombre}' creada.")

    return redirect('finanzas_dashboard')


@login_required
def exportar_finanzas_excel_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_fill = PatternFill(start_color="107C41", end_color="107C41", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    sub_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    from .models import CuentaFinanciera, MovimientoFinanciero, FacturaGasto

    # HOJA 1: RESUMEN DE CUENTAS & BALANCE
    ws1 = wb.create_sheet(title="Resumen & Cajas")
    ws1.views.sheetView[0].showGridLines = True
    ws1['A1'] = f"EDUTEKA - LIBRO DE FINANZAS Y TESORERÍA"
    ws1['A1'].font = title_font
    ws1['A2'] = f"Colegio: {colegio.nombre} | Emisión: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
    ws1['A2'].font = sub_font

    headers_c1 = ["Cuenta / Caja", "Tipo", "Banco / Ref.", "N° Cuenta", "Saldo Inicial", "Saldo Actual", "Estado"]
    for col_idx, h in enumerate(headers_c1, start=1):
        cell = ws1.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    cuentas = CuentaFinanciera.objects.filter(colegio=colegio, activo=True)
    for row_idx, c in enumerate(cuentas, start=5):
        row_data = [
            c.nombre,
            c.get_tipo_display(),
            c.banco or "-",
            c.numero_cuenta or "-",
            f"${c.saldo_inicial:,.0f}",
            f"${c.saldo_actual:,.0f}",
            "Activa" if c.activo else "Inactiva"
        ]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx in [2, 4, 7] else "left", vertical="center")

    # HOJA 2: MOVIMIENTOS
    ws2 = wb.create_sheet(title="Libro Ingresos y Egresos")
    ws2.views.sheetView[0].showGridLines = True
    ws2['A1'] = "HISTORIAL DETALLADO DE INGRESOS Y EGRESOS"
    ws2['A1'].font = title_font
    ws2['A2'] = f"Colegio: {colegio.nombre}"
    ws2['A2'].font = sub_font

    headers_mov = ["Fecha", "Tipo", "Cuenta", "Categoría", "Concepto", "Método Pago", "N° Comprobante", "Monto ($)", "Registrado Por"]
    for col_idx, h in enumerate(headers_mov, start=1):
        cell = ws2.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    movimientos = MovimientoFinanciero.objects.filter(colegio=colegio).select_related('cuenta', 'categoria', 'registrado_por').order_by('-fecha', '-id')
    for row_idx, m in enumerate(movimientos, start=5):
        signo = "+" if m.tipo == 'ingreso' else "-"
        monto_str = f"{signo}${m.monto:,.0f}"
        row_data = [
            m.fecha.strftime('%d/%m/%Y'),
            m.get_tipo_display(),
            m.cuenta.nombre,
            m.categoria.nombre if m.categoria else "Sin Categoría",
            m.concepto,
            m.get_metodo_pago_display(),
            m.numero_comprobante or "-",
            monto_str,
            m.registrado_por.get_full_name() or m.registrado_por.username if m.registrado_por else "-"
        ]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx in [1, 2, 6, 7] else "left", vertical="center")

    # HOJA 3: FACTURAS
    ws3 = wb.create_sheet(title="Facturas & Proveedores")
    ws3.views.sheetView[0].showGridLines = True
    ws3['A1'] = "REGISTRO DE FACTURAS Y DOCUMENTOS TRIBUTARIOS"
    ws3['A1'].font = title_font
    ws3['A2'] = f"Colegio: {colegio.nombre}"
    ws3['A2'].font = sub_font

    headers_fac = ["Tipo Documento", "Folio / N°", "Proveedor", "RUT Emisor", "Emisión", "Vencimiento", "Neto ($)", "IVA ($)", "Total ($)", "Estado Pago"]
    for col_idx, h in enumerate(headers_fac, start=1):
        cell = ws3.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    facturas = FacturaGasto.objects.filter(colegio=colegio).order_by('-fecha_emision', '-id')
    for row_idx, f in enumerate(facturas, start=5):
        row_data = [
            f.get_tipo_documento_display(),
            f.folio,
            f.proveedor_nombre,
            f.proveedor_rut or "-",
            f.fecha_emision.strftime('%d/%m/%Y'),
            f.fecha_vencimiento.strftime('%d/%m/%Y') if f.fecha_vencimiento else "-",
            f"${f.monto_neto:,.0f}",
            f"${f.monto_iva:,.0f}",
            f"${f.monto_total:,.0f}",
            f.get_estado_pago_display()
        ]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws3.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx in [2, 4, 5, 6, 10] else "left", vertical="center")

    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    if len(val_str) > max_len and len(val_str) < 50:
                        max_len = len(val_str)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    import io
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"finanzas_{colegio.nombre.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ==============================================================================
# MÓDULO DE INVENTARIO ESCOLAR, STOCK Y DIRECTORIO DE PROVEEDORES
# ==============================================================================

def inicializar_datos_inventario(colegio):
    from .models import ProveedorColegio, CategoriaInventario, ItemInventario

    # Proveedores iniciales
    p1, _ = ProveedorColegio.objects.get_or_create(
        colegio=colegio,
        nombre="Librería & Papelería Central SpA",
        defaults={
            'rut': '76.432.890-1',
            'categoria_insumos': 'Papelería, Útiles y Cartelería',
            'contacto_nombre': 'Rodrigo Valenzuela',
            'telefono': '+56991234567',
            'email': 'contacto@libreriacentral.cl',
            'direccion': 'Av. Providencia 1240, Santiago',
            'notas': 'Descuento institucional 10% en compras sobre $100.000.'
        }
    )

    p2, _ = ProveedorColegio.objects.get_or_create(
        colegio=colegio,
        nombre="TecnoEscuela & Soluciones TI",
        defaults={
            'rut': '77.890.123-4',
            'categoria_insumos': 'Tecnología, Impresión y Proyectores',
            'contacto_nombre': 'Camila Arancibia',
            'telefono': '+56987654321',
            'email': 'ventas@tecnoescuela.cl',
            'direccion': 'Calle Las Industrias 890, Santiago',
            'notas': 'Garantía técnica 12 meses en hardware y recargas de tóner.'
        }
    )

    p3, _ = ProveedorColegio.objects.get_or_create(
        colegio=colegio,
        nombre="Distribuidora Limpimax Institucional",
        defaults={
            'rut': '78.111.222-3',
            'categoria_insumos': 'Aseo, Higiene y Desinfección',
            'contacto_nombre': 'Mauricio Soto',
            'telefono': '+56955544433',
            'email': 'pedidos@limpimax.cl',
            'direccion': 'San Pablo 4500, Quinta Normal',
            'notas': 'Despacho gratuito los días martes y jueves.'
        }
    )

    # Categorías
    cat_pap, _ = CategoriaInventario.objects.get_or_create(colegio=colegio, nombre="Útiles & Papelería", defaults={'icono': 'bi-pencil-square', 'color': '#7C5CFC'})
    cat_tec, _ = CategoriaInventario.objects.get_or_create(colegio=colegio, nombre="Tecnología & Impresión", defaults={'icono': 'bi-laptop', 'color': '#3B82F6'})
    cat_ase, _ = CategoriaInventario.objects.get_or_create(colegio=colegio, nombre="Aseo & Limpieza", defaults={'icono': 'bi-droplet-half', 'color': '#10B981'})
    cat_mob, _ = CategoriaInventario.objects.get_or_create(colegio=colegio, nombre="Mobiliario & Infraestructura", defaults={'icono': 'bi-building', 'color': '#F59E0B'})

    # Items iniciales con alertas si no existen
    if not ItemInventario.objects.filter(colegio=colegio).exists():
        ItemInventario.objects.create(
            colegio=colegio,
            nombre="Resmas de Papel Carta 75g (Chamex / Report)",
            sku="PAP-CRT-01",
            categoria=cat_pap,
            proveedor_principal=p1,
            tipo="consumible",
            stock_actual=3,
            stock_minimo=12,
            unidad_medida="resmas",
            ubicacion="Bodega Principal - Estante A1",
            costo_unitario=4200.0,
            descripcion="Papel blanco multiuso para guías escolares y evaluaciones impresas."
        )

        ItemInventario.objects.create(
            colegio=colegio,
            nombre="Plumones de Pizarra Recargables (Caja 12 un. Surtidos)",
            sku="PLU-PIZ-12",
            categoria=cat_pap,
            proveedor_principal=p1,
            tipo="consumible",
            stock_actual=4,
            stock_minimo=10,
            unidad_medida="cajas",
            ubicacion="Sala de Profesores / Armario Insumos",
            costo_unitario=8900.0,
            descripcion="Plumones punta redonda para salas de clases (Azul, Negro, Rojo)."
        )

        ItemInventario.objects.create(
            colegio=colegio,
            nombre="Tóner Impresora HP LaserJet Pro 4003",
            sku="TON-HP-4003",
            categoria=cat_tec,
            proveedor_principal=p2,
            tipo="consumible",
            stock_actual=1,
            stock_minimo=3,
            unidad_medida="unidades",
            ubicacion="Oficina de Dirección",
            costo_unitario=45000.0,
            descripcion="Cartucho de tóner de alto rendimiento para fotocopiadora y secretaría."
        )

        ItemInventario.objects.create(
            colegio=colegio,
            nombre="Alcohol Gel Desinfectante 70% (Bidón 5L)",
            sku="ASE-ALC-5L",
            categoria=cat_ase,
            proveedor_principal=p3,
            tipo="consumible",
            stock_actual=8,
            stock_minimo=4,
            unidad_medida="bidones",
            ubicacion="Bodega de Auxiliares",
            costo_unitario=12500.0,
            descripcion="Para recarga de dispensadores en salas y patios."
        )

        ItemInventario.objects.create(
            colegio=colegio,
            nombre="Impresora Multifuncional Epson EcoTank L3250",
            sku="IMP-EPS-L32",
            categoria=cat_tec,
            proveedor_principal=p2,
            tipo="activo",
            stock_actual=3,
            stock_minimo=1,
            unidad_medida="unidades",
            ubicacion="Secretaría y Sala PIE",
            costo_unitario=189000.0,
            descripcion="Impresoras con sistema continuo para uso administrativo."
        )


@login_required
def inventario_dashboard_view(request):
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

    inicializar_datos_inventario(colegio)

    from .models import ItemInventario, CategoriaInventario, ProveedorColegio, MovimientoStock
    from django.db.models import Q, F, Sum, ExpressionWrapper, DecimalField

    categorias = CategoriaInventario.objects.filter(colegio=colegio, activo=True)
    proveedores = ProveedorColegio.objects.filter(colegio=colegio, activo=True)

    # Filtros
    cat_filtro = request.GET.get('categoria')
    prov_filtro = request.GET.get('proveedor')
    tipo_filtro = request.GET.get('tipo')
    estado_filtro = request.GET.get('estado')
    busqueda = request.GET.get('q', '').strip()

    items_qs = ItemInventario.objects.filter(colegio=colegio, activo=True).select_related('categoria', 'proveedor_principal')

    if cat_filtro and cat_filtro.isdigit():
        items_qs = items_qs.filter(categoria_id=int(cat_filtro))
    if prov_filtro and prov_filtro.isdigit():
        items_qs = items_qs.filter(proveedor_principal_id=int(prov_filtro))
    if tipo_filtro in ['consumible', 'activo']:
        items_qs = items_qs.filter(tipo=tipo_filtro)
    if estado_filtro == 'alerta':
        items_qs = items_qs.filter(stock_actual__lte=F('stock_minimo'), stock_actual__gt=0)
    elif estado_filtro == 'agotado':
        items_qs = items_qs.filter(stock_actual__lte=0)
    elif estado_filtro == 'optimo':
        items_qs = items_qs.filter(stock_actual__gt=F('stock_minimo'))

    if busqueda:
        items_qs = items_qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(sku__icontains=busqueda) |
            Q(ubicacion__icontains=busqueda) |
            Q(proveedor_principal__nombre__icontains=busqueda)
        )

    # KPIs
    todos_items = ItemInventario.objects.filter(colegio=colegio, activo=True)
    total_articulos = todos_items.count()
    total_en_alerta = todos_items.filter(stock_actual__lte=F('stock_minimo'), stock_actual__gt=0).count()
    total_agotados = todos_items.filter(stock_actual__lte=0).count()
    total_criticos = total_en_alerta + total_agotados

    # Valor total estimado del inventario
    valor_total_inv = sum([item.stock_actual * item.costo_unitario for item in todos_items if item.stock_actual > 0])

    # Movimientos recientes de bodega
    movimientos_recientes = MovimientoStock.objects.filter(item__colegio=colegio).select_related('item', 'registrado_por').order_by('-fecha')[:15]

    # Paginación
    paginator = Paginator(items_qs.order_by('stock_actual', 'nombre'), 15)
    page_number = request.GET.get('page', 1)
    items_page = paginator.get_page(page_number)

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'inventario',
        'hoy': timezone.now(),
        # Listados
        'items': items_page,
        'categorias': categorias,
        'proveedores': proveedores,
        'movimientos_recientes': movimientos_recientes,
        # Filtros
        'cat_filtro': int(cat_filtro) if cat_filtro and cat_filtro.isdigit() else None,
        'prov_filtro': int(prov_filtro) if prov_filtro and prov_filtro.isdigit() else None,
        'tipo_filtro': tipo_filtro,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        # KPIs
        'total_articulos': total_articulos,
        'total_en_alerta': total_en_alerta,
        'total_agotados': total_agotados,
        'total_criticos': total_criticos,
        'valor_total_inv': valor_total_inv,
    }
    return render(request, 'colegios/inventario_dashboard.html', context)


@login_required
def crear_item_inventario_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import ItemInventario, CategoriaInventario, ProveedorColegio, MovimientoStock
        from decimal import Decimal

        nombre = request.POST.get('nombre', '').strip()
        sku = request.POST.get('sku', '').strip()
        categoria_id = request.POST.get('categoria_id')
        proveedor_id = request.POST.get('proveedor_id')
        tipo = request.POST.get('tipo', 'consumible')
        stock_actual = int(request.POST.get('stock_actual', 0) or 0)
        stock_minimo = int(request.POST.get('stock_minimo', 5) or 5)
        unidad_medida = request.POST.get('unidad_medida', 'unidades').strip()
        ubicacion = request.POST.get('ubicacion', 'Bodega Principal').strip()
        costo_str = request.POST.get('costo_unitario', '0').replace('.', '').replace(',', '.').replace('$', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        try:
            costo_unitario = Decimal(costo_str)
        except Exception:
            costo_unitario = Decimal('0.0')

        categoria = CategoriaInventario.objects.filter(id=categoria_id, colegio=colegio).first() if categoria_id else None
        proveedor = ProveedorColegio.objects.filter(id=proveedor_id, colegio=colegio).first() if proveedor_id else None

        item = ItemInventario.objects.create(
            colegio=colegio,
            nombre=nombre,
            sku=sku,
            categoria=categoria,
            proveedor_principal=proveedor,
            tipo=tipo,
            stock_actual=stock_actual,
            stock_minimo=stock_minimo,
            unidad_medida=unidad_medida,
            ubicacion=ubicacion,
            costo_unitario=costo_unitario,
            descripcion=descripcion
        )

        if stock_actual > 0:
            MovimientoStock.objects.create(
                item=item,
                tipo='entrada',
                cantidad=stock_actual,
                stock_resultante=stock_actual,
                motivo='Stock Inicial al registrar artículo',
                registrado_por=request.user
            )

        messages.success(request, f"¡Artículo '{nombre}' agregado al inventario con éxito!")

    return redirect('inventario_dashboard')


@login_required
def ajustar_stock_view(request, item_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import ItemInventario, MovimientoStock
    item = get_object_or_404(ItemInventario, id=item_id, colegio=colegio)

    if request.method == 'POST':
        tipo_mov = request.POST.get('tipo_movimiento', 'entrada') # entrada / salida / ajuste
        cantidad = int(request.POST.get('cantidad', 1) or 1)
        motivo = request.POST.get('motivo', '').strip()
        entregado_a = request.POST.get('entregado_a', '').strip()

        if tipo_mov == 'entrada':
            item.stock_actual += cantidad
            mov_desc = f"+{cantidad} {item.unidad_medida} (Entrada / Compra)"
        elif tipo_mov == 'salida':
            if cantidad > item.stock_actual:
                messages.error(request, f"No puedes retirar {cantidad} {item.unidad_medida}. Solo hay {item.stock_actual} en stock.")
                return redirect('inventario_dashboard')
            item.stock_actual -= cantidad
            mov_desc = f"-{cantidad} {item.unidad_medida} (Salida / Entrega a {entregado_a or 'Personal'})"
        else: # ajuste directo
            item.stock_actual = cantidad
            mov_desc = f"Ajuste manual a {cantidad} {item.unidad_medida}"

        item.save()

        MovimientoStock.objects.create(
            item=item,
            tipo=tipo_mov,
            cantidad=cantidad,
            stock_resultante=item.stock_actual,
            motivo=motivo if motivo else mov_desc,
            entregado_a=entregado_a,
            registrado_por=request.user
        )

        messages.success(request, f"¡Stock de '{item.nombre}' actualizado a {item.stock_actual} {item.unidad_medida}!")

    return redirect('inventario_dashboard')


@login_required
def eliminar_item_inventario_view(request, item_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import ItemInventario
    item = get_object_or_404(ItemInventario, id=item_id, colegio=colegio)
    item.delete()
    messages.info(request, "Artículo eliminado del inventario.")
    return redirect('inventario_dashboard')


@login_required
def proveedores_directorio_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    inicializar_datos_inventario(colegio)

    from .models import ProveedorColegio
    busqueda = request.GET.get('q', '').strip()
    proveedores_qs = ProveedorColegio.objects.filter(colegio=colegio, activo=True).prefetch_related('articulos_suministrados')

    if busqueda:
        from django.db.models import Q
        proveedores_qs = proveedores_qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(categoria_insumos__icontains=busqueda) |
            Q(contacto_nombre__icontains=busqueda) |
            Q(email__icontains=busqueda) |
            Q(telefono__icontains=busqueda)
        )

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'proveedores',
        'hoy': timezone.now(),
        'proveedores': proveedores_qs,
        'busqueda': busqueda,
    }
    return render(request, 'colegios/proveedores_directorio.html', context)


@login_required
def crear_proveedor_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import ProveedorColegio
        nombre = request.POST.get('nombre', '').strip()
        rut = request.POST.get('rut', '').strip()
        categoria_insumos = request.POST.get('categoria_insumos', 'Papelería y Útiles').strip()
        contacto_nombre = request.POST.get('contacto_nombre', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        sitio_web = request.POST.get('sitio_web', '').strip()
        notas = request.POST.get('notas', '').strip()

        ProveedorColegio.objects.create(
            colegio=colegio,
            nombre=nombre,
            rut=rut,
            categoria_insumos=categoria_insumos,
            contacto_nombre=contacto_nombre,
            telefono=telefono,
            email=email,
            direccion=direccion,
            sitio_web=sitio_web,
            notas=notas,
            activo=True
        )

        messages.success(request, f"¡Proveedor '{nombre}' registrado exitosamente!")

    return redirect('proveedores_directorio')


@login_required
def editar_proveedor_view(request, proveedor_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import ProveedorColegio
    prov = get_object_or_404(ProveedorColegio, id=proveedor_id, colegio=colegio)

    if request.method == 'POST':
        prov.nombre = request.POST.get('nombre', prov.nombre).strip()
        prov.rut = request.POST.get('rut', prov.rut).strip()
        prov.categoria_insumos = request.POST.get('categoria_insumos', prov.categoria_insumos).strip()
        prov.contacto_nombre = request.POST.get('contacto_nombre', prov.contacto_nombre).strip()
        prov.telefono = request.POST.get('telefono', prov.telefono).strip()
        prov.email = request.POST.get('email', prov.email).strip()
        prov.direccion = request.POST.get('direccion', prov.direccion).strip()
        prov.sitio_web = request.POST.get('sitio_web', prov.sitio_web).strip()
        prov.notas = request.POST.get('notas', prov.notas).strip()
        prov.save()

        messages.success(request, f"¡Proveedor '{prov.nombre}' actualizado!")

    return redirect('proveedores_directorio')


@login_required
def eliminar_proveedor_view(request, proveedor_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import ProveedorColegio
    prov = get_object_or_404(ProveedorColegio, id=proveedor_id, colegio=colegio)
    prov.activo = False
    prov.save()
    messages.info(request, f"Proveedor '{prov.nombre}' archivado.")
    return redirect('proveedores_directorio')


@login_required
def exportar_inventario_excel_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    header_fill = PatternFill(start_color="107C41", end_color="107C41", fill_type="solid")
    alert_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    sub_font = Font(name="Calibri", size=10, italic=True, color="64748B")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    from .models import ItemInventario, ProveedorColegio, MovimientoStock

    # HOJA 1: CATÁLOGO DE INVENTARIO
    ws1 = wb.create_sheet(title="Inventario General")
    ws1.views.sheetView[0].showGridLines = True
    ws1['A1'] = f"EDUTEKA - INVENTARIO GENERAL DEL COLEGIO"
    ws1['A1'].font = title_font
    ws1['A2'] = f"Colegio: {colegio.nombre} | Emisión: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
    ws1['A2'].font = sub_font

    headers_inv = ["Código / SKU", "Artículo", "Categoría", "Tipo", "Stock Actual", "Stock Mínimo", "Unidad", "Estado", "Ubicación", "Costo Unit. ($)", "Proveedor Principal"]
    for col_idx, h in enumerate(headers_inv, start=1):
        cell = ws1.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    items = ItemInventario.objects.filter(colegio=colegio, activo=True).select_related('categoria', 'proveedor_principal').order_by('stock_actual', 'nombre')
    for row_idx, it in enumerate(items, start=5):
        estado_label = "Agotado (Crítico)" if it.stock_actual <= 0 else ("Bajo Stock (Alerta)" if it.stock_actual <= it.stock_minimo else "Óptimo")
        row_data = [
            it.sku or "-",
            it.nombre,
            it.categoria.nombre if it.categoria else "Sin Categoría",
            it.get_tipo_display(),
            it.stock_actual,
            it.stock_minimo,
            it.unidad_medida,
            estado_label,
            it.ubicacion,
            f"${it.costo_unitario:,.0f}",
            it.proveedor_principal.nombre if it.proveedor_principal else "-"
        ]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws1.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx in [1, 4, 5, 6, 7, 8] else "left", vertical="center")
            if it.en_alerta and col_idx == 8:
                cell.fill = alert_fill
                cell.font = Font(name="Calibri", size=11, bold=True, color="B91C1C")

    # HOJA 2: DIRECTORIO DE PROVEEDORES
    ws2 = wb.create_sheet(title="Proveedores")
    ws2.views.sheetView[0].showGridLines = True
    ws2['A1'] = "DIRECTORIO DE PROVEEDORES INSTITUCIONALES"
    ws2['A1'].font = title_font
    ws2['A2'] = f"Colegio: {colegio.nombre}"
    ws2['A2'].font = sub_font

    headers_prov = ["Razón Social / Proveedor", "RUT", "Rubro / Categoría", "Contacto Comercial", "Teléfono / WhatsApp", "Correo Electrónico", "Dirección", "Notas"]
    for col_idx, h in enumerate(headers_prov, start=1):
        cell = ws2.cell(row=4, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    proveedores = ProveedorColegio.objects.filter(colegio=colegio, activo=True).order_by('nombre')
    for row_idx, p in enumerate(proveedores, start=5):
        row_data = [
            p.nombre,
            p.rut or "-",
            p.categoria_insumos,
            p.contacto_nombre or "-",
            p.telefono or "-",
            p.email or "-",
            p.direccion or "-",
            p.notas or "-"
        ]
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws2.cell(row=row_idx, column=col_idx, value=val)
            cell.font = regular_font
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center" if col_idx in [2, 5] else "left", vertical="center")

    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    if len(val_str) > max_len and len(val_str) < 50:
                        max_len = len(val_str)
            sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

    import io
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"inventario_{colegio.nombre.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ==============================================================================
# MÓDULO DE TALLERES EXTRACURRICULARES (ACLES) & ASISTENCIA MULTICURSO
# ==============================================================================

def inicializar_datos_talleres(colegio):
    from .models import TallerExtracurricular, InscripcionTaller, Estudiante, SesionAsistenciaTaller, DetalleAsistenciaTaller

    if not TallerExtracurricular.objects.filter(colegio=colegio).exists():
        admin_docente = colegio.administrador

        t1 = TallerExtracurricular.objects.create(
            colegio=colegio,
            nombre="Taller de Robótica & Programación Escolar",
            categoria="cientifico",
            docente_encargado=admin_docente,
            dias_horario="Martes y Jueves 15:30 - 17:00",
            lugar="Laboratorio de Informática / Sala STEM",
            cupo_maximo=20,
            descripcion="Desarrollo de proyectos con Arduino, sensores y lógica de programación en bloques para competencias escolares.",
            icono="bi-robot",
            color="#3B82F6"
        )

        t2 = TallerExtracurricular.objects.create(
            colegio=colegio,
            nombre="Selección de Fútbol Masculino & Femenino",
            categoria="deportivo",
            monitor_externo="Prof. Gabriel Retamal (DT Deportivo)",
            dias_horario="Lunes y Miércoles 16:00 - 17:45",
            lugar="Cancha Principal de Césped",
            cupo_maximo=30,
            descripcion="Entrenamiento formativo, táctico y participación en ligas y torneos intercomunales.",
            icono="bi-trophy-fill",
            color="#10B981"
        )

        t3 = TallerExtracurricular.objects.create(
            colegio=colegio,
            nombre="Taller de Teatro & Expresión Corporal",
            categoria="artistico",
            docente_encargado=admin_docente,
            dias_horario="Viernes 15:00 - 17:00",
            lugar="Auditorio / Sala de Artes",
            cupo_maximo=25,
            descripcion="Expresión escénica, improvisación, modulación de voz y montaje de la obra de fin de año.",
            icono="bi-palette-fill",
            color="#EC4899"
        )

        t4 = TallerExtracurricular.objects.create(
            colegio=colegio,
            nombre="Club de Ajedrez & Pensamiento Estratégico",
            categoria="academico",
            docente_encargado=admin_docente,
            dias_horario="Miércoles 15:30 - 17:00",
            lugar="Biblioteca Central",
            cupo_maximo=20,
            descripcion="Tácticas de apertura, medio juego, finales y torneos suizos internos.",
            icono="bi-grid-3x3-gap-fill",
            color="#F59E0B"
        )

        # Inscribir algunos estudiantes de muestra si existen
        estudiantes = list(Estudiante.objects.filter(colegio=colegio, activo=True)[:15])
        if estudiantes:
            for est in estudiantes[:8]:
                InscripcionTaller.objects.get_or_create(taller=t1, estudiante=est)
            for est in estudiantes[4:14]:
                InscripcionTaller.objects.get_or_create(taller=t2, estudiante=est)
            for est in estudiantes[2:10]:
                InscripcionTaller.objects.get_or_create(taller=t3, estudiante=est)


@login_required
def talleres_dashboard_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    inicializar_datos_talleres(colegio)

    from .models import TallerExtracurricular, InscripcionTaller, SesionAsistenciaTaller, CursoColegio
    from django.db.models import Q, Count

    categoria_filtro = request.GET.get('categoria', '').strip()
    busqueda = request.GET.get('q', '').strip()

    talleres_qs = TallerExtracurricular.objects.filter(colegio=colegio, activo=True).annotate(
        num_inscritos=Count('inscripciones', filter=Q(inscripciones__activo=True)),
        num_sesiones=Count('sesiones_asistencia')
    ).select_related('docente_encargado')

    if categoria_filtro:
        talleres_qs = talleres_qs.filter(categoria=categoria_filtro)

    if busqueda:
        talleres_qs = talleres_qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(lugar__icontains=busqueda) |
            Q(monitor_externo__icontains=busqueda) |
            Q(docente_encargado__first_name__icontains=busqueda) |
            Q(docente_encargado__last_name__icontains=busqueda)
        )

    # KPIs
    todos_talleres = TallerExtracurricular.objects.filter(colegio=colegio, activo=True)
    total_talleres = todos_talleres.count()
    total_inscripciones = InscripcionTaller.objects.filter(taller__colegio=colegio, activo=True).count()
    total_sesiones = SesionAsistenciaTaller.objects.filter(taller__colegio=colegio).count()
    
    # Docentes/Personal disponibles para ser monitores
    docentes_disponibles = User.objects.filter(
        Q(membresias_colegio__colegio=colegio, membresias_colegio__activo=True) |
        Q(colegios_administrados=colegio)
    ).distinct()

    categorias_choices = TallerExtracurricular.CATEGORIA_CHOICES

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'talleres',
        'hoy': timezone.now(),
        'talleres': talleres_qs.order_by('nombre'),
        'total_talleres': total_talleres,
        'total_inscripciones': total_inscripciones,
        'total_sesiones': total_sesiones,
        'categoria_filtro': categoria_filtro,
        'busqueda': busqueda,
        'categorias_choices': categorias_choices,
        'docentes_disponibles': docentes_disponibles,
    }
    return render(request, 'colegios/talleres_dashboard.html', context)


@login_required
def crear_taller_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import TallerExtracurricular

        nombre = request.POST.get('nombre', '').strip()
        categoria = request.POST.get('categoria', 'deportivo')
        docente_id = request.POST.get('docente_encargado')
        monitor_externo = request.POST.get('monitor_externo', '').strip()
        dias_horario = request.POST.get('dias_horario', '').strip()
        lugar = request.POST.get('lugar', 'Gimnasio / Sala Multiuso').strip()
        cupo_str = request.POST.get('cupo_maximo', '30')
        descripcion = request.POST.get('descripcion', '').strip()
        icono = request.POST.get('icono', 'bi-star-fill')
        color = request.POST.get('color', '#7C5CFC')

        try:
            cupo_maximo = int(cupo_str) if cupo_str else 30
        except Exception:
            cupo_maximo = 30

        docente = User.objects.filter(id=docente_id).first() if docente_id else None

        taller = TallerExtracurricular.objects.create(
            colegio=colegio,
            nombre=nombre,
            categoria=categoria,
            docente_encargado=docente,
            monitor_externo=monitor_externo,
            dias_horario=dias_horario,
            lugar=lugar,
            cupo_maximo=cupo_maximo,
            descripcion=descripcion,
            icono=icono,
            color=color,
            activo=True
        )

        messages.success(request, f"¡Taller '{nombre}' creado exitosamente!")
        return redirect('detalle_taller', taller_id=taller.id)

    return redirect('talleres_dashboard')


@login_required
def detalle_taller_view(request, taller_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    from .models import TallerExtracurricular, InscripcionTaller, SesionAsistenciaTaller, DetalleAsistenciaTaller, Estudiante, CursoColegio

    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)
    inscripciones = InscripcionTaller.objects.filter(taller=taller, activo=True).select_related('estudiante', 'estudiante__seccion', 'estudiante__seccion__curso').order_by('estudiante__nombre_completo')
    sesiones = SesionAsistenciaTaller.objects.filter(taller=taller).prefetch_related('detalles').order_by('-fecha', '-id')

    # Estudiantes ya inscritos IDs
    inscritos_ids = inscripciones.values_list('estudiante_id', flat=True)

    # Estudiantes disponibles de todos los cursos para inscribir
    cursos = CursoColegio.objects.filter(colegio=colegio, activo=True).prefetch_related('secciones')
    
    # Filtro del selector de alumnos
    curso_filtro = request.GET.get('curso_filtro')
    estudiantes_disponibles_qs = Estudiante.objects.filter(colegio=colegio, activo=True).exclude(id__in=inscritos_ids).select_related('seccion', 'seccion__curso')

    if curso_filtro and curso_filtro.isdigit():
        estudiantes_disponibles_qs = estudiantes_disponibles_qs.filter(seccion__curso_id=int(curso_filtro))

    estudiantes_disponibles = estudiantes_disponibles_qs.order_by('seccion__curso__orden', 'nombre_completo')[:100]

    # Calcular estadísticas de asistencia de los inscritos
    total_sesiones_count = sesiones.count()
    inscripciones_con_stats = []
    for insc in inscripciones:
        if total_sesiones_count > 0:
            asistidas = DetalleAsistenciaTaller.objects.filter(
                sesion__taller=taller,
                estudiante=insc.estudiante,
                estado__in=['presente', 'tarde', 'justificado']
            ).count()
            porc = round((asistidas / total_sesiones_count) * 100, 1)
        else:
            porc = 100.0
        inscripciones_con_stats.append({
            'inscripcion': insc,
            'estudiante': insc.estudiante,
            'porcentaje_asistencia': porc
        })

    # Docentes disponibles para edición
    docentes_disponibles = User.objects.filter(
        Q(membresias_colegio__colegio=colegio, membresias_colegio__activo=True) |
        Q(colegios_administrados=colegio)
    ).distinct()


    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'talleres',
        'hoy': timezone.now(),
        'taller': taller,
        'inscripciones_con_stats': inscripciones_con_stats,
        'total_inscritos': len(inscripciones),
        'sesiones': sesiones,
        'total_sesiones': total_sesiones_count,
        'cursos': cursos,
        'curso_filtro': int(curso_filtro) if curso_filtro and curso_filtro.isdigit() else None,
        'estudiantes_disponibles': estudiantes_disponibles,
        'docentes_disponibles': docentes_disponibles,
        'categorias_choices': TallerExtracurricular.CATEGORIA_CHOICES,
    }
    return render(request, 'colegios/detalle_taller.html', context)


@login_required
def inscribir_estudiante_taller_view(request, taller_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import TallerExtracurricular, InscripcionTaller, Estudiante

    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)

    if request.method == 'POST':
        estudiantes_ids = request.POST.getlist('estudiantes_ids')
        estudiante_id = request.POST.get('estudiante_id')
        
        if estudiante_id and not estudiantes_ids:
            estudiantes_ids = [estudiante_id]

        agregados = 0
        for est_id in estudiantes_ids:
            if est_id and est_id.isdigit():
                est = Estudiante.objects.filter(id=int(est_id), colegio=colegio).first()
                if est:
                    _, created = InscripcionTaller.objects.get_or_create(
                        taller=taller,
                        estudiante=est,
                        defaults={'activo': True}
                    )
                    if created:
                        agregados += 1

        if agregados > 0:
            messages.success(request, f"¡Se inscribieron {agregados} alumno(s) en {taller.nombre}!")
        else:
            messages.info(request, "Los alumnos seleccionados ya estaban inscritos.")

    return redirect('detalle_taller', taller_id=taller.id)


@login_required
def desinscribir_estudiante_taller_view(request, taller_id, inscripcion_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import TallerExtracurricular, InscripcionTaller

    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)
    inscripcion = get_object_or_404(InscripcionTaller, id=inscripcion_id, taller=taller)
    
    nombre_est = inscripcion.estudiante.nombre_completo
    inscripcion.delete()
    messages.info(request, f"{nombre_est} fue retirado(a) del taller.")

    return redirect('detalle_taller', taller_id=taller.id)


@login_required
def tomar_asistencia_taller_view(request, taller_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director'])
    )

    from .models import TallerExtracurricular, InscripcionTaller, SesionAsistenciaTaller, DetalleAsistenciaTaller, Estudiante

    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)
    inscripciones = InscripcionTaller.objects.filter(taller=taller, activo=True).select_related('estudiante', 'estudiante__seccion', 'estudiante__seccion__curso').order_by('estudiante__nombre_completo')

    if request.method == 'POST':
        fecha_str = request.POST.get('fecha', timezone.now().strftime('%Y-%m-%d'))
        contenido = request.POST.get('contenido_actividad', '').strip()

        import datetime
        try:
            fecha_sesion = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except Exception:
            fecha_sesion = timezone.now().date()

        sesion, _ = SesionAsistenciaTaller.objects.get_or_create(
            taller=taller,
            fecha=fecha_sesion,
            defaults={
                'contenido_actividad': contenido,
                'registrado_por': request.user
            }
        )
        sesion.contenido_actividad = contenido
        sesion.registrado_por = request.user
        sesion.save()

        # Guardar estado de cada estudiante inscrito
        for insc in inscripciones:
            est = insc.estudiante
            estado = request.POST.get(f'estado_{est.id}', 'presente')
            obs = request.POST.get(f'obs_{est.id}', '').strip()

            DetalleAsistenciaTaller.objects.update_or_create(
                sesion=sesion,
                estudiante=est,
                defaults={
                    'estado': estado,
                    'observacion': obs
                }
            )

        messages.success(request, f"¡Asistencia de {taller.nombre} guardada con éxito para el {fecha_sesion.strftime('%d/%m/%Y')}!")
        return redirect('detalle_taller', taller_id=taller.id)

    # GET
    fecha_hoy = timezone.now().strftime('%Y-%m-%d')
    # Verificar si ya hay una sesión guardada hoy
    sesion_hoy = SesionAsistenciaTaller.objects.filter(taller=taller, fecha=timezone.now().date()).first()
    detalles_dict = {}
    if sesion_hoy:
        for d in sesion_hoy.detalles.all():
            detalles_dict[d.estudiante_id] = {'estado': d.estado, 'observacion': d.observacion}

    for insc in inscripciones:
        det = detalles_dict.get(insc.estudiante_id, {})
        insc.estudiante.estado_actual = det.get('estado', 'presente')
        insc.estudiante.obs_actual = det.get('observacion', '')

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'talleres',
        'hoy': timezone.now(),
        'taller': taller,
        'inscripciones': inscripciones,
        'fecha_hoy': fecha_hoy,
        'sesion_hoy': sesion_hoy,
    }
    return render(request, 'colegios/tomar_asistencia_taller.html', context)



@login_required
def detalle_sesion_taller_view(request, taller_id, sesion_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('solicitar_acceso')

    from .models import TallerExtracurricular, SesionAsistenciaTaller

    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)
    sesion = get_object_or_404(SesionAsistenciaTaller, id=sesion_id, taller=taller)
    detalles = sesion.detalles.select_related('estudiante', 'estudiante__seccion', 'estudiante__seccion__curso').order_by('estudiante__nombre_completo')

    context = {
        'colegio': colegio,
        'active_page': 'talleres',
        'taller': taller,
        'sesion': sesion,
        'detalles': detalles,
        'hoy': timezone.now(),
    }
    return render(request, 'colegios/detalle_sesion_taller.html', context)


@login_required
def eliminar_sesion_taller_view(request, taller_id, sesion_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import TallerExtracurricular, SesionAsistenciaTaller
    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)
    sesion = get_object_or_404(SesionAsistenciaTaller, id=sesion_id, taller=taller)
    sesion.delete()
    messages.info(request, "Sesión de asistencia eliminada.")
    return redirect('detalle_taller', taller_id=taller.id)


@login_required
def editar_taller_view(request, taller_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import TallerExtracurricular
    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)

    if request.method == 'POST':
        taller.nombre = request.POST.get('nombre', taller.nombre).strip()
        taller.categoria = request.POST.get('categoria', taller.categoria)
        docente_id = request.POST.get('docente_encargado')
        taller.docente_encargado = User.objects.filter(id=docente_id).first() if docente_id else None
        taller.monitor_externo = request.POST.get('monitor_externo', '').strip()
        taller.dias_horario = request.POST.get('dias_horario', taller.dias_horario).strip()
        taller.lugar = request.POST.get('lugar', taller.lugar).strip()
        cupo_str = request.POST.get('cupo_maximo')
        try:
            taller.cupo_maximo = int(cupo_str) if cupo_str else None
        except Exception:
            pass
        taller.descripcion = request.POST.get('descripcion', taller.descripcion).strip()
        taller.color = request.POST.get('color', taller.color)
        taller.save()

        messages.success(request, f"¡Taller '{taller.nombre}' actualizado!")

    return redirect('detalle_taller', taller_id=taller.id)


@login_required
def eliminar_taller_view(request, taller_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import TallerExtracurricular
    taller = get_object_or_404(TallerExtracurricular, id=taller_id, colegio=colegio)
    taller.activo = False
    taller.save()
    messages.info(request, f"Taller '{taller.nombre}' archivado.")
    return redirect('talleres_dashboard')


# ==============================================================================
# VISTAS DE EVALUACIÓN Y GESTIÓN SIMCE / DIA
# ==============================================================================

def inicializar_datos_simce_demo(colegio, user):
    """Inicializa datos históricos y ensayos de prueba para que el colegio tenga métricas reales al comenzar."""
    from .models import EnsayoSIMCE, ResultadoEnsayoSIMCE, PuntajeHistoricoSIMCE, CursoColegio, Estudiante
    import random

    # 1. Histórico Oficial Agencia de Calidad (si no existen)
    if not PuntajeHistoricoSIMCE.objects.filter(colegio=colegio).exists():
        historicos = [
            # 2024
            {'anio': 2024, 'nivel_escolar': '4° Básico', 'asignatura': 'Lectura', 'puntaje_colegio': 272, 'puntaje_gse': 258, 'puntaje_nacional': 253, 'insuf': 15.0, 'elem': 40.0, 'adec': 45.0},
            {'anio': 2024, 'nivel_escolar': '4° Básico', 'asignatura': 'Matemática', 'puntaje_colegio': 265, 'puntaje_gse': 252, 'puntaje_nacional': 249, 'insuf': 22.0, 'elem': 45.0, 'adec': 33.0},
            {'anio': 2024, 'nivel_escolar': 'II° Medio', 'asignatura': 'Lectura', 'puntaje_colegio': 260, 'puntaje_gse': 250, 'puntaje_nacional': 248, 'insuf': 25.0, 'elem': 45.0, 'adec': 30.0},
            {'anio': 2024, 'nivel_escolar': 'II° Medio', 'asignatura': 'Matemática', 'puntaje_colegio': 258, 'puntaje_gse': 245, 'puntaje_nacional': 244, 'insuf': 30.0, 'elem': 42.0, 'adec': 28.0},
            # 2023
            {'anio': 2023, 'nivel_escolar': '4° Básico', 'asignatura': 'Lectura', 'puntaje_colegio': 264, 'puntaje_gse': 255, 'puntaje_nacional': 250, 'insuf': 20.0, 'elem': 45.0, 'adec': 35.0},
            {'anio': 2023, 'nivel_escolar': '4° Básico', 'asignatura': 'Matemática', 'puntaje_colegio': 254, 'puntaje_gse': 248, 'puntaje_nacional': 245, 'insuf': 28.0, 'elem': 44.0, 'adec': 28.0},
            # 2022
            {'anio': 2022, 'nivel_escolar': '4° Básico', 'asignatura': 'Lectura', 'puntaje_colegio': 258, 'puntaje_gse': 251, 'puntaje_nacional': 247, 'insuf': 26.0, 'elem': 46.0, 'adec': 28.0},
            {'anio': 2022, 'nivel_escolar': '4° Básico', 'asignatura': 'Matemática', 'puntaje_colegio': 248, 'puntaje_gse': 244, 'puntaje_nacional': 241, 'insuf': 34.0, 'elem': 42.0, 'adec': 24.0},
        ]
        for h in historicos:
            PuntajeHistoricoSIMCE.objects.create(
                colegio=colegio,
                anio=h['anio'],
                nivel_escolar=h['nivel_escolar'],
                asignatura=h['asignatura'],
                puntaje_colegio=h['puntaje_colegio'],
                puntaje_gse=h['puntaje_gse'],
                puntaje_nacional=h['puntaje_nacional'],
                nivel_insuficiente_pct=h['insuf'],
                nivel_elemental_pct=h['elem'],
                nivel_adecuado_pct=h['adec']
            )

    # 2. Ensayos Internos de ejemplo
    if not EnsayoSIMCE.objects.filter(colegio=colegio).exists():
        cursos = CursoColegio.objects.filter(colegio=colegio, activo=True)
        if cursos.exists():
            curso_sample = cursos.first()
            ensayos_seed = [
                {'titulo': f"1° Ensayo SIMCE Matemática - {curso_sample.nombre}", 'asig': 'matematica', 'preg': 35},
                {'titulo': f"1° Ensayo SIMCE Lectura - {curso_sample.nombre}", 'asig': 'lectura', 'preg': 30},
            ]
            estudiantes = Estudiante.objects.filter(seccion__curso=curso_sample, activo=True)

            for item in ensayos_seed:
                ens = EnsayoSIMCE.objects.create(
                    colegio=colegio,
                    titulo=item['titulo'],
                    asignatura=item['asig'],
                    curso=curso_sample,
                    fecha=timezone.now().date(),
                    total_preguntas=item['preg'],
                    creado_por=user,
                    descripcion="Simulacro institucional de diagnóstico para nivelación y refuerzo UTP."
                )
                for est in estudiantes:
                    correctas = random.randint(int(item['preg'] * 0.4), item['preg'])
                    res = ResultadoEnsayoSIMCE(
                        ensayo=ens,
                        estudiante=est,
                        respuestas_correctas=correctas
                    )
                    res.calcular_puntaje_y_nivel()
                    res.save()


@login_required
def simce_dashboard_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director', 'UTP'])
    )

    from .models import EnsayoSIMCE, ResultadoEnsayoSIMCE, PuntajeHistoricoSIMCE, CursoColegio

    # Inicializar datos demo si está vacío
    inicializar_datos_simce_demo(colegio, request.user)

    # Filtros
    asignatura_filtro = request.GET.get('asignatura', '')
    curso_filtro = request.GET.get('curso', '')

    ensayos_qs = EnsayoSIMCE.objects.filter(colegio=colegio).select_related('curso', 'creado_por').prefetch_related('resultados')
    if asignatura_filtro:
        ensayos_qs = ensayos_qs.filter(asignatura=asignatura_filtro)
    if curso_filtro:
        ensayos_qs = ensayos_qs.filter(curso_id=curso_filtro)

    # Métricas Globales de Ensayos
    todos_ensayos = EnsayoSIMCE.objects.filter(colegio=colegio).prefetch_related('resultados')
    total_ensayos = todos_ensayos.count()
    
    todos_resultados = ResultadoEnsayoSIMCE.objects.filter(ensayo__colegio=colegio)
    total_evaluados = todos_resultados.count()
    
    if todos_resultados.exists():
        promedio_general_simce = round(sum(r.puntaje_simce for r in todos_resultados) / total_evaluados)
        promedio_logro_general = round(sum(r.porcentaje_logro for r in todos_resultados) / total_evaluados, 1)
        total_insuficientes = todos_resultados.filter(nivel_aprendizaje='insuficiente').count()
        total_elementales = todos_resultados.filter(nivel_aprendizaje='elemental').count()
        total_adecuados = todos_resultados.filter(nivel_aprendizaje='adecuado').count()
        pct_insuficiente = round((total_insuficientes / total_evaluados) * 100, 1)
        pct_elemental = round((total_elementales / total_evaluados) * 100, 1)
        pct_adecuado = round((total_adecuados / total_evaluados) * 100, 1)
    else:
        promedio_general_simce = 0
        promedio_logro_general = 0.0
        total_insuficientes = total_elementales = total_adecuados = 0
        pct_insuficiente = pct_elemental = pct_adecuado = 0.0

    # Histórico Oficial
    historicos = PuntajeHistoricoSIMCE.objects.filter(colegio=colegio).order_by('-anio', 'nivel_escolar', 'asignatura')
    
    # Preparar datos JSON para gráficos
    # 1. Gráfico Histórico Oficial
    hist_recientes = list(historicos[:8])
    hist_recientes.reverse()
    chart_labels = [f"{h.anio} {h.nivel_escolar} ({h.asignatura[:3]})" for h in hist_recientes]
    chart_colegio = [h.puntaje_colegio for h in hist_recientes]
    chart_gse = [h.puntaje_gse for h in hist_recientes]
    chart_nacional = [h.puntaje_nacional for h in hist_recientes]

    # Cursos disponibles para crear nuevo ensayo
    cursos_colegio = CursoColegio.objects.filter(colegio=colegio, activo=True).order_by('nivel', 'nombre')

    # Estudiantes en Nivel Insuficiente (Riesgo Pedagógico)
    alumnos_riesgo = ResultadoEnsayoSIMCE.objects.filter(
        ensayo__colegio=colegio,
        nivel_aprendizaje='insuficiente'
    ).select_related('estudiante', 'estudiante__seccion', 'ensayo').order_by('puntaje_simce')[:20]

    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'simce',
        'hoy': timezone.now(),
        'ensayos': ensayos_qs,
        'total_ensayos': total_ensayos,
        'total_evaluados': total_evaluados,
        'promedio_general_simce': promedio_general_simce,
        'promedio_logro_general': promedio_logro_general,
        'pct_insuficiente': pct_insuficiente,
        'pct_elemental': pct_elemental,
        'pct_adecuado': pct_adecuado,
        'total_insuficientes': total_insuficientes,
        'total_elementales': total_elementales,
        'total_adecuados': total_adecuados,
        'historicos': historicos,
        'cursos_colegio': cursos_colegio,
        'asignaturas_choices': EnsayoSIMCE.ASIGNATURAS_SIMCE,
        'asignatura_filtro': asignatura_filtro,
        'curso_filtro': curso_filtro,
        'chart_labels': json.dumps(chart_labels),
        'chart_colegio': json.dumps(chart_colegio),
        'chart_gse': json.dumps(chart_gse),
        'chart_nacional': json.dumps(chart_nacional),
        'alumnos_riesgo': alumnos_riesgo,
    }
    return render(request, 'colegios/simce_dashboard.html', context)


@login_required
def crear_ensayo_simce_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import EnsayoSIMCE, ResultadoEnsayoSIMCE, CursoColegio, Estudiante

        titulo = request.POST.get('titulo', '').strip()
        asignatura = request.POST.get('asignatura', 'matematica')
        curso_id = request.POST.get('curso')
        fecha_str = request.POST.get('fecha')
        total_preguntas = int(request.POST.get('total_preguntas', 35))
        descripcion = request.POST.get('descripcion', '').strip()

        curso = get_object_or_404(CursoColegio, id=curso_id, colegio=colegio)
        
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()
        except ValueError:
            fecha_obj = timezone.now().date()

        ensayo = EnsayoSIMCE.objects.create(
            colegio=colegio,
            titulo=titulo,
            asignatura=asignatura,
            curso=curso,
            fecha=fecha_obj,
            total_preguntas=total_preguntas,
            descripcion=descripcion,
            creado_por=request.user
        )

        # Generar automáticamente filas vacías de resultados para los estudiantes del curso
        estudiantes = Estudiante.objects.filter(seccion__curso=curso, activo=True).order_by('nombre_completo')
        for est in estudiantes:
            ResultadoEnsayoSIMCE.objects.get_or_create(
                ensayo=ensayo,
                estudiante=est,
                defaults={
                    'respuestas_correctas': 0,
                    'porcentaje_logro': 0.0,
                    'puntaje_simce': 150,
                    'nivel_aprendizaje': 'insuficiente'
                }
            )

        messages.success(request, f"¡Ensayo '{titulo}' creado con éxito! Ya puedes registrar los resultados.")
        return redirect('detalle_ensayo_simce', ensayo_id=ensayo.id)

    return redirect('simce_dashboard')


@login_required
def detalle_ensayo_simce_view(request, ensayo_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('solicitar_acceso')

    miembro = MiembroColegio.objects.filter(usuario=request.user, colegio=colegio, activo=True).first()
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    is_admin = (
        request.user.colegios_administrados.filter(id=colegio.id).exists()
        or (miembro and miembro.rol and miembro.rol.nombre in ['Administrador', 'Director', 'UTP'])
    )

    from .models import EnsayoSIMCE, ResultadoEnsayoSIMCE, Estudiante

    ensayo = get_object_or_404(EnsayoSIMCE, id=ensayo_id, colegio=colegio)
    
    # Asegurar que todos los alumnos del curso tengan fila en el ensayo
    alumnos_curso = Estudiante.objects.filter(seccion__curso=ensayo.curso, activo=True)
    for al in alumnos_curso:
        ResultadoEnsayoSIMCE.objects.get_or_create(
            ensayo=ensayo,
            estudiante=al,
            defaults={'respuestas_correctas': 0, 'puntaje_simce': 150, 'nivel_aprendizaje': 'insuficiente'}
        )

    resultados = ResultadoEnsayoSIMCE.objects.filter(ensayo=ensayo).select_related('estudiante', 'estudiante__seccion').order_by('estudiante__nombre_completo')
    
    context = {
        'colegio': colegio,
        'miembro': miembro,
        'periodo': periodo,
        'is_admin': is_admin,
        'active_page': 'simce',
        'hoy': timezone.now(),
        'ensayo': ensayo,
        'resultados': resultados,
        'desglose': ensayo.desglose_niveles,
    }
    return render(request, 'colegios/detalle_ensayo_simce.html', context)


@login_required
def guardar_resultados_ensayo_view(request, ensayo_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import EnsayoSIMCE, ResultadoEnsayoSIMCE

    ensayo = get_object_or_404(EnsayoSIMCE, id=ensayo_id, colegio=colegio)

    if request.method == 'POST':
        resultados = ResultadoEnsayoSIMCE.objects.filter(ensayo=ensayo).select_related('estudiante')
        for res in resultados:
            correctas_str = request.POST.get(f'correctas_{res.id}', '0')
            obs = request.POST.get(f'obs_{res.id}', '').strip()

            try:
                correctas = int(correctas_str)
            except ValueError:
                correctas = 0

            # Validar que no supere el total de preguntas
            if correctas > ensayo.total_preguntas:
                correctas = ensayo.total_preguntas
            if correctas < 0:
                correctas = 0

            res.respuestas_correctas = correctas
            res.observaciones = obs
            res.calcular_puntaje_y_nivel()
            res.save()

        messages.success(request, f"¡Resultados del ensayo '{ensayo.titulo}' guardados y recalculados exitosamente!")
        return redirect('detalle_ensayo_simce', ensayo_id=ensayo.id)

    return redirect('detalle_ensayo_simce', ensayo_id=ensayo.id)


@login_required
def eliminar_ensayo_simce_view(request, ensayo_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import EnsayoSIMCE
    ensayo = get_object_or_404(EnsayoSIMCE, id=ensayo_id, colegio=colegio)
    titulo = ensayo.titulo
    ensayo.delete()
    messages.info(request, f"Ensayo '{titulo}' eliminado correctamente.")
    return redirect('simce_dashboard')


@login_required
def crear_historico_simce_view(request):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    if request.method == 'POST':
        from .models import PuntajeHistoricoSIMCE

        anio = int(request.POST.get('anio', 2024))
        nivel_escolar = request.POST.get('nivel_escolar', '4° Básico').strip()
        asignatura = request.POST.get('asignatura', 'Lectura').strip()
        puntaje_colegio = int(request.POST.get('puntaje_colegio', 250))
        puntaje_gse = int(request.POST.get('puntaje_gse', 250))
        puntaje_nacional = int(request.POST.get('puntaje_nacional', 250))
        
        try:
            insuf = float(request.POST.get('nivel_insuficiente_pct', 20.0))
            elem = float(request.POST.get('nivel_elemental_pct', 45.0))
            adec = float(request.POST.get('nivel_adecuado_pct', 35.0))
        except ValueError:
            insuf, elem, adec = 20.0, 45.0, 35.0

        PuntajeHistoricoSIMCE.objects.create(
            colegio=colegio,
            anio=anio,
            nivel_escolar=nivel_escolar,
            asignatura=asignatura,
            puntaje_colegio=puntaje_colegio,
            puntaje_gse=puntaje_gse,
            puntaje_nacional=puntaje_nacional,
            nivel_insuficiente_pct=insuf,
            nivel_elemental_pct=elem,
            nivel_adecuado_pct=adec
        )

        messages.success(request, f"¡Puntaje histórico SIMCE {anio} ({nivel_escolar} - {asignatura}) agregado!")
    return redirect('simce_dashboard')


@login_required
def eliminar_historico_simce_view(request, historico_id):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    from .models import PuntajeHistoricoSIMCE
    hist = get_object_or_404(PuntajeHistoricoSIMCE, id=historico_id, colegio=colegio)
    hist.delete()
    messages.info(request, "Registro histórico SIMCE eliminado.")
    return redirect('simce_dashboard')


@login_required
def exportar_simce_excel_view(request, ensayo_id=None):
    colegio = obtener_colegio_usuario(request.user)
    if not colegio:
        return redirect('dashboard_usuario')

    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from .models import EnsayoSIMCE, ResultadoEnsayoSIMCE, PuntajeHistoricoSIMCE

    wb = openpyxl.Workbook()

    # Estilos
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="7C5CFC", end_color="7C5CFC", fill_type="solid")
    title_font = Font(name="Arial", size=14, bold=True, color="151A35")
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    if ensayo_id:
        # Exportar Ensayo Específico
        ensayo = get_object_or_404(EnsayoSIMCE, id=ensayo_id, colegio=colegio)
        ws = wb.active
        ws.title = "Resultados Ensayo"

        ws.append([f"INFORME DE ENSAYO SIMCE: {ensayo.titulo}"])
        ws.append([f"Establecimiento: {colegio.nombre} | Curso: {ensayo.curso.nombre} | Fecha: {ensayo.fecha.strftime('%d/%m/%Y')}"])
        ws.append([f"Promedio SIMCE: {ensayo.promedio_puntaje} pts | Promedio Logro: {ensayo.promedio_logro}% | Preguntas: {ensayo.total_preguntas}"])
        ws.append([])

        ws.cell(row=1, column=1).font = title_font

        headers = ["N°", "Estudiante", "Sección", "RUT", "Resp. Correctas", "% Logro", "Puntaje SIMCE", "Nivel de Aprendizaje", "Observaciones"]
        ws.append(headers)

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=5, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        resultados = ResultadoEnsayoSIMCE.objects.filter(ensayo=ensayo).select_related('estudiante', 'estudiante__seccion').order_by('estudiante__nombre_completo')
        
        for idx, r in enumerate(resultados, 1):
            sec_nombre = r.estudiante.seccion.nombre if r.estudiante.seccion else "-"
            ws.append([
                idx,
                r.estudiante.nombre_completo,
                sec_nombre,
                r.estudiante.rut or "-",
                r.respuestas_correctas,
                f"{r.porcentaje_logro}%",
                r.puntaje_simce,
                r.get_nivel_aprendizaje_display(),
                r.observaciones or ""
            ])

        for row in ws.iter_rows(min_row=5, max_row=ws.max_row, min_col=1, max_col=len(headers)):
            for cell in row:
                cell.border = thin_border

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

        filename = f"SIMCE_{ensayo.curso.nombre}_{ensayo.asignatura}_{ensayo.fecha.strftime('%Y%m%d')}.xlsx"
    else:
        # Exportar Resumen General del Colegio
        ws1 = wb.active
        ws1.title = "Ensayos Internos"
        ws1.append([f"RESUMEN GENERAL DE ENSAYOS SIMCE - {colegio.nombre}"])
        ws1.append([f"Fecha de Exportación: {timezone.now().strftime('%d/%m/%Y %H:%M')}"])
        ws1.append([])

        headers1 = ["ID", "Título del Ensayo", "Asignatura", "Curso", "Fecha", "N° Preguntas", "Alumnos Evaluados", "Promedio SIMCE", "% Logro", "% Insuficiente", "% Elemental", "% Adecuado"]
        ws1.append(headers1)
        for col_num in range(1, len(headers1) + 1):
            cell = ws1.cell(row=4, column=col_num)
            cell.font = header_font
            cell.fill = header_fill

        ensayos = EnsayoSIMCE.objects.filter(colegio=colegio).select_related('curso').prefetch_related('resultados')
        for e in ensayos:
            d = e.desglose_niveles
            ws1.append([
                e.id,
                e.titulo,
                e.get_asignatura_display(),
                e.curso.nombre,
                e.fecha.strftime('%d/%m/%Y'),
                e.total_preguntas,
                e.total_rendidos,
                e.promedio_puntaje,
                f"{e.promedio_logro}%",
                f"{d['pct_insuficiente']}%",
                f"{d['pct_elemental']}%",
                f"{d['pct_adecuado']}%"
            ])

        for col in ws1.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws1.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # Hoja 2: Histórico Oficial
        ws2 = wb.create_sheet(title="Histórico Oficial Agencia")
        ws2.append([f"HISTORIAL OFICIAL DE RESULTADOS SIMCE - {colegio.nombre}"])
        ws2.append([])

        headers2 = ["Año", "Nivel Escolar", "Asignatura", "Puntaje Colegio", "Promedio GSE", "Promedio Nacional", "Diferencia vs GSE", "% Insuficiente", "% Elemental", "% Adecuado"]
        ws2.append(headers2)
        for col_num in range(1, len(headers2) + 1):
            cell = ws2.cell(row=3, column=col_num)
            cell.font = header_font
            cell.fill = header_fill

        historicos = PuntajeHistoricoSIMCE.objects.filter(colegio=colegio)
        for h in historicos:
            diff = h.puntaje_colegio - h.puntaje_gse
            sign = "+" if diff > 0 else ""
            ws2.append([
                h.anio,
                h.nivel_escolar,
                h.asignatura,
                h.puntaje_colegio,
                h.puntaje_gse,
                h.puntaje_nacional,
                f"{sign}{diff} pts",
                f"{h.nivel_insuficiente_pct}%",
                f"{h.nivel_elemental_pct}%",
                f"{h.nivel_adecuado_pct}%"
            ])

        for col in ws2.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws2.column_dimensions[col_letter].width = max(max_len + 3, 12)

        filename = f"SIMCE_Informe_General_{colegio.nombre.replace(' ', '_')}.xlsx"

    from django.http import HttpResponse
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response
