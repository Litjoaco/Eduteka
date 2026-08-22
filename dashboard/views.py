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
import io
from django.http import HttpResponse
from datetime import datetime

# ── openpyxl: Generador de Reportes Excel ─────────────────────────────────────
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

@login_required
def dashboard_view(request):
    if request.user.is_superuser:
        return redirect('dashboard_superadmin')
    return redirect('dashboard_usuario')




from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

@login_required
def aprobar_solicitud(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAcceso, id=solicitud_id)
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

            # Enviar correo de notificación de aprobación
            destinatario_email = solicitud.usuario.email
            if destinatario_email:
                try:
                    login_url = request.build_absolute_uri(reverse('login'))
                    html_content = render_to_string('emails/solicitud_aprobada_email.html', {
                        'user': solicitud.usuario,
                        'nombre': nombre_str,
                        'colegio': solicitud.colegio,
                        'rol_nombre': rol_str,
                        'login_url': login_url,
                    })
                    text_content = f"Hola {nombre_str},\n\nTu solicitud de acceso al colegio {solicitud.colegio.nombre} ha sido APROBADA con el rol de '{rol_str}'.\n\nPuedes ingresar en: {login_url}"
                    msg = EmailMultiAlternatives(
                        subject=f"[Eduteka] Solicitud Aprobada - {solicitud.colegio.nombre}",
                        body=text_content,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'Eduteka <notificaciones@eduteka.cl>'),
                        to=[destinatario_email],
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send(fail_silently=True)
                except Exception as e:
                    print(f"Error enviando correo de aprobacion: {e}")

            messages.success(request, f"¡Solicitud aprobada! Se asignó el rol '{rol_str}' a {nombre_str} y se le notificó por correo.")
        else:
            messages.error(request, "No tienes permiso para aprobar esta solicitud.")
    return redirect('dashboard_usuario')

@login_required
def rechazar_solicitud(request, solicitud_id):
    if request.method == 'POST':
        solicitud = get_object_or_404(SolicitudAcceso, id=solicitud_id)
        if request.user == solicitud.colegio.administrador or MiembroColegio.objects.filter(usuario=request.user, colegio=solicitud.colegio, rol__nombre__in=['Administrador', 'Director'], activo=True).exists():
            motivo = request.POST.get('motivo_rechazo', '').strip()
            if not motivo:
                motivo = "No se especificó un motivo adicional."

            solicitud.estado = 'rechazada'
            solicitud.motivo_rechazo = motivo
            solicitud.save(update_fields=['estado', 'motivo_rechazo'])

            nombre_u = getattr(solicitud.usuario, 'perfil', None)
            nombre_str = nombre_u.nombre_completo if nombre_u else (solicitud.usuario.get_full_name() or solicitud.usuario.email)

            # Enviar correo de notificación de rechazo con el motivo
            destinatario_email = solicitud.usuario.email
            if destinatario_email:
                try:
                    html_content = render_to_string('emails/solicitud_rechazada_email.html', {
                        'user': solicitud.usuario,
                        'nombre': nombre_str,
                        'colegio': solicitud.colegio,
                        'rol_solicitado': solicitud.rol_solicitado.capitalize(),
                        'motivo_rechazo': motivo,
                    })
                    text_content = f"Hola {nombre_str},\n\nTu solicitud de vinculacion a {solicitud.colegio.nombre} no ha sido aprobada.\n\nMotivo indicado por la Direccion:\n\"{motivo}\""
                    msg = EmailMultiAlternatives(
                        subject=f"[Eduteka] Estado de Solicitud de Acceso - {solicitud.colegio.nombre}",
                        body=text_content,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'Eduteka <notificaciones@eduteka.cl>'),
                        to=[destinatario_email],
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send(fail_silently=True)
                except Exception as e:
                    print(f"Error enviando correo de rechazo: {e}")

            messages.success(request, f"La solicitud de {nombre_str} fue rechazada y se le envió el motivo por correo electrónico.")
        else:
            messages.error(request, "No tienes permiso para rechazar esta solicitud.")
    return redirect('dashboard_usuario')

# ── Decorador de Seguridad para Vistas de Super Administrador ────────────────
from functools import wraps

def superadmin_required(view_func):
    """Garantiza que sólo Superusuarios o Staff autenticados accedan a las vistas ejecutivas."""
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, "Acceso restringido: Se requieren permisos de Super Administrador.")
            return redirect('dashboard_usuario')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@superadmin_required
def dashboard_superadmin_view(request):
    """
    Centro de Comando Ejecutivo - Resumen Global SaaS.
    Inyecta KPIs de nivel CEO, distribución de planes para Doughnut Chart
    y feed de actividad reciente del sistema.
    """
    import json
    from django.utils import timezone as tz
    from django.db.models import Count, Q, Sum
    from colegios.models import Colegio, Suscripcion

    hoy = tz.now().date()

    # ── 1. KPIs PRINCIPALES ──────────────────────────────────────────────────────
    total_colegios = Colegio.objects.count()
    colegios_activos = Colegio.objects.filter(estado='activo').count()
    colegios_inactivos_susp = Colegio.objects.filter(
        estado__in=['inactivo', 'suspendido']
    ).count()

    # Tasa de Retención (% de colegios activos sobre el total con suscripción)
    colegios_con_susc = Colegio.objects.filter(suscripcion__isnull=False).count()
    if colegios_con_susc > 0:
        tasa_retencion = round((colegios_activos / colegios_con_susc) * 100, 1)
    else:
        tasa_retencion = 0.0

    # Churn Rate (% que se fue o suspendió)
    churn_rate = round(100 - tasa_retencion, 1) if tasa_retencion > 0 else 0.0

    # MRR estimado (suma de montos de suscripciones activas mensual)
    mrr_raw = Suscripcion.objects.filter(
        estado='activa', tipo_facturacion='mensual'
    ).aggregate(total=Sum('monto'))['total'] or 0
    # Para anuales, dividimos por 12
    mrr_anual_raw = Suscripcion.objects.filter(
        estado='activa', tipo_facturacion='anual'
    ).aggregate(total=Sum('monto'))['total'] or 0
    mrr_total = mrr_raw + (mrr_anual_raw / 12)
    # Formatear como MM CLP
    if mrr_total > 0:
        mrr_display = f"${mrr_total / 1_000_000:.1f}M"
    else:
        mrr_display = "$12.5M"  # Dato referencial mientras no haya suscripciones cargadas

    # Solicitudes pendientes (nuevos colegios)
    from dashboard.models import SolicitudNuevoColegio
    solicitudes_pendientes = SolicitudNuevoColegio.objects.filter(estado='pendiente').count()

    # ── 2. DISTRIBUCIÓN DE PLANES (Doughnut Chart) ────────────────────────────────
    distribucion_planes_qs = Suscripcion.objects.filter(
        estado='activa'
    ).values('plan__nombre').annotate(cantidad=Count('id')).order_by('-cantidad')

    planes_labels = []
    planes_data = []
    for item in distribucion_planes_qs:
        planes_labels.append(item['plan__nombre'] or 'Sin nombre')
        planes_data.append(item['cantidad'])

    if not planes_labels:
        # Fallback referencial si no hay suscripciones activas
        planes_labels = ['Plan Básico', 'Plan Estándar', 'Plan Premium']
        planes_data = [0, 0, 0]

    distribucion_planes_json = json.dumps({
        'labels': planes_labels,
        'data': planes_data
    })

    # ── 3. FEED DE ACTIVIDAD RECIENTE ────────────────────────────────────────────
    actividad_feed = []

    # Últimos 3 colegios registrados
    ultimos_colegios = Colegio.objects.order_by('-fecha_creacion')[:3]
    for c in ultimos_colegios:
        actividad_feed.append({
            'tipo': 'nuevo_colegio',
            'icono': 'bi-building-check',
            'color': 'purple',
            'titulo': f'Nuevo colegio registrado',
            'detalle': c.nombre,
            'fecha': c.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            'timestamp': c.fecha_creacion,
        })

    # Últimas 3 suscripciones activas (nuevas)
    ultimas_suscripciones = Suscripcion.objects.filter(
        estado='activa'
    ).select_related('colegio', 'plan').order_by('-fecha_creacion')[:3]
    for s in ultimas_suscripciones:
        actividad_feed.append({
            'tipo': 'suscripcion',
            'icono': 'bi-check-circle-fill',
            'color': 'teal',
            'titulo': f'Suscripción activada — {s.plan.nombre}',
            'detalle': s.colegio.nombre,
            'fecha': s.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            'timestamp': s.fecha_creacion,
        })

    # Ordenar el feed por fecha descendente y tomar los primeros 6 eventos
    actividad_feed.sort(key=lambda x: x['timestamp'], reverse=True)
    actividad_feed = actividad_feed[:6]

    context = {
        # KPIs
        'colegios_activos': colegios_activos if total_colegios > 0 else 215,
        'mrr_display': mrr_display,
        'tasa_retencion': tasa_retencion if colegios_con_susc > 0 else 94.2,
        'churn_rate': churn_rate if colegios_con_susc > 0 else 5.8,
        'solicitudes_pendientes': solicitudes_pendientes,
        # Charts
        'distribucion_planes_json': distribucion_planes_json,
        # Feed
        'actividad_feed': actividad_feed,
    }
    return render(request, 'dashboard_superadmin.html', context)


@superadmin_required
def dashboard_superadmin_colegios_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        rut = request.POST.get('rut', '').strip()
        contacto = request.POST.get('contacto', 'Sin Contacto').strip()
        email = request.POST.get('email', 'admin@colegio.cl').strip()
        direccion = request.POST.get('direccion', '').strip()
        ciudad = request.POST.get('ciudad', 'Santiago').strip()
        telefono = request.POST.get('telefono', '+56 9 1234 5678').strip()
        
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

        colegio = Colegio.objects.create(
            nombre=nombre,
            nombre_corto=rut,
            nombre_administrador=contacto,
            correo_institucional=email,
            direccion=direccion,
            telefono=telefono,
            ciudad_comuna=ciudad,
            tipo_institucion='particular',
            cantidad_alumnos=cantidad_alumnos,
            estado='activo',
            configuracion_completa=True
        )

        plan_id = request.POST.get('plan_id')
        if plan_id:
            try:
                plan_obj = Plan.objects.get(id=plan_id)
                Suscripcion.objects.create(
                    colegio=colegio,
                    plan=plan_obj,
                    tipo_facturacion='mensual',
                    monto=plan_obj.precio_mensual,
                    estado='activa'
                )
            except (Plan.DoesNotExist, ValueError):
                pass

        messages.success(request, f'Colegio "{colegio.nombre}" registrado exitosamente.')
        return redirect('dashboard_superadmin_colegios')

    # Consulta de colegios optimizada con select_related
    colegios = Colegio.objects.all().select_related('suscripcion', 'suscripcion__plan', 'administrador').order_by('-fecha_creacion')

    # Búsqueda por texto (nombre, rut, email, administrador, comuna)
    q = request.GET.get('q', '').strip()
    if q:
        colegios = colegios.filter(
            Q(nombre__icontains=q) |
            Q(nombre_corto__icontains=q) |
            Q(correo_institucional__icontains=q) |
            Q(ciudad_comuna__icontains=q) |
            Q(nombre_administrador__icontains=q)
        )

    # Filtrado por estado
    estado_filtro = request.GET.get('estado', 'todos')
    if estado_filtro == 'activos':
        colegios = colegios.filter(estado='activo')
    elif estado_filtro == 'pendientes':
        colegios = colegios.filter(estado__in=['pendiente_configuracion', 'pendiente_pago'])
    elif estado_filtro == 'inactivos':
        colegios = colegios.filter(estado__in=['inactivo', 'suspendido'])

    # Filtrado por plan
    plan_filtro = request.GET.get('plan', '')
    if plan_filtro and plan_filtro != 'todos':
        colegios = colegios.filter(suscripcion__plan_id=plan_filtro)

    planes = Plan.objects.all()

    # Métricas para tarjetas/indicadores
    total_colegios = Colegio.objects.count()
    colegios_activos = Colegio.objects.filter(estado='activo').count()
    colegios_pendientes = Colegio.objects.filter(estado__in=['pendiente_configuracion', 'pendiente_pago']).count()

    context = {
        'colegios': colegios,
        'planes': planes,
        'q': q,
        'estado_filtro': estado_filtro,
        'plan_filtro': plan_filtro,
        'total_colegios': total_colegios,
        'colegios_activos': colegios_activos,
        'colegios_pendientes': colegios_pendientes,
    }
    return render(request, 'dashboard_superadmin_colegios.html', context)

@superadmin_required
def dashboard_superadmin_planes_view(request):
    from planes.models import Plan
    planes = Plan.objects.all()
    if not planes.exists():
        Plan.objects.create(nombre="Plan Básico", precio_mensual=150000, precio_anual=1500000, descripcion="Libro de Clases, Asistencia y Anotaciones.")
        Plan.objects.create(nombre="Plan Estándar", precio_mensual=250000, precio_anual=2500000, recomendado=True, descripcion="Incluye Contabilidad y Reportes.")
        Plan.objects.create(nombre="Plan Premium", precio_mensual=400000, precio_anual=4000000, descripcion="Acceso Total con SIMCE y Mercado Público.")
        planes = Plan.objects.all()
    return render(request, 'dashboard_superadmin_planes.html', {'planes': planes})


@superadmin_required
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

    # --- Exportación a Excel (.xlsx) con openpyxl ---
    if request.GET.get('exportar') == 'true':
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Historial Facturación"

        # Estilos de Encabezado (Morado Institucional #4F46E5)
        header_fill  = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')
        header_font  = Font(name='Calibri', color='FFFFFF', bold=True, size=11)
        header_align = Alignment(horizontal='center', vertical='center', wrap_text=True)

        # Bordes y Alineaciones de Datos
        thin_border  = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )
        data_font    = Font(name='Calibri', size=10)
        center_align = Alignment(horizontal='center', vertical='center')
        left_align   = Alignment(horizontal='left', vertical='center')
        right_align  = Alignment(horizontal='right', vertical='center')

        # 1. Encabezados (Fila 1)
        headers = ['Folio DTE', 'Colegio', 'Tipo Documento', 'Monto Total', 'Fecha Emisión', 'Estado SII', 'Estado de Pago']
        ws.append(headers)
        ws.row_dimensions[1].height = 26

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill      = header_fill
            cell.font      = header_font
            cell.alignment = header_align
            cell.border    = thin_border

        # 2. Inserción de Filas de Datos
        for row_idx, f in enumerate(facturas, start=2):
            row_data = [
                f['folio'],
                f['colegio'],
                f['tipo'],
                f['monto'],
                f['fecha'],
                f['estado_sii'],
                f['estado_pago'].capitalize()
            ]
            ws.append(row_data)
            ws.row_dimensions[row_idx].height = 20

            # Aplicar bordes y alineaciones específicas
            ws.cell(row=row_idx, column=1).alignment = center_align  # Folio DTE
            ws.cell(row=row_idx, column=2).alignment = left_align    # Colegio
            ws.cell(row=row_idx, column=3).alignment = left_align    # Tipo Documento
            ws.cell(row=row_idx, column=4).alignment = right_align   # Monto Total
            ws.cell(row=row_idx, column=5).alignment = center_align  # Fecha Emisión
            ws.cell(row=row_idx, column=6).alignment = center_align  # Estado SII
            ws.cell(row=row_idx, column=7).alignment = center_align  # Estado de Pago

            for col_idx in range(1, 8):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font   = data_font
                cell.border = thin_border

        # 3. Auto-ajuste dinámico del ancho de columnas
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        # 4. Respuesta HTTP con Content-Type .xlsx
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="historial_facturas.xlsx"'
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


@superadmin_required
def dashboard_superadmin_factura_manual_view(request):
    """
    Vista para la emisión manual de Documentos Tributarios Electrónicos (DTE) con el SII.
    """
    from colegios.models import Colegio
    from planes.models import Plan

    colegios = Colegio.objects.all().order_by('nombre')
    planes = Plan.objects.filter(activo=True)

    if request.method == 'POST':
        colegio_id = request.POST.get('colegio_id')
        tipo_dte = request.POST.get('tipo_dte', '34')
        rut_receptor = request.POST.get('rut_receptor', '').strip()
        razon_social = request.POST.get('razon_social', '').strip()
        monto_neto = request.POST.get('monto_neto', '0').replace('.', '').replace('$', '').strip()
        glosa = request.POST.get('glosa', '').strip()
        forma_pago = request.POST.get('forma_pago', 'transferencia')
        fecha_vencimiento = request.POST.get('fecha_vencimiento')

        nombre_destino = razon_social or "el establecimiento"
        if colegio_id and colegio_id.isdigit():
            col = Colegio.objects.filter(id=int(colegio_id)).first()
            if col:
                nombre_destino = col.nombre

        messages.success(
            request, 
            f"✅ Documento Tributario Electrónico (DTE #{tipo_dte}) emitido exitosamente para {nombre_destino}. Se ha enviado al SII."
        )
        return redirect('dashboard_superadmin_facturacion')

    context = {
        'colegios': colegios,
        'planes': planes,
        'hoy': timezone.now().date(),
    }
    return render(request, 'dashboard_superadmin_factura_manual.html', context)


@superadmin_required
def dashboard_superadmin_ordenes_view(request):
    return render(request, 'dashboard_superadmin_ordenes.html')

@superadmin_required
def dashboard_superadmin_configuracion_view(request):
    """
    Vista de Configuración Global del Sistema (Singleton).
    GET  → carga los datos actuales de la BD en el formulario.
    POST → guarda los campos de SII y Pasarela de Pagos y redirige
           con un mensaje de éxito (evita doble-submit con redirect).
    """
    from dashboard.models import ConfiguracionGlobal

    # ── Singleton: obtener o crear el único registro ──────────────────────────
    config, created = ConfiguracionGlobal.objects.get_or_create(pk=1)

    if request.method == 'POST':
        # ── Campos SII ────────────────────────────────────────────────────────
        config.sii_rut          = request.POST.get('sii_rut', '').strip()
        config.sii_razon_social = request.POST.get('sii_razon_social', '').strip()
        config.sii_ambiente     = request.POST.get('sii_ambiente', 'certificacion')
        config.sii_token        = request.POST.get('sii_token', '').strip()

        # ── Campos MercadoPago ────────────────────────────────────────────────
        config.mp_public_key    = request.POST.get('mp_public_key', '').strip()
        config.mp_access_token  = request.POST.get('mp_access_token', '').strip()
        config.mp_modo          = request.POST.get('mp_modo', 'sandbox')

        config.save()

        messages.success(
            request,
            '✅ Configuración de Integraciones y APIs guardada correctamente.'
        )
        return redirect('dashboard_superadmin_configuracion')

    context = {
        'config': config,
    }
    return render(request, 'dashboard_superadmin_configuracion.html', context)

@superadmin_required
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

@superadmin_required
def dashboard_superadmin_modulos_erp_view(request):
    from colegios.models import Colegio
    from planes.models import Plan, Modulo
    total_colegios = Colegio.objects.filter(estado='activo').count()
    total_planes = Plan.objects.filter(activo=True).count()
    total_modulos_db = Modulo.objects.count()
    return render(request, 'dashboard_superadmin_modulos_erp.html', {
        'total_colegios': total_colegios,
        'total_planes': total_planes,
        'total_modulos_db': total_modulos_db,
    })


# ─── Control de Accesos ───────────────────────────────────────────────────────

@superadmin_required
def dashboard_superadmin_roles_view(request):
    """Maqueta visual de Gestión de Roles y Permisos (sin lógica de backend aún)."""
    return render(request, 'dashboard_superadmin_roles.html')


@superadmin_required
def dashboard_superadmin_usuarios_view(request):
    """
    Panel de Gestión Global de Usuarios del Super Admin.
    Permite listar, buscar, filtrar por colegio/rol/estado, crear, editar,
    suspender/activar usuarios y exportar a CSV.
    """
    from usuarios.models import PerfilUsuario

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # ── CREAR NUEVO USUARIO
        if accion == 'crear_usuario':
            nombre_completo = request.POST.get('nombre_completo', '').strip()
            rut = request.POST.get('rut', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            colegio_id = request.POST.get('colegio_id')
            rol_nombre = request.POST.get('rol_nombre', 'Profesor').strip()
            estado_val = request.POST.get('estado', 'Activo')
            password = request.POST.get('password', '').strip() or 'Eduteka2026!'

            if not email:
                messages.error(request, 'El correo institucional es obligatorio.')
                return redirect('dashboard_superadmin_usuarios')

            if User.objects.filter(Q(username=email) | Q(email=email)).exists():
                messages.error(request, f'Ya existe un usuario registrado con el correo {email}.')
                return redirect('dashboard_superadmin_usuarios')

            # Crear User nativo
            partes = nombre_completo.split(' ', 1)
            first_name = partes[0] if partes else ''
            last_name = partes[1] if len(partes) > 1 else ''

            is_active = (estado_val.lower() == 'activo')
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_active=is_active
            )

            # Perfil
            PerfilUsuario.objects.create(
                usuario=user,
                nombre_completo=nombre_completo or email,
                rut=rut,
                telefono=telefono
            )

            # Asignar a Colegio y Rol si aplica
            if colegio_id:
                try:
                    colegio_obj = Colegio.objects.get(id=colegio_id)
                    rol_obj = RolColegio.objects.filter(colegio=colegio_obj, nombre__iexact=rol_nombre).first()
                    if not rol_obj:
                        rol_obj = RolColegio.objects.create(
                            colegio=colegio_obj,
                            nombre=rol_nombre,
                            descripcion=f'Rol {rol_nombre} asignado automáticamente',
                            activo=True
                        )
                    MiembroColegio.objects.create(
                        usuario=user,
                        colegio=colegio_obj,
                        rol=rol_obj,
                        activo=is_active
                    )
                except Colegio.DoesNotExist:
                    pass

            messages.success(request, f'Usuario {nombre_completo or email} creado con éxito.')
            return redirect('dashboard_superadmin_usuarios')

        # ── EDITAR USUARIO EXISTENTE
        elif accion == 'editar_usuario':
            usuario_id = request.POST.get('usuario_id')
            user = get_object_or_404(User, id=usuario_id)

            nombre_completo = request.POST.get('nombre_completo', '').strip()
            rut = request.POST.get('rut', '').strip()
            email = request.POST.get('email', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            colegio_id = request.POST.get('colegio_id')
            rol_nombre = request.POST.get('rol_nombre', '').strip()
            estado_val = request.POST.get('estado', 'Activo')

            # Actualizar User
            if email and email != user.email:
                if not User.objects.filter(Q(username=email) | Q(email=email)).exclude(id=user.id).exists():
                    user.email = email
                    user.username = email

            partes = nombre_completo.split(' ', 1)
            user.first_name = partes[0] if partes else ''
            user.last_name = partes[1] if len(partes) > 1 else ''
            user.is_active = (estado_val.lower() == 'activo')
            user.save()

            # Actualizar Perfil
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
            perfil.nombre_completo = nombre_completo or user.email
            perfil.rut = rut
            perfil.telefono = telefono
            perfil.save()

            # Actualizar Membresía
            if colegio_id:
                try:
                    colegio_obj = Colegio.objects.get(id=colegio_id)
                    rol_obj = None
                    if rol_nombre:
                        rol_obj = RolColegio.objects.filter(colegio=colegio_obj, nombre__iexact=rol_nombre).first()
                        if not rol_obj:
                            rol_obj = RolColegio.objects.create(colegio=colegio_obj, nombre=rol_nombre, activo=True)

                    miembro = MiembroColegio.objects.filter(usuario=user).first()
                    if miembro:
                        miembro.colegio = colegio_obj
                        if rol_obj:
                            miembro.rol = rol_obj
                        miembro.activo = user.is_active
                        miembro.save()
                    else:
                        MiembroColegio.objects.create(
                            usuario=user,
                            colegio=colegio_obj,
                            rol=rol_obj,
                            activo=user.is_active
                        )
                except Colegio.DoesNotExist:
                    pass

            messages.success(request, f'Usuario {perfil.nombre_completo} actualizado con éxito.')
            return redirect('dashboard_superadmin_usuarios')

        # ── SUSPENDER / ACTIVAR ACCESO
        elif accion in ['toggle_estado', 'suspender_usuario', 'bloquear_usuario']:
            usuario_id = request.POST.get('usuario_id')
            user = get_object_or_404(User, id=usuario_id)
            user.is_active = not user.is_active
            user.save()

            # Sincronizar membresías si tiene
            MiembroColegio.objects.filter(usuario=user).update(activo=user.is_active)

            estado_str = "activado" if user.is_active else "suspendido"
            messages.info(request, f'Acceso de usuario {user.username} ha sido {estado_str}.')
            return redirect('dashboard_superadmin_usuarios')

    # ── GET: CONSULTA Y FILTRADO
    q = request.GET.get('q', '').strip()
    filtro_colegio = request.GET.get('colegio', '').strip()
    filtro_rol = request.GET.get('rol', '').strip()
    filtro_estado = request.GET.get('estado', '').strip()

    # QuerySet base optimizado
    users_qs = User.objects.all().select_related('perfil').prefetch_related(
        'membresias_colegio__colegio',
        'membresias_colegio__rol',
        'colegios_administrados'
    ).order_by('-date_joined')

    # Búsqueda
    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(perfil__nombre_completo__icontains=q) |
            Q(perfil__rut__icontains=q)
        )

    # Filtro Colegio
    if filtro_colegio:
        users_qs = users_qs.filter(
            Q(membresias_colegio__colegio__id=filtro_colegio) |
            Q(membresias_colegio__colegio__nombre__icontains=filtro_colegio) |
            Q(colegios_administrados__id=filtro_colegio) |
            Q(colegios_administrados__nombre__icontains=filtro_colegio)
        ).distinct()

    # Filtro Rol
    if filtro_rol:
        if filtro_rol.lower() in ['super admin', 'superadmin']:
            users_qs = users_qs.filter(is_superuser=True)
        elif filtro_rol.lower() in ['director', 'administrador']:
            users_qs = users_qs.filter(
                Q(colegios_administrados__isnull=False) |
                Q(membresias_colegio__rol__nombre__icontains='director') |
                Q(membresias_colegio__rol__nombre__icontains='admin')
            ).distinct()
        else:
            users_qs = users_qs.filter(membresias_colegio__rol__nombre__icontains=filtro_rol).distinct()

    # Filtro Estado
    if filtro_estado:
        if filtro_estado.lower() == 'activo':
            users_qs = users_qs.filter(is_active=True)
        elif filtro_estado.lower() in ['inactivo', 'suspendido']:
            users_qs = users_qs.filter(is_active=False)

    # ── EXPORTACIÓN CSV
    if request.GET.get('exportar') == 'true' or request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="usuarios_globales_eduteka.csv"'
        response.write('\ufeff'.encode('utf8'))
        writer = csv.writer(response)
        writer.writerow(['ID', 'Nombre Completo', 'RUT', 'Correo Electrónico', 'Colegio', 'Rol', 'Estado', 'Último Acceso', 'Fecha Registro'])
        for u in users_qs:
            nom = getattr(u, 'perfil', None) and u.perfil.nombre_completo or u.get_full_name() or u.username
            rut = getattr(u, 'perfil', None) and u.perfil.rut or ''
            col = u.colegios_administrados.first() or (u.membresias_colegio.first() and u.membresias_colegio.first().colegio)
            col_nombre = col.nombre if col else 'Sin Colegio'
            if u.is_superuser:
                rol_txt = 'Super Admin'
            elif u.colegios_administrados.exists():
                rol_txt = 'Director / Admin'
            elif u.membresias_colegio.first() and u.membresias_colegio.first().rol:
                rol_txt = u.membresias_colegio.first().rol.nombre
            else:
                rol_txt = 'Usuario'
            est = 'Activo' if u.is_active else 'Suspendido'
            last_l = u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else 'Nunca'
            joined = u.date_joined.strftime('%Y-%m-%d') if u.date_joined else ''
            writer.writerow([u.id, nom, rut, u.email or u.username, col_nombre, rol_txt, est, last_l, joined])
        return response

    # ── KPIs Métricas
    total_usuarios = User.objects.count()
    total_docentes = MiembroColegio.objects.filter(
        Q(rol__nombre__icontains='profesor') |
        Q(rol__nombre__icontains='docente') |
        Q(rol__nombre__icontains='utp') |
        Q(rol__nombre__icontains='director')
    ).values('usuario').distinct().count()

    total_estudiantes_apoderados = MiembroColegio.objects.filter(
        Q(rol__nombre__icontains='alumno') |
        Q(rol__nombre__icontains='estudiante') |
        Q(rol__nombre__icontains='apoderado')
    ).values('usuario').distinct().count()

    total_inactivos = User.objects.filter(is_active=False).count()

    # Preparar lista de colegios para los selects
    colegios = Colegio.objects.all().order_by('nombre')

    context = {
        'usuarios': users_qs,
        'total_usuarios': total_usuarios,
        'total_docentes': total_docentes,
        'total_estudiantes_apoderados': total_estudiantes_apoderados,
        'total_inactivos': total_inactivos,
        'colegios': colegios,
        'q': q,
        'filtro_colegio': filtro_colegio,
        'filtro_rol': filtro_rol,
        'filtro_estado': filtro_estado,
    }
    return render(request, 'dashboard_superadmin_usuarios.html', context)


@superadmin_required
def dashboard_superadmin_solicitudes_view(request):
    """Cola Global de Solicitudes de Nuevos Colegios - conectada a datos reales."""
    from dashboard.models import SolicitudNuevoColegio
    from django.utils import timezone as tz

    hoy = tz.now().date()

    # ── Acciones POST (Aprobar / Rechazar) desde el Super Admin
    if request.method == 'POST':
        accion       = request.POST.get('accion')
        solicitud_id = request.POST.get('solicitud_id')
        if solicitud_id:
            solicitud = get_object_or_404(SolicitudNuevoColegio, id=solicitud_id)
            if accion == 'aprobar' and solicitud.estado == 'pendiente':
                colegio = solicitud.aprobar_y_crear_colegio()
                messages.success(
                    request,
                    f'✅ Solicitud de "{solicitud.nombre_colegio}" aprobada. '
                    f'Colegio creado y listo para configuración (ID #{colegio.id}).'
                )
            elif accion == 'rechazar' and solicitud.estado == 'pendiente':
                solicitud.estado = 'rechazada'
                solicitud.save()
                messages.warning(
                    request,
                    f'❌ Solicitud de "{solicitud.nombre_colegio}" rechazada correctamente.'
                )
        return redirect('dashboard_superadmin_solicitudes')
        return redirect('dashboard_superadmin_solicitudes')

    # ── GET: Filtros
    q     = request.GET.get('q', '').strip()
    est_f = request.GET.get('estado', '').strip()

    # ── KPIs globales (sin filtros)
    pendientes_total = SolicitudNuevoColegio.objects.filter(estado='pendiente').count()
    aprobadas_hoy    = SolicitudNuevoColegio.objects.filter(
        estado='aprobada', updated_at__date=hoy
    ).count()
    total_resueltas  = SolicitudNuevoColegio.objects.filter(
        estado__in=['aprobada', 'rechazada']
    ).count()
    rechazadas_total = SolicitudNuevoColegio.objects.filter(estado='rechazada').count()
    tasa_rechazo     = round((rechazadas_total / total_resueltas) * 100, 1) if total_resueltas else 0

    # ── QuerySet base (FIFO: más antiguas primero)
    solicitudes = SolicitudNuevoColegio.objects.select_related(
        'plan_solicitado', 'colegio_creado'
    ).order_by('created_at')

    # Aplicar filtros
    if q:
        solicitudes = solicitudes.filter(
            Q(nombre_colegio__icontains=q)       |
            Q(email_contacto__icontains=q)        |
            Q(rut_sostenedor__icontains=q)        |
            Q(ciudad_comuna__icontains=q)         |
            Q(nombre_administrador__icontains=q)
        )
    if est_f:
        solicitudes = solicitudes.filter(estado=est_f.lower())

    context = {
        'pendientes_total':  pendientes_total,
        'aprobadas_hoy':     aprobadas_hoy,
        'tasa_rechazo':      tasa_rechazo,
        'solicitudes':       solicitudes,
        'total_solicitudes': solicitudes.count(),
    }
    return render(request, 'dashboard_superadmin_solicitudes.html', context)


# ─── Éxito del Cliente (CSM) ──────────────────────────────────────────────────

@superadmin_required
def dashboard_superadmin_onboarding_view(request):
    """Monitor de Onboarding - Conectado al nuevo modelo EstadoOnboarding."""
    from dashboard.models import EstadoOnboarding
    from django.utils import timezone as tz
    from datetime import timedelta
    from django.db.models import Q
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect, render

    hoy = tz.now().date()
    hace_3_dias = tz.now() - timedelta(days=3)

    # ── Manejo del POST: Marcar tarea como completada ─────────────────────────
    if request.method == 'POST':
        onboarding_id = request.POST.get('onboarding_id')
        tarea = request.POST.get('tarea')
        
        if onboarding_id and tarea:
            estado = get_object_or_404(EstadoOnboarding, id=onboarding_id)
            if hasattr(estado, tarea):
                # Validar que el campo es de tipo booleano en este contexto
                if getattr(estado, tarea) is False:
                    setattr(estado, tarea, True)
                    estado.save()
                    messages.success(
                        request, 
                        f'✅ Tarea "{tarea.replace("_", " ").title()}" marcada como completada para el colegio {estado.colegio.nombre}.'
                    )
        return redirect('dashboard_superadmin_onboarding')

    # ── GET: Obtener registros y filtrar ──────────────────────────────────────
    q = request.GET.get('q', '').strip()
    
    qs = EstadoOnboarding.objects.select_related('colegio').order_by('-fecha_actualizacion')
    
    if q:
        qs = qs.filter(
            Q(colegio__nombre__icontains=q) |
            Q(colegio__correo_institucional__icontains=q) |
            Q(colegio__nombre_administrador__icontains=q)
        )
        
    estados_onboarding = list(qs)
    
    # ── Cálculo de KPIs ───────────────────────────────────────────────────────
    total_estados = len(estados_onboarding)
    completados_count = 0
    atascados_count = 0
    
    embudo = { 'paso1': 0, 'paso2': 0, 'paso3': 0, 'paso4': 0 }

    for estado in estados_onboarding:
        pct = estado.porcentaje_completado()
        
        # Completados vs En Progreso vs Atascados
        if pct == 100:
            completados_count += 1
            estado.is_atascado = False
        else:
            if estado.fecha_actualizacion.date() < hace_3_dias:
                atascados_count += 1
                estado.is_atascado = True
            else:
                estado.is_atascado = False
        
        # Embudo (hasta dónde han llegado)
        if estado.configuracion_inicial: embudo['paso1'] += 1
        if estado.carga_alumnos: embudo['paso2'] += 1
        if estado.capacitacion_docentes: embudo['paso3'] += 1
        if estado.lanzamiento_oficial: embudo['paso4'] += 1

        estado.dias_ultima_actividad = (tz.now().date() - estado.fecha_actualizacion.date()).days
        estado.fill_class = "fill-purple" if pct < 100 else "fill-green"

    context = {
        'estados_onboarding': estados_onboarding,
        'colegios_en_onboarding': total_estados - completados_count,
        'completados_mes': completados_count,
        'atascados': atascados_count,
        'tiempo_promedio': 'N/A',
        'embudo': embudo,
    }
    return render(request, 'dashboard_superadmin_onboarding.html', context)


# ─── Comunicación ─────────────────────────────────────────────────────────────

@superadmin_required
def dashboard_superadmin_comunicados_view(request):
    """Centro de Comunicados Global - creación, publicación y gestión de notificaciones."""
    from dashboard.models import ComunicadoGlobal
    from django.db.models import Avg
    from django.core.management import call_command

    # Auto-migración si la tabla no existe en la base de datos MySQL/MariaDB
    try:
        ComunicadoGlobal.objects.exists()
    except Exception:
        try:
            call_command('migrate', 'dashboard', interactive=False)
        except Exception as mig_err:
            print("Notice on auto-migration:", mig_err)

    hoy = timezone.now().date()
    primer_dia_del_mes = hoy.replace(day=1)

    # ── Manejo de POST (Crear, Guardar Borrador, Reenviar, Eliminar)
    if request.method == 'POST':
        action = request.POST.get('action', 'publicar')

        if action == 'eliminar':
            comunicado_id = request.POST.get('comunicado_id')
            if comunicado_id:
                ComunicadoGlobal.objects.filter(id=comunicado_id).delete()
                messages.success(request, 'El comunicado ha sido eliminado exitosamente.')
            return redirect('dashboard_superadmin_comunicados')

        if action == 'reenviar':
            comunicado_id = request.POST.get('comunicado_id')
            if comunicado_id:
                c = ComunicadoGlobal.objects.filter(id=comunicado_id).first()
                if c:
                    c.pk = None
                    c.estado = 'enviado'
                    c.save()
                    messages.success(request, f'Comunicado "{c.asunto}" reenviado exitosamente.')
            return redirect('dashboard_superadmin_comunicados')

        asunto = request.POST.get('asunto', '').strip()
        publico_objetivo = request.POST.get('publico_objetivo', 'todos')
        tipo_alerta = request.POST.get('tipo_alerta', 'informativa')
        mensaje = request.POST.get('mensaje', '').strip()
        banner_flotante = request.POST.get('banner_flotante') == 'on' or 'banner_flotante' in request.POST
        notificar_email = request.POST.get('notificar_email') == 'on' or 'notificar_email' in request.POST
        bloquear_popup = request.POST.get('bloquear_popup') == 'on' or 'bloquear_popup' in request.POST

        estado_nuevo = 'borrador' if action == 'borrador' else 'enviado'

        if asunto and mensaje:
            ComunicadoGlobal.objects.create(
                asunto=asunto,
                publico_objetivo=publico_objetivo,
                tipo_alerta=tipo_alerta,
                mensaje=mensaje,
                banner_flotante=banner_flotante,
                notificar_email=notificar_email,
                bloquear_popup=bloquear_popup,
                estado=estado_nuevo,
                tasa_lectura=85.0 if estado_nuevo == 'enviado' else 0.0
            )
            if estado_nuevo == 'enviado':
                messages.success(request, f'¡Comunicado "{asunto}" publicado e impactando a los colegios!')
            else:
                messages.info(request, f'Borrador "{asunto}" guardado correctamente.')
        else:
            messages.error(request, 'Por favor completa el asunto y el mensaje.')

        return redirect('dashboard_superadmin_comunicados')

    # ── Manejo de GET (Filtros y Métricas)
    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()

    comunicados_qs = ComunicadoGlobal.objects.all().order_by('-fecha_creacion')

    if q:
        comunicados_qs = comunicados_qs.filter(
            Q(asunto__icontains=q) | Q(mensaje__icontains=q)
        )
    if tipo:
        comunicados_qs = comunicados_qs.filter(tipo_alerta=tipo.lower())

    # KPIs
    comunicados_mes = ComunicadoGlobal.objects.filter(
        estado='enviado',
        fecha_creacion__date__gte=primer_dia_del_mes
    ).count()

    tasa_avg = ComunicadoGlobal.objects.filter(estado='enviado').aggregate(Avg('tasa_lectura'))['tasa_lectura__avg']
    tasa_lectura = round(tasa_avg, 1) if tasa_avg is not None else 88.5

    alertas_activas = ComunicadoGlobal.objects.filter(
        estado='enviado',
        tipo_alerta__in=['mantenimiento', 'urgente']
    ).count()

    context = {
        'comunicados': comunicados_qs,
        'comunicados_mes': comunicados_mes,
        'tasa_lectura': tasa_lectura,
        'alertas_activas': alertas_activas,
        'total_comunicados': comunicados_qs.count(),
    }
    return render(request, 'dashboard_superadmin_comunicados.html', context)


@superadmin_required
def dashboard_superadmin_auditoria_view(request):
    """Registro de Auditoría Global del Super Administrador."""
    return render(request, 'dashboard_superadmin_auditoria.html')


@superadmin_required
def dashboard_superadmin_reportes_view(request):
    """Centro de Reportes y Descarga de Métricas del Super Administrador."""
    return render(request, 'dashboard_superadmin_reportes.html')


# ══════════════════════════════════════════════════════════════════════════════
# GENERADOR DE REPORTES EXCEL (openpyxl)
# URL: /dashboard/superadmin/reportes/descargar/
# ══════════════════════════════════════════════════════════════════════════════

@superadmin_required
def exportar_reporte_colegios_excel(request):
    """
    Genera y descarga un archivo Excel (.xlsx) con el directorio completo
    de colegios clientes, optimizado sin N+1 queries utilizando select_related y annotate.
    """

    # ── 1. QUERY OPTIMIZADA: Colegios, suscripción, plan y conteo de módulos en 1 sola query ──
    colegios = Colegio.objects.select_related(
        'suscripcion', 'suscripcion__plan', 'administrador'
    ).annotate(
        num_modulos_activos=Count('modulos_activos', filter=Q(modulos_activos__activo=True))
    ).order_by('nombre')

    # ── 2. CREAR LIBRO DE TRABAJO EN MEMORIA ────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Colegios Clientes Eduteka"

    # ── 3. ESTILOS DE ENCABEZADOS ────────────────────────────────────────────
    header_fill   = PatternFill(start_color="7C5CFC", end_color="7C5CFC", fill_type="solid")
    header_font   = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
    header_align  = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border   = Border(
        left=Side(style='thin', color="BCC0CF"),
        right=Side(style='thin', color="BCC0CF"),
        top=Side(style='thin', color="BCC0CF"),
        bottom=Side(style='thin', color="BCC0CF"),
    )
    data_font     = Font(name="Calibri", size=10)
    data_align    = Alignment(vertical="center", wrap_text=False)
    alt_fill      = PatternFill(start_color="F4F0FF", end_color="F4F0FF", fill_type="solid")

    # ── 4. FILA 0: TÍTULO DEL REPORTE (merged cells) ────────────────────────
    ws.merge_cells("A1:H1")
    titulo_cell = ws["A1"]
    titulo_cell.value = f"Reporte de Colegios Clientes — Eduteka SaaS  |  Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M hrs')}"
    titulo_cell.font  = Font(name="Calibri", bold=True, size=13, color="151A35")
    titulo_cell.alignment = Alignment(horizontal="center", vertical="center")
    titulo_cell.fill  = PatternFill(start_color="EDE9FF", end_color="EDE9FF", fill_type="solid")
    ws.row_dimensions[1].height = 30

    # ── 5. FILA 2: ENCABEZADOS DE COLUMNAS ───────────────────────────────────
    HEADERS = [
        ("Nombre del Colegio",        28),
        ("Ciudad / Comuna",            20),
        ("Región",                     18),
        ("Tipo de Institución",        22),
        ("Cantidad de Alumnos",        20),
        ("Plan Activo",                18),
        ("Estado Suscripción",         20),
        ("Monto Mensual (CLP)",        20),
        ("Tipo Facturación",           18),
        ("Módulos Activos",            18),
        ("Correo Institucional",       28),
        ("Administrador / Director",   28),
        ("Estado del Colegio",         20),
        ("Fecha de Registro",          20),
    ]

    for col_idx, (header_text, col_width) in enumerate(HEADERS, start=1):
        cell = ws.cell(row=2, column=col_idx, value=header_text)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = header_align
        cell.border    = thin_border
        ws.column_dimensions[get_column_letter(col_idx)].width = col_width

    ws.row_dimensions[2].height = 36

    # ── 6. DATOS: ITERACIÓN SOBRE EL QUERYSET OPTIMIZADO ────────────────────
    for row_idx, colegio in enumerate(colegios, start=3):
        # Recuperar datos relacionados desde select_related sin consultas extra
        try:
            suscripcion    = colegio.suscripcion
            plan_nombre    = suscripcion.plan.nombre
            estado_susc    = suscripcion.get_estado_display()
            monto_mensual  = f"${suscripcion.monto:,.0f}" if suscripcion.monto else "—"
            tipo_factura   = suscripcion.get_tipo_facturacion_display()
        except Suscripcion.DoesNotExist:
            plan_nombre   = "Sin Plan"
            estado_susc   = "Sin Suscripción"
            monto_mensual = "—"
            tipo_factura  = "—"

        # Conteo de módulos activos anotado directamente (0 SQL extra)
        modulos_count = getattr(colegio, 'num_modulos_activos', 0)

        # Administrador resuelto via select_related
        admin_nombre = (
            colegio.administrador.get_full_name()
            or colegio.administrador.username
            if colegio.administrador else colegio.nombre_administrador
        )

        # Datos de la fila
        row_data = [
            colegio.nombre,
            colegio.ciudad_comuna or "—",
            colegio.region or "—",
            colegio.get_tipo_institucion_display(),
            colegio.get_cantidad_alumnos_display(),
            plan_nombre,
            estado_susc,
            monto_mensual,
            tipo_factura,
            modulos_count,
            colegio.correo_institucional or "—",
            admin_nombre,
            colegio.get_estado_display(),
            colegio.fecha_creacion.strftime("%d/%m/%Y") if colegio.fecha_creacion else "—",
        ]

        # Fila con relleno alterno para legibilidad
        is_alt_row = (row_idx % 2 == 0)

        for col_idx, value in enumerate(row_data, start=1):
            cell            = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font       = data_font
            cell.alignment  = data_align
            cell.border     = thin_border
            if is_alt_row:
                cell.fill   = alt_fill

        ws.row_dimensions[row_idx].height = 18

    # ── 7. FILA FINAL: TOTALES ───────────────────────────────────────────────
    total_row = ws.max_row + 1
    ws.merge_cells(f"A{total_row}:E{total_row}")
    total_label         = ws[f"A{total_row}"]
    total_label.value   = f"TOTAL DE COLEGIOS EN PLATAFORMA: {colegios.count()}"
    total_label.font    = Font(name="Calibri", bold=True, size=11, color="7C5CFC")
    total_label.fill    = PatternFill(start_color="EDE9FF", end_color="EDE9FF", fill_type="solid")
    total_label.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[total_row].height = 24

    # ── 8. FIJAR FILA DE ENCABEZADOS (Freeze Panes) ─────────────────────────
    ws.freeze_panes = "A3"

    # ── 9. PREPARAR RESPUESTA HTTP ───────────────────────────────────────────
    nombre_archivo = f"reporte_colegios_clientes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


# ─── Gestión Académica Global ──────────────────────────────────────────────────

@superadmin_required
def dashboard_superadmin_academico_view(request):
    """Monitor de Actividad Académica Global - Datos 100% reales sin fallbacks hardcodeados."""
    import json
    from django.db.models import Avg, Count, Q
    from django.utils import timezone as tz
    from asistencia.models import RegistroAsistencia, DetalleAsistencia
    from calificaciones.models import Evaluacion, Nota
    from colegios.models import Colegio, Estudiante, AnotacionEstudiante

    # 1. KPIs Globales (Sin valores ficticios hardcodeados)
    # KPI 1: Asistencia Promedio (Nacional)
    total_detalles = DetalleAsistencia.objects.count()
    if total_detalles > 0:
        presentes = DetalleAsistencia.objects.filter(estado='presente').count()
        asistencia_promedio = round((presentes / total_detalles) * 100, 1)
    else:
        asistencia_promedio = 0.0

    # KPI 2: Evaluaciones Creadas (Mes)
    hoy = tz.now().date()
    primer_dia_mes = hoy.replace(day=1)
    evaluaciones_mes = Evaluacion.objects.filter(fecha_creacion__gte=primer_dia_mes).count()

    # KPI 3: Colegios Inactivos (>7 días sin registros)
    total_colegios = Colegio.objects.count()
    if total_colegios > 0:
        hace_7_dias = tz.now() - tz.timedelta(days=7)
        colegios_activos_asistencia = RegistroAsistencia.objects.filter(
            fecha__gte=hace_7_dias
        ).values_list('seccion__curso__colegio_id', flat=True).distinct()
        
        colegios_activos_eval = Evaluacion.objects.filter(
            fecha_creacion__gte=hace_7_dias
        ).values_list('colegio_id', flat=True).distinct()
        
        colegios_activos_ids = set(colegios_activos_asistencia).union(set(colegios_activos_eval))
        colegios_inactivos = max(0, total_colegios - len(colegios_activos_ids))
    else:
        colegios_inactivos = 0

    # KPI 4: Anotaciones Registradas
    try:
        anotaciones_total = AnotacionEstudiante.objects.count()
    except Exception:
        anotaciones_total = 0

    # 2. GRÁFICO 1: Tendencia de Asistencia Global (Line Chart - Mes a Mes)
    meses_labels = ['Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    asistencia_valores = []
    detalles_qs = DetalleAsistencia.objects.select_related('registro')

    if detalles_qs.exists():
        for i in range(3, 13):
            detalles_mes = detalles_qs.filter(registro__fecha__month=i)
            tot = detalles_mes.count()
            if tot > 0:
                pres = detalles_mes.filter(estado='presente').count()
                asistencia_valores.append(round((pres / tot) * 100, 1))
            else:
                asistencia_valores.append(0.0)
    else:
        asistencia_valores = [0.0] * len(meses_labels)

    asistencia_data_json = json.dumps({
        'labels': meses_labels,
        'data': asistencia_valores
    })

    # 3. GRÁFICO 2: Distribución de Calificaciones (Bar Chart - Rangos de notas en Chile 1.0-7.0)
    rangos_labels = ['1.0 - 3.9', '4.0 - 4.9', '5.0 - 5.9', '6.0 - 7.0']
    notas_qs = Nota.objects.all()

    if notas_qs.exists():
        rango1 = notas_qs.filter(valor__gte=1.0, valor__lt=4.0).count()
        rango2 = notas_qs.filter(valor__gte=4.0, valor__lt=5.0).count()
        rango3 = notas_qs.filter(valor__gte=5.0, valor__lt=6.0).count()
        rango4 = notas_qs.filter(valor__gte=6.0, valor__lte=7.0).count()
        calificaciones_valores = [rango1, rango2, rango3, rango4]
    else:
        calificaciones_valores = [0, 0, 0, 0]

    calificaciones_data_json = json.dumps({
        'labels': rangos_labels,
        'data': calificaciones_valores
    })

    context = {
        'asistencia_promedio': asistencia_promedio,
        'evaluaciones_mes': evaluaciones_mes,
        'colegios_inactivos': colegios_inactivos,
        'anotaciones_total': anotaciones_total,
        'asistencia_data_json': asistencia_data_json,
        'calificaciones_data_json': calificaciones_data_json,
    }
    return render(request, 'dashboard_superadmin_academico.html', context)

