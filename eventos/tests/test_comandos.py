"""O comando popular_dados cria exatamente o que o README promete ao avaliador.

Se o mapa de dados do README mentir (uma sala pequena que não é pequena, eventos que não se cruzam),
metade dos critérios não pode ser demonstrada. Este teste roda o comando no banco de teste.
"""
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token

from eventos.management.commands.popular_dados import TOKENS
from eventos.models import Atividade, Evento, InscricaoEvento, Sala
from eventos.signals import GRUPO_ORGANIZADORES


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PopularDadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('popular_dados', stdout=StringIO())

    def atividade(self, titulo):
        return Atividade.objects.get(titulo=titulo)

    def test_cinco_contas_com_papeis_senhas_e_tokens_do_readme(self):
        papeis = {'admin': None, 'ana': True, 'bruno': True, 'carla': False, 'diego': False}
        senhas = {'admin': 'admin', 'ana': 'eventos2026', 'bruno': 'eventos2026',
                  'carla': 'eventos2026', 'diego': 'eventos2026'}
        self.assertEqual(set(User.objects.values_list('username', flat=True)), set(papeis))
        for username, organizador in papeis.items():
            with self.subTest(username):
                usuario = User.objects.get(username=username)
                self.assertTrue(usuario.check_password(senhas[username]))
                self.assertEqual(Token.objects.get(user=usuario).key, TOKENS[username])
                if organizador is None:
                    self.assertTrue(usuario.is_superuser)
                else:
                    self.assertEqual(usuario.groups.filter(name=GRUPO_ORGANIZADORES).exists(), organizador)

    def test_existe_uma_sala_de_capacidade_2(self):
        self.assertEqual(Sala.objects.get(nome='Laboratório 1').capacidade, 2)

    def test_semana_e_jornada_tem_periodos_que_se_cruzam_e_donos_diferentes(self):
        semana = Evento.objects.get(nome='Semana de Tecnologia')
        jornada = Evento.objects.get(nome='Jornada Científica')
        self.assertTrue(semana.data_inicio <= jornada.data_fim and jornada.data_inicio <= semana.data_fim)
        self.assertNotEqual(semana.organizador, jornada.organizador)

    def test_existe_evento_com_inscricoes_fechadas(self):
        self.assertFalse(Evento.objects.get(nome='Encontro de Egressos').inscricoes_abertas)

    def test_atividades_simultaneas_em_salas_distintas(self):
        abertura, oficina = self.atividade('Abertura: o futuro da web'), self.atividade('Oficina de Django')
        self.assertTrue(abertura.sobrepoe(oficina))
        self.assertNotEqual(abertura.sala, oficina.sala)

    def test_atividades_na_mesma_sala_em_horarios_que_nao_se_cruzam(self):
        oficina, git = self.atividade('Oficina de Django'), self.atividade('Git na prática')
        self.assertEqual(oficina.sala, git.sala)
        self.assertFalse(oficina.sobrepoe(git))
        self.assertEqual(oficina.sala.capacidade, 2)

    def test_atividades_simultaneas_em_eventos_diferentes(self):
        projetos, iniciacao = self.atividade('Projetos dos alunos'), self.atividade('Iniciação científica no IFPB')
        self.assertTrue(projetos.sobrepoe(iniciacao))
        self.assertNotEqual(projetos.evento, iniciacao.evento)

    def test_banco_entregue_sem_inscricoes(self):
        self.assertFalse(InscricaoEvento.objects.exists())

    def test_rodar_de_novo_nao_duplica_nada(self):
        call_command('popular_dados', stdout=StringIO())
        self.assertEqual((User.objects.count(), Evento.objects.count(), Atividade.objects.count()), (5, 3, 7))

    def test_limpar_recria_os_dados(self):
        Sala.objects.filter(nome='Laboratório 1').update(capacidade=50)
        call_command('popular_dados', '--limpar', stdout=StringIO())
        self.assertEqual(Sala.objects.get(nome='Laboratório 1').capacidade, 2)
        self.assertEqual(Atividade.objects.count(), 7)
