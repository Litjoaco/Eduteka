"""
URL configuration for Eduteka project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from inicio import views
from colegios import views as colegios_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing_page'),
    
    path('usuarios/', include('usuarios.urls')),
    path('colegios/', include('colegios.urls')),
    path('solicitudes/', include('solicitudes.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('asistencia/', include('asistencia.urls')),
    path('calificaciones/', include('calificaciones.urls')),
    path('planes/', include('planes.urls')),
    path('api/buscar-colegios/', colegios_views.api_buscar_colegios, name='api_buscar_colegios'),
    path('terminos-y-condiciones/', views.terminos_privacidad_view, name='terminos_condiciones'),
    path('politica-privacidad/', views.terminos_privacidad_view, name='politica_privacidad'),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
