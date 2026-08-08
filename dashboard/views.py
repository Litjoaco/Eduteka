from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from solicitudes.models import SolicitudAcceso, MiembroColegio
from colegios.models import Colegio, ColegioModulo, RolColegio, Estudiante, CursoColegio, Suscripcion
from planes.models import Plan

from django.contrib.auth.models import User
from django.utils import timezone
import csv
from django.http import HttpResponse
from datetime import datetime

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

def dashboard_superadmin_view(request):
    return render(request, 'dashboard_superadmin.html')

def dashboard_superadmin_colegios_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        contacto = request.POST.get('contacto', 'Sin Contacto')
        email = request.POST.get('email', 'admin@colegio.cl')
        direccion = request.POST.get('direccion', '')
        
        # Mapeo simple de cantidad de alumnos al choice del modelo
        alumnos_raw = request.POST.get('alumnos', '0')
        try:
            num_alumnos = int(alumnos_raw)
        except ValueError:
            num_alumnos = 0
            
        if num_alumnos < 100:
            cantidad_alumnos = 'menos_100'
        elif num_alumnos <= 300:
            cantidad_alumnos = '100_300'
        elif num_alumnos <= 600:
            cantidad_alumnos = '301_600'
        else:
            cantidad_alumnos = 'mas_600'

        Colegio.objects.create(
            nombre=nombre,
            nombre_administrador=contacto,
            correo_institucional=email,
            direccion=direccion,
            telefono='000000000', # Dummy
            ciudad_comuna='Santiago', # Dummy
            tipo_institucion='particular', # Dummy
            cantidad_alumnos=cantidad_alumnos,
            estado='activo',
            configuracion_completa=True
        )
        messages.success(request, 'Colegio creado exitosamente.')
        return redirect('dashboard_superadmin_colegios')

    colegios = Colegio.objects.all().order_by('-fecha_creacion')
    return render(request, 'dashboard_superadmin_colegios.html', {'colegios': colegios})

def dashboard_superadmin_planes_view(request):
    from planes.models import Plan
    planes = Plan.objects.all()
    if not planes.exists():
        Plan.objects.create(nombre="Plan Básico", precio_mensual=150000, precio_anual=1500000, descripcion="Libro de Clases, Asistencia y Anotaciones.")
        Plan.objects.create(nombre="Plan Estándar", precio_mensual=250000, precio_anual=2500000, recomendado=True, descripcion="Incluye Contabilidad y Reportes.")
        Plan.objects.create(nombre="Plan Premium", precio_mensual=400000, precio_anual=4000000, descripcion="Acceso Total con SIMCE y Mercado Público.")
        planes = Plan.objects.all()
    return render(request, 'dashboard_superadmin_planes.html', {'planes': planes})


def dashboard_superadmin_facturacion_view(request):
    """
    Vista del panel de Facturación y SII.
    Soporta filtrado por estado de pago, mes de emisión y búsqueda por folio/colegio.
    Si se recibe el parámetro ?exportar=true, descarga un CSV con los resultados filtrados.
    """
    # --- Datos de demostración (reemplazar con QuerySet real cuando exista el modelo) ---
    facturas_demo = [
        {'folio': 'F-8492', 'colegio': 'Liceo Santa María',               'tipo': 'Factura Electrónica Exenta', 'monto': '$400.000 CLP', 'fecha': '2026-08-01', 'estado_sii': 'Aceptado', 'estado_pago': 'pagado'},
        {'folio': 'F-8491', 'colegio': 'Colegio Los Alerces',             'tipo': 'Factura Electrónica Exenta', 'monto': '$250.000 CLP', 'fecha': '2026-07-28', 'estado_sii': 'Aceptado', 'estado_pago': 'pendiente'},
        {'folio': 'F-8490', 'colegio': 'Instituto Profesional del Norte', 'tipo': 'Factura Electrónica Exenta', 'monto': '$650.000 CLP', 'fecha': '2026-07-15', 'estado_sii': 'Aceptado', 'estado_pago': 'vencido'},
        {'folio': 'F-8489', 'colegio': 'Colegio San Agustín',            'tipo': 'Factura Electrónica Exenta', 'monto': '$320.000 CLP', 'fecha': '2026-08-02', 'estado_sii': 'En envío', 'estado_pago': 'pendiente'},
        {'folio': 'F-8488', 'colegio': 'Escuela Básica El Porvenir',     'tipo': 'Factura Electrónica Exenta', 'monto': '$180.000 CLP', 'fecha': '2026-08-01', 'estado_sii': 'Aceptado', 'estado_pago': 'pagado'},
    ]

    # --- Captura de parámetros GET ---
    estado = request.GET.get('estado', '').strip()
    mes    = request.GET.get('mes', '').strip()   # formato "YYYY-MM"
    q      = request.GET.get('q', '').strip()

    # --- Filtrado dinámico sobre la lista de demo ---
    facturas = facturas_demo

    if estado:
        facturas = [f for f in facturas if f['estado_pago'] == estado]

    if mes:
        # mes viene como "2026-08"; comparamos con los 7 primeros caracteres de la fecha ISO
        facturas = [f for f in facturas if f['fecha'].startswith(mes)]

    if q:
        q_lower = q.lower()
        facturas = [
            f for f in facturas
            if q_lower in f['folio'].lower() or q_lower in f['colegio'].lower()
        ]

    # --- Exportación a CSV ---
    if request.GET.get('exportar') == 'true':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="historial_facturas.csv"'

        # BOM para que Excel (Windows) abra el CSV con tildes correctamente
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow(['Folio DTE', 'Colegio', 'Tipo Documento', 'Monto Total', 'Fecha Emisión', 'Estado SII', 'Estado de Pago'])
        for f in facturas:
            writer.writerow([
                f['folio'],
                f['colegio'],
                f['tipo'],
                f['monto'],
                f['fecha'],
                f['estado_sii'],
                f['estado_pago'].capitalize(),
            ])
        return response

    # --- Contexto para el template ---
    context = {
        'facturas': facturas,
        'filtros': {
            'estado': estado,
            'mes': mes,
            'q': q,
        },
    }
    return render(request, 'dashboard_superadmin_facturacion.html', context)

def dashboard_superadmin_ordenes_view(request):
    return render(request, 'dashboard_superadmin_ordenes.html')

def dashboard_superadmin_configuracion_view(request):
    return render(request, 'dashboard_superadmin_configuracion.html')

def dashboard_superadmin_estadisticas_view(request):
    """
    Vista del Centro de Inteligencia de Negocios / Estadísticas Globales.
    Soporta filtrado por fecha_desde, fecha_hasta, plan y region.
    Permite exportar los resultados filtrados a CSV.
    """
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    plan_filtro = request.GET.get('plan', '').strip()
    region_filtro = request.GET.get('region', '').strip()
    exportar = request.GET.get('exportar', '').strip()

    # QuerySet base
    colegios = Colegio.objects.all().select_related('suscripcion', 'suscripcion__plan').annotate(
        estudiantes_count=Count('estudiantes')
    )

    # Filtrado dinámico por rango de fecha de creación
    if fecha_desde and fecha_hasta:
        colegios = colegios.filter(fecha_creacion__date__range=[fecha_desde, fecha_hasta])
    elif fecha_desde:
        colegios = colegios.filter(fecha_creacion__date__gte=fecha_desde)
    elif fecha_hasta:
        colegios = colegios.filter(fecha_creacion__date__lte=fecha_hasta)

    # Filtrado por plan (ID o nombre)
    if plan_filtro:
        if plan_filtro.isdigit():
            colegios = colegios.filter(suscripcion__plan_id=int(plan_filtro))
        else:
            colegios = colegios.filter(
                Q(suscripcion__plan__nombre__iexact=plan_filtro) |
                Q(suscripcion__plan__nombre__icontains=plan_filtro)
            )

    # Filtrado por región
    if region_filtro:
        colegios = colegios.filter(region__iexact=region_filtro)

    # Exportación a CSV
    if exportar == 'true':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="reporte_estadisticas_colegios.csv"'
        response.write('\ufeff')  # BOM UTF-8 para Excel

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Nombre Colegio', 'Administrador', 'Correo Institucional',
            'Región', 'Ciudad/Comuna', 'Tipo Institución', 'Plan', 'Estado',
            'Cant. Estudiantes', 'Fecha Creación'
        ])
        for col in colegios:
            plan_nombre = col.suscripcion.plan.nombre if hasattr(col, 'suscripcion') and col.suscripcion and col.suscripcion.plan else 'Sin Plan'
            writer.writerow([
                col.id,
                col.nombre,
                col.nombre_administrador,
                col.correo_institucional,
                col.region or '',
                col.ciudad_comuna or '',
                col.get_tipo_institucion_display() if hasattr(col, 'get_tipo_institucion_display') else col.tipo_institucion,
                plan_nombre,
                col.get_estado_display() if hasattr(col, 'get_estado_display') else col.estado,
                col.estudiantes_count,
                col.fecha_creacion.strftime('%Y-%m-%d %H:%M') if col.fecha_creacion else ''
            ])
        return response

    # Recálculo dinámico de KPIs
    total_colegios_count = colegios.count()
    colegios_activos = colegios.filter(estado='activo').count()
    alumnos_totales = Estudiante.objects.filter(colegio__in=colegios).count()

    # MRR Proyectado (suma de suscripciones activas en el QuerySet filtrado)
    mrr_val = colegios.filter(suscripcion__estado='activa').aggregate(
        total=Sum('suscripcion__monto')
    )['total'] or 0

    if mrr_val >= 1_000_000:
        mrr_formatted = f"${mrr_val / 1_000_000:.1f}M"
    elif mrr_val > 0:
        mrr_formatted = f"${mrr_val:,.0f} CLP"
    else:
        mrr_formatted = "$0 CLP"

    # Tasa de Churn (inactivos o suspendidos / total)
    colegios_inactivos = colegios.filter(estado__in=['inactivo', 'suspendido']).count()
    churn_rate = (colegios_inactivos / total_colegios_count * 100) if total_colegios_count > 0 else 0.0

    kpis = {
        'colegios_activos': colegios_activos if total_colegios_count > 0 else 0,
        'alumnos_total': f"{alumnos_totales:,}".replace(',', '.') if alumnos_totales > 0 else "0",
        'mrr_proyectado': mrr_formatted,
        'tasa_churn': f"{churn_rate:.1f}%",
        'total_colegios': total_colegios_count,
    }

    # Top 5 colegios según total de estudiantes
    top_colegios = colegios.order_by('-estudiantes_count', '-fecha_creacion')[:5]

    # Colección de planes para el select
    planes = Plan.objects.filter(activo=True)

    # Colección de regiones disponibles
    regiones_bd = Colegio.objects.exclude(region__isnull=True).exclude(region='').values_list('region', flat=True).distinct()
    regiones_list = sorted(list(set(list(regiones_bd) + [
        "Región Metropolitana", "Valparaíso", "Biobío", "La Araucanía",
        "Los Lagos", "Antofagasta", "O'Higgins", "Maule", "Los Ríos",
        "Coquimbo", "Atacama", "Tarapacá", "Aysén", "Magallanes",
        "Arica y Parinacota", "Ñuble"
    ])))

    context = {
        'kpis': kpis,
        'filtros': {
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'plan': plan_filtro,
            'region': region_filtro,
        },
        'planes': planes,
        'regiones': regiones_list,
        'top_colegios': top_colegios,
    }
    return render(request, 'dashboard_superadmin_estadisticas.html', context)

def dashboard_superadmin_modulos_erp_view(request):
    return render(request, 'dashboard_superadmin_modulos_erp.html')

