from django import forms

from .models import Atividade, Evento


class EventoForm(forms.ModelForm):
    # O organizador fica de fora de propósito: quem preenche é a view, com request.user.
    class Meta:
        model = Evento
        fields = ['nome', 'descricao', 'data_inicio', 'data_fim', 'inscricoes_abertas']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'data_fim': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }


class AtividadeForm(forms.ModelForm):
    # O evento também fica de fora: vem da URL e é definido pela view.
    class Meta:
        model = Atividade
        fields = ['titulo', 'tipo', 'descricao', 'responsavel', 'sala', 'data_hora_inicio', 'data_hora_fim']
        widgets = {
            'data_hora_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'data_hora_fim': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }
        help_texts = {
            'responsavel': 'Nome de quem vai ministrar.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sala'].label_from_instance = (
            lambda sala: f'{sala.nome} — Bloco {sala.bloco} ({sala.capacidade} lugares)'
        )
        evento = self.instance.evento
        periodo = f'{evento.data_inicio:%d/%m/%Y} a {evento.data_fim:%d/%m/%Y}'
        self.fields['data_hora_inicio'].help_text = f'Dentro do período do evento: {periodo}.'
