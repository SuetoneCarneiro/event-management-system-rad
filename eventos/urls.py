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
    path('eventos/<int:evento_pk>/atividades/nova/', views.AtividadeCreateView.as_view(), name='atividade_criar'),
    path('atividades/<int:pk>/editar/', views.AtividadeUpdateView.as_view(), name='atividade_editar'),
    path('atividades/<int:pk>/excluir/', views.AtividadeDeleteView.as_view(), name='atividade_excluir'),
    path('meus-eventos/', views.meus_eventos, name='meus_eventos'),
]
