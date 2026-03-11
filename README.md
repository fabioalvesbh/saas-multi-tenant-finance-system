## SaaS Multi-Tenant Communication System

Clean Django-based multi-tenant application for internal team communication, featuring:
- **Chat** organized by users and profiles.
- **Tickets/incidents** with full lifecycle tracking.
- **Meeting scheduling** with email invitations.

This repository is a sanitized version, designed to serve as a **portfolio project**, with no real data or sensitive credentials.

### Main technologies
- **Python** 3.10+
- **Django** 5
- **PostgreSQL**
- **Docker** and **Docker Compose** (recommended)

### Folder structure (overview)
- `config`: Django project configuration (settings, URLs, tenants, API).
- `core`: base pages and utilities.
- `usuarios`: user and profile management.
- `chat`: conversations and meetings.
- `chamados`: ticket/incident registration and tracking.
- `tenant_management`: tenant lifecycle, subscriptions, webhooks and analytics.

### Running with Docker (recommended)

1. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
2. Adjust environment variables (`DJANGO_SECRET_KEY`, DB and email credentials, etc.).
3. Start the services:
   ```bash
   docker compose up --build
   ```
4. Access the app at `http://localhost:8000`.

5. To explore the **API** and documentation:
   - Swagger UI: `http://localhost:8000/api/schema/swagger/`
   - Schema OpenAPI (JSON): `http://localhost:8000/api/schema/`

### Running locally (without Docker)

1. Create and activate a virtualenv:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Configure environment variables (for example using `.env` + `export`/`direnv`) following `.env.example`.
3. Run migrations and start the dev server:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
4. (Optional, recommended for quick testing) Create a demo user:
   ```bash
   python manage.py create_demo_user
   ```
   This creates/updates the user:
   - **username**: `username`
   - **password**: `username`

### Environment configuration

All sensitive configuration (secret key, database, email and meeting URLs) is read from environment variables in `config/settings.py`.  
Use `.env.example` as a reference to prepare your local `.env`.

### Multi-tenant architecture (django-tenants)

- **Tenant model**: `tenant_management.Client` extends `TenantMixin` and represents each customer/company, with its own `schema_name` in PostgreSQL.
- **Domain model**: `tenant_management.Domain` extends `DomainMixin` and maps domains (e.g. `client1.app.example-saas.com`) to the right tenant.
- **App separation**:
  - `SHARED_APPS`: `django_tenants`, Django core apps and `tenant_management` (tenant admin, subscriptions, webhooks, campaigns).
  - `TENANT_APPS`: `core`, `usuarios`, `chat`, `chamados` — executed in isolation per schema.
- **Request-based tenant resolution**: `TenantMainMiddleware` (from `django_tenants`) inspects the host and chooses the correct schema, allowing a single instance to serve multiple clients.

### Company (tenant) creation flow

- Automatic tenant creation endpoint:
  - `POST /api/tenants/`
  - Example payload:
    ```json
    {
      "name": "Demo Company",
      "schema_name": "demo_company",
      "domain": "demo-company.localhost",
      "email": "contact@company.com",
      "plano": "trial"
    }
    ```
  - The backend creates the `Client` record, links a `Domain`, and `django-tenants` creates the schema in PostgreSQL.  
- JWT authentication:
  - Obtain token: `POST /api/token/` with `username`/`password`.
  - Refresh token: `POST /api/token/refresh/`.
  - DRF views use `JWTAuthentication` with default permissions configured in `REST_FRAMEWORK`.

### Portfolio focus

This project demonstrates:
- Organization of a multi-app Django project.
- Use of PostgreSQL and environment-driven configuration.
- Integration of chat, tickets and meetings into a single SaaS multi-tenant system.

From a **mid-level engineer** perspective, the code emphasizes:
- **Scalability**: schema-based isolation, multi-tenant routing and an API that automates tenant onboarding.
- **Data isolation**: explicit use of `Client`/`Domain` and `django-tenants` to separate data per tenant at the database level.
- **Versioning & automation**: pinned dependencies in `requirements.txt`, Docker setup and automatic tenant creation endpoint.
- **Documentation**: detailed `README` plus OpenAPI/Swagger docs at `/api/schema/swagger/`.

---

## (Historical) Internal Communication – Chat & Tickets

> This section preserves the original internal context of the project.  
> For portfolio purposes, focus on the “SaaS Multi-Tenant Communication System” section above.

The initial version of this project started as an internal communication tool between gatehouse and office sectors, with:
- Real-time chat.
- Ticket/incident logging and tracking.

The multi-tenant SaaS architecture evolved from this base to support multiple companies on the same platform.

