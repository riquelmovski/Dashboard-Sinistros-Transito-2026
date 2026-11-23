"""
Arquivo: dashboard/urls.py
Descrição: Arquitetura de rotas multipáginas do Observatório de Sinistros (PRF).
           - Visão Geral Executiva (Bento Grid)
           - Mapa Geoespacial Dedicado
           - Rodovias e Trechos Críticos
           - Fator Humano e Cinemática de Colisão
           - Inteligência Temporal e Clima
           - API GeoJSON e Exportação de Relatório CSV
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Rota 1: Dashboard Principal (Bento Grid)
    path('', views.index, name='index'),
    
    # Rota 2: Mapa Geoespacial Interativo Dedicado
    path('mapa/', views.mapa, name='mapa'),
    
    # Rota 3: Rodovias e Trechos Críticos
    path('rodovias/', views.rodovias, name='rodovias'),
    
    # Rota 4: Fator Humano e Dinâmica dos Sinistros
    path('causas/', views.causas, name='causas'),
    
    # Rota 5: Inteligência Temporal e Clima
    path('temporal/', views.temporal, name='temporal'),
    
    # Rotas de Suporte / APIs
    path('api/geojson/', views.geojson_brasil, name='geojson_brasil'),
    path('exportar/', views.export_csv, name='export_csv'),
]
