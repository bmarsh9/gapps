Title: Add Swagger UI and dynamic OpenAPI generation + fix token validation

Summary

Add interactive API docs (Swagger UI) at /api/docs, dynamically generate OpenAPI JSON at /api/v1/swagger.json from Flask routes, and fix token validation to use the User model's confirmation field.

What changed

- Register Swagger UI blueprint and point it to /api/v1/swagger.json.
- Add a dynamic OpenAPI generator that inspects Flask's url_map and emits a minimal OpenAPI 3.0 spec with an API-key header "token" security scheme.
- Add POST /api/v1/token endpoint to exchange email/password for tokens (already present in the working branch).
- Fix token validation in `app/utils/decorators.py` to use `email_confirmed_at` and `is_active`.
- Add a compatibility `confirmed` property on `User` model to mirror `email_confirmed_at`.
- Prefer development SQLite config when FLASK_ENV=development and adjust `flask_app.py` to pick it.

How to test

1. Build and run with Docker Compose (or run locally):
   - `docker compose up -d --build`
2. Open Swagger UI: `http://localhost:5000/api/docs/`
3. Obtain token (defaults are in `config.py`):
   - POST `http://localhost:5000/api/v1/token` with JSON `{ "email": "admin@example.com", "password": "admin1234567" }`
   - Use returned token in Swagger Authorize (header `token`).
4. Call protected endpoints from the UI.

Notes

- If you see "no such table: users" then run `python manage.py init_db` inside the container (or run locally) to create tables and a default admin user.
- I attempted to create a remote GitHub issue but the environment returned a "Bad credentials" error; this local issue file is here as a record and can be pasted into a new GitHub issue if needed.

Next steps

- Open PR from the created branch and run CI (if any) and/or initialize DB in container for demo.
