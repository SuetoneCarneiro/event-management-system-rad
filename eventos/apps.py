from django.apps import AppConfig
from django.db.models.signals import post_migrate


class EventosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eventos'
    verbose_name = 'Eventos'

    def ready(self):
        from .signals import criar_grupo_organizadores

        post_migrate.connect(criar_grupo_organizadores, sender=self)
