from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Plan
from .forms import PlanForm

@login_required
def editar_plan(request, pk):
    plan = get_object_or_404(Plan, pk=pk)

    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f"El plan '{plan.nombre}' ha sido actualizado con éxito.")
            return redirect('dashboard_superadmin_planes')
        else:
            messages.error(request, "Por favor corrija los errores en el formulario.")
    else:
        form = PlanForm(instance=plan)

    return render(request, 'planes/editar_plan.html', {'form': form, 'plan': plan})


@login_required
def crear_plan(request):
    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"El plan '{plan.nombre}' ha sido creado exitosamente.")
            return redirect('dashboard_superadmin_planes')
        else:
            messages.error(request, "Por favor corrija los errores en el formulario.")
    else:
        form = PlanForm()

    return render(request, 'planes/crear_plan.html', {'form': form})


from django.views.decorators.http import require_POST


@login_required
@require_POST
def eliminar_plan(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    nombre = plan.nombre
    plan.delete()
    messages.success(request, f"El plan '{nombre}' ha sido eliminado correctamente.")
    return redirect('dashboard_superadmin_planes')


