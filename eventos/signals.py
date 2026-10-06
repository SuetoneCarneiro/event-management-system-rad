from django.contrib.auth.models import Group, Permission

GRUPO_ORGANIZADORES = 'Organizadores'

PERMISSOES_ORGANIZADOR = [
    'add_evento', 'change_evento', 'delete_evento', 'view_evento',
    'add_atividade', 'change_atividade', 'delete_atividade', 'view_atividade',
]


def criar_grupo_organizadores(sender, **kwargs):
    """Garante, após cada migrate, que o grupo Organizadores exista com suas permissões.

    Roda no post_migrate porque as permissões dos models só são criadas nesse momento.
    """
    grupo, _ = Group.objects.get_or_create(name=GRUPO_ORGANIZADORES)
    permissoes = Permission.objects.filter(
        content_type__app_label='eventos',
        codename__in=PERMISSOES_ORGANIZADOR,
    )
    grupo.permissions.add(*permissoes)
