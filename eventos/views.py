from django.utils import timezone
from django.views.generic import DetailView, ListView

from eventos.models import Evento


class EventoListView(ListView):
    template_name = 'eventos/evento_list.html'
    context_object_name = 'eventos'
    queryset = (
        Evento.objects.all()
    )


class EventoDetailView(DetailView):
    """Programação pública do evento: não exige login (RF3)."""
    model = Evento
    context_object_name = 'evento'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        atividades = list(self.object.atividades.com_vagas().select_related('sala'))
        # O dia é calculado no fuso local: 22h em Recife já é o dia seguinte em UTC.
        for atividade in atividades:
            atividade.dia = timezone.localtime(atividade.data_hora_inicio).date()
        contexto['atividades'] = atividades
        contexto['eh_organizador'] = self.object.organizador_id == self.request.user.id
        return contexto
