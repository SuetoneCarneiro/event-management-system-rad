from django.views.generic import ListView

from eventos.models import Evento


class EventoListView(ListView):
    template_name = 'eventos/evento_list.html'
    context_object_name = 'eventos'
    queryset = (
        Evento.objects.all()
    )
