# HoodooMart

## Scope and boundaries
- Read `docs/PROGRESS.md` and `docs/IMPLEMENTATION_PLAN.md` before extending a milestone.
- API routers depend on application services, never SQL repositories. Composition lives in `app/core/dependencies.py`.
- Application services depend on domain ports. Domain cannot import FastAPI, SQLAlchemy or infrastructure.
- PostgreSQL schema changes use Alembic. Never use runtime `create_all()` or silently reset user data.
- Preserve unrelated files and dirty changes. Do not download model weights without explicit consent.
- UI and public errors use natural Vietnamese. Money is integer VND, never float.
- Only published, verified products with approved/demo provenance and images enter public catalog results.
- Fixtures are original simulated data, not fetched Tiki records. Never invent reviews, sales, performance or AI capability.
- Keep `LOCAL_ONLY=true`; no paid APIs. External datasets stay quarantined until rights review.
- Media and order endpoints must pass upload/ownership negative tests before being exposed.

## Commands (repository root, PowerShell)
```powershell
.\scripts\setup.ps1
docker compose -f infra/docker-compose.yml up -d --build --wait
docker compose -f infra/docker-compose.yml exec api alembic upgrade head
docker compose -f infra/docker-compose.yml exec api python -m app.infrastructure.seed
.\.venv\Scripts\python.exe -m ruff check apps/api scripts
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q
```

Tests must use `TEST_DATABASE_URL` pointing at the separate `hoodoomart_test` database. See RUNBOOK for migration rollback and seed checks. Report commands actually run, failures and evidence. M2-M7 gates are not satisfied by M1.
