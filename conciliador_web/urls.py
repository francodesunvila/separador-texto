from django.contrib import admin
from django.urls import path, include  # 👈 incluimos 'include'

urlpatterns = [
    path('', include('procesador.urls')),  # 👈 apuntamos a las rutas de tu app
    path('admin/', admin.site.urls),
]
