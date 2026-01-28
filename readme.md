# Portfolio API

FastAPI backend for the portfolio site. Provides user auth, portfolio CRUD, uploads, rate limiting, and background jobs. Supports MongoDB and Redis, with Google OAuth for admin sign-in.

## Features

- FastAPI REST API with versioned routes
- MongoDB persistence via Motor / PyMongo
- JWT auth + refresh tokens
- Role-based rate limits (anonymous / member / admin)
- Portfolio CRUD endpoints
- Resume upload support (Cloudflare R2)
- Google OAuth login for admin access
- Background jobs with Celery + APScheduler

## Project Structure

```
api/
  v1/
    portfolio.py
    user_route.py
core/
  database.py
repositories/
services/
security/
schemas/
email_templates/
main.py
seed.py
```

## Requirements

- Python 3.10+
- MongoDB
- Redis

## Environment

Create a `.env` in the project root. Example:

```
DB_NAME=Portfolio
DB_TYPE=mongodb
MONGO_URL=mongodb://localhost:27017/

GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET
ALLOWED_GOOGLE_EMAILS=you@example.com,admin@example.com

REDIS_HOST=127.0.0.1
REDIS_PORT=6379

CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1

R2_ACCESS_KEY_ID=YOUR_R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY=YOUR_R2_SECRET_ACCESS_KEY
R2_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
R2_BUCKET=your-bucket
PUBLIC_BASE_URL=https://<public-bucket-url>

SUCCESS_PAGE_URL=http://localhost:3000/admin/success
ERROR_PAGE_URL=http://localhost:3000/admin/error
```

## Setup

Install dependencies:

```
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
```

Run the API:

```
uvicorn main:app --reload
```

## Authentication

- Google OAuth redirects to `/v1/users/google/auth`
- Callback: `/v1/users/auth/callback`
- Tokens issued on successful login
- Auth header: `Authorization: Bearer <access_token>`

## Rate Limiting

Defined in `main.py`:

- anonymous: 20/minute
- member: 60/minute
- admin: 140/minute

## API Routes (v1)

### Users

- `GET /v1/users/me`
- `POST /v1/users/refresh`
- `GET /v1/users/google/auth`
- `GET /v1/users/auth/callback`

### Portfolios

- `GET /v1/portfolios/{user_id}`
- `POST /v1/portfolios`
- `PATCH /v1/portfolios`
- `DELETE /v1/portfolios`
- `POST /v1/portfolios/upload-resume`

## Seeding

Seed a portfolio for a specific user ID:

```
python seed.py 697a3a30fa806c842c24d553
```

Or:

```
SEED_USER_ID=697a3a30fa806c842c24d553 python seed.py
```

## Notes

- MongoDB is the default DB. If you switch to SQLite, update `DB_TYPE` in `.env` and ensure schemas match.
- R2 upload requires valid credentials and bucket settings.

## License

MIT
