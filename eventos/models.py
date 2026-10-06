from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q


class Sala(models.Model):
    nome = models.CharField('nome', max_length=100)
    bloco = models.CharField('bloco', max_length=100)
    capacidade = models.PositiveIntegerField('capacidade', validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'sala'
        ordering = ['bloco', 'nome']

    def __str__(self):
        return f'{self.nome} ({self.bloco})'


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


class Atividade(models.Model):

    class Tipo(models.TextChoices):
        PALESTRA = 'PALESTRA', 'Palestra'
        TREINAMENTO = 'TREINAMENTO', 'Treinamento'
        APRESENTACAO = 'APRESENTACAO', 'Apresentação'

    evento = models.ForeignKey(
        Evento,
        on_delete=models.CASCADE,
        related_name='atividades',
        verbose_name='evento',
    )
    titulo = models.CharField('título', max_length=200)
    tipo = models.CharField('tipo', max_length=20, choices=Tipo.choices)
    descricao = models.TextField('descrição')
    responsavel = models.CharField('responsável', max_length=100)
    sala = models.ForeignKey(
        Sala,
        on_delete=models.PROTECT,
        related_name='atividades',
        verbose_name='sala',
    )
    data_hora_inicio = models.DateTimeField('data e hora de início')
    data_hora_fim = models.DateTimeField('data e hora de fim')

    class Meta:
        verbose_name = 'atividade'
        verbose_name_plural = 'atividades'
        ordering = ['data_hora_inicio', 'titulo']
        constraints = [
            models.CheckConstraint(
                check=Q(data_hora_fim__gte=F('data_hora_inicio')),
                name='atividade_fim_depois_do_inicio',
                violation_error_message='A data e hora de fim não podem ser anteriores à data e hora de início.',
            ),
        ]

    def __str__(self):
        return f'{self.titulo} ({self.get_tipo_display()})'


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


class InscricaoAtividade(models.Model):
    inscricao_evento = models.ForeignKey(
        InscricaoEvento,
        on_delete=models.CASCADE,
        related_name='inscricoes_atividade',
        verbose_name='inscrição no evento',
    )
    atividade = models.ForeignKey(
        Atividade,
        on_delete=models.CASCADE,
        related_name='inscricoes',
        verbose_name='atividade',
    )
    data_hora_inscricao = models.DateTimeField('data e hora da inscrição', auto_now_add=True)

    class Meta:
        verbose_name = 'inscrição na atividade'
        verbose_name_plural = 'inscrições na atividade'
        ordering = ['data_hora_inscricao']
        constraints = [
            models.UniqueConstraint(
                fields=['inscricao_evento', 'atividade'],
                name='inscricao_atividade_unica',
                violation_error_message='Você já está inscrito nesta atividade.',
            ),
        ]

    def __str__(self):
        return f'{self.inscricao_evento} - {self.atividade}'
