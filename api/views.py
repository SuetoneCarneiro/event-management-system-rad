from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny, DjangoModelPermissionsOrAnonReadOnly

from eventos.models import Atividade, Evento, Sala

from .permissions import EhOrganizadorDoEventoOuSomenteLeitura
from .serializers import AtividadeSerializer, EventoProgramacaoSerializer, EventoSerializer, SalaSerializer

# --- Recursos com CRUD completo: ViewSet + router ---
# Permissões em duas camadas, como no site:
#   DjangoModelPermissionsOrAnonReadOnly -> leitura aberta; escrever exige token (401) e
#                                           a permissão do grupo Organizadores (403)
#   EhOrganizadorDoEventoOuSomenteLeitura -> alterar/excluir exige ser o dono do evento (403)

PERMISSOES_ORGANIZADOR = [DjangoModelPermissionsOrAnonReadOnly, EhOrganizadorDoEventoOuSomenteLeitura]


class EventoViewSet(viewsets.ModelViewSet):
    """Lista e programação públicas; criar, alterar e excluir são do organizador."""
    permission_classes = PERMISSOES_ORGANIZADOR

    def get_queryset(self):
        eventos = Evento.objects.all()
        if self.action == 'retrieve':
            # Uma consulta para o evento e uma para todas as atividades (com sala e vagas),
            # não importa quantas atividades existam.
            eventos = eventos.prefetch_related(
                Prefetch('atividades', queryset=Atividade.objects.com_vagas().select_related('sala'))
            )
        return eventos

    def get_serializer_class(self):
        return EventoProgramacaoSerializer if self.action == 'retrieve' else EventoSerializer

    def perform_create(self, serializer):
        serializer.save(organizador=self.request.user)


@extend_schema(parameters=[OpenApiParameter('evento', int, description='Filtra pelas atividades de um evento.')])
class AtividadeViewSet(viewsets.ModelViewSet):
    """Atividades: lista paginada, com busca no título/descrição e ordenação por data de início."""
    serializer_class = AtividadeSerializer
    permission_classes = PERMISSOES_ORGANIZADOR
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titulo', 'descricao']
    ordering_fields = ['data_hora_inicio', 'titulo']
    ordering = ['data_hora_inicio']

    def get_queryset(self):
        atividades = Atividade.objects.com_vagas().select_related('sala', 'evento')
        evento = self.request.query_params.get('evento')
        if evento and evento.isdigit():
            atividades = atividades.filter(evento_id=evento)
        return atividades


class SalaViewSet(viewsets.ReadOnlyModelViewSet):
    """Salas são cadastradas só pelo Admin; a API apenas as expõe para consulta."""
    queryset = Sala.objects.all()
    serializer_class = SalaSerializer
    permission_classes = [AllowAny]

