from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('descargar_excel/', views.descargar_excel, name='descargar_excel'),
    path('eliminar_preview/', views.eliminar_preview, name='eliminar_preview'),
]