from django.urls import path

from eventos import views

app_name = 'eventos'

# estava assim: path('', EventoListView.as_view(template_name='eventos/evento_list.html'), name='lista')
# mas evento_list.html já é o template padrão do ListView, então não precisa passar o template_name
# (formato: <app>/<model>_list.html)
urlpatterns = [
    path('', views.EventoListView.as_view(), name='lista'),
    path('eventos/novo/', views.EventoCreateView.as_view(), name='criar'),
    path('eventos/<int:pk>/', views.EventoDetailView.as_view(), name='detalhe'),
    path('eventos/<int:pk>/editar/', views.EventoUpdateView.as_view(), name='editar'),
    path('eventos/<int:pk>/excluir/', views.EventoDeleteView.as_view(), name='excluir'),
    path('eventos/<int:pk>/painel/', views.PainelEventoView.as_view(), name='painel'),
    path('eventos/<int:evento_pk>/atividades/nova/', views.AtividadeCreateView.as_view(), name='atividade_criar'),
    path('atividades/<int:pk>/editar/', views.AtividadeUpdateView.as_view(), name='atividade_editar'),
    path('atividades/<int:pk>/excluir/', views.AtividadeDeleteView.as_view(), name='atividade_excluir'),
    path('meus-eventos/', views.meus_eventos, name='meus_eventos'),
    path('agenda/', views.AgendaView.as_view(), name='agenda'),
    path('eventos/<int:pk>/inscrever/', views.inscrever_evento, name='inscrever_evento'),
    path('inscricoes/<int:pk>/cancelar/', views.cancelar_inscricao_evento, name='cancelar_inscricao_evento'),
    path('atividades/<int:pk>/inscrever/', views.inscrever_atividade, name='inscrever_atividade'),
    path('inscricoes-atividade/<int:pk>/cancelar/', views.cancelar_inscricao_atividade,
         name='cancelar_inscricao_atividade'),
]
