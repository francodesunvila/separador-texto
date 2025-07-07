from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('descargar_directo/<int:bloque_id>/', views.descargar_directo, name='descargar_directo'),
    path('eliminar_preview/', views.eliminar_preview, name='eliminar_preview'),
]