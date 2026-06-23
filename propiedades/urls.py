from django.urls import path

from . import views

urlpatterns = [
    path("propiedades/", views.listar_propiedades, name="listar_propiedades"),
    path("barrios/", views.listar_barrios, name="listar_barrios"),
    path("estadisticas/", views.estadisticas, name="estadisticas"),
    path("predecir/", views.predecir_precio, name="predecir_precio"),
    path("cargar-csv/", views.cargar_csv, name="cargar_csv"),
    path("modelo-info/", views.info_modelo, name="info_modelo"),
]
