from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler


def como_erro_da_api(erro):
    """Converte o ValidationError do Django no do DRF, com as chaves que a API sempre usa.

    Erros sem campo vêm do Django como "__all__" (clean do model) ou como lista (serviços);
    os dois viram "non_field_errors", como nos erros do próprio DRF.
    """
    detalhe = serializers.as_serializer_error(erro)
    if NON_FIELD_ERRORS in detalhe:
        detalhe[api_settings.NON_FIELD_ERRORS_KEY] = detalhe.pop(NON_FIELD_ERRORS)
    return serializers.ValidationError(detalhe)


def tratar_excecao(exc, context):
    """As regras de negócio levantam o ValidationError do Django (models e eventos/servicos.py).

    O DRF só conhece o próprio ValidationError; sem esta conversão, uma regra violada viraria 500.
    Aqui ela vira 400 com as mensagens em JSON, no mesmo formato dos erros de serializer.
    """
    if isinstance(exc, DjangoValidationError):
        exc = como_erro_da_api(exc)
    return exception_handler(exc, context)
