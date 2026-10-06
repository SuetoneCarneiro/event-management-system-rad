from django.urls import path

from eventos.views import EventoListView

app_name = 'eventos'

# estava assim: path('', EventoListView.as_view(template_name='eventos/evento_list.html'), name='lista')
# mas evento_list.html já é o template padrão do ListView, então não precisa passar o template_name 
# (formato: <app>/<model>_list.html)
urlpatterns = [
    path('', EventoListView.as_view(), name='lista'),
]
