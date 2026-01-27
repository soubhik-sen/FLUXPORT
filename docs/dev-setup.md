# Developer Setup

## Prerequisites

- Python 3.11+
- PostgreSQL (local or remote)

## Install dependencies

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## Configure database

`DATABASE_URL` is read from the environment in `app/core/config.py`.
Set it to a Postgres DSN, for example:

```bash
set DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

You can validate the resolved URL with:

```bash
python check_env.py
```

## Run the API

```bash
python -m uvicorn app.main:app --port 8000 --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Migrations

Alembic config lives in `alembic.ini`.

Common commands:

```bash
alembic upgrade head
alembic revision --autogenerate -m "your message"
```

## API contracts

- `openapi.json` contains the exported OpenAPI schema
- `collection.json` contains a Postman collection
