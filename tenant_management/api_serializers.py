from django_tenants.utils import get_public_schema_name
from rest_framework import serializers

from .models import Client, Domain


class TenantCreateSerializer(serializers.Serializer):
    """
    Payload minimalista para criação automática de tenant.
    Pensado para fins de demo/portfólio.
    """

    name = serializers.CharField(max_length=100)
    schema_name = serializers.SlugField(max_length=63)
    domain = serializers.CharField(max_length=255)
    email = serializers.EmailField(required=False, allow_blank=True)
    plano = serializers.ChoiceField(choices=Client.PLANO_CHOICES, default="trial")

    def validate_schema_name(self, value: str) -> str:
        public_schema = get_public_schema_name()
        if value == public_schema:
            raise serializers.ValidationError("schema_name reservado para schema público.")
        return value

    def create(self, validated_data):
        domain_name = validated_data.pop("domain")
        email = validated_data.pop("email", "")

        client = Client.objects.create(
            email=email or None,
            **validated_data,
        )

        Domain.objects.create(
            tenant=client,
            domain=domain_name,
            is_primary=True,
        )

        return client

