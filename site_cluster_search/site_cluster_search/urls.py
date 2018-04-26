from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('cluster_search/', include('cluster_search.urls')),
    path('admin/', admin.site.urls),
  ]
