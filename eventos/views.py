from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from eventos.forms import AtividadeForm, EventoForm
from eventos.models import Atividade, Evento


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


# --- Organizador: autorização em três camadas ---
# 1. LoginRequiredMixin       -> anônimo vai para o login
# 2. PermissionRequiredMixin  -> precisa ser organizador (grupo com a permissão)
# 3. OrganizadorDoEventoMixin -> precisa ser o dono do evento (propriedade, não permissão)
# Usuário logado que falha em 2 ou 3 recebe 403.

class OrganizadorDoEventoMixin(UserPassesTestMixin):
    """Só passa quem criou o evento. Não consulta is_superuser: o admin também é barrado."""

    def get_evento(self):
        raise NotImplementedError

    def test_func(self):
        return self.get_evento().organizador_id == self.request.user.id


class EventoCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = 'eventos.add_evento'
    model = Evento
    form_class = EventoForm
    success_message = 'Evento "%(nome)s" criado.'

    def form_valid(self, form):
        form.instance.organizador = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('eventos:detalhe', args=[self.object.pk])


class EventoDoOrganizadorMixin(OrganizadorDoEventoMixin):
    """Para editar/excluir evento: o próprio evento da URL precisa ser do usuário."""
    model = Evento

    @cached_property
    def evento(self):
        return get_object_or_404(Evento, pk=self.kwargs['pk'])

    def get_object(self, queryset=None):
        return self.evento

    def get_evento(self):
        return self.evento


class EventoUpdateView(LoginRequiredMixin, PermissionRequiredMixin, EventoDoOrganizadorMixin,
                       SuccessMessageMixin, UpdateView):
    permission_required = 'eventos.change_evento'
    form_class = EventoForm
    success_message = 'Evento "%(nome)s" atualizado.'

    def get_success_url(self):
        return reverse('eventos:detalhe', args=[self.object.pk])


class EventoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, EventoDoOrganizadorMixin,
                       SuccessMessageMixin, DeleteView):
    permission_required = 'eventos.delete_evento'
    success_url = reverse_lazy('eventos:lista')
    success_message = 'Evento excluído.'


class AtividadeCreateView(LoginRequiredMixin, PermissionRequiredMixin, OrganizadorDoEventoMixin,
                          SuccessMessageMixin, CreateView):
    permission_required = 'eventos.add_atividade'
    model = Atividade
    form_class = AtividadeForm
    success_message = 'Atividade "%(titulo)s" cadastrada.'

    def get_evento(self):
        return self.evento

    @cached_property
    def evento(self):
        return get_object_or_404(Evento, pk=self.kwargs['evento_pk'])

    def get_form_kwargs(self):
        # O evento precisa estar na instância ANTES da validação: o clean() confere o período.
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Atividade(evento=self.evento)
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['evento'] = self.evento
        return contexto

    def get_success_url(self):
        return reverse('eventos:detalhe', args=[self.evento.pk])


class AtividadeDoOrganizadorMixin(OrganizadorDoEventoMixin):
    """Para editar/excluir atividade: o dono é o organizador do evento da atividade."""
    model = Atividade

    @cached_property
    def atividade(self):
        return get_object_or_404(Atividade.objects.select_related('evento'), pk=self.kwargs['pk'])

    def get_object(self, queryset=None):
        return self.atividade

    def get_evento(self):
        return self.atividade.evento

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['evento'] = self.atividade.evento
        return contexto

    def get_success_url(self):
        return reverse('eventos:detalhe', args=[self.atividade.evento_id])


class AtividadeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AtividadeDoOrganizadorMixin,
                          SuccessMessageMixin, UpdateView):
    permission_required = 'eventos.change_atividade'
    form_class = AtividadeForm
    success_message = 'Atividade "%(titulo)s" atualizada.'


class AtividadeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, AtividadeDoOrganizadorMixin,
                          SuccessMessageMixin, DeleteView):
    permission_required = 'eventos.delete_atividade'
    success_message = 'Atividade excluída.'
