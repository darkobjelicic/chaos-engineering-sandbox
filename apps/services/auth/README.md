# Auth Service

FastAPI-based authentication service used for the BookStore project.

Endpoints:
- `POST /register` – register with `{"email":..., "password":...}`
- `POST /login` – form-urlencoded `username` and `password` -> OAuth2 token
- `GET /me` – returns current user (requires Bearer token)

Environment variables:
- `DATABASE_URL` - Postgres connection string
- `SECRET_KEY` - JWT secret

Run locally:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
