from datetime import date, datetime

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from eventos.models import Atividade, Evento, InscricaoAtividade, InscricaoEvento, Sala
from eventos.signals import GRUPO_ORGANIZADORES

SENHA_PADRAO = 'eventos2026'

# (username, senha, nome, sobrenome, papel)
CONTAS = [
    ('admin', 'admin', 'Admin', '', 'superusuario'),              # conta 1: cadastra salas pelo Admin
    ('ana', SENHA_PADRAO, 'Ana', 'Organizadora', 'organizador'),    # conta 2: cria eventos e atividades
    ('bruno', SENHA_PADRAO, 'Bruno', 'Organizador', 'organizador'),  # conta 3: não altera o que é da Ana
    ('carla', SENHA_PADRAO, 'Carla', 'Participante', 'participante'),  # conta 4: inscreve-se
    ('diego', SENHA_PADRAO, 'Diego', 'Participante', 'participante'),  # conta 5: ocupa a última vaga
]


def dt(dia, mes, hora, minuto=0):
    return timezone.make_aware(datetime(2026, mes, dia, hora, minuto))


class Command(BaseCommand):
    help = 'Cadastra as cinco contas de teste e os dados do enunciado (salas, eventos e atividades).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar', action='store_true',
            help='Apaga salas, eventos, atividades e inscrições antes de popular.',
        )

    @transaction.atomic
    def handle(self, *args, limpar=False, **options):
        if limpar:
            InscricaoAtividade.objects.all().delete()
            InscricaoEvento.objects.all().delete()
            Atividade.objects.all().delete()
            Evento.objects.all().delete()
            Sala.objects.all().delete()
            self.stdout.write('Dados de eventos apagados.')

        usuarios = self.criar_contas()
        if Evento.objects.exists():
            self.stdout.write(self.style.WARNING(
                'Já existem eventos cadastrados; nada foi criado. Use --limpar para recriar.'
            ))
            return
        self.criar_dados(usuarios)
        self.stdout.write(self.style.SUCCESS('Dados de teste cadastrados.'))

    def criar_contas(self):
        organizadores = Group.objects.get(name=GRUPO_ORGANIZADORES)
        usuarios = {}
        for username, senha, nome, sobrenome, papel in CONTAS:
            usuario, criado = User.objects.get_or_create(
                username=username, defaults={'first_name': nome, 'last_name': sobrenome},
            )
            if criado:
                usuario.set_password(senha)  # nunca atribuir direto em usuario.password
                if papel == 'superusuario':
                    usuario.is_staff = usuario.is_superuser = True
                usuario.save()
                self.stdout.write(f'Conta criada: {username} ({papel})')
            else:
                self.stdout.write(f'Conta já existia, senha mantida: {username}')
            if papel == 'organizador':
                usuario.groups.add(organizadores)
            usuarios[username] = usuario
        return usuarios

    def criar_dados(self, usuarios):
        auditorio = Sala.objects.create(nome='Auditório', bloco='A', capacidade=100)
        laboratorio = Sala.objects.create(nome='Laboratório 1', bloco='B', capacidade=2)
        sala_203 = Sala.objects.create(nome='Sala 203', bloco='C', capacidade=30)

        # Semana e Jornada têm períodos que se cruzam (12 e 13/11), e são de organizadores diferentes.
        semana = Evento.objects.create(
            nome='Semana de Tecnologia',
            descricao='Palestras, minicursos e apresentações de projetos do curso de Sistemas para Internet.',
            data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 14),
            organizador=usuarios['ana'],
        )
        jornada = Evento.objects.create(
            nome='Jornada Científica',
            descricao='Apresentação dos trabalhos de iniciação científica do campus.',
            data_inicio=date(2026, 11, 12), data_fim=date(2026, 11, 13),
            organizador=usuarios['bruno'],
        )
        egressos = Evento.objects.create(
            nome='Encontro de Egressos',
            descricao='Ex-alunos contam suas trajetórias. Inscrições encerradas.',
            data_inicio=date(2026, 12, 5), data_fim=date(2026, 12, 5),
            inscricoes_abertas=False,
            organizador=usuarios['ana'],
        )

        atividades = [
            # Abertura e Oficina de Django: mesmo horário (10h–10h30), salas distintas.
            dict(evento=semana, titulo='Abertura: o futuro da web', tipo=Atividade.Tipo.PALESTRA,
                 responsavel='Profa. Helena Duarte', sala=auditorio,
                 data_hora_inicio=dt(11, 11, 9), data_hora_fim=dt(11, 11, 10, 30)),
            # Oficina de Django e Git na prática: mesma sala (capacidade 2), horários que não se cruzam.
            dict(evento=semana, titulo='Oficina de Django', tipo=Atividade.Tipo.TREINAMENTO,
                 responsavel='Prof. Marcos Lima', sala=laboratorio,
                 data_hora_inicio=dt(11, 11, 10), data_hora_fim=dt(11, 11, 12)),
            dict(evento=semana, titulo='Git na prática', tipo=Atividade.Tipo.TREINAMENTO,
                 responsavel='Prof. Marcos Lima', sala=laboratorio,
                 data_hora_inicio=dt(11, 11, 14), data_hora_fim=dt(11, 11, 16)),
            # Projetos dos alunos (Semana) e Iniciação científica (Jornada): eventos diferentes, horários sobrepostos.
            dict(evento=semana, titulo='Projetos dos alunos', tipo=Atividade.Tipo.APRESENTACAO,
                 responsavel='Turma P5', sala=sala_203,
                 data_hora_inicio=dt(12, 11, 9), data_hora_fim=dt(12, 11, 11)),
            dict(evento=jornada, titulo='Iniciação científica no IFPB', tipo=Atividade.Tipo.PALESTRA,
                 responsavel='Prof. Ricardo Alves', sala=auditorio,
                 data_hora_inicio=dt(12, 11, 10), data_hora_fim=dt(12, 11, 11, 30)),
            dict(evento=jornada, titulo='Sessão de pôsteres', tipo=Atividade.Tipo.APRESENTACAO,
                 responsavel='Bolsistas PIBIC', sala=sala_203,
                 data_hora_inicio=dt(13, 11, 14), data_hora_fim=dt(13, 11, 17)),
            dict(evento=egressos, titulo='Roda de conversa com egressos', tipo=Atividade.Tipo.PALESTRA,
                 responsavel='Coordenação do curso', sala=auditorio,
                 data_hora_inicio=dt(5, 12, 19), data_hora_fim=dt(5, 12, 21)),
        ]
        for dados in atividades:
            atividade = Atividade(descricao=f'{dados["titulo"]}.', **dados)
            atividade.full_clean()  # os dados de teste também respeitam as regras (RN3 etc.)
            atividade.save()
