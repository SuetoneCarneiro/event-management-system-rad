"""Cenário compartilhado pelos testes.

Tudo é criado aqui, no banco de teste: nenhum teste depende do db.sqlite3 nem do popular_dados.
O setUpTestData roda uma vez por classe, e o Django entrega a cada teste uma cópia dos objetos,
então um teste não enxerga o que outro alterou (a suíte passa com --shuffle).

Mapa do cenário (todas as datas em novembro de 2026, horário de Recife):

    Semana (ana, 10 a 14/11)                         Jornada (bruno, 12 a 13/11)
    - abertura   Auditório   11/11 09:00–10:30       - iniciacao  Sala 203   12/11 10:00–11:30
    - oficina    Laboratório 11/11 10:00–12:00
    - git        Laboratório 11/11 14:00–16:00       Egressos (ana, 05/12, inscrições fechadas)
    - projetos   Auditório   12/11 09:00–11:00

    Laboratório tem capacidade 2.
    abertura x oficina: mesmo horário, salas diferentes (conflito do participante, mesmo evento).
    projetos x iniciacao: mesmo horário, eventos diferentes (conflito entre eventos).
    oficina x git: mesma sala, horários que não se cruzam.
"""
from datetime import date, datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from eventos.models import Atividade, Evento, InscricaoAtividade, InscricaoEvento, Sala
from eventos.signals import GRUPO_ORGANIZADORES


def dt(dia, mes, hora, minuto=0):
    """Data e hora no fuso local, como o usuário digitaria."""
    return timezone.make_aware(datetime(2026, mes, dia, hora, minuto))


# Hash rápido: o padrão (PBKDF2) é lento de propósito e deixaria a suíte lenta à toa.
@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class Cenario(TestCase):

    @classmethod
    def setUpTestData(cls):
        organizadores = Group.objects.get(name=GRUPO_ORGANIZADORES)  # criado no post_migrate

        cls.ana = User.objects.create_user('ana', password='senha-ana')
        cls.bruno = User.objects.create_user('bruno', password='senha-bruno')
        cls.ana.groups.add(organizadores)
        cls.bruno.groups.add(organizadores)
        cls.carla = User.objects.create_user('carla', password='senha-carla')
        cls.diego = User.objects.create_user('diego', password='senha-diego')
        cls.eva = User.objects.create_user('eva', password='senha-eva')
        cls.admin = User.objects.create_superuser('admin', password='senha-admin')

        cls.auditorio = Sala.objects.create(nome='Auditório', bloco='A', capacidade=100)
        cls.laboratorio = Sala.objects.create(nome='Laboratório', bloco='B', capacidade=2)
        cls.sala_203 = Sala.objects.create(nome='Sala 203', bloco='C', capacidade=30)

        cls.semana = Evento.objects.create(
            nome='Semana de Tecnologia', descricao='Palestras e oficinas.',
            data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 14), organizador=cls.ana,
        )
        cls.jornada = Evento.objects.create(
            nome='Jornada Científica', descricao='Iniciação científica.',
            data_inicio=date(2026, 11, 12), data_fim=date(2026, 11, 13), organizador=cls.bruno,
        )
        cls.egressos = Evento.objects.create(
            nome='Encontro de Egressos', descricao='Ex-alunos.',
            data_inicio=date(2026, 12, 5), data_fim=date(2026, 12, 5), organizador=cls.ana,
            inscricoes_abertas=False,
        )

        cls.abertura = cls.criar_atividade(cls.semana, 'Abertura', cls.auditorio, dt(11, 11, 9), dt(11, 11, 10, 30))
        cls.oficina = cls.criar_atividade(cls.semana, 'Oficina de Django', cls.laboratorio, dt(11, 11, 10), dt(11, 11, 12))
        cls.git = cls.criar_atividade(cls.semana, 'Git na prática', cls.laboratorio, dt(11, 11, 14), dt(11, 11, 16))
        cls.projetos = cls.criar_atividade(cls.semana, 'Projetos dos alunos', cls.auditorio, dt(12, 11, 9), dt(12, 11, 11))
        cls.iniciacao = cls.criar_atividade(cls.jornada, 'Iniciação científica', cls.sala_203, dt(12, 11, 10), dt(12, 11, 11, 30))

        cls.tokens = {usuario.username: Token.objects.create(user=usuario).key
                      for usuario in [cls.ana, cls.bruno, cls.carla, cls.diego, cls.eva, cls.admin]}

    @staticmethod
    def criar_atividade(evento, titulo, sala, inicio, fim, tipo=Atividade.Tipo.PALESTRA):
        return Atividade.objects.create(
            evento=evento, titulo=titulo, tipo=tipo, descricao=f'{titulo}.', responsavel='Profa. Ana',
            sala=sala, data_hora_inicio=inicio, data_hora_fim=fim,
        )

    # --- Montagem de estado direto no banco (o "arrange"): não passa pelas regras ---

    @staticmethod
    def inscrever_no_evento(usuario, evento):
        return InscricaoEvento.objects.create(evento=evento, participante=usuario)

    @staticmethod
    def inscrever_na_atividade(inscricao_evento, atividade):
        return InscricaoAtividade.objects.create(inscricao_evento=inscricao_evento, atividade=atividade)

    def lotar_oficina(self):
        """carla e diego ocupam as duas vagas do Laboratório na Oficina."""
        for usuario in [self.carla, self.diego]:
            self.inscrever_na_atividade(self.inscrever_no_evento(usuario, self.semana), self.oficina)

    # --- Consultas usadas nas asserções ---

    @staticmethod
    def vagas(atividade):
        return Atividade.objects.com_vagas().get(pk=atividade.pk).vagas_restantes

    # --- Clientes ---

    def entrar(self, usuario):
        """Site: sessão autenticada (sem passar pela tela de login)."""
        self.client.force_login(usuario)

    def api(self, usuario=None):
        """API: cliente com o token no cabeçalho, como um app ou um script faria."""
        cliente = APIClient()
        if usuario is not None:
            cliente.credentials(HTTP_AUTHORIZATION=f'Token {self.tokens[usuario.username]}')
        return cliente
