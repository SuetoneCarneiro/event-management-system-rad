from django.contrib import admin

from .models import Atividade, Evento, InscricaoAtividade, InscricaoEvento, Sala


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'bloco', 'capacidade']
    list_filter = ['bloco']
    search_fields = ['nome', 'bloco']


class AtividadeInline(admin.TabularInline):
    """Somente leitura: atividades são criadas pela tela de atividade, com todas as validações."""
    model = Atividade
    fields = ['titulo', 'tipo', 'sala', 'data_hora_inicio', 'data_hora_fim']
    readonly_fields = fields
    extra = 0
    show_change_link = True
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'data_inicio', 'data_fim', 'inscricoes_abertas', 'organizador']
    list_filter = ['inscricoes_abertas', 'data_inicio', 'organizador']
    search_fields = ['nome', 'descricao']
    date_hierarchy = 'data_inicio'
    # O organizador nunca é escolhido em formulário, nem aqui.
    readonly_fields = ['organizador']
    inlines = [AtividadeInline]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.organizador = request.user
        super().save_model(request, obj, form, change)


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = [
        'titulo', 'tipo', 'evento', 'sala', 'data_hora_inicio', 'data_hora_fim',
        'total_inscritos', 'vagas_restantes',
    ]
    list_filter = ['tipo', 'evento', 'sala']
    search_fields = ['titulo', 'responsavel', 'evento__nome']
    date_hierarchy = 'data_hora_inicio'
    list_select_related = ['evento', 'sala']

    def get_queryset(self, request):
        return super().get_queryset(request).com_vagas()

    @admin.display(description='inscritos', ordering='total_inscritos')
    def total_inscritos(self, obj):
        return obj.total_inscritos

    @admin.display(description='vagas restantes', ordering='vagas_restantes')
    def vagas_restantes(self, obj):
        return obj.vagas_restantes


class SomenteConsultaMixin:
    """Inscrições são feitas pelo site; no Admin, só se consulta e exclui."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class InscricaoAtividadeInline(SomenteConsultaMixin, admin.TabularInline):
    model = InscricaoAtividade
    fields = ['atividade', 'data_hora_inscricao']
    readonly_fields = fields
    extra = 0


@admin.register(InscricaoEvento)
class InscricaoEventoAdmin(SomenteConsultaMixin, admin.ModelAdmin):
    list_display = ['participante', 'evento', 'data']
    list_filter = ['evento']
    search_fields = ['participante__username', 'participante__first_name', 'evento__nome']
    list_select_related = ['participante', 'evento']
    inlines = [InscricaoAtividadeInline]


@admin.register(InscricaoAtividade)
class InscricaoAtividadeAdmin(SomenteConsultaMixin, admin.ModelAdmin):
    list_display = ['participante', 'atividade', 'evento', 'data_hora_inscricao']
    list_filter = ['atividade__evento', 'atividade']
    search_fields = ['inscricao_evento__participante__username', 'atividade__titulo']
    list_select_related = ['inscricao_evento__participante', 'inscricao_evento__evento', 'atividade']

    @admin.display(description='participante', ordering='inscricao_evento__participante__username')
    def participante(self, obj):
        return obj.inscricao_evento.participante

    @admin.display(description='evento', ordering='inscricao_evento__evento__nome')
    def evento(self, obj):
        return obj.inscricao_evento.evento
