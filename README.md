## SaaS Multi-Tenant Communication System

Aplicação Django multi-tenant para comunicação interna entre equipes, com:
- **Chat** organizado por usuários e perfis.
- **Chamados/ocorrências** com acompanhamento de status.
- **Agendamento de reuniões** com envio de convites por e-mail.

Este repositório é uma versão limpa, pronta para servir como **portfólio**, sem dados reais nem credenciais sensíveis.

### Tecnologias principais
- **Python** 3.10+
- **Django** 5
- **PostgreSQL**
- **Docker** e **Docker Compose** (opcional, recomendado)

### Estrutura de pastas (resumo)
- `config`: configuração do projeto Django.
- `core`: páginas e utilitários base.
- `usuarios`: gestão de usuários e perfis.
- `chat`: conversas e reuniões.
- `chamados`: registro e acompanhamento de chamados.

### Como rodar com Docker (recomendado)

1. Crie um arquivo `.env` a partir do modelo:
   ```bash
   cp .env.example .env
   ```
2. Ajuste as variáveis no `.env` (por exemplo, `DJANGO_SECRET_KEY`, credenciais de banco e e-mail).
3. Suba os serviços:
   ```bash
   docker compose up --build
   ```
4. Acesse a aplicação em `http://localhost:8000`.

### Como rodar localmente (sem Docker)

1. Crie e ative um ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Defina as variáveis de ambiente (por exemplo via `.env` + `export`/`direnv`) seguindo o `.env.example`.
3. Execute as migrações e o servidor de desenvolvimento:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

### Configuração de ambiente

As principais configurações sensíveis (chave secreta, banco de dados, e-mail e base das URLs de reunião) são lidas de variáveis de ambiente em `config/settings.py`.  
Use o arquivo `.env.example` como referência para preparar o seu `.env` em desenvolvimento.

### Arquitetura multi-tenant (django-tenants)

- **Modelo de tenant**: `tenant_management.Client` herda de `TenantMixin` e representa cada cliente/empresa, com `schema_name` próprio no PostgreSQL.
- **Modelo de domínio**: `tenant_management.Domain` herda de `DomainMixin` e mapeia domínios (ex.: `cliente1.app.example-saas.com`) para o tenant correto.
- **Separação de apps**:
  - `SHARED_APPS`: `django_tenants`, apps core do Django e `tenant_management` (administra tenants, assinaturas, webhooks, campanhas).
  - `TENANT_APPS`: `core`, `usuarios`, `chat`, `chamados` — executados isoladamente por schema.
- **Resolução de tenant por request**: o `TenantMainMiddleware` (de `django_tenants`) inspeciona o host e escolhe o schema correto, permitindo que a mesma instância sirva múltiplos clientes.

### Objetivo como portfólio

Este projeto demonstra:
- Organização de um projeto Django multi-app.
- Uso de PostgreSQL e boas práticas básicas de configuração por ambiente.
- Integração de fluxo de chat, chamados e reuniões em um único sistema SaaS multi-tenant.

---

## (Histórico) Comunicação Interna - Chat & Chamados

> Esta seção registra o contexto original interno do projeto.  
> Para o portfólio, foque na seção “SaaS Multi-Tenant Communication System” acima.

## Comunicação Interna - Chat & Chamados

Projeto Django para comunicação interna entre portaria e setores administrativos, com chat em tempo real e registro de ocorrências.

### Tecnologias principais
- Python 3.10
- Django 5
- PostgreSQL

### Estrutura inicial de apps
- `core`: configurações e utilitários comuns.
- `usuarios`: gestão de usuários e perfis (portaria, gerente, TI, compras, etc.).
- `chat`: conversas em tempo real entre portaria e setores.
- `chamados`: registro e acompanhamento de ocorrências.

### Ambiente virtual

```bash
cd /var/www/chat_comunicacao
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuração de banco de dados (PostgreSQL)

Banco já configurado em `config/settings.py` para:
- **BD**: `comunicacao`
- **Usuário**: `kuttner`

Atualize a senha do banco em `config/settings.py` antes de subir para produção.

