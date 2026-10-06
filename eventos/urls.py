from django.urls import path
from django.views.generic import TemplateView

app_name = 'eventos'

urlpatterns = [
    # TODO (Suetone): substituir pela view da lista de eventos (fase 4).
    path('', TemplateView.as_view(template_name='base.html'), name='lista'),
]
