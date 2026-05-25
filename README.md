# URL Shortner

A FastAPI-based URL shortening service with PostgreSQL persistence, Redis caching, and click analytics.

## Overview

This repository provides a URL shortener API that:
- creates deterministic short codes for URLs using MD5 + Base62 encoding
- stores original URLs in PostgreSQL
- redirects short codes to their target URLs
- records click events for analytics
- caches URL redirects and applies simple rate limiting using Redis
- includes Alembic migrations for schema management

## Key Components

- `app/main.py` - FastAPI application entrypoint
- `app/routers/shorten.py` - POST `/shorten` for creating short URLs
- `app/routers/redirect.py` - GET `/{short_code}` for redirecting and logging clicks
- `app/routers/stats.py` - GET `/stats/{short_code}` for click analytics
- `app/models/url.py` - `URL` database model
- `app/models/click.py` - `Click` database model
- `app/db.py` - SQLAlchemy database engine and session setup
- `app/redis.py` - Redis client setup
- `app/utils.py` - encoding, rate limiting, and click logging helpers

## Requirements

- Python 3.11+
- PostgreSQL (containerized by Docker Compose in this repo)
- Redis (containerized by Docker Compose in this repo)
- `pip` for Python dependency installation

## Installation

1. Create and activate your virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

> Note: This project uses `pyproject.toml`. If `requirements.txt` is not present, install dependencies with `pip install -e .`.

## Running with Docker Compose

This repository includes `docker-compose.yml` for a complete local stack.

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Environment Variables

The repository includes a `.env` file with these values:

- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_DB` - PostgreSQL database name
- `POSTGRES_HOST` - PostgreSQL hostname
- `POSTGRES_PORT` - PostgreSQL port
- `DISABLE_RATE_LIMITING` - set to `true` to disable rate limiting

Redis configuration is read from `REDIS_URL` in `app/redis.py`, defaulting to `redis://redis:6379/0`.

## Database Migrations

Alembic is used to manage database migrations.

To create or apply migrations:

```bash
alembic upgrade head
```

If you need to generate a new migration after changing models:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## API Endpoints

### Health

- `GET /health`
- Returns service health status:

```json
{ "status": "ok" }
```

### Shorten URL

- `POST /shorten`
- Query parameter: `long_url`
- Example:

```bash
curl -X POST "http://localhost:8000/shorten?long_url=https://example.com"
```

Response:

```json
{ "short_code": "abc12345" }
```

### Redirect

- `GET /{short_code}`
- Example:

```bash
curl -L "http://localhost:8000/abc12345"
```

This endpoint redirects to the original URL.

### Stats

- `GET /stats/{short_code}`
- Example:

```bash
curl "http://localhost:8000/stats/abc12345"
```

Response example:

```json
{
  "short_code": "abc12345",
  "original_url": "https://example.com",
  "created_at": "2026-05-25T12:34:56",
  "total_clicks": 42,
  "clicks_last_7_days": [
    { "date": "2026-05-18", "clicks": 10 },
    { "date": "2026-05-19", "clicks": 7 }
  ]
}
```

## Rate Limiting

Rate limiting is implemented in `app/utils.py` using Redis.

- `POST /shorten` is limited to 10 requests per minute per IP
- `GET /{short_code}` is limited to 100 requests per minute per IP

If Redis is unavailable, requests fall back to allowing traffic rather than failing.

## Caching

`app/routers/redirect.py` caches redirect targets in Redis:

- `/url:{short_code}` stores the original URL
- `/hits:{short_code}` tracks redirect request hits

Cache TTL adjusts dynamically based on request volume.

## Notes

- `app/db.py` currently uses a hardcoded PostgreSQL connection string for `db` service access.
- `app/main.py` includes routers for shortening, redirecting, and stats.
- `tests/` is present but currently empty.

## Local Development

To run locally without Docker:

1. Start a PostgreSQL instance and Redis instance.
2. Update `REDIS_URL` and database settings if needed.
3. Launch the app:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Troubleshooting

- Ensure PostgreSQL and Redis are running.
- Confirm the Docker Compose service names match `db` and `redis`.
- If rate limiting blocks your tests, set `DISABLE_RATE_LIMITING=true`.

## Project Structure

- `app/` - application package
  - `models/` - SQLAlchemy ORM models
  - `routers/` - API route definitions
  - `db.py` - database session and engine setup
  - `redis.py` - Redis connection setup
  - `utils.py` - encoding, rate limiting, and click logging helpers
- `alembic/` - migration configuration and version history
- `Dockerfile` - container image build instructions
- `docker-compose.yml` - local compose stack for API, PostgreSQL, and Redis

---

Feel free to update this README with examples from your own deployment or add a `requirements.txt` if needed.