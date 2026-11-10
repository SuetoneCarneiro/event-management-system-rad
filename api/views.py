from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, DjangoModelPermissionsOrAnonReadOnly, IsAuthenticated
from rest_framework.response import Response

from eventos import servicos
from eventos.models import Atividade, Evento, InscricaoAtividade, InscricaoEvento, Sala

from .permissions import EhOrganizadorDoEventoOuSomenteLeitura
from .serializers import (
    AgendaSerializer, AtividadeSerializer, EventoProgramacaoSerializer, EventoSerializer,
    InscricaoAtividadeSerializer, InscricaoEventoSerializer, SalaSerializer,
)

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


# --- Ações do participante: views-função com @api_view ---
# Não são CRUD de um recurso: são operações (inscrever, cancelar, ver a agenda) que delegam
# para eventos/servicos.py, o mesmo código usado pelo site. O participante sempre é request.user.

@extend_schema(request=InscricaoEventoSerializer, responses=InscricaoEventoSerializer)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def inscricoes_evento(request):
    """GET: minhas inscrições em eventos. POST: inscrever-me em um evento."""
    if request.method == 'GET':
        inscricoes = InscricaoEvento.objects.filter(participante=request.user).select_related('evento')
        return Response(InscricaoEventoSerializer(inscricoes, many=True).data)

    serializer = InscricaoEventoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    inscricao = servicos.inscrever_no_evento(request.user, serializer.validated_data['evento'])
    return Response(InscricaoEventoSerializer(inscricao).data, status=status.HTTP_201_CREATED)


@extend_schema(responses={204: None})
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancelar_inscricao_evento(request, pk):
    """Cancela minha inscrição no evento e, junto, as inscrições nas atividades dele."""
    inscricao = get_object_or_404(InscricaoEvento, pk=pk)
    servicos.cancelar_inscricao_evento(request.user, inscricao)  # PermissionDenied -> 403
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(request=InscricaoAtividadeSerializer, responses={201: InscricaoAtividadeSerializer})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def inscrever_atividade(request):
    """Inscreve-me em uma atividade de um evento em que já estou inscrito."""
    serializer = InscricaoAtividadeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    inscricao = servicos.inscrever_na_atividade(request.user, serializer.validated_data['atividade'])
    return Response(InscricaoAtividadeSerializer(inscricao).data, status=status.HTTP_201_CREATED)


@extend_schema(responses={204: None})
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancelar_inscricao_atividade(request, pk):
    """Cancela minha inscrição em uma atividade; a vaga volta imediatamente."""
    inscricao = get_object_or_404(InscricaoAtividade.objects.select_related('inscricao_evento'), pk=pk)
    servicos.cancelar_inscricao_atividade(request.user, inscricao)  # PermissionDenied -> 403
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses=AgendaSerializer(many=True))
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agenda(request):
    """Atividades em que estou inscrito, de todos os eventos, em ordem cronológica."""
    inscricoes = (
        InscricaoAtividade.objects
        .filter(inscricao_evento__participante=request.user)
        .select_related('atividade__evento', 'atividade__sala')
        .order_by('atividade__data_hora_inicio')
    )
    return Response(AgendaSerializer(inscricoes, many=True).data)
