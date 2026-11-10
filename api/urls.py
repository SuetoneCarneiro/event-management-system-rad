from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'api'

router = DefaultRouter()
router.register('eventos', views.EventoViewSet, basename='evento')
router.register('atividades', views.AtividadeViewSet, basename='atividade')
router.register('salas', views.SalaViewSet, basename='sala')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', obtain_auth_token, name='token'),
    path('inscricoes/', views.inscricoes_evento, name='inscricoes'),
    path('inscricoes/<int:pk>/', views.cancelar_inscricao_evento, name='inscricao-cancelar'),
    path('inscricoes-atividade/', views.inscrever_atividade, name='inscricoes-atividade'),
    path('inscricoes-atividade/<int:pk>/', views.cancelar_inscricao_atividade, name='inscricao-atividade-cancelar'),
    path('agenda/', views.agenda, name='agenda'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='docs'),
]
