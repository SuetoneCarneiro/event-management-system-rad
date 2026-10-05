from django.conf import settings
from django.db import models
from django.db.models import F, Q


# TODO (Suetone): model Sala


class Evento(models.Model):
    nome = models.CharField('nome', max_length=200)
    descricao = models.TextField('descrição')
    data_inicio = models.DateField('data de início')
    data_fim = models.DateField('data de fim')
    inscricoes_abertas = models.BooleanField('inscrições abertas', default=True)
    # Preenchido pela view com request.user; nunca aparece em formulário.
    organizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='eventos_organizados',
        verbose_name='organizador',
    )

    class Meta:
        verbose_name = 'evento'
        verbose_name_plural = 'eventos'
        ordering = ['data_inicio', 'nome']
        constraints = [
            models.CheckConstraint(
                check=Q(data_fim__gte=F('data_inicio')),
                name='evento_fim_depois_do_inicio',
                violation_error_message='A data de fim não pode ser anterior à data de início.',
            ),
        ]

    def __str__(self):
        return self.nome


# TODO (Suetone): model Atividade


class InscricaoEvento(models.Model):
    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='inscricoes',
        verbose_name='evento',
    )
    # Preenchido pela view com request.user; nunca aparece em formulário.
    participante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='inscricoes_evento',
        verbose_name='participante',
    )
    data = models.DateTimeField('data da inscrição', auto_now_add=True)

    class Meta:
        verbose_name = 'inscrição no evento'
        verbose_name_plural = 'inscrições no evento'
        ordering = ['data']
        constraints = [
            models.UniqueConstraint(
                fields=['evento', 'participante'],
                name='inscricao_evento_unica',
                violation_error_message='Você já está inscrito neste evento.',
            ),
        ]

    def __str__(self):
        return f'{self.participante} em {self.evento}'


# TODO (Suetone): model InscricaoAtividade
