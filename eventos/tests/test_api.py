"""API REST: porta aberta (RF10), porta fechada (RF11) e as cinco regras pela porta da API (RF3).

Os clientes usam o token no cabeçalho (Authorization: Token <chave>), como um app ou script faria.
"""
from django.urls import reverse

from eventos.models import Atividade, Evento, InscricaoAtividade, InscricaoEvento

from .base import Cenario, dt

CAMPOS_EVENTO = {'id', 'nome', 'descricao', 'data_inicio', 'data_fim', 'inscricoes_abertas'}
CAMPOS_ATIVIDADE = {
    'id', 'evento', 'titulo', 'tipo', 'tipo_display', 'descricao', 'responsavel',
    'sala', 'sala_nome', 'sala_bloco', 'data_hora_inicio', 'data_hora_fim', 'vagas_restantes',
}


def nova_atividade(evento, sala, inicio, fim, titulo='Nova'):
    return {'evento': evento.pk, 'titulo': titulo, 'tipo': 'PALESTRA', 'descricao': 'd', 'responsavel': 'R',
            'sala': sala.pk, 'data_hora_inicio': inicio.isoformat(), 'data_hora_fim': fim.isoformat()}


# --- RF10: a porta aberta ---

class PortaAbertaTests(Cenario):
    def test_lista_de_eventos_responde_sem_token(self):
        resposta = self.api().get(reverse('api:evento-list'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([e['nome'] for e in resposta.json()['results']],
                         ['Semana de Tecnologia', 'Jornada Científica', 'Encontro de Egressos'])

    def test_programacao_responde_sem_token_com_sala_e_vagas(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        resposta = self.api().get(reverse('api:evento-detail', args=[self.semana.pk]))
        self.assertEqual(resposta.status_code, 200)
        atividades = {a['titulo']: a for a in resposta.json()['atividades']}
        self.assertEqual(len(atividades), 4)
        self.assertEqual(atividades['Oficina de Django']['sala_nome'], 'Laboratório')
        self.assertEqual(atividades['Oficina de Django']['vagas_restantes'], 1)
        self.assertEqual(atividades['Git na prática']['vagas_restantes'], 2)

    def test_evento_publico_traz_exatamente_os_campos_esperados(self):
        evento = self.api().get(reverse('api:evento-list')).json()['results'][0]
        self.assertEqual(set(evento), CAMPOS_EVENTO)

    def test_programacao_publica_traz_exatamente_os_campos_esperados(self):
        programacao = self.api().get(reverse('api:evento-detail', args=[self.semana.pk])).json()
        self.assertEqual(set(programacao), CAMPOS_EVENTO | {'atividades'})
        for atividade in programacao['atividades']:
            self.assertEqual(set(atividade), CAMPOS_ATIVIDADE)

    def test_porta_aberta_nao_expoe_organizador_nem_inscritos(self):
        self.carla.email = 'carla@ifpb.edu.br'
        self.carla.save()
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        for url in [reverse('api:evento-list'), reverse('api:evento-detail', args=[self.semana.pk]),
                    reverse('api:atividade-list')]:
            with self.subTest(url):
                conteudo = self.api().get(url).content.decode()
                self.assertNotIn('organizador', conteudo)
                self.assertNotIn('carla', conteudo)
                self.assertNotIn('@ifpb.edu.br', conteudo)

    def test_lista_de_atividades_e_paginada(self):
        resposta = self.api().get(reverse('api:atividade-list'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(set(resposta.json()), {'count', 'next', 'previous', 'results'})
        self.assertEqual(resposta.json()['count'], 5)

    def test_busca_por_termo_no_titulo_ou_na_descricao(self):
        resposta = self.api().get(reverse('api:atividade-list'), {'search': 'django'})
        self.assertEqual([a['titulo'] for a in resposta.json()['results']], ['Oficina de Django'])

    def test_ordenacao_por_data_de_inicio(self):
        resposta = self.api().get(reverse('api:atividade-list'), {'ordering': '-data_hora_inicio'})
        titulos = [a['titulo'] for a in resposta.json()['results']]
        self.assertEqual(titulos, ['Iniciação científica', 'Projetos dos alunos', 'Git na prática',
                                   'Oficina de Django', 'Abertura'])

    def test_filtro_por_evento(self):
        resposta = self.api().get(reverse('api:atividade-list'), {'evento': self.jornada.pk})
        self.assertEqual([a['titulo'] for a in resposta.json()['results']], ['Iniciação científica'])

    def test_salas_sao_publicas(self):
        resposta = self.api().get(reverse('api:sala-list'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['count'], 3)

    def test_documentacao_e_schema_respondem(self):
        self.assertEqual(self.api().get(reverse('api:docs')).status_code, 200)
        self.assertEqual(self.api().get(reverse('api:schema')).status_code, 200)

    def test_programacao_da_api_tem_consultas_constantes(self):
        url = reverse('api:evento-detail', args=[self.semana.pk])
        with self.assertNumQueries(2):  # evento + atividades (com sala e vagas, via prefetch)
            self.api().get(url)
        for i in range(10):
            self.criar_atividade(self.semana, f'Extra {i}', self.auditorio, dt(13, 11, 8 + i), dt(13, 11, 9 + i))
        with self.assertNumQueries(2):
            resposta = self.api().get(url)
        self.assertEqual(len(resposta.json()['atividades']), 14)


# --- RF11: a porta fechada ---

class PortaFechadaTests(Cenario):
    def setUp(self):
        self.url_atividades = reverse('api:atividade-list')
        self.dados = nova_atividade(self.semana, self.sala_203, dt(13, 11, 10), dt(13, 11, 11))

    def test_criar_atividade_sem_token_responde_401(self):
        resposta = self.api().post(self.url_atividades, self.dados, format='json')
        self.assertEqual(resposta.status_code, 401)
        self.assertFalse(Atividade.objects.filter(titulo='Nova').exists())

    def test_token_invalido_responde_401(self):
        cliente = self.api()
        cliente.credentials(HTTP_AUTHORIZATION='Token chave-que-nao-existe')
        self.assertEqual(cliente.post(self.url_atividades, self.dados, format='json').status_code, 401)

    def test_criar_atividade_com_token_de_participante_responde_403(self):
        resposta = self.api(self.carla).post(self.url_atividades, self.dados, format='json')
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Atividade.objects.filter(titulo='Nova').exists())

    def test_criar_atividade_em_evento_de_outro_organizador_responde_403(self):
        resposta = self.api(self.bruno).post(self.url_atividades, self.dados, format='json')
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Atividade.objects.filter(titulo='Nova').exists())

    def test_criar_atividade_com_token_do_organizador_responde_201(self):
        resposta = self.api(self.ana).post(self.url_atividades, self.dados, format='json')
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()['vagas_restantes'], 30)
        self.assertTrue(Atividade.objects.filter(titulo='Nova', evento=self.semana).exists())

    def test_alterar_evento_sem_token_responde_401(self):
        resposta = self.api().patch(reverse('api:evento-detail', args=[self.semana.pk]), {'nome': 'X'}, format='json')
        self.assertEqual(resposta.status_code, 401)

    def test_organizador_nao_altera_evento_de_outro(self):
        resposta = self.api(self.bruno).patch(reverse('api:evento-detail', args=[self.semana.pk]),
                                              {'nome': 'Invadido'}, format='json')
        self.assertEqual(resposta.status_code, 403)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana de Tecnologia')

    def test_organizador_nao_exclui_evento_de_outro(self):
        resposta = self.api(self.bruno).delete(reverse('api:evento-detail', args=[self.semana.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(Evento.objects.filter(pk=self.semana.pk).exists())

    def test_nem_o_superusuario_altera_evento_de_outro(self):
        resposta = self.api(self.admin).patch(reverse('api:evento-detail', args=[self.semana.pk]),
                                              {'nome': 'Invadido'}, format='json')
        self.assertEqual(resposta.status_code, 403)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana de Tecnologia')

    def test_dono_altera_o_proprio_evento(self):
        resposta = self.api(self.ana).patch(reverse('api:evento-detail', args=[self.semana.pk]),
                                            {'nome': 'Semana 2026'}, format='json')
        self.assertEqual(resposta.status_code, 200)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana 2026')

    def test_organizador_do_evento_criado_vem_do_token_e_nao_do_json(self):
        resposta = self.api(self.ana).post(reverse('api:evento-list'), {
            'nome': 'Hackathon', 'descricao': 'd', 'data_inicio': '2026-11-20', 'data_fim': '2026-11-21',
            'organizador': self.bruno.pk,
        }, format='json')
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(Evento.objects.get(nome='Hackathon').organizador, self.ana)

    def test_participante_da_inscricao_vem_do_token_e_nao_do_json(self):
        resposta = self.api(self.carla).post(reverse('api:inscricoes'),
                                             {'evento': self.semana.pk, 'participante': self.diego.pk}, format='json')
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(InscricaoEvento.objects.get().participante, self.carla)

    def test_agenda_sem_token_responde_401(self):
        self.assertEqual(self.api().get(reverse('api:agenda')).status_code, 401)

    def test_agenda_traz_so_as_atividades_de_quem_apresentou_o_token_em_ordem(self):
        semana = self.inscrever_no_evento(self.carla, self.semana)
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.jornada), self.iniciacao)
        self.inscrever_na_atividade(semana, self.git)
        self.inscrever_na_atividade(semana, self.oficina)
        self.inscrever_na_atividade(self.inscrever_no_evento(self.diego, self.semana), self.abertura)
        resposta = self.api(self.carla).get(reverse('api:agenda'))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual([i['atividade']['titulo'] for i in resposta.json()],
                         ['Oficina de Django', 'Git na prática', 'Iniciação científica'])

    def test_token_obtido_com_usuario_e_senha(self):
        resposta = self.api().post(reverse('api:token'), {'username': 'carla', 'password': 'senha-carla'},
                                   format='json')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['token'], self.tokens['carla'])


class CancelarInscricaoAlheiaPelaApiTests(Cenario):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.inscricao_carla = cls.inscrever_no_evento(cls.carla, cls.semana)
        cls.carla_na_oficina = cls.inscrever_na_atividade(cls.inscricao_carla, cls.oficina)

    def test_cancelar_atividade_alheia_responde_403_e_mantem_a_inscricao(self):
        resposta = self.api(self.diego).delete(
            reverse('api:inscricao-atividade-cancelar', args=[self.carla_na_oficina.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(InscricaoAtividade.objects.filter(pk=self.carla_na_oficina.pk).exists())

    def test_cancelar_evento_alheio_responde_403_e_mantem_a_inscricao(self):
        resposta = self.api(self.diego).delete(reverse('api:inscricao-cancelar', args=[self.inscricao_carla.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(InscricaoEvento.objects.filter(pk=self.inscricao_carla.pk).exists())

    def test_cancelar_sem_token_responde_401(self):
        resposta = self.api().delete(reverse('api:inscricao-cancelar', args=[self.inscricao_carla.pk]))
        self.assertEqual(resposta.status_code, 401)
        self.assertTrue(InscricaoEvento.objects.filter(pk=self.inscricao_carla.pk).exists())


# --- Inscrição no evento pela API ---

class InscricaoNoEventoPelaApiTests(Cenario):
    def inscrever(self, evento):
        return self.api(self.carla).post(reverse('api:inscricoes'), {'evento': evento.pk}, format='json')

    def test_inscricao_responde_201_e_grava(self):
        resposta = self.inscrever(self.semana)
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()['evento_nome'], 'Semana de Tecnologia')
        self.assertTrue(InscricaoEvento.objects.filter(evento=self.semana, participante=self.carla).exists())

    def test_segunda_inscricao_responde_400(self):
        self.inscrever_no_evento(self.carla, self.semana)
        resposta = self.inscrever(self.semana)
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'non_field_errors': ['Você já está inscrito neste evento.']})

    def test_evento_fechado_responde_400(self):
        resposta = self.inscrever(self.egressos)
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'non_field_errors': ['As inscrições deste evento estão fechadas.']})

    def test_evento_inexistente_responde_400(self):
        resposta = self.api(self.carla).post(reverse('api:inscricoes'), {'evento': 9999}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('evento', resposta.json())


# --- RF3: as cinco regras pela porta da API ---

class RegrasPelaApiTests(Cenario):
    def inscrever(self, usuario, atividade):
        return self.api(usuario).post(reverse('api:inscricoes-atividade'), {'atividade': atividade.pk},
                                      format='json')

    # RN1 — capacidade
    def test_rn1_inscricao_com_vaga_responde_201_e_vagas_diminuem(self):
        self.inscrever_no_evento(self.carla, self.semana)
        resposta = self.inscrever(self.carla, self.oficina)
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(self.vagas(self.oficina), 1)

    def test_rn1_inscricao_alem_da_capacidade_responde_400(self):
        self.lotar_oficina()
        self.inscrever_no_evento(self.eva, self.semana)
        resposta = self.inscrever(self.eva, self.oficina)
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'non_field_errors': ['Esta atividade está lotada.']})
        self.assertEqual(self.oficina.inscricoes.count(), 2)

    # RN2 — conflito na agenda do participante
    def test_rn2_atividade_em_outro_horario_responde_201(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        self.assertEqual(self.inscrever(self.carla, self.git).status_code, 201)

    def test_rn2_atividade_simultanea_responde_400(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        resposta = self.inscrever(self.carla, self.abertura)
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'non_field_errors': [
            'Conflito de horário com "Oficina de Django" (Semana de Tecnologia), 11/11 10:00–12:00.']})
        self.assertFalse(self.abertura.inscricoes.exists())

    def test_rn2_atividade_simultanea_de_outro_evento_responde_400(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.projetos)
        self.inscrever_no_evento(self.carla, self.jornada)
        resposta = self.inscrever(self.carla, self.iniciacao)
        self.assertEqual(resposta.status_code, 400)
        self.assertIn('Conflito de horário com "Projetos dos alunos"', resposta.json()['non_field_errors'][0])
        self.assertFalse(self.iniciacao.inscricoes.exists())

    # RN3 — sala ocupada
    def test_rn3_mesma_sala_em_outro_horario_responde_201(self):
        dados = nova_atividade(self.semana, self.laboratorio, dt(11, 11, 12), dt(11, 11, 13))
        resposta = self.api(self.ana).post(reverse('api:atividade-list'), dados, format='json')
        self.assertEqual(resposta.status_code, 201)

    def test_rn3_sala_ocupada_responde_400_com_mensagem(self):
        dados = nova_atividade(self.semana, self.laboratorio, dt(11, 11, 11), dt(11, 11, 13))
        resposta = self.api(self.ana).post(reverse('api:atividade-list'), dados, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'sala': [
            'Sala ocupada nesse horário por "Oficina de Django" (Semana de Tecnologia), 11/11 10:00–12:00.']})
        self.assertFalse(Atividade.objects.filter(titulo='Nova').exists())

    def test_fim_antes_do_inicio_responde_400_em_json(self):
        dados = nova_atividade(self.semana, self.sala_203, dt(13, 11, 11), dt(13, 11, 10))
        resposta = self.api(self.ana).post(reverse('api:atividade-list'), dados, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'non_field_errors': [
            'A data e hora de fim não podem ser anteriores à data e hora de início.']})

    # RN4 — inscrição prévia no evento
    def test_rn4_quem_esta_no_evento_se_inscreve_na_atividade(self):
        self.inscrever_no_evento(self.carla, self.semana)
        self.assertEqual(self.inscrever(self.carla, self.oficina).status_code, 201)

    def test_rn4_quem_nao_esta_no_evento_responde_400(self):
        resposta = self.inscrever(self.carla, self.oficina)
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json(), {'non_field_errors': ['Inscreva-se no evento antes de escolher atividades.']})
        self.assertFalse(InscricaoAtividade.objects.exists())

    # RN5 — cancelamento em cascata
    def test_rn5_cancelar_evento_cancela_as_atividades_dele(self):
        inscricao = self.inscrever_no_evento(self.carla, self.semana)
        self.inscrever_na_atividade(inscricao, self.oficina)
        self.inscrever_na_atividade(inscricao, self.git)
        resposta = self.api(self.carla).delete(reverse('api:inscricao-cancelar', args=[inscricao.pk]))
        self.assertEqual(resposta.status_code, 204)
        self.assertFalse(InscricaoAtividade.objects.filter(inscricao_evento__participante=self.carla).exists())
        self.assertEqual(self.vagas(self.oficina), 2)

    def test_rn5_cancelar_evento_preserva_atividades_de_outros_eventos(self):
        inscricao_semana = self.inscrever_no_evento(self.carla, self.semana)
        self.inscrever_na_atividade(inscricao_semana, self.oficina)
        na_iniciacao = self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.jornada), self.iniciacao)
        self.api(self.carla).delete(reverse('api:inscricao-cancelar', args=[inscricao_semana.pk]))
        self.assertTrue(InscricaoAtividade.objects.filter(pk=na_iniciacao.pk).exists())

    def test_cancelar_so_a_atividade_mantem_o_evento_e_devolve_a_vaga(self):
        inscricao = self.inscrever_no_evento(self.carla, self.semana)
        na_oficina = self.inscrever_na_atividade(inscricao, self.oficina)
        resposta = self.api(self.carla).delete(reverse('api:inscricao-atividade-cancelar', args=[na_oficina.pk]))
        self.assertEqual(resposta.status_code, 204)
        self.assertTrue(InscricaoEvento.objects.filter(pk=inscricao.pk).exists())
        self.assertEqual(self.vagas(self.oficina), 2)
