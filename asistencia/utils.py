from colegios.models import Estudiante
from asistencia.models import DetalleAsistencia
from django.db.models import Count, Q

def calcular_alumnos_en_riesgo(colegio):
    """
    Calcula dinámicamente qué alumnos tienen un porcentaje de asistencia menor al 85%.
    Utiliza agregaciones nativas de Django para optimizar la consulta SQL.
    """
    estudiantes = Estudiante.objects.filter(colegio=colegio, activo=True).annotate(
        total_clases=Count('detalles_asistencia'),
        presentes_tardes_justificados=Count(
            'detalles_asistencia',
            filter=Q(detalles_asistencia__estado__in=['presente', 'tarde', 'justificado'])
        ),
        faltas=Count(
            'detalles_asistencia',
            filter=Q(detalles_asistencia__estado='ausente')
        )
    ).select_related('seccion')
    
    from colegios.models import ConfiguracionAcademica
    periodo = ConfiguracionAcademica.objects.filter(colegio=colegio).first()
    porcentaje_minimo = float(periodo.porcentaje_asistencia_minima) if (periodo and periodo.porcentaje_asistencia_minima) else 85.0

    alumnos_en_riesgo = []
    for est in estudiantes:
        if est.total_clases > 0:
            tasa = (est.presentes_tardes_justificados / est.total_clases) * 100
            if tasa < porcentaje_minimo:
                alumnos_en_riesgo.append({
                    'estudiante': est,
                    'tasa': round(tasa, 1),
                    'porcentaje_asistencia': round(tasa, 1),
                    'faltas': est.faltas,
                    'total_inasistencias': est.faltas,
                    'negativas_count': est.faltas,
                })
    return alumnos_en_riesgo


