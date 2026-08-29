# Walkthrough: Implementación de Leccionario Digital & Módulo PIE (Inclusión Escolar)

Se implementaron exitosamente y al 100% los dos nuevos módulos en **Eduteka**:
1. **Módulo 1: Leccionario Digital & Planificación Curricular Clase a Clase** (con Firma Electrónica por PIN y Auditoría UTP).
2. **Módulo 2: Módulo PIE - Programa de Integración Escolar / NEE** (Decretos 170 y 83 MINEDUC, Fichas de Estudiantes, Bitácora de Especialistas y Generador de PACI Oficial en PDF).

---

## 1. Módulo 1: Leccionario Digital & Planificaciones Curriculares

### A. Modelos de Base de Datos
- **`RegistroLeccionario`** ([colegios/models.py](file:///c:/Users/joaqu/Desktop/eduteka/colegios/models.py)):
  - Campos: `colegio`, `horario_clase`, `seccion`, `asignatura`, `docente`, `bloque`, `fecha`, `oa_codigo`, `contenido_tratado`, `actividad_tipo`, `observaciones`, `firmado`, `fecha_firma`, `hash_firma`.
  - Generación de **Hash SHA-256** para sellado y no-repudio legal.
- **`PlanificacionCurricular`** ([colegios/models.py](file:///c:/Users/joaqu/Desktop/eduteka/colegios/models.py)):
  - Campos: `colegio`, `asignatura`, `seccion`, `docente`, `titulo_unidad`, `semestre`, `anio_lectivo`, `fecha_inicio`, `fecha_termino`, `oas_curriculares`, `estrategias_metodologicas`, `evaluacion_descripcion`, `estado`, `feedback_utp`, `revisado_por_utp`, `fecha_revision_utp`.

### B. Vistas y Plantillas
- **Hub de Leccionario** (`/colegios/leccionario/`):
  - Semáforo y barra de cumplimiento del día (`X / Total Clases`).
  - Tarjetas de clases del día con estado (`Firmado` / `Pendiente`).
  - Modal de firma digital y registro de contenidos.
  - Tabla de auditoría fiscalizable con filtros de fecha, curso, materia y docente.
- **Planificaciones Curriculares** (`/colegios/planificaciones/`):
  - Tablero de unidades didácticas por semestre.
  - Modal de creación y envío a UTP.
  - Modal de auditoría UTP con dictamen (`Aprobada`, `Observada`, `En Revisión`) y retroalimentación pedagógica.
- **Botón Directo en el Horario Docente**:
  - En las tarjetas del dashboard se incorporaron dos botones: `Asistencia` y `Leccionario`.

---

## 2. Módulo 2: Programa de Integración Escolar (PIE / NEE)

### A. Modelos de Base de Datos
- **`FichaEstudiantePIE`** ([colegios/models.py](file:///c:/Users/joaqu/Desktop/eduteka/colegios/models.py)):
  - Clasificación según **Decreto 170 MINEDUC**:
    - **NEET (Transitorias)**: DEA, TEL Expresivo/Mixto, TDA/TDAH, FIL.
    - **NEEP (Permanentes)**: TEA, Discapacidad Intelectual, Visual, Auditiva, Motora, Multidéficit.
  - Asignación de Educadora Diferencial / Especialista a cargo, fechas de ingreso y reevaluación.
- **`AtencionEspecialistaPIE`** ([colegios/models.py](file:///c:/Users/joaqu/Desktop/eduteka/colegios/models.py)):
  - Bitácora de intervenciones por Psicóloga, Fonoaudióloga, Terapeuta Ocupacional o Educadora Diferencial.
  - Modalidad: *Aula de Recursos*, *Aula Regular (Co-Docencia)*, *Sesión Individual*, *Entrevista Apoderado*.
- **`PlanAdecuacionCurricular (PACI)`** ([colegios/models.py](file:///c:/Users/joaqu/Desktop/eduteka/colegios/models.py)):
  - Adecuaciones de **Acceso** (tiempo adicional, materiales adaptados, espacio de evaluación).
  - Adecuaciones de **Objetivos** (graduación de complejidad, priorización de OAs basales).
  - **Evaluación diferenciada** y aprobación de UTP.

### B. Vistas y Plantillas
- **PIE Dashboard** (`/colegios/pie/`):
  - KPIs: Total Matrícula PIE, Alumnos NEET, Alumnos NEEP, Planes PACI Activos.
  - Búsqueda y filtrado dinámico por RUT, nombre o diagnóstico.
  - Modal de ingreso de nuevo estudiante al programa.
- **Ficha 360° del Estudiante PIE** (`/colegios/pie/estudiante/<id>/`):
  - Tab 1: Diagnóstico clínico y contacto de emergencia del apoderado.
  - Tab 2: Bitácora cronológica de atenciones y sesiones de especialistas.
  - Tab 3: Gestor y editor del Plan PACI.
- **Expediente Imprimible PACI Oficial** (`/colegios/pie/estudiante/<id>/imprimir-paci/`):
  - Documento formal estructurado según la normativa del MINEDUC y la Superintendencia de Educación, con membrete institucional y recuadros para firmas de la Especialista PIE, Jefatura UTP y Apoderado.

---

## 3. Menú Lateral (Sidebar)
Se actualizaron los accesos en el Sidebar institucional ([templates/colegios/_sidebar.html](file:///c:/Users/joaqu/Desktop/eduteka/templates/colegios/_sidebar.html)):
- **Gestión de Aula & Alumnos**:
  - `Leccionario Digital` (`bi-journal-check`)
  - `Programa PIE (NEE)` (`bi-puzzle-fill`)
- **Planificación & Análisis**:
  - `Planificaciones Curriculares` (`bi-card-checklist`)

---

## 4. Pruebas y Validación Automatizada
Se ejecutó la suite `scratch/test_leccionario_and_pie.py`:
- [OK] Leccionario Hub y firma criptográfica con hash SHA-256: **100% Aprobado**.
- [OK] Creación y auditoría de Planificación Curricular por UTP: **100% Aprobado**.
- [OK] Registro de estudiante PIE y diagnósticos NEET/NEEP: **100% Aprobado**.
- [OK] Bitácora de atenciones de especialistas y creación de PACI: **100% Aprobado**.
- [OK] Aprobación UTP del PACI y renderizado del documento oficial imprimible: **100% Aprobado**.
