"""Inscrições e cancelamentos: o único caminho até o banco, tanto para o site quanto para a API.

Onde cada regra mora:
- RN1 (capacidade), RN2 (conflito do participante), coerência do evento e inscrições fechadas:
  no clean() dos models, chamado aqui por full_clean().
- RN3 (sala ocupada): no Atividade.clean(), chamado pelo ModelForm do site e pelo serializer da API.
- RN4 (inscrição prévia no evento) e a posse da inscrição: aqui.
- RN5 (cancelamento em cascata): no on_delete=CASCADE de InscricaoAtividade.inscricao_evento.

As funções levantam o ValidationError e o PermissionDenied do Django. Cada porta traduz:
o site em mensagem/403, a API em 400/403 (api/excecoes.py).
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from .models import Atividade, InscricaoAtividade, InscricaoEvento


def inscrever_no_evento(participante, evento):
    if InscricaoEvento.objects.filter(evento=evento, participante=participante).exists():
        raise ValidationError('Você já está inscrito neste evento.')

    inscricao = InscricaoEvento(evento=evento, participante=participante)
    inscricao.full_clean()  # inscrições fechadas (InscricaoEvento.clean)
    try:
        with transaction.atomic():
            inscricao.save()
    except IntegrityError:
        # Duas requisições quase simultâneas: a UniqueConstraint do banco barra a segunda.
        raise ValidationError('Você já está inscrito neste evento.')
    return inscricao


def cancelar_inscricao_evento(usuario, inscricao):
    """Devolve quantas inscrições em atividades saíram junto (RN5)."""
    if inscricao.participante_id != usuario.id:
        raise PermissionDenied('Você só pode cancelar as suas próprias inscrições.')
    # O CASCADE de InscricaoAtividade.inscricao_evento apaga as atividades junto.
    _, apagados = inscricao.delete()
    return apagados.get('eventos.InscricaoAtividade', 0)


@transaction.atomic
def inscrever_na_atividade(participante, atividade):
    # select_for_update trava a linha da atividade até o fim da transação: duas pessoas
    # disputando a última vaga são atendidas uma de cada vez, e a contagem da RN1 fica certa.
    atividade = Atividade.objects.select_for_update().select_related('sala', 'evento').get(pk=atividade.pk)

    inscricao_evento = InscricaoEvento.objects.filter(
        evento_id=atividade.evento_id, participante=participante,
    ).first()
    if inscricao_evento is None:  # RN4
        raise ValidationError('Inscreva-se no evento antes de escolher atividades.')
    if inscricao_evento.inscricoes_atividade.filter(atividade=atividade).exists():
        raise ValidationError('Você já está inscrito nesta atividade.')

    nova = InscricaoAtividade(inscricao_evento=inscricao_evento, atividade=atividade)
    nova.full_clean()  # RN1, RN2 e coerência do evento (InscricaoAtividade.clean)
    nova.save()
    return nova


def cancelar_inscricao_atividade(usuario, inscricao):
    if inscricao.inscricao_evento.participante_id != usuario.id:
        raise PermissionDenied('Você só pode cancelar as suas próprias inscrições.')
    inscricao.delete()
