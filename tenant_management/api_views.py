from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .api_serializers import TenantCreateSerializer


class TenantAutoCreateView(APIView):
    """
    Endpoint de criação automática de tenant.

    POST /api/tenants/

    Exemplo de payload:
    {
      "name": "Empresa Demo",
      "schema_name": "empresa_demo",
      "domain": "empresa-demo.localhost",
      "email": "contato@empresa.com",
      "plano": "trial"
    }
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = TenantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()

        return Response(
            {
                "id": client.id,
                "name": client.name,
                "schema_name": client.schema_name,
            },
            status=status.HTTP_201_CREATED,
        )

