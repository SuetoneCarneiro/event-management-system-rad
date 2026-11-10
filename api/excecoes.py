from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.views import exception_handler


def tratar_excecao(exc, context):
    """As regras de negócio levantam o ValidationError do Django (models e eventos/servicos.py).

    O DRF só conhece o próprio ValidationError; sem esta conversão, uma regra violada viraria 500.
    Aqui ela vira 400 com as mensagens em JSON, no mesmo formato dos erros de serializer.
    """
    if isinstance(exc, DjangoValidationError):
        exc = serializers.ValidationError(serializers.as_serializer_error(exc))
    return exception_handler(exc, context)
