from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from eventos import servicos
from eventos.forms import AtividadeForm, EventoForm
from eventos.models import Atividade, Evento, InscricaoAtividade, InscricaoEvento


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
            atividade.minha_inscricao = None
            atividade.conflita = False

        usuario = self.request.user
        inscricao_evento = None
        if usuario.is_authenticated:
            inscricao_evento = InscricaoEvento.objects.filter(evento=self.object, participante=usuario).first()
            # Todas as atividades do participante, de qualquer evento (RN2 vale entre eventos).
            minhas = list(
                InscricaoAtividade.objects
                .filter(inscricao_evento__participante=usuario)
                .select_related('atividade')
            )
            por_atividade = {inscricao.atividade_id: inscricao for inscricao in minhas}
            for atividade in atividades:
                atividade.minha_inscricao = por_atividade.get(atividade.pk)
                atividade.conflita = any(
                    inscricao.atividade.sobrepoe(atividade)
                    for inscricao in minhas if inscricao.atividade_id != atividade.pk
                )

        contexto['atividades'] = atividades
        contexto['inscricao_evento'] = inscricao_evento
        contexto['eh_organizador'] = self.object.organizado_por(usuario)
        return contexto


# Fazendo 1 com função e decoradores
@login_required
@permission_required('eventos.add_evento', raise_exception=True)
def meus_eventos(request):
    eventos = Evento.objects.filter(organizador=request.user)
    return render(request, 'eventos/meus_eventos.html', {'eventos': eventos})


class AgendaView(LoginRequiredMixin, ListView):
    """RF8: atividades do usuário logado, de todos os eventos, em ordem cronológica."""
    template_name = 'eventos/agenda.html'
    context_object_name = 'inscricoes'

    def get_queryset(self):
        # get_queryset (e não o atributo queryset) porque o filtro depende de quem acessa.
        return (
            InscricaoAtividade.objects
            .filter(inscricao_evento__participante=self.request.user)
            .select_related('atividade__evento', 'atividade__sala')
            .order_by('atividade__data_hora_inicio')
        )


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
        return self.get_evento().organizado_por(self.request.user)


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
    success_url = reverse_lazy('eventos:meus_eventos')
    success_message = 'Evento excluído.'


class PainelEventoView(LoginRequiredMixin, PermissionRequiredMixin, EventoDoOrganizadorMixin, DetailView):
    """RF9: inscritos por atividade, só para o organizador do evento."""
    permission_required = 'eventos.view_evento'
    template_name = 'eventos/painel.html'
    context_object_name = 'evento'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # prefetch_related busca os inscritos de TODAS as atividades numa consulta só,
        # em vez de uma consulta por atividade no template.
        inscritos = (
            InscricaoAtividade.objects
            .select_related('inscricao_evento__participante')
            .order_by('data_hora_inscricao')
        )
        contexto['atividades'] = (
            self.object.atividades
            .com_vagas()
            .select_related('sala')
            .prefetch_related(Prefetch('inscricoes', queryset=inscritos))
        )
        contexto['total_inscritos_evento'] = self.object.inscricoes.count()
        return contexto


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


# --- Inscrições e cancelamentos ---
# Views-função: @login_required manda o anônimo para o login e @require_POST
# recusa (405) qualquer método que não seja POST, porque todas alteram o estado.

def _voltar(request, padrao):
    """Volta para o campo 'next' do formulário, se for uma URL deste site; senão, para o padrão."""
    destino = request.POST.get('next')
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    ):
        return redirect(destino)
    return redirect(padrao)


@login_required
@require_POST
def inscrever_evento(request, pk):
    evento = get_object_or_404(Evento, pk=pk)
    try:
        servicos.inscrever_no_evento(request.user, evento)
    except ValidationError as erro:
        messages.error(request, ' '.join(erro.messages))
    else:
        messages.success(request, f'Inscrição em "{evento.nome}" realizada. Agora escolha suas atividades.')
    return redirect('eventos:detalhe', pk=evento.pk)


@login_required
@require_POST
def cancelar_inscricao_evento(request, pk):
    inscricao = get_object_or_404(InscricaoEvento.objects.select_related('evento'), pk=pk)
    evento = inscricao.evento
    atividades = servicos.cancelar_inscricao_evento(request.user, inscricao)  # PermissionDenied -> 403
    mensagem = f'Inscrição em "{evento.nome}" cancelada.'
    if atividades:
        mensagem += f' Você também saiu de {atividades} atividade(s) deste evento.'
    messages.success(request, mensagem)
    return _voltar(request, reverse('eventos:detalhe', args=[evento.pk]))


@login_required
@require_POST
def inscrever_atividade(request, pk):
    atividade = get_object_or_404(Atividade, pk=pk)
    try:
        servicos.inscrever_na_atividade(request.user, atividade)
    except ValidationError as erro:
        messages.error(request, ' '.join(erro.messages))
    else:
        messages.success(request, f'Inscrição em "{atividade.titulo}" realizada.')
    return _voltar(request, reverse('eventos:detalhe', args=[atividade.evento_id]))


@login_required
@require_POST
def cancelar_inscricao_atividade(request, pk):
    inscricao = get_object_or_404(
        InscricaoAtividade.objects.select_related('inscricao_evento', 'atividade'), pk=pk,
    )
    atividade = inscricao.atividade
    servicos.cancelar_inscricao_atividade(request.user, inscricao)  # PermissionDenied -> 403
    messages.success(request, f'Você saiu de "{atividade.titulo}". A vaga foi liberada.')
    return _voltar(request, reverse('eventos:detalhe', args=[atividade.evento_id]))
