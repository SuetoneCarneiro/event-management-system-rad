"""Testes dos critérios de aceitação (seção 9 do enunciado).

Os dados vêm do comando popular_dados, os mesmos do db.sqlite3 entregue:
- ana organiza a Semana de Tecnologia e o Encontro de Egressos (inscrições fechadas)
- bruno organiza a Jornada Científica
- Laboratório 1 tem capacidade 2
"""
from datetime import datetime
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Atividade, Evento, InscricaoAtividade, InscricaoEvento, Sala


def dt(dia, mes, hora, minuto=0):
    return timezone.make_aware(datetime(2026, mes, dia, hora, minuto))


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_dados', stdout=StringIO())
        cls.ana, cls.bruno, cls.carla, cls.diego, cls.admin = (
            User.objects.get(username=nome) for nome in ['ana', 'bruno', 'carla', 'diego', 'admin']
        )
        cls.semana = Evento.objects.get(nome='Semana de Tecnologia')
        cls.jornada = Evento.objects.get(nome='Jornada Científica')
        cls.egressos = Evento.objects.get(nome='Encontro de Egressos')
        cls.laboratorio = Sala.objects.get(nome='Laboratório 1')
        cls.abertura = Atividade.objects.get(titulo='Abertura: o futuro da web')
        cls.oficina = Atividade.objects.get(titulo='Oficina de Django')
        cls.git = Atividade.objects.get(titulo='Git na prática')
        cls.projetos = Atividade.objects.get(titulo='Projetos dos alunos')
        cls.iniciacao = Atividade.objects.get(titulo='Iniciação científica no IFPB')

    def entrar(self, usuario):
        self.client.force_login(usuario)

    def mensagens(self, resposta):
        return [str(m) for m in resposta.context['messages']]

    def vagas(self, atividade):
        return Atividade.objects.com_vagas().get(pk=atividade.pk).vagas_restantes

    def inscrever_evento(self, evento):
        return self.client.post(reverse('eventos:inscrever_evento', args=[evento.pk]), follow=True)

    def inscrever_atividade(self, atividade):
        return self.client.post(reverse('eventos:inscrever_atividade', args=[atividade.pk]), follow=True)


class ProgramacaoPublicaTests(BaseTestCase):
    def test_01_anonimo_ve_lista_de_eventos(self):
        resposta = self.client.get(reverse('eventos:lista'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Semana de Tecnologia')
        self.assertContains(resposta, 'Jornada Científica')

    def test_02_anonimo_ve_atividades_e_vagas(self):
        resposta = self.client.get(reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Oficina de Django')
        oficina = next(a for a in resposta.context['atividades'] if a.pk == self.oficina.pk)
        self.assertEqual(oficina.vagas_restantes, 2)

    def test_03_anonimo_que_tenta_se_inscrever_vai_para_o_login(self):
        url = reverse('eventos:inscrever_evento', args=[self.semana.pk])
        resposta = self.client.post(url)
        self.assertRedirects(resposta, f"{reverse('login')}?next={url}", fetch_redirect_response=False)


class CadastroTests(BaseTestCase):
    def test_04_conta_nova_e_participante_comum(self):
        resposta = self.client.post(reverse('cadastro'), {
            'username': 'novato', 'first_name': 'Novo', 'last_name': 'Aluno', 'email': 'novo@ifpb.edu.br',
            'password1': 'SenhaForte!2026', 'password2': 'SenhaForte!2026',
        })
        self.assertRedirects(resposta, reverse('eventos:lista'))
        novato = User.objects.get(username='novato')
        self.assertFalse(novato.groups.exists())
        self.assertFalse(novato.is_staff)
        self.assertFalse(novato.has_perm('eventos.add_evento'))
        self.assertTrue(novato.check_password('SenhaForte!2026'))  # senha guardada com hash
        self.assertEqual(self.client.get(reverse('eventos:criar')).status_code, 403)


class CadastroEventosTests(BaseTestCase):
    def test_05_organizador_preenchido_pelo_sistema(self):
        self.entrar(self.ana)
        self.client.post(reverse('eventos:criar'), {
            'nome': 'Hackathon', 'descricao': 'Maratona', 'data_inicio': '2026-11-20', 'data_fim': '2026-11-21',
            'inscricoes_abertas': 'on',
            'organizador': self.bruno.pk,  # tentativa de forjar: o campo nem existe no formulário
        })
        self.assertEqual(Evento.objects.get(nome='Hackathon').organizador, self.ana)

    def test_06_organizador_nao_edita_evento_alheio_pela_url(self):
        self.entrar(self.bruno)
        url = reverse('eventos:editar', args=[self.semana.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        resposta = self.client.post(url, {
            'nome': 'Invadido', 'descricao': 'x', 'data_inicio': '2026-11-10', 'data_fim': '2026-11-14',
        })
        self.assertEqual(resposta.status_code, 403)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana de Tecnologia')

    def test_06b_nem_o_superusuario_edita_evento_alheio(self):
        self.entrar(self.admin)
        self.assertEqual(self.client.get(reverse('eventos:editar', args=[self.semana.pk])).status_code, 403)

    def test_06c_participante_nao_cria_evento(self):
        self.entrar(self.carla)
        self.assertEqual(self.client.get(reverse('eventos:criar')).status_code, 403)

    def criar_atividade(self, inicio, fim, sala=None):
        self.entrar(self.ana)
        return self.client.post(reverse('eventos:atividade_criar', args=[self.semana.pk]), {
            'titulo': 'Nova', 'tipo': 'PALESTRA', 'descricao': 'd', 'responsavel': 'R',
            'sala': (sala or self.laboratorio).pk, 'data_hora_inicio': inicio, 'data_hora_fim': fim,
        })

    def test_07_atividade_fora_do_periodo_recusada(self):
        resposta = self.criar_atividade('2026-11-20T10:00', '2026-11-20T11:00')
        self.assertFormError(
            resposta.context['form'], 'data_hora_inicio',
            'A atividade precisa acontecer dentro do período do evento (10/11/2026 a 14/11/2026).',
        )

    def test_08_fim_antes_do_inicio_recusado(self):
        resposta = self.criar_atividade('2026-11-11T15:00', '2026-11-11T14:00')
        self.assertIn(
            'A data e hora de fim não podem ser anteriores à data e hora de início.',
            resposta.context['form'].non_field_errors(),
        )

    def test_09_sala_ocupada_recusada(self):
        resposta = self.criar_atividade('2026-11-11T11:00', '2026-11-11T13:00')  # Oficina: 10h–12h
        self.assertFalse(Atividade.objects.filter(titulo='Nova').exists())
        self.assertIn('Sala ocupada', resposta.context['form'].errors['sala'][0])

    def test_10_mesma_sala_em_outro_horario_aceita(self):
        resposta = self.criar_atividade('2026-11-11T12:00', '2026-11-11T13:00')  # encosta na Oficina
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertTrue(Atividade.objects.filter(titulo='Nova').exists())


class SobreposicaoTests(BaseTestCase):
    """RN3: todos os casos de sobreposição com a Oficina (Laboratório 1, 11/11, 10h–12h)."""

    def nova(self, inicio, fim):
        return Atividade(
            evento=self.semana, titulo='Teste', tipo='PALESTRA', descricao='d', responsavel='R',
            sala=self.laboratorio, data_hora_inicio=inicio, data_hora_fim=fim,
        )

    def test_casos_que_conflitam(self):
        casos = {
            'parcial pela esquerda': (dt(11, 11, 9), dt(11, 11, 11)),
            'parcial pela direita': (dt(11, 11, 11), dt(11, 11, 13)),
            'contida': (dt(11, 11, 10, 30), dt(11, 11, 11)),
            'contém': (dt(11, 11, 9), dt(11, 11, 13)),
            'idêntica': (dt(11, 11, 10), dt(11, 11, 12)),
        }
        for nome, (inicio, fim) in casos.items():
            with self.subTest(nome):
                with self.assertRaisesMessage(ValidationError, 'Sala ocupada'):
                    self.nova(inicio, fim).full_clean()

    def test_casos_que_nao_conflitam(self):
        casos = {
            'encosta antes': (dt(11, 11, 8), dt(11, 11, 10)),
            'encosta depois': (dt(11, 11, 12), dt(11, 11, 14)),
        }
        for nome, (inicio, fim) in casos.items():
            with self.subTest(nome):
                self.nova(inicio, fim).full_clean()

    def test_conflito_de_sala_entre_eventos_diferentes(self):
        atividade = Atividade(
            evento=self.jornada, titulo='Teste', tipo='PALESTRA', descricao='d', responsavel='R',
            sala=self.abertura.sala, data_hora_inicio=dt(12, 11, 11), data_hora_fim=dt(12, 11, 12),
        )  # Auditório já tem "Iniciação científica" (Jornada) das 10h às 11h30
        with self.assertRaisesMessage(ValidationError, 'Sala ocupada'):
            atividade.full_clean()


class InscricaoEventoTests(BaseTestCase):
    def test_11_inscricao_registrada(self):
        self.entrar(self.carla)
        self.inscrever_evento(self.semana)
        self.assertTrue(InscricaoEvento.objects.filter(evento=self.semana, participante=self.carla).exists())

    def test_12_inscricao_duplicada_recusada(self):
        self.entrar(self.carla)
        self.inscrever_evento(self.semana)
        resposta = self.inscrever_evento(self.semana)
        self.assertIn('Você já está inscrito neste evento.', self.mensagens(resposta))
        self.assertEqual(InscricaoEvento.objects.filter(evento=self.semana, participante=self.carla).count(), 1)

    def test_13_inscricoes_fechadas_recusadas(self):
        self.entrar(self.carla)
        resposta = self.inscrever_evento(self.egressos)
        self.assertIn('As inscrições deste evento estão fechadas.', self.mensagens(resposta))
        self.assertFalse(InscricaoEvento.objects.filter(evento=self.egressos).exists())

    def test_acoes_que_alteram_estado_exigem_post(self):
        self.entrar(self.carla)
        self.assertEqual(self.client.get(reverse('eventos:inscrever_evento', args=[self.semana.pk])).status_code, 405)


class InscricaoAtividadeTests(BaseTestCase):
    def test_14_atividade_sem_estar_no_evento_recusada(self):
        self.entrar(self.carla)
        resposta = self.inscrever_atividade(self.oficina)
        self.assertIn('Inscreva-se no evento antes de escolher atividades.', self.mensagens(resposta))
        self.assertFalse(InscricaoAtividade.objects.exists())

    def test_15_vagas_diminuem_em_um(self):
        self.entrar(self.carla)
        self.inscrever_evento(self.semana)
        self.assertEqual(self.vagas(self.oficina), 2)
        self.inscrever_atividade(self.oficina)
        self.assertEqual(self.vagas(self.oficina), 1)

    def lotar_oficina(self):
        for usuario in [self.carla, self.diego]:
            self.entrar(usuario)
            self.inscrever_evento(self.semana)
            self.inscrever_atividade(self.oficina)

    def test_16_terceira_inscricao_na_sala_de_capacidade_2_recusada(self):
        self.lotar_oficina()
        self.entrar(self.bruno)
        self.inscrever_evento(self.semana)
        resposta = self.inscrever_atividade(self.oficina)
        self.assertIn('Esta atividade está lotada.', self.mensagens(resposta))
        self.assertEqual(self.oficina.inscricoes.count(), 2)

    def test_17_botao_nao_aparece_apos_lotar(self):
        self.lotar_oficina()
        self.entrar(self.bruno)
        self.inscrever_evento(self.semana)
        resposta = self.client.get(reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertNotContains(resposta, reverse('eventos:inscrever_atividade', args=[self.oficina.pk]))
        self.assertContains(resposta, reverse('eventos:inscrever_atividade', args=[self.git.pk]))

    def test_18_atividade_simultanea_recusada(self):
        self.entrar(self.carla)
        self.inscrever_evento(self.semana)
        self.inscrever_atividade(self.oficina)
        resposta = self.inscrever_atividade(self.abertura)  # 9h–10h30 x 10h–12h
        self.assertTrue(any('Conflito de horário' in m for m in self.mensagens(resposta)))
        self.assertFalse(self.abertura.inscricoes.exists())

    def test_19_atividade_simultanea_de_outro_evento_recusada(self):
        self.entrar(self.carla)
        self.inscrever_evento(self.semana)
        self.inscrever_evento(self.jornada)
        self.inscrever_atividade(self.projetos)  # Semana, 12/11 9h–11h
        resposta = self.inscrever_atividade(self.iniciacao)  # Jornada, 12/11 10h–11h30
        self.assertTrue(any('Conflito de horário' in m for m in self.mensagens(resposta)))
        self.assertFalse(self.iniciacao.inscricoes.exists())

    def test_botao_nao_aparece_para_quem_nao_esta_no_evento_nem_em_conflito(self):
        self.entrar(self.carla)
        resposta = self.client.get(reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertNotContains(resposta, reverse('eventos:inscrever_atividade', args=[self.oficina.pk]))
        self.inscrever_evento(self.semana)
        self.inscrever_atividade(self.oficina)
        resposta = self.client.get(reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertNotContains(resposta, reverse('eventos:inscrever_atividade', args=[self.abertura.pk]))
        self.assertContains(resposta, 'Conflito de horário')

    def test_atividade_de_outro_evento_nao_usa_inscricao_errada(self):
        inscricao = InscricaoEvento.objects.create(evento=self.semana, participante=self.carla)
        with self.assertRaisesMessage(ValidationError, 'não pertence ao evento'):
            InscricaoAtividade(inscricao_evento=inscricao, atividade=self.iniciacao).full_clean()


class CancelamentoTests(BaseTestCase):
    def setUp(self):
        self.entrar(self.carla)
        self.inscrever_evento(self.semana)
        self.inscrever_atividade(self.oficina)
        self.inscrever_atividade(self.git)
        self.inscricao_evento = InscricaoEvento.objects.get(evento=self.semana, participante=self.carla)
        self.inscricao_oficina = InscricaoAtividade.objects.get(inscricao_evento=self.inscricao_evento,
                                                                atividade=self.oficina)

    def test_20_cancelar_atividade_mantem_inscricao_no_evento(self):
        self.client.post(reverse('eventos:cancelar_inscricao_atividade', args=[self.inscricao_oficina.pk]))
        self.assertFalse(InscricaoAtividade.objects.filter(pk=self.inscricao_oficina.pk).exists())
        self.assertTrue(InscricaoEvento.objects.filter(pk=self.inscricao_evento.pk).exists())

    def test_21_vaga_volta_apos_cancelamento(self):
        self.assertEqual(self.vagas(self.oficina), 1)
        self.client.post(reverse('eventos:cancelar_inscricao_atividade', args=[self.inscricao_oficina.pk]))
        self.assertEqual(self.vagas(self.oficina), 2)

    def test_22_cancelar_evento_remove_todas_as_atividades(self):
        self.client.post(reverse('eventos:cancelar_inscricao_evento', args=[self.inscricao_evento.pk]))
        self.assertFalse(InscricaoEvento.objects.filter(pk=self.inscricao_evento.pk).exists())
        self.assertFalse(InscricaoAtividade.objects.filter(inscricao_evento__participante=self.carla).exists())

    def test_23_ninguem_cancela_inscricao_alheia(self):
        self.entrar(self.diego)
        url_atividade = reverse('eventos:cancelar_inscricao_atividade', args=[self.inscricao_oficina.pk])
        url_evento = reverse('eventos:cancelar_inscricao_evento', args=[self.inscricao_evento.pk])
        self.assertEqual(self.client.post(url_atividade).status_code, 403)
        self.assertEqual(self.client.post(url_evento).status_code, 403)
        self.assertTrue(InscricaoAtividade.objects.filter(pk=self.inscricao_oficina.pk).exists())
        self.assertTrue(InscricaoEvento.objects.filter(pk=self.inscricao_evento.pk).exists())


class AgendaTests(BaseTestCase):
    def setUp(self):
        self.entrar(self.carla)
        self.inscrever_evento(self.semana)
        self.inscrever_evento(self.jornada)
        # Inscrições fora de ordem, em dois eventos.
        self.inscrever_atividade(self.git)            # 11/11 14h
        self.inscrever_atividade(self.iniciacao)      # 12/11 10h (Jornada)
        self.inscrever_atividade(self.oficina)        # 11/11 10h

    def test_24_agenda_mostra_atividades_de_todos_os_eventos(self):
        resposta = self.client.get(reverse('eventos:agenda'))
        eventos = {inscricao.atividade.evento for inscricao in resposta.context['inscricoes']}
        self.assertEqual(eventos, {self.semana, self.jornada})

    def test_24b_agenda_mostra_so_as_inscricoes_de_quem_abriu(self):
        self.entrar(self.diego)
        self.inscrever_evento(self.semana)
        self.inscrever_atividade(self.abertura)
        resposta = self.client.get(reverse('eventos:agenda'))
        self.assertEqual([i.atividade for i in resposta.context['inscricoes']], [self.abertura])

    def test_24c_agenda_exige_login(self):
        self.client.logout()
        resposta = self.client.get(reverse('eventos:agenda'))
        self.assertRedirects(resposta, f"{reverse('login')}?next={reverse('eventos:agenda')}",
                             fetch_redirect_response=False)

    def test_25_agenda_ordenada_por_data_e_hora(self):
        resposta = self.client.get(reverse('eventos:agenda'))
        atividades = [inscricao.atividade for inscricao in resposta.context['inscricoes']]
        self.assertEqual(atividades, [self.oficina, self.git, self.iniciacao])


class PainelTests(BaseTestCase):
    def setUp(self):
        for usuario in [self.carla, self.diego]:
            self.entrar(usuario)
            self.inscrever_evento(self.semana)
            self.inscrever_atividade(self.oficina)

    def test_26_organizador_ve_inscritos_por_atividade(self):
        self.entrar(self.ana)
        resposta = self.client.get(reverse('eventos:painel', args=[self.semana.pk]))
        self.assertEqual(resposta.status_code, 200)
        oficina = next(a for a in resposta.context['atividades'] if a.pk == self.oficina.pk)
        self.assertEqual(oficina.total_inscritos, 2)
        self.assertEqual(oficina.vagas_restantes, 0)
        self.assertContains(resposta, 'carla')
        self.assertContains(resposta, 'diego')

    def test_27_organizador_nao_ve_painel_de_evento_alheio(self):
        url = reverse('eventos:painel', args=[self.semana.pk])
        for usuario in [self.bruno, self.carla, self.admin]:
            with self.subTest(usuario.username):
                self.entrar(usuario)
                self.assertEqual(self.client.get(url).status_code, 403)
