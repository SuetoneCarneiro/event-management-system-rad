import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from eventos.models import Atividade, Evento, Sala

from .excecoes import como_erro_da_api


class ValidacaoDoModelMixin:
    """Faz o serializer chamar o full_clean() do model.

    O ModelSerializer do DRF valida tipos e campos obrigatórios, mas NÃO chama o clean() nem as
    constraints do model. Sem este mixin, a API aceitaria uma atividade em sala ocupada que o site
    recusa. Com ele, a regra continua escrita uma única vez: no model.
    """

    def validate(self, attrs):
        attrs = super().validate(attrs)
        modelo = self.Meta.model
        # Cópia para não sujar a instância original se a validação falhar.
        instancia = copy.copy(self.instance) if self.instance else modelo()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        # O que o cliente não envia (id, organizador, preenchido pela view) fica fora da validação.
        excluir = [f.name for f in modelo._meta.concrete_fields if getattr(instancia, f.attname) is None]
        try:
            instancia.full_clean(exclude=excluir)
        except DjangoValidationError as erro:
            raise como_erro_da_api(erro)
        return attrs


class SalaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sala
        fields = ['id', 'nome', 'bloco', 'capacidade']


class AtividadeSerializer(ValidacaoDoModelMixin, serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    sala_nome = serializers.CharField(source='sala.nome', read_only=True)
    sala_bloco = serializers.CharField(source='sala.bloco', read_only=True)
    vagas_restantes = serializers.SerializerMethodField()

    class Meta:
        model = Atividade
        fields = [
            'id', 'evento', 'titulo', 'tipo', 'tipo_display', 'descricao', 'responsavel',
            'sala', 'sala_nome', 'sala_bloco', 'data_hora_inicio', 'data_hora_fim', 'vagas_restantes',
        ]

    def get_vagas_restantes(self, atividade) -> int:
        # Calculada, nunca guardada. Nas listagens vem da anotação de com_vagas(), sem consulta extra.
        if hasattr(atividade, 'vagas_restantes'):
            return atividade.vagas_restantes
        return atividade.sala.capacidade - atividade.inscricoes.count()

    def validate_evento(self, evento):
        if self.instance and evento != self.instance.evento:
            raise serializers.ValidationError('Uma atividade não pode ser movida para outro evento.')
        if evento.organizador_id != self.context['request'].user.id:
            raise PermissionDenied('Somente o organizador do evento pode cadastrar atividades nele.')
        return evento


class EventoSerializer(ValidacaoDoModelMixin, serializers.ModelSerializer):
    """O organizador não é campo: vem de request.user, nunca do JSON."""

    class Meta:
        model = Evento
        fields = ['id', 'nome', 'descricao', 'data_inicio', 'data_fim', 'inscricoes_abertas']


class EventoProgramacaoSerializer(EventoSerializer):
    """Programação completa numa requisição: o evento, as atividades, a sala e as vagas de cada uma."""
    atividades = AtividadeSerializer(many=True, read_only=True)

    class Meta(EventoSerializer.Meta):
        fields = EventoSerializer.Meta.fields + ['atividades']

