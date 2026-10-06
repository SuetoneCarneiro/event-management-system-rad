from django.contrib import messages
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CadastroForm


class CadastroView(CreateView):
    """Cadastro público. A conta nasce sem grupo: um participante comum."""
    form_class = CadastroForm
    template_name = 'registration/cadastro.html'
    success_url = reverse_lazy('eventos:lista')

    def form_valid(self, form):
        resposta = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, 'Conta criada. Bem-vindo(a)!')
        return resposta
