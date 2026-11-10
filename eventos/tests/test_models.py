"""Models: validação de dados (RF4) e as regras que moram no clean() (RN1, RN2, RN3, RN5).

Aqui não há HTTP: o teste chama full_clean() direto, que é o mesmo método que o site (via ModelForm
e serviços) e a API (via serializer e serviços) chamam.
"""
from datetime import date

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError

from eventos.models import Atividade, Evento, InscricaoAtividade, InscricaoEvento, Sala

from .base import Cenario, dt


class ValidacaoSalaTests(Cenario):
    def test_capacidade_negativa_e_recusada(self):
        with self.assertRaises(ValidationError) as erro:
            Sala(nome='Sala X', bloco='D', capacidade=-5).full_clean()
        self.assertIn('capacidade', erro.exception.message_dict)

    def test_capacidade_zero_e_recusada(self):
        with self.assertRaises(ValidationError) as erro:
            Sala(nome='Sala X', bloco='D', capacidade=0).full_clean()
        self.assertIn('capacidade', erro.exception.message_dict)

    def test_nome_vazio_e_recusado(self):
        with self.assertRaises(ValidationError) as erro:
            Sala(nome='', bloco='D', capacidade=10).full_clean()
        self.assertIn('nome', erro.exception.message_dict)

    def test_sala_com_dados_validos_e_aceita(self):
        Sala(nome='Sala X', bloco='D', capacidade=1).full_clean()


class ValidacaoEventoTests(Cenario):
    def evento(self, **campos):
        dados = dict(nome='Hackathon', descricao='d', data_inicio=date(2026, 11, 20),
                     data_fim=date(2026, 11, 21), organizador=self.ana)
        dados.update(campos)
        return Evento(**dados)

    def test_fim_antes_do_inicio_e_recusado(self):
        with self.assertRaisesMessage(ValidationError, 'A data de fim não pode ser anterior à data de início.'):
            self.evento(data_fim=date(2026, 11, 19)).full_clean()

    def test_evento_de_um_dia_so_e_aceito(self):
        self.evento(data_fim=date(2026, 11, 20)).full_clean()

    def test_nome_vazio_e_recusado(self):
        with self.assertRaises(ValidationError) as erro:
            self.evento(nome='').full_clean()
        self.assertIn('nome', erro.exception.message_dict)

    def test_so_o_organizador_e_dono_do_evento(self):
        self.assertTrue(self.semana.organizado_por(self.ana))
        for usuario in [self.bruno, self.carla, self.admin, AnonymousUser()]:
            with self.subTest(str(usuario)):
                self.assertFalse(self.semana.organizado_por(usuario))

    def test_encurtar_periodo_deixando_atividade_de_fora_e_recusado(self):
        self.semana.data_inicio = date(2026, 11, 12)  # a Oficina é em 11/11
        with self.assertRaisesMessage(ValidationError, 'deixa de fora atividades já cadastradas'):
            self.semana.full_clean()


class ValidacaoAtividadeTests(Cenario):
    def atividade(self, inicio, fim, **campos):
        dados = dict(evento=self.semana, titulo='Nova', tipo=Atividade.Tipo.PALESTRA, descricao='d',
                     responsavel='R', sala=self.sala_203, data_hora_inicio=inicio, data_hora_fim=fim)
        dados.update(campos)
        return Atividade(**dados)

    def test_fim_antes_do_inicio_e_recusado(self):
        with self.assertRaisesMessage(ValidationError, 'não podem ser anteriores à data e hora de início'):
            self.atividade(dt(11, 11, 15), dt(11, 11, 14)).full_clean()

    def test_duracao_zero_e_recusada(self):
        with self.assertRaisesMessage(ValidationError, 'A atividade precisa ter duração'):
            self.atividade(dt(11, 11, 15), dt(11, 11, 15)).full_clean()

    def test_atividade_fora_do_periodo_do_evento_e_recusada(self):
        with self.assertRaisesMessage(ValidationError, 'dentro do período do evento'):
            self.atividade(dt(20, 11, 10), dt(20, 11, 11)).full_clean()

    def test_titulo_vazio_e_recusado(self):
        with self.assertRaises(ValidationError) as erro:
            self.atividade(dt(11, 11, 15), dt(11, 11, 16), titulo='').full_clean()
        self.assertIn('titulo', erro.exception.message_dict)

    def test_tipo_fora_das_opcoes_e_recusado(self):
        with self.assertRaises(ValidationError) as erro:
            self.atividade(dt(11, 11, 15), dt(11, 11, 16), tipo='SHOW').full_clean()
        self.assertIn('tipo', erro.exception.message_dict)

    def test_atividade_valida_e_aceita(self):
        self.atividade(dt(11, 11, 15), dt(11, 11, 16)).full_clean()


class SalaOcupadaTests(Cenario):
    """RN3: a Oficina ocupa o Laboratório em 11/11, das 10h às 12h."""

    def no_laboratorio(self, inicio, fim, evento=None):
        return Atividade(evento=evento or self.semana, titulo='Teste', tipo=Atividade.Tipo.PALESTRA,
                         descricao='d', responsavel='R', sala=self.laboratorio,
                         data_hora_inicio=inicio, data_hora_fim=fim)

    def test_todos_os_casos_de_sobreposicao_sao_recusados(self):
        casos = {
            'começa antes e termina no meio': (dt(11, 11, 9), dt(11, 11, 11)),
            'começa no meio e termina depois': (dt(11, 11, 11), dt(11, 11, 13)),
            'está contida': (dt(11, 11, 10, 30), dt(11, 11, 11)),
            'contém a outra': (dt(11, 11, 9), dt(11, 11, 13)),
            'idêntica': (dt(11, 11, 10), dt(11, 11, 12)),
        }
        for caso, (inicio, fim) in casos.items():
            with self.subTest(caso):
                with self.assertRaisesMessage(ValidationError, 'Sala ocupada nesse horário por "Oficina de Django"'):
                    self.no_laboratorio(inicio, fim).full_clean()

    def test_intervalos_que_apenas_encostam_sao_aceitos(self):
        for caso, (inicio, fim) in {'termina quando a outra começa': (dt(11, 11, 8), dt(11, 11, 10)),
                                    'começa quando a outra termina': (dt(11, 11, 12), dt(11, 11, 14))}.items():
            with self.subTest(caso):
                self.no_laboratorio(inicio, fim).full_clean()

    def test_sala_ocupada_por_atividade_de_outro_evento_e_recusada(self):
        sala_da_iniciacao = Atividade(
            evento=self.semana, titulo='Teste', tipo=Atividade.Tipo.PALESTRA, descricao='d', responsavel='R',
            sala=self.sala_203, data_hora_inicio=dt(12, 11, 11), data_hora_fim=dt(12, 11, 12),
        )
        with self.assertRaisesMessage(ValidationError, 'Sala ocupada nesse horário por "Iniciação científica"'):
            sala_da_iniciacao.full_clean()

    def test_editar_atividade_nao_conflita_com_ela_mesma(self):
        self.oficina.data_hora_fim = dt(11, 11, 12, 30)
        self.oficina.full_clean()


class CapacidadeTests(Cenario):
    """RN1: o Laboratório tem 2 lugares."""

    def test_inscricao_com_vaga_e_aceita(self):
        inscricao = self.inscrever_no_evento(self.carla, self.semana)
        InscricaoAtividade(inscricao_evento=inscricao, atividade=self.oficina).full_clean()

    def test_inscricao_alem_da_capacidade_e_recusada(self):
        self.lotar_oficina()
        inscricao = self.inscrever_no_evento(self.eva, self.semana)
        with self.assertRaisesMessage(ValidationError, 'Esta atividade está lotada.'):
            InscricaoAtividade(inscricao_evento=inscricao, atividade=self.oficina).full_clean()

    def test_vagas_restantes_sao_calculadas_a_partir_das_inscricoes(self):
        self.assertEqual(self.vagas(self.oficina), 2)
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        self.assertEqual(self.vagas(self.oficina), 1)
        self.inscrever_na_atividade(self.inscrever_no_evento(self.diego, self.semana), self.oficina)
        self.assertEqual(self.vagas(self.oficina), 0)


class ConflitoDoParticipanteTests(Cenario):
    """RN2: a carla já está na Oficina (11/11, 10h–12h)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.inscricao_semana = cls.inscrever_no_evento(cls.carla, cls.semana)
        cls.inscrever_na_atividade(cls.inscricao_semana, cls.oficina)

    def test_atividade_em_outro_horario_e_aceita(self):
        InscricaoAtividade(inscricao_evento=self.inscricao_semana, atividade=self.git).full_clean()

    def test_atividade_simultanea_do_mesmo_evento_e_recusada(self):
        with self.assertRaisesMessage(ValidationError, 'Conflito de horário com "Oficina de Django"'):
            InscricaoAtividade(inscricao_evento=self.inscricao_semana, atividade=self.abertura).full_clean()

    def test_atividade_simultanea_de_outro_evento_e_recusada(self):
        self.inscrever_na_atividade(self.inscricao_semana, self.projetos)  # 12/11 9h–11h
        inscricao_jornada = self.inscrever_no_evento(self.carla, self.jornada)
        with self.assertRaisesMessage(ValidationError, 'Conflito de horário com "Projetos dos alunos"'):
            InscricaoAtividade(inscricao_evento=inscricao_jornada, atividade=self.iniciacao).full_clean()

    def test_conflito_de_outra_pessoa_nao_atrapalha(self):
        inscricao_diego = self.inscrever_no_evento(self.diego, self.semana)
        InscricaoAtividade(inscricao_evento=inscricao_diego, atividade=self.abertura).full_clean()


class CoerenciaDoEventoTests(Cenario):
    def test_atividade_de_outro_evento_e_recusada(self):
        inscricao_semana = self.inscrever_no_evento(self.carla, self.semana)
        with self.assertRaisesMessage(ValidationError, 'não pertence ao evento'):
            InscricaoAtividade(inscricao_evento=inscricao_semana, atividade=self.iniciacao).full_clean()

    def test_inscricao_em_atividade_exige_inscricao_no_evento(self):
        """RN4 estrutural: sem InscricaoEvento não há o que pôr na FK obrigatória."""
        with self.assertRaises(ValidationError) as erro:
            InscricaoAtividade(atividade=self.oficina).full_clean()
        self.assertIn('inscricao_evento', erro.exception.message_dict)


class InscricaoEventoTests(Cenario):
    def test_inscricao_em_evento_aberto_e_aceita(self):
        InscricaoEvento(evento=self.semana, participante=self.carla).full_clean()

    def test_inscricao_em_evento_fechado_e_recusada(self):
        with self.assertRaisesMessage(ValidationError, 'As inscrições deste evento estão fechadas.'):
            InscricaoEvento(evento=self.egressos, participante=self.carla).full_clean()

    def test_segunda_inscricao_no_mesmo_evento_e_recusada(self):
        self.inscrever_no_evento(self.carla, self.semana)
        with self.assertRaises(ValidationError):
            InscricaoEvento(evento=self.semana, participante=self.carla).full_clean()


class CancelamentoEmCascataTests(Cenario):
    """RN5: o CASCADE de InscricaoAtividade.inscricao_evento."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.inscricao_semana = cls.inscrever_no_evento(cls.carla, cls.semana)
        cls.inscrever_na_atividade(cls.inscricao_semana, cls.oficina)
        cls.inscrever_na_atividade(cls.inscricao_semana, cls.git)
        cls.inscricao_jornada = cls.inscrever_no_evento(cls.carla, cls.jornada)
        cls.inscrever_na_atividade(cls.inscricao_jornada, cls.iniciacao)

    def test_apagar_inscricao_no_evento_apaga_as_das_atividades(self):
        self.inscricao_semana.delete()
        self.assertFalse(InscricaoAtividade.objects.filter(atividade__evento=self.semana).exists())

    def test_inscricoes_de_outros_eventos_sao_preservadas(self):
        self.inscricao_semana.delete()
        self.assertTrue(InscricaoAtividade.objects.filter(inscricao_evento=self.inscricao_jornada).exists())


class SobreposicaoTests(Cenario):
    """Atividade.sobrepoe(): a mesma regra da consulta, usada pela interface (RF10)."""

    def test_sobrepoe_e_simetrico(self):
        self.assertTrue(self.oficina.sobrepoe(self.abertura))
        self.assertTrue(self.abertura.sobrepoe(self.oficina))

    def test_intervalos_que_encostam_nao_se_sobrepoem(self):
        self.assertFalse(self.oficina.sobrepoe(self.git))
        encostada = Atividade(data_hora_inicio=dt(11, 11, 12), data_hora_fim=dt(11, 11, 13))
        self.assertFalse(self.oficina.sobrepoe(encostada))
