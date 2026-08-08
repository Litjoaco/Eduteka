"""
Comando Django: seed_colegios
Crea colegios ficticios con suscripciones para poblar la base de datos
y probar los filtros del dashboard de estadísticas.

Uso:
    python manage.py seed_colegios              # Crea 30 colegios (sin borrar los anteriores)
    python manage.py seed_colegios --cantidad 50
    python manage.py seed_colegios --limpiar    # Borra colegios de prueba anteriores y recrea
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

from colegios.models import Colegio, Suscripcion
from planes.models import Plan


# ──────────────────────────────────────────────────────────────────────────────
# Datos ficticios localizados para Chile
# ──────────────────────────────────────────────────────────────────────────────

PREFIJOS = [
    "Liceo", "Colegio", "Escuela Básica", "Instituto", "Escuela Municipal",
    "Centro Educacional", "Colegio Particular", "Academia", "Escuela",
    "Instituto Profesional",
]

NOMBRES = [
    "Santa María", "Los Alerces", "El Porvenir", "Bello Horizonte",
    "San Agustín", "La Esperanza", "Los Andes", "El Bosque", "La Araucaria",
    "Nueva Estrella", "San Francisco", "Los Tilos", "Villa Alegre",
    "Las Américas", "El Roble", "Puerto Nuevo", "San Martín", "Las Palmas",
    "Libertad", "El Litre", "Valle Verde", "Las Violetas", "San Juan",
    "El Alerce", "La Montaña", "San Pedro", "Las Rosas", "El Naranjal",
    "Nueva Luz", "Colón", "Los Pinos", "La Colina", "San Miguel",
    "El Coihue", "Las Lilas", "Villa del Mar", "Los Boldos",
]

REGIONES = [
    "Región Metropolitana",
    "Valparaíso",
    "Biobío",
    "La Araucanía",
    "Los Lagos",
    "Antofagasta",
    "O'Higgins",
    "Maule",
    "Los Ríos",
    "Coquimbo",
    "Atacama",
    "Tarapacá",
    "Aysén",
    "Magallanes",
    "Arica y Parinacota",
    "Ñuble",
]

CIUDADES_POR_REGION = {
    "Región Metropolitana": ["Santiago", "Puente Alto", "Maipú", "La Florida", "Las Condes", "Peñalolén", "Ñuñoa"],
    "Valparaíso": ["Valparaíso", "Viña del Mar", "Quilpué", "Villa Alemana", "San Antonio"],
    "Biobío": ["Concepción", "Talcahuano", "Chillán", "Los Ángeles", "Coronel"],
    "La Araucanía": ["Temuco", "Padre Las Casas", "Angol", "Nueva Imperial"],
    "Los Lagos": ["Puerto Montt", "Osorno", "Castro", "Ancud", "Puerto Varas"],
    "Antofagasta": ["Antofagasta", "Calama", "Tocopilla", "Mejillones"],
    "O'Higgins": ["Rancagua", "San Fernando", "Machalí", "Rengo"],
    "Maule": ["Talca", "Curicó", "Linares", "Constitución"],
    "Los Ríos": ["Valdivia", "La Unión", "Río Bueno"],
    "Coquimbo": ["La Serena", "Coquimbo", "Ovalle", "Illapel"],
    "Atacama": ["Copiapó", "Caldera", "Vallenar"],
    "Tarapacá": ["Iquique", "Alto Hospicio"],
    "Aysén": ["Coyhaique", "Puerto Aysén"],
    "Magallanes": ["Punta Arenas", "Puerto Natales"],
    "Arica y Parinacota": ["Arica", "Putre"],
    "Ñuble": ["Chillán", "San Carlos", "Bulnes"],
}

TIPOS = ["municipal", "subvencionado", "particular", "instituto"]
CANTIDADES = ["menos_100", "100_300", "301_600", "mas_600"]
FACTURACION = ["mensual", "anual"]
ESTADOS_SUSCRIPCION = ["activa", "activa", "activa", "pendiente_pago", "vencida"]  # ponderado
ESTADOS_COLEGIO = ["activo", "activo", "activo", "pendiente_pago", "inactivo"]

# Dominos de correo ficticios
DOMINIOS = [
    "educ.cl", "colegio.cl", "escuela.cl", "liceo.cl",
    "instituto.cl", "enseñanza.cl", "academia.cl",
]

# Marca para identificar registros de prueba
SEED_MARKER = "[SEED]"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def nombre_aleatorio():
    prefijo = random.choice(PREFIJOS)
    nombre  = random.choice(NOMBRES)
    sufijo  = random.choice(["", " de Chile", " del Norte", " del Sur", ""])
    return f"{prefijo} {nombre}{sufijo}".strip()


def correo_desde_nombre(nombre: str) -> str:
    slug = nombre.lower()
    for ch in " áéíóúñ":
        slug = slug.replace(ch, "")
    slug = slug[:20]
    dominio = random.choice(DOMINIOS)
    return f"admin@{slug}.{dominio}"


def fecha_aleatoria_ultimos_n_meses(meses: int = 6):
    """Devuelve un datetime aware aleatorio dentro de los últimos N meses."""
    ahora = timezone.now()
    dias_atras = random.randint(1, meses * 30)
    return ahora - timedelta(days=dias_atras)


# ──────────────────────────────────────────────────────────────────────────────
# Comando
# ──────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        "Puebla la BD con colegios ficticios y sus suscripciones para probar "
        "los filtros del dashboard de estadísticas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--cantidad",
            type=int,
            default=30,
            help="Número de colegios a crear (default: 30)",
        )
        parser.add_argument(
            "--limpiar",
            action="store_true",
            default=False,
            help="Eliminar los colegios de prueba anteriores antes de crear nuevos.",
        )
        parser.add_argument(
            "--meses",
            type=int,
            default=6,
            help="Rango de meses hacia atrás para distribuir las fechas (default: 6)",
        )

    def handle(self, *args, **options):
        cantidad = options["cantidad"]
        limpiar  = options["limpiar"]
        meses    = options["meses"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n🌱  Eduteka — Seed de Colegios de Prueba\n" + "─" * 45
        ))

        # ── 1. Limpieza opcional ───────────────────────────────────────────
        if limpiar:
            anteriores = Colegio.objects.filter(nombre__startswith=SEED_MARKER)
            total_borrados = anteriores.count()
            anteriores.delete()
            self.stdout.write(self.style.WARNING(
                f"  ✗  {total_borrados} colegios de prueba anteriores eliminados."
            ))

        # ── 2. Verificar que existan planes ───────────────────────────────
        planes = list(Plan.objects.filter(activo=True))
        if not planes:
            self.stdout.write(self.style.ERROR(
                "  ✗  No se encontraron planes activos en la base de datos.\n"
                "     Crea al menos un Plan antes de ejecutar este seed.\n"
                "     Tip: Ve a /admin y crea planes Básico, Estándar, Premium."
            ))
            return

        self.stdout.write(
            f"  ✓  {len(planes)} plan(es) encontrado(s): "
            + ", ".join(f"«{p.nombre}»" for p in planes)
        )

        # ── 3. Obtener o crear usuario administrador dummy ─────────────────
        admin_user, _ = User.objects.get_or_create(
            username="seed_admin",
            defaults={
                "first_name": "Admin",
                "last_name":  "Seed",
                "email":      "seed@eduteka.cl",
                "is_active":  False,
            },
        )

        # ── 4. Crear colegios ──────────────────────────────────────────────
        creados = 0
        errores = 0

        self.stdout.write(f"  ⏳  Creando {cantidad} colegios...\n")

        with transaction.atomic():
            for i in range(cantidad):
                try:
                    # Región y ciudad coherentes
                    region  = random.choice(REGIONES)
                    ciudad  = random.choice(CIUDADES_POR_REGION.get(region, ["Ciudad Desconocida"]))

                    nombre  = f"{SEED_MARKER} {nombre_aleatorio()}"
                    correo  = correo_desde_nombre(nombre)
                    fecha   = fecha_aleatoria_ultimos_n_meses(meses)

                    # Crear el Colegio
                    colegio = Colegio(
                        nombre                 = nombre,
                        nombre_administrador   = f"Director(a) {random.choice(['García','López','Martínez','Rodríguez','Muñoz','González','Perez'])}",
                        correo_institucional   = correo,
                        telefono               = f"+569{random.randint(10000000, 99999999)}",
                        ciudad_comuna          = ciudad,
                        tipo_institucion       = random.choice(TIPOS),
                        cantidad_alumnos       = random.choice(CANTIDADES),
                        region                 = region,
                        pais                   = "Chile",
                        direccion              = f"Av. {random.choice(NOMBRES)} #{random.randint(100,9999)}, {ciudad}",
                        estado                 = random.choice(ESTADOS_COLEGIO),
                        configuracion_completa = random.choice([True, True, False]),
                        administrador          = admin_user,
                    )

                    # Guardar sin auto_now_add para poder manipular fechas
                    colegio.save()

                    # Retroceder la fecha_creacion manualmente usando update
                    Colegio.objects.filter(pk=colegio.pk).update(fecha_creacion=fecha)

                    # Crear Suscripcion asociada
                    plan = random.choice(planes)
                    tipo_fact = random.choice(FACTURACION)
                    monto_base = plan.precio_mensual if tipo_fact == "mensual" else plan.precio_anual
                    fecha_inicio_subs = fecha.date()
                    meses_duracion = 1 if tipo_fact == "mensual" else 12
                    fecha_fin_subs = fecha_inicio_subs + timedelta(days=30 * meses_duracion)

                    Suscripcion.objects.create(
                        colegio         = colegio,
                        plan            = plan,
                        tipo_facturacion= tipo_fact,
                        monto           = monto_base,
                        estado          = random.choice(ESTADOS_SUSCRIPCION),
                        fecha_inicio    = fecha_inicio_subs,
                        fecha_fin       = fecha_fin_subs,
                    )

                    creados += 1
                    # Progreso visual cada 10 registros
                    if (i + 1) % 10 == 0 or (i + 1) == cantidad:
                        self.stdout.write(f"    [{i+1:>3}/{cantidad}] ✓ {nombre[:55]}")

                except Exception as exc:
                    errores += 1
                    self.stdout.write(self.style.ERROR(f"    [{i+1:>3}/{cantidad}] ✗ Error: {exc}"))

        # ── 5. Resumen ─────────────────────────────────────────────────────
        self.stdout.write("\n" + "─" * 45)
        self.stdout.write(self.style.SUCCESS(f"  ✅  {creados} colegios creados exitosamente."))
        if errores:
            self.stdout.write(self.style.ERROR(f"  ⚠️   {errores} errores durante la creación."))

        # Estadísticas rápidas por plan
        self.stdout.write(self.style.MIGRATE_HEADING("\n  📊  Distribución por plan (seed actual):"))
        for plan in planes:
            total = Suscripcion.objects.filter(
                plan=plan,
                colegio__nombre__startswith=SEED_MARKER
            ).count()
            bar = "█" * total
            self.stdout.write(f"      {plan.nombre:<12} {bar}  ({total})")

        self.stdout.write(self.style.MIGRATE_HEADING("\n  📅  Distribución por región (seed actual):"))
        from collections import Counter
        regiones_usadas = Counter(
            Colegio.objects.filter(nombre__startswith=SEED_MARKER)
            .values_list("region", flat=True)
        )
        for reg, cnt in sorted(regiones_usadas.items(), key=lambda x: -x[1])[:8]:
            self.stdout.write(f"      {(reg or 'Sin región'):<30} {cnt}")

        self.stdout.write(f"\n  💡  Para eliminarlos: python manage.py seed_colegios --limpiar\n")
