"""Site HTML: leitura (RF5), escrita (RF6), anônimo (RF7), autorização (RF8), consultas (RF12)
e as cinco regras de negócio pela porta do site (RF2/RF3).
"""
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse

from eventos.models import Atividade, Evento, InscricaoAtividade, InscricaoEvento

from .base import Cenario, dt


def mensagens(resposta):
    return [str(m) for m in get_messages(resposta.wsgi_request)]


# --- RF5: views de leitura ---

class ProgramacaoTests(Cenario):
    def setUp(self):
        self.url = reverse('eventos:detalhe', args=[self.semana.pk])

    def test_anonimo_ve_a_programacao_com_status_200_e_o_template_certo(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'eventos/evento_detail.html')

    def test_pagina_mostra_atividades_tipo_responsavel_sala_e_horario(self):
        resposta = self.client.get(self.url)
        for texto in ['Semana de Tecnologia', 'Oficina de Django', 'Palestra', 'Profa. Ana', 'Laboratório',
                      '10:00–12:00']:
            self.assertContains(resposta, texto)
        self.assertNotContains(resposta, 'Iniciação científica')  # atividade de outro evento

    def test_contexto_traz_o_evento_e_as_atividades_com_vagas(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context['evento'], self.semana)
        atividades = {a.titulo: a for a in resposta.context['atividades']}
        self.assertEqual(set(atividades), {'Abertura', 'Oficina de Django', 'Git na prática', 'Projetos dos alunos'})
        self.assertEqual(atividades['Oficina de Django'].vagas_restantes, 1)
        self.assertEqual(atividades['Git na prática'].vagas_restantes, 2)
        self.assertIsNone(resposta.context['inscricao_evento'])
        self.assertFalse(resposta.context['eh_organizador'])

    def test_atividade_lotada_aparece_como_lotada(self):
        self.lotar_oficina()
        self.assertContains(self.client.get(self.url), 'Lotada')

    def test_evento_inexistente_responde_404(self):
        self.assertEqual(self.client.get(reverse('eventos:detalhe', args=[9999])).status_code, 404)


class ListaDeEventosTests(Cenario):
    def test_anonimo_ve_a_lista_de_eventos(self):
        resposta = self.client.get(reverse('eventos:lista'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'eventos/evento_list.html')
        self.assertQuerySetEqual(resposta.context['eventos'], [self.semana, self.jornada, self.egressos])
        self.assertContains(resposta, 'Inscrições fechadas')


# --- RF12: consultas ao banco ---

class ConsultasDaProgramacaoTests(Cenario):
    """O número de consultas não pode crescer com a quantidade de atividades (sem N+1)."""

    CONSULTAS_ANONIMO = 2       # evento + atividades (com sala e vagas, num JOIN)
    # + sessão, usuário, inscrição no evento, inscrições do participante
    # e as 2 de permissões que o menu consulta ({% if perms.eventos.add_evento %})
    CONSULTAS_PARTICIPANTE = 8

    def acrescentar_atividades(self, quantidade):
        for i in range(quantidade):
            inicio = dt(13, 11, 8, 0)
            self.criar_atividade(self.semana, f'Extra {i}', self.auditorio,
                                 inicio.replace(hour=8 + i), inicio.replace(hour=9 + i))

    def test_programacao_para_anonimo_tem_consultas_constantes(self):
        url = reverse('eventos:detalhe', args=[self.semana.pk])
        with self.assertNumQueries(self.CONSULTAS_ANONIMO):
            self.client.get(url)
        self.acrescentar_atividades(10)
        with self.assertNumQueries(self.CONSULTAS_ANONIMO):
            resposta = self.client.get(url)
        self.assertEqual(len(resposta.context['atividades']), 14)

    def test_programacao_para_participante_tem_consultas_constantes(self):
        inscricao = self.inscrever_no_evento(self.carla, self.semana)
        self.inscrever_na_atividade(inscricao, self.oficina)
        self.entrar(self.carla)
        url = reverse('eventos:detalhe', args=[self.semana.pk])
        with self.assertNumQueries(self.CONSULTAS_PARTICIPANTE):
            self.client.get(url)
        self.acrescentar_atividades(10)
        self.inscrever_na_atividade(inscricao, Atividade.objects.get(titulo='Extra 0'))
        with self.assertNumQueries(self.CONSULTAS_PARTICIPANTE):
            self.client.get(url)


# --- RF6: views de escrita ---

class InscricaoNoEventoPeloSiteTests(Cenario):
    def setUp(self):
        self.entrar(self.carla)
        self.url = reverse('eventos:inscrever_evento', args=[self.semana.pk])

    def test_inscricao_grava_no_banco_redireciona_e_avisa(self):
        resposta = self.client.post(self.url)
        self.assertTrue(InscricaoEvento.objects.filter(evento=self.semana, participante=self.carla).exists())
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertIn('Inscrição em "Semana de Tecnologia" realizada. Agora escolha suas atividades.',
                      mensagens(resposta))

    def test_segunda_inscricao_e_recusada_com_mensagem(self):
        self.inscrever_no_evento(self.carla, self.semana)
        resposta = self.client.post(self.url)
        self.assertEqual(InscricaoEvento.objects.filter(evento=self.semana, participante=self.carla).count(), 1)
        self.assertIn('Você já está inscrito neste evento.', mensagens(resposta))

    def test_evento_com_inscricoes_fechadas_recusa_com_mensagem(self):
        resposta = self.client.post(reverse('eventos:inscrever_evento', args=[self.egressos.pk]))
        self.assertFalse(InscricaoEvento.objects.filter(evento=self.egressos).exists())
        self.assertIn('As inscrições deste evento estão fechadas.', mensagens(resposta))

    def test_get_nao_inscreve(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertFalse(InscricaoEvento.objects.exists())


class CancelamentosPeloSiteTests(Cenario):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.inscricao_semana = cls.inscrever_no_evento(cls.carla, cls.semana)
        cls.na_oficina = cls.inscrever_na_atividade(cls.inscricao_semana, cls.oficina)
        cls.no_git = cls.inscrever_na_atividade(cls.inscricao_semana, cls.git)

    def setUp(self):
        self.entrar(self.carla)

    def test_cancelar_atividade_libera_a_vaga_redireciona_e_avisa(self):
        resposta = self.client.post(reverse('eventos:cancelar_inscricao_atividade', args=[self.na_oficina.pk]))
        self.assertFalse(InscricaoAtividade.objects.filter(pk=self.na_oficina.pk).exists())
        self.assertTrue(InscricaoEvento.objects.filter(pk=self.inscricao_semana.pk).exists())
        self.assertEqual(self.vagas(self.oficina), 2)
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertIn('Você saiu de "Oficina de Django". A vaga foi liberada.', mensagens(resposta))

    def test_cancelar_pela_agenda_volta_para_a_agenda(self):
        resposta = self.client.post(reverse('eventos:cancelar_inscricao_atividade', args=[self.na_oficina.pk]),
                                    {'next': reverse('eventos:agenda')})
        self.assertRedirects(resposta, reverse('eventos:agenda'))

    def test_next_para_outro_site_e_ignorado(self):
        resposta = self.client.post(reverse('eventos:cancelar_inscricao_atividade', args=[self.na_oficina.pk]),
                                    {'next': 'https://site-malicioso.example/'})
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))

    def test_cancelar_evento_redireciona_e_avisa_quantas_atividades_sairam(self):
        resposta = self.client.post(reverse('eventos:cancelar_inscricao_evento', args=[self.inscricao_semana.pk]))
        self.assertFalse(InscricaoEvento.objects.filter(pk=self.inscricao_semana.pk).exists())
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertIn('Inscrição em "Semana de Tecnologia" cancelada. '
                      'Você também saiu de 2 atividade(s) deste evento.', mensagens(resposta))


# --- RF2/RF3: as cinco regras pela porta do site ---

class RegrasPeloSiteTests(Cenario):
    def inscrever(self, atividade):
        return self.client.post(reverse('eventos:inscrever_atividade', args=[atividade.pk]))

    # RN1 — capacidade
    def test_rn1_inscricao_com_vaga_e_aceita_e_vagas_diminuem(self):
        self.inscrever_no_evento(self.carla, self.semana)
        self.entrar(self.carla)
        resposta = self.inscrever(self.oficina)
        self.assertTrue(InscricaoAtividade.objects.filter(atividade=self.oficina,
                                                          inscricao_evento__participante=self.carla).exists())
        self.assertEqual(self.vagas(self.oficina), 1)
        self.assertIn('Inscrição em "Oficina de Django" realizada.', mensagens(resposta))

    def test_rn1_inscricao_alem_da_capacidade_e_recusada(self):
        self.lotar_oficina()
        self.inscrever_no_evento(self.eva, self.semana)
        self.entrar(self.eva)
        resposta = self.inscrever(self.oficina)
        self.assertEqual(self.oficina.inscricoes.count(), 2)
        self.assertIn('Esta atividade está lotada.', mensagens(resposta))

    def test_repetir_a_mesma_atividade_e_recusado_com_mensagem_propria(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        self.entrar(self.carla)
        resposta = self.inscrever(self.oficina)
        self.assertEqual(self.oficina.inscricoes.count(), 1)
        self.assertIn('Você já está inscrito nesta atividade.', mensagens(resposta))

    # RN2 — conflito na agenda do participante
    def test_rn2_atividade_em_outro_horario_e_aceita(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        self.entrar(self.carla)
        self.inscrever(self.git)
        self.assertTrue(self.git.inscricoes.exists())

    def test_rn2_atividade_simultanea_e_recusada(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        self.entrar(self.carla)
        resposta = self.inscrever(self.abertura)
        self.assertFalse(self.abertura.inscricoes.exists())
        self.assertIn('Conflito de horário com "Oficina de Django" (Semana de Tecnologia), 11/11 10:00–12:00.',
                      mensagens(resposta))

    def test_rn2_atividade_simultanea_de_outro_evento_e_recusada(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.projetos)
        self.inscrever_no_evento(self.carla, self.jornada)
        self.entrar(self.carla)
        resposta = self.inscrever(self.iniciacao)
        self.assertFalse(self.iniciacao.inscricoes.exists())
        self.assertIn('Conflito de horário com "Projetos dos alunos" (Semana de Tecnologia), 12/11 09:00–11:00.',
                      mensagens(resposta))

    # RN3 — sala ocupada
    def criar_no_laboratorio(self, inicio, fim):
        self.entrar(self.ana)
        return self.client.post(reverse('eventos:atividade_criar', args=[self.semana.pk]), {
            'titulo': 'Nova', 'tipo': 'PALESTRA', 'descricao': 'd', 'responsavel': 'R',
            'sala': self.laboratorio.pk, 'data_hora_inicio': inicio, 'data_hora_fim': fim,
        })

    def test_rn3_mesma_sala_em_outro_horario_e_aceita(self):
        resposta = self.criar_no_laboratorio('2026-11-11T12:00', '2026-11-11T13:00')
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))
        self.assertTrue(Atividade.objects.filter(titulo='Nova').exists())

    def test_rn3_sala_ocupada_e_recusada_com_mensagem(self):
        resposta = self.criar_no_laboratorio('2026-11-11T11:00', '2026-11-11T13:00')
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Atividade.objects.filter(titulo='Nova').exists())
        self.assertFormError(resposta.context['form'], 'sala',
                             'Sala ocupada nesse horário por "Oficina de Django" (Semana de Tecnologia), '
                             '11/11 10:00–12:00.')

    # RN4 — inscrição prévia no evento
    def test_rn4_quem_esta_no_evento_se_inscreve_na_atividade(self):
        self.inscrever_no_evento(self.carla, self.semana)
        self.entrar(self.carla)
        self.inscrever(self.oficina)
        self.assertTrue(self.oficina.inscricoes.exists())

    def test_rn4_quem_nao_esta_no_evento_e_recusado(self):
        self.entrar(self.carla)
        resposta = self.inscrever(self.oficina)
        self.assertFalse(InscricaoAtividade.objects.exists())
        self.assertIn('Inscreva-se no evento antes de escolher atividades.', mensagens(resposta))

    # RN5 — cancelamento em cascata
    def test_rn5_cancelar_evento_cancela_as_atividades_dele(self):
        inscricao = self.inscrever_no_evento(self.carla, self.semana)
        self.inscrever_na_atividade(inscricao, self.oficina)
        self.inscrever_na_atividade(inscricao, self.git)
        self.entrar(self.carla)
        self.client.post(reverse('eventos:cancelar_inscricao_evento', args=[inscricao.pk]))
        self.assertFalse(InscricaoAtividade.objects.filter(inscricao_evento__participante=self.carla).exists())
        self.assertEqual(self.vagas(self.oficina), 2)

    def test_rn5_cancelar_evento_preserva_atividades_de_outros_eventos(self):
        inscricao_semana = self.inscrever_no_evento(self.carla, self.semana)
        self.inscrever_na_atividade(inscricao_semana, self.oficina)
        na_iniciacao = self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.jornada), self.iniciacao)
        self.entrar(self.carla)
        self.client.post(reverse('eventos:cancelar_inscricao_evento', args=[inscricao_semana.pk]))
        self.assertTrue(InscricaoAtividade.objects.filter(pk=na_iniciacao.pk).exists())


# --- RF7: autenticação ---

class AnonimoTests(Cenario):
    def assertRedirecionaParaLogin(self, resposta, url):
        self.assertRedirects(resposta, f"{reverse('login')}?next={url}", fetch_redirect_response=False)

    def test_anonimo_que_tenta_se_inscrever_vai_para_o_login_com_next(self):
        url = reverse('eventos:inscrever_evento', args=[self.semana.pk])
        self.assertRedirecionaParaLogin(self.client.post(url), url)
        self.assertFalse(InscricaoEvento.objects.exists())

    def test_anonimo_que_abre_a_agenda_vai_para_o_login_com_next(self):
        url = reverse('eventos:agenda')
        self.assertRedirecionaParaLogin(self.client.get(url), url)

    def test_anonimo_que_tenta_criar_evento_vai_para_o_login_com_next(self):
        url = reverse('eventos:criar')
        self.assertRedirecionaParaLogin(self.client.get(url), url)

    def test_anonimo_que_abre_meus_eventos_vai_para_o_login_com_next(self):
        url = reverse('eventos:meus_eventos')
        self.assertRedirecionaParaLogin(self.client.get(url), url)

    def test_programacao_mostra_link_de_login_que_volta_para_o_evento(self):
        url = reverse('eventos:detalhe', args=[self.semana.pk])
        self.assertContains(self.client.get(url), f"{reverse('login')}?next={url}")


class CadastroTests(Cenario):
    def test_conta_recem_cadastrada_entra_como_participante_comum(self):
        resposta = self.client.post(reverse('cadastro'), {
            'username': 'novato', 'first_name': 'Novo', 'last_name': 'Aluno', 'email': 'novo@ifpb.edu.br',
            'password1': 'SenhaForte!2026', 'password2': 'SenhaForte!2026',
        })
        self.assertRedirects(resposta, reverse('eventos:lista'))
        novato = User.objects.get(username='novato')
        self.assertFalse(novato.groups.exists())
        self.assertFalse(novato.has_perm('eventos.add_evento'))
        self.assertEqual(int(self.client.session['_auth_user_id']), novato.pk)  # já entrou logado


# --- RF8: autorização (resposta + banco intacto) ---

class AutorizacaoTests(Cenario):
    dados_evento = {'nome': 'Invadido', 'descricao': 'x', 'data_inicio': '2026-11-10', 'data_fim': '2026-11-14'}

    def test_participante_nao_cria_evento(self):
        self.entrar(self.carla)
        resposta = self.client.post(reverse('eventos:criar'), self.dados_evento)
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Evento.objects.filter(nome='Invadido').exists())

    def test_participante_nao_edita_evento(self):
        self.entrar(self.carla)
        resposta = self.client.post(reverse('eventos:editar', args=[self.semana.pk]), self.dados_evento)
        self.assertEqual(resposta.status_code, 403)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana de Tecnologia')

    def test_organizador_nao_edita_evento_de_outro(self):
        self.entrar(self.bruno)
        url = reverse('eventos:editar', args=[self.semana.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        resposta = self.client.post(url, self.dados_evento)
        self.assertEqual(resposta.status_code, 403)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana de Tecnologia')

    def test_organizador_nao_exclui_evento_de_outro(self):
        self.entrar(self.bruno)
        resposta = self.client.post(reverse('eventos:excluir', args=[self.semana.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(Evento.objects.filter(pk=self.semana.pk).exists())

    def test_organizador_nao_cria_atividade_em_evento_de_outro(self):
        self.entrar(self.bruno)
        resposta = self.client.post(reverse('eventos:atividade_criar', args=[self.semana.pk]), {
            'titulo': 'Intrusa', 'tipo': 'PALESTRA', 'descricao': 'd', 'responsavel': 'R',
            'sala': self.sala_203.pk, 'data_hora_inicio': '2026-11-13T10:00', 'data_hora_fim': '2026-11-13T11:00',
        })
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Atividade.objects.filter(titulo='Intrusa').exists())

    def test_organizador_nao_edita_atividade_de_evento_de_outro(self):
        self.entrar(self.bruno)
        url = reverse('eventos:atividade_editar', args=[self.oficina.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        resposta = self.client.post(url, {
            'titulo': 'Invadida', 'tipo': 'PALESTRA', 'descricao': 'd', 'responsavel': 'R',
            'sala': self.laboratorio.pk, 'data_hora_inicio': '2026-11-11T10:00', 'data_hora_fim': '2026-11-11T12:00',
        })
        self.assertEqual(resposta.status_code, 403)
        self.oficina.refresh_from_db()
        self.assertEqual(self.oficina.titulo, 'Oficina de Django')

    def test_organizador_nao_exclui_atividade_de_evento_de_outro(self):
        self.entrar(self.bruno)
        resposta = self.client.post(reverse('eventos:atividade_excluir', args=[self.oficina.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(Atividade.objects.filter(pk=self.oficina.pk).exists())

    def test_dono_edita_atividade_do_proprio_evento(self):
        self.entrar(self.ana)
        resposta = self.client.post(reverse('eventos:atividade_editar', args=[self.oficina.pk]), {
            'titulo': 'Oficina de Django REST', 'tipo': 'TREINAMENTO', 'descricao': 'd', 'responsavel': 'R',
            'sala': self.laboratorio.pk, 'data_hora_inicio': '2026-11-11T10:00', 'data_hora_fim': '2026-11-11T12:00',
        })
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))
        self.oficina.refresh_from_db()
        self.assertEqual(self.oficina.titulo, 'Oficina de Django REST')

    def test_participante_que_abre_meus_eventos_recebe_403_e_nao_volta_ao_login(self):
        self.entrar(self.carla)
        self.assertEqual(self.client.get(reverse('eventos:meus_eventos')).status_code, 403)

    def test_organizador_ve_so_os_proprios_eventos_em_meus_eventos(self):
        self.entrar(self.bruno)
        resposta = self.client.get(reverse('eventos:meus_eventos'))
        self.assertQuerySetEqual(resposta.context['eventos'], [self.jornada])

    def test_nem_o_superusuario_edita_evento_de_outro(self):
        self.entrar(self.admin)
        resposta = self.client.post(reverse('eventos:editar', args=[self.semana.pk]), self.dados_evento)
        self.assertEqual(resposta.status_code, 403)
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana de Tecnologia')

    def test_dono_edita_o_proprio_evento(self):
        self.entrar(self.ana)
        resposta = self.client.post(reverse('eventos:editar', args=[self.semana.pk]),
                                    {**self.dados_evento, 'nome': 'Semana 2026'})
        self.assertRedirects(resposta, reverse('eventos:detalhe', args=[self.semana.pk]))
        self.semana.refresh_from_db()
        self.assertEqual(self.semana.nome, 'Semana 2026')

    def test_organizador_criado_pelo_sistema_mesmo_se_o_post_tentar_forjar(self):
        self.entrar(self.ana)
        self.client.post(reverse('eventos:criar'), {**self.dados_evento, 'nome': 'Hackathon',
                                                    'organizador': self.bruno.pk})
        self.assertEqual(Evento.objects.get(nome='Hackathon').organizador, self.ana)


class CancelarInscricaoAlheiaTests(Cenario):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.inscricao_carla = cls.inscrever_no_evento(cls.carla, cls.semana)
        cls.carla_na_oficina = cls.inscrever_na_atividade(cls.inscricao_carla, cls.oficina)

    def setUp(self):
        self.entrar(self.diego)

    def test_ninguem_cancela_inscricao_de_atividade_alheia(self):
        resposta = self.client.post(reverse('eventos:cancelar_inscricao_atividade', args=[self.carla_na_oficina.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(InscricaoAtividade.objects.filter(pk=self.carla_na_oficina.pk).exists())

    def test_ninguem_cancela_inscricao_de_evento_alheia(self):
        resposta = self.client.post(reverse('eventos:cancelar_inscricao_evento', args=[self.inscricao_carla.pk]))
        self.assertEqual(resposta.status_code, 403)
        self.assertTrue(InscricaoEvento.objects.filter(pk=self.inscricao_carla.pk).exists())
        self.assertTrue(InscricaoAtividade.objects.filter(pk=self.carla_na_oficina.pk).exists())


# --- RF10 da entrega anterior: a interface reflete o papel ---

class InterfaceTests(Cenario):
    def programacao(self):
        return self.client.get(reverse('eventos:detalhe', args=[self.semana.pk]))

    def url_inscrever(self, atividade):
        return reverse('eventos:inscrever_atividade', args=[atividade.pk])

    def test_botao_de_atividade_nao_aparece_para_quem_nao_esta_no_evento(self):
        self.entrar(self.carla)
        self.assertNotContains(self.programacao(), self.url_inscrever(self.oficina))

    def test_botao_nao_aparece_em_atividade_lotada(self):
        self.lotar_oficina()
        self.inscrever_no_evento(self.eva, self.semana)
        self.entrar(self.eva)
        resposta = self.programacao()
        self.assertNotContains(resposta, self.url_inscrever(self.oficina))
        self.assertContains(resposta, self.url_inscrever(self.git))

    def test_botao_nao_aparece_em_atividade_que_conflita(self):
        self.inscrever_na_atividade(self.inscrever_no_evento(self.carla, self.semana), self.oficina)
        self.entrar(self.carla)
        resposta = self.programacao()
        self.assertNotContains(resposta, self.url_inscrever(self.abertura))
        self.assertContains(resposta, 'Conflito de horário')

    def test_editar_e_excluir_aparecem_so_para_o_dono(self):
        url_editar = reverse('eventos:editar', args=[self.semana.pk])
        self.entrar(self.ana)
        self.assertContains(self.programacao(), url_editar)
        self.entrar(self.bruno)
        self.assertNotContains(self.programacao(), url_editar)


# --- Agenda e painel ---

class AgendaTests(Cenario):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        semana = cls.inscrever_no_evento(cls.carla, cls.semana)
        # Inscrições criadas fora de ordem, em dois eventos.
        cls.inscrever_na_atividade(cls.inscrever_no_evento(cls.carla, cls.jornada), cls.iniciacao)
        cls.inscrever_na_atividade(semana, cls.git)
        cls.inscrever_na_atividade(semana, cls.oficina)
        cls.inscrever_na_atividade(cls.inscrever_no_evento(cls.diego, cls.semana), cls.abertura)

    def test_agenda_traz_so_as_atividades_de_quem_abriu_em_ordem_cronologica(self):
        self.entrar(self.carla)
        resposta = self.client.get(reverse('eventos:agenda'))
        self.assertTemplateUsed(resposta, 'eventos/agenda.html')
        self.assertEqual([i.atividade for i in resposta.context['inscricoes']],
                         [self.oficina, self.git, self.iniciacao])


class PainelTests(Cenario):
    def setUp(self):
        self.lotar_oficina()
        self.url = reverse('eventos:painel', args=[self.semana.pk])

    def test_organizador_ve_inscritos_total_e_vagas_por_atividade(self):
        self.entrar(self.ana)
        resposta = self.client.get(self.url)
        oficina = next(a for a in resposta.context['atividades'] if a.pk == self.oficina.pk)
        self.assertEqual(oficina.total_inscritos, 2)
        self.assertEqual(oficina.vagas_restantes, 0)
        self.assertContains(resposta, 'carla')
        self.assertContains(resposta, 'diego')

    def test_ninguem_alem_do_dono_ve_o_painel(self):
        for usuario in [self.bruno, self.carla, self.admin]:
            with self.subTest(usuario.username):
                self.entrar(usuario)
                self.assertEqual(self.client.get(self.url).status_code, 403)
