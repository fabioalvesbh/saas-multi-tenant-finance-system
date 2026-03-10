# -*- coding: utf-8 -*-
"""
Comando: Opção C – limpar TUDO (HD Virtual + usuários + tenants).

ATENÇÃO: Operação DESTRUTIVA e IRREVERSÍVEL.
- Remove todos os tenants (schemas no PostgreSQL)
- Remove todos os usuários (CustomUser)
- Remove todos os domínios e registros de Client
- Remove pedidos de assinatura (SubscriptionRequest)
- Apaga todo o conteúdo de media/HDvirtual/

Faça backup do banco e da pasta media/ antes de executar.
Uso:
  python manage.py limpar_tudo_opcao_c --dry-run           # só lista o que seria removido
  python manage.py limpar_tudo_opcao_c --confirm-destroy   # executa (faça backup antes)
"""
import os
import shutil
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import ProgrammingError, IntegrityError
from django.contrib.auth import get_user_model
from tenant_management.models import Client, SubscriptionRequest


class Command(BaseCommand):
    help = (
        "Opção C: Remove todos os tenants, usuários, domínios e conteúdo do HD Virtual. "
        "Requer --confirm-destroy (faça backup antes)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm-destroy",
            action="store_true",
            help="Confirma que deseja apagar tudo (obrigatório para executar).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas lista o que seria removido, sem alterar nada.",
        )

    def handle(self, *args, **options):
        if not options["confirm_destroy"] and not options["dry_run"]:
            self.stdout.write(
                self.style.ERROR(
                    "Use --confirm-destroy para confirmar a exclusão total, "
                    "ou --dry-run para apenas listar o que seria removido."
                )
            )
            return

        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Modo DRY-RUN: nenhuma alteração será feita.\n"))

        # Garantir schema public para operações de modelo
        connection.set_schema("public")

        clients = list(Client.objects.exclude(schema_name="public").order_by("schema_name"))
        User = get_user_model()
        user_count = User.objects.count()
        sub_count = SubscriptionRequest.objects.count()

        self.stdout.write(
            f"Seriam afetados: {len(clients)} tenant(s), "
            f"{user_count} usuário(s), {sub_count} pedido(s) de assinatura."
        )

        if dry_run:
            for c in clients:
                self.stdout.write(f"  - Schema: {c.schema_name} (Client: {c.name})")
            self.stdout.write(
                self.style.WARNING(
                    "\nPasta a limpar: media/HDvirtual/ (todo o conteúdo)."
                )
            )
            return

        if not options["confirm_destroy"]:
            return

        # 1) Dropar cada schema de tenant
        with connection.cursor() as cursor:
            for client in clients:
                schema = client.schema_name
                self.stdout.write(f"Removendo schema: {schema} ...")
                cursor.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        self.stdout.write(self.style.SUCCESS("Schemas removidos."))

        # 2) Pedidos de assinatura (public)
        SubscriptionRequest.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Pedidos de assinatura removidos."))

        # 3) Todos os usuários (public)
        try:
            User.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Usuários removidos."))
        except (ProgrammingError, IntegrityError) as e:
            # Possível falha por causa de relações ManyToMany (apps de tenant ou
            # tabelas de junção locais). Forçamos a remoção via SQL direto na
            # ordem correta, usando TRUNCATE ... CASCADE para respeitar FKs.
            self.stdout.write(
                self.style.WARNING(
                    f"Falha ao remover usuários via ORM ({e}); tentando via SQL direto."
                )
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    "TRUNCATE TABLE users_customuser RESTART IDENTITY CASCADE"
                )
            self.stdout.write(self.style.SUCCESS("Usuários removidos via TRUNCATE CASCADE."))

        # 4) Clients (cascade: Domain, TenantDeleteRequest, EmailDepoimentoEnviado, ChatThread, etc.)
        try:
            Client.objects.exclude(schema_name="public").delete()
            self.stdout.write(self.style.SUCCESS("Tenants (Client) e domínios removidos."))
        except (ProgrammingError, IntegrityError) as e:
            # Em alguns cenários, o ORM tenta acessar tabelas de apps de tenant
            # (ex.: tabelas ManyToMany em schemas já removidos), gerando erro
            # de tabela inexistente, ou pode haver problemas de integridade.
            # Como já derrubamos os schemas e removemos os usuários, podemos
            # forçar a remoção via SQL direto no schema public.
            self.stdout.write(
                self.style.WARNING(
                    f"Falha ao remover tenants via ORM ({e}); tentando via SQL direto."
                )
            )
            with connection.cursor() as cursor:
                # Remove dependências explícitas antes, depois os Clients.
                cursor.execute(
                    """
                    DELETE FROM tenant_management_domain
                    WHERE tenant_id IN (
                        SELECT id FROM tenant_management_client
                        WHERE schema_name <> %s
                    )
                    """,
                    ["public"],
                )
                cursor.execute(
                    """
                    DELETE FROM tenant_management_tenantdeleterequest
                    WHERE tenant_id IN (
                        SELECT id FROM tenant_management_client
                        WHERE schema_name <> %s
                    )
                    """,
                    ["public"],
                )
                cursor.execute(
                    """
                    DELETE FROM tenant_management_client
                    WHERE schema_name <> %s
                    """,
                    ["public"],
                )
            self.stdout.write(
                self.style.SUCCESS("Tenants (Client) e domínios removidos via SQL.")
            )

        # 5) Limpar pasta HD Virtual
        from django.conf import settings
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if not media_root:
            self.stdout.write(self.style.WARNING("MEDIA_ROOT não definido; pulando limpeza de HD."))
        else:
            hd_path = os.path.join(media_root, "HDvirtual")
            if os.path.isdir(hd_path):
                for name in os.listdir(hd_path):
                    path = os.path.join(hd_path, name)
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                        self.stdout.write(f"  Removida pasta: {path}")
                    else:
                        try:
                            os.remove(path)
                        except OSError:
                            pass
                self.stdout.write(self.style.SUCCESS("Conteúdo de HD Virtual removido."))
            else:
                self.stdout.write("Pasta HDvirtual não existia; nada a limpar.")

        self.stdout.write(self.style.SUCCESS("\nOpção C concluída: tudo removido."))
