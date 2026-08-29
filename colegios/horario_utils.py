import datetime
from django.utils import timezone
from .models import BloqueHorario, HorarioClase, Asignatura, SeccionCurso, CursoColegio
from django.contrib.auth.models import User

def inicializar_bloques_horario(colegio):
    """
    Inicializa los bloques horarios estándares de la jornada escolar chilena (8:00 a 15:15)
    si aún no existen en el establecimiento.
    """
    if BloqueHorario.objects.filter(colegio=colegio).exists():
        return BloqueHorario.objects.filter(colegio=colegio).order_by('orden', 'hora_inicio')

    bloques_base = [
        (1, "1° Bloque", datetime.time(8, 0), datetime.time(8, 45), "clase", 1),
        (2, "2° Bloque", datetime.time(8, 45), datetime.time(9, 30), "clase", 2),
        (0, "Recreo Mañana", datetime.time(9, 30), datetime.time(9, 45), "recreo", 3),
        (3, "3° Bloque", datetime.time(9, 45), datetime.time(10, 30), "clase", 4),
        (4, "4° Bloque", datetime.time(10, 30), datetime.time(11, 15), "clase", 5),
        (0, "Recreo Mediodía", datetime.time(11, 15), datetime.time(11, 30), "recreo", 6),
        (5, "5° Bloque", datetime.time(11, 30), datetime.time(12, 15), "clase", 7),
        (6, "6° Bloque", datetime.time(12, 15), datetime.time(13, 0), "clase", 8),
        (0, "Almuerzo Escolar", datetime.time(13, 0), datetime.time(13, 45), "almuerzo", 9),
        (7, "7° Bloque", datetime.time(13, 45), datetime.time(14, 30), "clase", 10),
        (8, "8° Bloque", datetime.time(14, 30), datetime.time(15, 15), "clase", 11),
    ]

    for num, nombre, h_ini, h_fin, tipo, ord_n in bloques_base:
        BloqueHorario.objects.create(
            colegio=colegio,
            numero_bloque=num,
            nombre=nombre,
            hora_inicio=h_ini,
            hora_fin=h_fin,
            tipo=tipo,
            orden=ord_n,
            activo=True
        )

    return BloqueHorario.objects.filter(colegio=colegio).order_by('orden', 'hora_inicio')


def obtener_datos_horario_docente(colegio, docente, dia_semana_forzado=None):
    """
    Retorna un diccionario completo con la agenda y horario semanal del docente,
    incluyendo clases de hoy, matriz semanal Lunes a Viernes, horas pedagógicas y estado en vivo.
    """
    if not colegio or not docente:
        return {}

    bloques = inicializar_bloques_horario(colegio)
    
    # Obtener todas las clases activas del docente
    clases_docente_qs = HorarioClase.objects.filter(
        colegio=colegio,
        docente=docente,
        activo=True
    ).select_related('seccion__curso', 'asignatura', 'bloque')

    # Identificar día de la semana actual (1=Lunes .. 7=Domingo)
    hoy = timezone.now()
    dia_actual_num = dia_semana_forzado or hoy.isoweekday()
    es_fin_de_semana = dia_actual_num in [6, 7]

    nombres_dias = {
        1: 'Lunes',
        2: 'Martes',
        3: 'Miércoles',
        4: 'Jueves',
        5: 'Viernes',
        6: 'Sábado',
        7: 'Domingo'
    }
    nombre_dia_actual = nombres_dias.get(dia_actual_num, 'Lunes')

    # Clases de hoy para el docente
    clases_hoy_qs = clases_docente_qs.filter(dia_semana=dia_actual_num).order_by('bloque__orden', 'bloque__hora_inicio')
    clases_hoy = list(clases_hoy_qs)

    # Identificar clase en curso o próxima
    hora_actual = hoy.time()
    clase_actual = None
    proxima_clase = None

    for c in clases_hoy:
        if c.bloque.hora_inicio <= hora_actual <= c.bloque.hora_fin:
            clase_actual = c
            break
        elif c.bloque.hora_inicio > hora_actual and not proxima_clase:
            proxima_clase = c

    # Construir Matriz Semanal (Lunes a Viernes)
    # Mapa rápido: (bloque_id, dia_semana) -> HorarioClase
    mapa_clases = {}
    for c in clases_docente_qs:
        mapa_clases[(c.bloque_id, c.dia_semana)] = c

    dias_semana_columnas = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes')
    ]

    matriz_semanal = []
    for blk in bloques:
        fila = {
            'bloque': blk,
            'es_recreo': blk.tipo == 'recreo',
            'es_almuerzo': blk.tipo == 'almuerzo',
            'es_clase': blk.tipo == 'clase',
            'celdas': []
        }
        for dia_num, dia_nom in dias_semana_columnas:
            clase_slot = mapa_clases.get((blk.id, dia_num))
            fila['celdas'].append({
                'dia_num': dia_num,
                'dia_nom': dia_nom,
                'es_hoy': dia_num == dia_actual_num,
                'clase': clase_slot
            })
        matriz_semanal.append(fila)

    # Construir mapa de clases por día de la semana (1 a 5) con enriquecimiento de estado
    clases_por_dia = {1: [], 2: [], 3: [], 4: [], 5: []}
    for dia_n in range(1, 6):
        dia_clases = list(clases_docente_qs.filter(dia_semana=dia_n).order_by('bloque__orden', 'bloque__hora_inicio'))
        for c in dia_clases:
            if dia_n == dia_actual_num:
                if c.bloque.hora_inicio <= hora_actual <= c.bloque.hora_fin:
                    c.estado_tiempo = 'en_curso'
                    c.estado_badge = '🟢 En Curso'
                    c.estado_badge_class = 'badge-live-now'
                elif c.bloque.hora_inicio > hora_actual:
                    if proxima_clase and proxima_clase.id == c.id:
                        c.estado_tiempo = 'proxima'
                        c.estado_badge = '⏳ Próxima'
                        c.estado_badge_class = 'badge-next-up'
                    else:
                        c.estado_tiempo = 'programada'
                        c.estado_badge = '📌 Por Iniciar'
                        c.estado_badge_class = 'badge-scheduled'
                else:
                    c.estado_tiempo = 'finalizada'
                    c.estado_badge = '✅ Completada'
                    c.estado_badge_class = 'badge-completed'
            else:
                c.estado_tiempo = 'programada'
                c.estado_badge = '📌 Programada'
                c.estado_badge_class = 'badge-scheduled'
        clases_por_dia[dia_n] = dia_clases

    # Estadísticas resumen del docente
    total_horas_semanales = clases_docente_qs.count() # Cada bloque de clase = 1 hora pedagógica (45 min)
    cursos_distintos = set(c.seccion.nombre for c in clases_docente_qs)
    asignaturas_distintas = set(c.asignatura.nombre for c in clases_docente_qs)

    return {
        'docente': docente,
        'nombre_docente': docente.get_full_name() or docente.username,
        'dia_actual_num': dia_actual_num,
        'nombre_dia_actual': nombre_dia_actual,
        'es_fin_de_semana': es_fin_de_semana,
        'clases_hoy': clases_hoy,
        'clases_hoy_count': len(clases_hoy),
        'clase_actual': clase_actual,
        'proxima_clase': proxima_clase,
        'matriz_semanal': matriz_semanal,
        'clases_por_dia': clases_por_dia,
        'dias_semana_columnas': dias_semana_columnas,
        'total_horas_semanales': total_horas_semanales,
        'total_cursos_count': len(cursos_distintos),
        'cursos_nombres': list(cursos_distintos),
        'asignaturas_nombres': list(asignaturas_distintas),
        'bloques': bloques,
    }

