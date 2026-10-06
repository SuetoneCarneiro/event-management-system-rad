from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Count, F, Q
from django.utils import timezone


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

    def clean(self):
        # Ao editar o período, nenhuma atividade já cadastrada pode ficar de fora.
        if self.pk and self.data_inicio and self.data_fim:
            fora_do_periodo = [
                atividade for atividade in self.atividades.all()
                if not atividade.cabe_no_periodo(self.data_inicio, self.data_fim)
            ]
            if fora_do_periodo:
                titulos = ', '.join(a.titulo for a in fora_do_periodo)
                raise ValidationError(
                    f'O novo período deixa de fora atividades já cadastradas: {titulos}.'
                )


class AtividadeQuerySet(models.QuerySet):
    def com_vagas(self):
        """Anota total de inscritos e vagas restantes, calculados no banco."""
        return self.annotate(
            total_inscritos=Count('inscricoes'),
            vagas_restantes=F('sala__capacidade') - Count('inscricoes'),
        )

    def sobrepostas_a(self, inicio, fim):
        """Atividades cujo horário se sobrepõe ao intervalo [inicio, fim).

        Dois intervalos se sobrepõem quando cada um começa antes do outro terminar.
        Encostar (um termina exatamente quando o outro começa) não é sobreposição.
        """
        return self.filter(data_hora_inicio__lt=fim, data_hora_fim__gt=inicio)


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

    objects = AtividadeQuerySet.as_manager()

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

    def cabe_no_periodo(self, data_inicio, data_fim):
        # As datas do evento estão no fuso local; os horários são gravados em UTC.
        inicio = timezone.localtime(self.data_hora_inicio).date()
        fim = timezone.localtime(self.data_hora_fim).date()
        return data_inicio <= inicio and fim <= data_fim

    def clean(self):
        if not (self.data_hora_inicio and self.data_hora_fim):
            return  # o erro de campo obrigatório já foi apontado

        if self.data_hora_fim == self.data_hora_inicio:
            raise ValidationError(
                {'data_hora_fim': 'A atividade precisa ter duração: o fim deve ser posterior ao início.'}
            )

        if self.evento_id and not self.cabe_no_periodo(self.evento.data_inicio, self.evento.data_fim):
            inicio = self.evento.data_inicio.strftime('%d/%m/%Y')
            fim = self.evento.data_fim.strftime('%d/%m/%Y')
            raise ValidationError(
                {'data_hora_inicio': f'A atividade precisa acontecer dentro do período do evento ({inicio} a {fim}).'}
            )

        # RN3: a sala não pode ter outra atividade (de qualquer evento) no mesmo horário.
        if self.sala_id:
            conflito = (
                Atividade.objects
                .filter(sala_id=self.sala_id)
                .sobrepostas_a(self.data_hora_inicio, self.data_hora_fim)
                .exclude(pk=self.pk)
                .select_related('evento')
                .first()
            )
            if conflito:
                raise ValidationError({'sala': (
                    f'Sala ocupada nesse horário por "{conflito.titulo}" '
                    f'({conflito.evento}), {_intervalo(conflito)}.'
                )})


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

    def clean(self):
        # Só bloqueia inscrições novas; as já existentes continuam válidas se o evento fechar.
        if self._state.adding and self.evento_id and not self.evento.inscricoes_abertas:
            raise ValidationError('As inscrições deste evento estão fechadas.')


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

    def clean(self):
        if not (self.inscricao_evento_id and self.atividade_id):
            return

        atividade = self.atividade

        # RN4: os dois caminhos até Evento precisam chegar ao mesmo evento.
        if atividade.evento_id != self.inscricao_evento.evento_id:
            raise ValidationError('Esta atividade não pertence ao evento em que você está inscrito.')

        # RN1: conta os inscritos agora, no banco, no momento da inscrição.
        inscritos = atividade.inscricoes.exclude(pk=self.pk).count()
        if inscritos >= atividade.sala.capacidade:
            raise ValidationError('Esta atividade está lotada.')

        # RN2: parte do participante, então pega atividades de qualquer evento.
        conflito = (
            InscricaoAtividade.objects
            .filter(
                inscricao_evento__participante_id=self.inscricao_evento.participante_id,
                atividade__in=Atividade.objects.sobrepostas_a(
                    atividade.data_hora_inicio, atividade.data_hora_fim
                ),
            )
            .exclude(pk=self.pk)
            .exclude(atividade_id=atividade.pk)  # repetir a mesma atividade é caso da UniqueConstraint
            .select_related('atividade__evento')
            .first()
        )
        if conflito:
            outra = conflito.atividade
            raise ValidationError(
                f'Conflito de horário com "{outra.titulo}" ({outra.evento}), {_intervalo(outra)}.'
            )


def _intervalo(atividade):
    inicio = timezone.localtime(atividade.data_hora_inicio)
    fim = timezone.localtime(atividade.data_hora_fim)
    return f'{inicio:%d/%m %H:%M}–{fim:%H:%M}'
