"""Formulários instanciados diretamente, sem view nem requisição (RF9)."""
from datetime import date

from django.contrib.auth.models import User

from contas.forms import CadastroForm
from eventos.forms import AtividadeForm, EventoForm
from eventos.models import Atividade

from .base import Cenario, dt


class AtividadeFormTests(Cenario):
    def formulario(self, **campos):
        dados = {
            'titulo': 'Oficina de testes', 'tipo': 'TREINAMENTO', 'descricao': 'Testes no Django.',
            'responsavel': 'Prof. Marcos', 'sala': self.sala_203.pk,
            'data_hora_inicio': '2026-11-13T14:00', 'data_hora_fim': '2026-11-13T16:00',
        }
        dados.update(campos)
        # O evento não vem dos dados: a view o coloca na instância, e aqui fazemos o mesmo.
        return AtividadeForm(data=dados, instance=Atividade(evento=self.semana))

    def test_dados_validos_sao_convertidos_em_cleaned_data(self):
        form = self.formulario()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.errors, {})
        self.assertEqual(form.cleaned_data['titulo'], 'Oficina de testes')
        self.assertEqual(form.cleaned_data['tipo'], Atividade.Tipo.TREINAMENTO)
        self.assertEqual(form.cleaned_data['sala'], self.sala_203)  # o id virou o objeto Sala
        self.assertEqual(form.cleaned_data['data_hora_inicio'], dt(13, 11, 14))  # texto virou datetime no fuso local

    def test_evento_nao_e_campo_do_formulario(self):
        self.assertNotIn('evento', self.formulario().fields)

    def test_sala_ocupada_gera_erro_no_campo_sala(self):
        form = self.formulario(sala=self.laboratorio.pk, data_hora_inicio='2026-11-11T11:00',
                               data_hora_fim='2026-11-11T13:00')
        self.assertFalse(form.is_valid())
        self.assertIn('Sala ocupada', form.errors['sala'][0])
        self.assertNotIn('sala', form.cleaned_data)

    def test_fim_antes_do_inicio_gera_erro_geral(self):
        form = self.formulario(data_hora_inicio='2026-11-13T16:00', data_hora_fim='2026-11-13T14:00')
        self.assertFalse(form.is_valid())
        self.assertIn('A data e hora de fim não podem ser anteriores à data e hora de início.',
                      form.non_field_errors())

    def test_campo_obrigatorio_vazio_gera_erro_no_campo(self):
        form = self.formulario(titulo='')
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['titulo'], ['Este campo é obrigatório.'])

    def test_ajuda_mostra_o_periodo_do_evento(self):
        self.assertIn('10/11/2026 a 14/11/2026', self.formulario().fields['data_hora_inicio'].help_text)


class EventoFormTests(Cenario):
    def test_organizador_nao_e_campo_do_formulario(self):
        self.assertNotIn('organizador', EventoForm().fields)

    def test_dados_validos(self):
        form = EventoForm(data={'nome': 'Hackathon', 'descricao': 'd', 'data_inicio': '2026-11-20',
                                'data_fim': '2026-11-21', 'inscricoes_abertas': 'on'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['data_inicio'], date(2026, 11, 20))
        self.assertIs(form.cleaned_data['inscricoes_abertas'], True)

    def test_checkbox_desmarcado_vira_false(self):
        form = EventoForm(data={'nome': 'Hackathon', 'descricao': 'd', 'data_inicio': '2026-11-20',
                                'data_fim': '2026-11-21'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIs(form.cleaned_data['inscricoes_abertas'], False)

    def test_fim_antes_do_inicio_e_recusado(self):
        form = EventoForm(data={'nome': 'Hackathon', 'descricao': 'd', 'data_inicio': '2026-11-21',
                                'data_fim': '2026-11-20'})
        self.assertFalse(form.is_valid())
        self.assertIn('A data de fim não pode ser anterior à data de início.', form.non_field_errors())


class CadastroFormTests(Cenario):
    dados = {'username': 'novato', 'first_name': 'Novo', 'last_name': 'Aluno', 'email': 'novo@ifpb.edu.br',
             'password1': 'SenhaForte!2026', 'password2': 'SenhaForte!2026'}

    def test_dados_validos_criam_usuario_com_senha_em_hash(self):
        form = CadastroForm(data=self.dados)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['username'], 'novato')
        usuario = form.save()
        self.assertNotEqual(usuario.password, 'SenhaForte!2026')  # nunca a senha em texto puro
        self.assertTrue(usuario.check_password('SenhaForte!2026'))

    def test_senhas_diferentes_sao_recusadas(self):
        form = CadastroForm(data={**self.dados, 'password2': 'OutraSenha!2026'})
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_usuario_ja_existente_e_recusado(self):
        form = CadastroForm(data={**self.dados, 'username': 'carla'})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertEqual(User.objects.filter(username='carla').count(), 1)
