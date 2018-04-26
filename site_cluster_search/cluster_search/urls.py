from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/', views.search, name='search'),
    path('no_cluster_search/', views.no_cluster_search, name='no_cluster_search'),
    path('<domain>/<query>/<cluster_alg>/<summary_alg>/<rank_alg>/results/',
         views.results, name='results'),
    path('<domain>/<query>/no_cluster_results/',
         views.no_cluster_results, name='no_cluster_results'),
    path('scrape_domain/', views.index, name='index'),
  ]
