# calTrack server

FastAPI + SQLite backend — the single source of truth `/web` and `/mobile` both talk to.

## Dev setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
DATABASE_URL="sqlite:///./caltrack_dev.db" .venv/bin/alembic upgrade head
DATABASE_URL="sqlite:///./caltrack_dev.db" JWT_SECRET=dev-secret .venv/bin/uvicorn app.main:app --reload
```

`requirements-dev.txt` adds `pytest` on top of `requirements.txt` (the production image only installs the latter, to keep it lean).

## Tests

```bash
.venv/bin/pytest tests/
```

Coverage focuses on `sync_engine.py` (the conflict-detection algorithm — see `docs/sync-protocol.md`) and `nutrition_calc.py` (target/RDA-gap math), per the project's own risk assessment: these are the pieces most likely to have a subtle bug with real consequences. `food_lookup.py`'s pure parsing/unit-conversion helpers are covered too; the actual Open Food Facts/USDA HTTP calls are verified manually against the real APIs rather than mocked.

## Migrations

```bash
DATABASE_URL="sqlite:///./caltrack_dev.db" .venv/bin/alembic revision --autogenerate -m "description"
DATABASE_URL="sqlite:///./caltrack_dev.db" .venv/bin/alembic upgrade head
```

## Adding an LLM provider

Implement the `LLMProvider` interface in `app/llm/` and register it in `app/llm/factory.py`. See `app/llm/base.py` for the exact contract, and `app/llm/cohere.py` for a complete reference implementation.
