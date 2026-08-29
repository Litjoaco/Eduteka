from django.shortcuts import render
from planes.models import Plan

def landing_page(request):
    planes = Plan.objects.filter(activo=True).prefetch_related('modulos').order_by('precio_mensual')
    return render(request, 'landingpage.html', {'planes': planes})


def terminos_privacidad_view(request):
    return render(request, 'terminos_privacidad.html')
