from django.core.management.base import BaseCommand
from planes.models import Modulo, Plan
from colegios.models import Permiso, RolColegio, RolPermiso

class Command(BaseCommand):
    help = 'Sembrar datos iniciales para Eduteka (Módulos, Planes, Permisos, Roles Base)'

    def handle(self, *args, **options):
        self.stdout.write('Sembrando módulos...')
        # Alineados con el template registrocolegiopaso2.html
        modulos_data = [
            ('Libro de clases', 'bi-book'),
            ('Asistencia', 'bi-person-check'),
            ('Perfil del estudiante', 'bi-person-vcard'),
            ('Calendario', 'bi-calendar-event'),
            ('Reportes y analíticas', 'bi-bar-chart'),
            ('Finanzas', 'bi-calculator'),
            ('Proveedores', 'bi-truck'),
            ('SIMCE', 'bi-clipboard-data'),
            ('Comunicación', 'bi-chat-dots'),
            ('Comportamiento', 'bi-emoji-smile'),
            ('Configuración avanzada', 'bi-gear'),
        ]
        
        modulos_objs = {}
        for nombre, icono in modulos_data:
            mod, created = Modulo.objects.get_or_create(
                nombre=nombre,
                defaults={'icono': icono, 'activo': True}
            )
            modulos_objs[nombre] = mod
            if created:
                self.stdout.write(f'  - Módulo "{nombre}" creado.')

        self.stdout.write('Sembrando planes...')
        planes_data = [
            ('Básico', 49900, 499000, False, ['Libro de clases', 'Asistencia', 'Perfil del estudiante', 'Reportes y analíticas']),
            ('Profesional', 89900, 899000, True, ['Libro de clases', 'Asistencia', 'Perfil del estudiante', 'Reportes y analíticas', 'Calendario']),
            ('Institucional', 149900, 1499000, False, ['Libro de clases', 'Asistencia', 'Perfil del estudiante', 'Reportes y analíticas', 'Calendario', 'Finanzas', 'Proveedores', 'SIMCE']),
            ('Personalizado', 0, 0, False, []),
        ]

        for nombre, mensual, anual, recomendado, mods in planes_data:
            plan, created = Plan.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'precio_mensual': mensual,
                    'precio_anual': anual,
                    'recomendado': recomendado,
                    'activo': True
                }
            )
            if mods:
                plan.modulos.set([modulos_objs[m] for m in mods])
            if created:
                self.stdout.write(f'  - Plan "{nombre}" creado.')

        self.stdout.write('Sembrando permisos...')
        permisos_data = [
            ('ver', 'Ver', 'Puede visualizar la información del módulo.'),
            ('crear', 'Crear', 'Puede registrar nuevos datos.'),
            ('editar', 'Editar', 'Puede modificar registros existentes.'),
            ('eliminar', 'Eliminar', 'Puede quitar registros del sistema.'),
            ('exportar', 'Exportar', 'Puede descargar reportes en PDF/Excel.'),
            ('aprobar', 'Aprobar', 'Puede autorizar solicitudes o procesos.'),
            ('enviar_mensajes', 'Enviar Mensajes', 'Puede enviar notificaciones o correos.'),
            ('administrar', 'Administrar', 'Acceso total a la configuración del módulo.'),
        ]

        for codigo, nombre, desc in permisos_data:
            perm, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'descripcion': desc}
            )
            if created:
                self.stdout.write(f'  - Permiso "{nombre}" creado.')

        self.stdout.write('Sembrando roles base (plantillas)...')
        roles_base = [
            ('Administrador', 'Acceso total al sistema y configuración del colegio.'),
            ('Director', 'Supervisión general y reportes institucionales.'),
            ('Inspector', 'Gestión de asistencia y comportamiento.'),
            ('Profesor', 'Gestión de clases, notas y asistencia de sus cursos.'),
            ('Administrativo', 'Apoyo en tareas de secretaría y finanzas.'),
            ('Contabilidad', 'Gestión de pagos y finanzas.'),
            ('Apoderado', 'Consulta de información de su pupilo.'),
        ]

        for nombre, desc in roles_base:
            rol, created = RolColegio.objects.get_or_create(
                nombre=nombre,
                colegio=None,
                defaults={'descripcion': desc, 'es_base': True, 'activo': True}
            )
            
            # Asignar permisos por defecto a los roles base
            if created:
                for mod in Modulo.objects.all():
                    rp, _ = RolPermiso.objects.get_or_create(rol=rol, modulo=mod)
                    if nombre == 'Administrador':
                        rp.puede_ver = rp.puede_crear = rp.puede_editar = rp.puede_eliminar = \
                        rp.puede_exportar = rp.puede_aprobar = rp.puede_enviar_mensajes = \
                        rp.puede_administrar = True
                    elif nombre == 'Profesor':
                        if mod.nombre in ['Libro de clases', 'Asistencia', 'Perfil del estudiante', 'Calendario']:
                            rp.puede_ver = rp.puede_crear = rp.puede_editar = rp.puede_exportar = True
                        else:
                            rp.puede_ver = True
                    rp.save()
                self.stdout.write(f'  - Rol base "{nombre}" creado con permisos predefinidos.')

        self.stdout.write(self.style.SUCCESS('Seed completado exitosamente.'))
