/**
 * Eduteka SweetAlert2 Helper - Sistema Universal de Alertas y Confirmaciones
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Toast configurado globalmente
  window.Toast = Swal.mixin({
    toast: true,
    position: "top",
    showConfirmButton: false,
    timer: 3000,
    timerProgressBar: true,

    didOpen: (toast) => {
      toast.addEventListener("mouseenter", Swal.stopTimer);
      toast.addEventListener("mouseleave", Swal.resumeTimer);
    }
  });

  // 2. Interceptador universal de confirmación para enlaces y botones con clase .js-confirm
  document.body.addEventListener("click", function (e) {
    const target = e.target.closest(".js-confirm-delete, [data-confirm]");
    if (target) {
      e.preventDefault();

      const href = target.getAttribute("href");
      const title = target.getAttribute("data-confirm-title") || "¿Estás seguro?";
      const text = target.getAttribute("data-confirm-text") || "Esta acción no se podrá deshacer.";
      const confirmButtonText = target.getAttribute("data-confirm-btn") || "Sí, eliminar";
      const isDanger = target.classList.contains("text-danger") || target.classList.contains("btn-outline-danger") || target.classList.contains("btn-danger");

      Swal.fire({
        title: title,
        text: text,
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: isDanger ? "#E11D48" : "#7C5CFC",
        cancelButtonColor: "#687089",
        confirmButtonText: confirmButtonText,
        cancelButtonText: "Cancelar",
        customClass: {
          popup: "rounded-4 shadow-lg",
          confirmButton: "fw-bold px-4 py-2",
          cancelButton: "fw-bold px-4 py-2"
        }
      }).then((result) => {
        if (result.isConfirmed) {
          if (href && href !== "#") {
            window.location.href = href;
          } else if (target.form) {
            target.form.submit();
          }
        }
      });
    }
  });
});

/**
 * Función disparadora manual para notificaciones Toast
 */
function showEdutekaToast(icon, message) {
  if (window.Toast) {
    window.Toast.fire({
      icon: icon,
      title: message
    });
  }
}
