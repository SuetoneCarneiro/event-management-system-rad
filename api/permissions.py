from rest_framework.permissions import SAFE_METHODS, BasePermission

from eventos.models import Evento


class EhOrganizadorDoEventoOuSomenteLeitura(BasePermission):
    """Leitura para todos; alterar ou excluir só para quem organiza o evento (posse, não permissão).

    Não consulta is_superuser: o administrador também é barrado em eventos alheios.
    """
    message = 'Somente o organizador do evento pode alterá-lo.'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        evento = obj if isinstance(obj, Evento) else obj.evento
        return evento.organizado_por(request.user)
