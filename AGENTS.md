# Repository Guidelines

## Project Structure & Module Organization
`backend/` holds the FastAPI service, `alembic/` migrations, and `tests/`. `frontend/` holds the Next.js app: routes in `src/app`, shared UI in `src/components`, services in `src/services`, unit tests in `src/**/__tests__`, and Playwright flows in `tests/e2e`. `mobile/` is the Expo client in `mobile/src`. Use `data/`, `database/`, `ml/`, `docs/`, and `specs/` for datasets, schema assets, model artifacts, and design notes.

## Build, Test, and Development Commands
- `cd backend && pip install -r requirements.txt` installs backend dependencies.
- `cd backend && alembic upgrade head` applies database migrations.
- `cd backend && uvicorn app.main:app --reload` starts the API locally.
- `cd backend && pytest --cov=app` runs backend tests with coverage.
- `cd frontend && npm install && npm run dev` starts the web app.
- `cd frontend && npm run build` creates the production bundle.
- `cd frontend && npm run lint` runs ESLint.
- `cd frontend && npm test` runs Vitest.
- `cd frontend && npx playwright test` runs end-to-end tests; start backend and frontend first.
- `cd mobile && npm start` launches the Expo app.

## Coding Style & Naming Conventions
Use 4-space indentation in Python and keep backend modules, functions, and tests in `snake_case`. Follow Black/Ruff-style formatting and prefer explicit type hints at backend service and schema boundaries. In TypeScript/TSX, preserve local formatting, keep semicolons, use `PascalCase` for components and screens, `camelCase` for utilities and stores, and `useX` for hooks. Prefer the `@/` alias for frontend imports from `src/`.

## Testing Guidelines
Backend pytest discovery uses `tests/test_*.py`; apply `unit`, `integration`, and `slow` markers when relevant. Frontend unit tests belong in `__tests__` folders with `*.test.ts(x)` names, while browser tests use `frontend/tests/e2e/*.spec.ts`. No hard coverage gate is configured, so every fix or feature should add regression tests for touched behavior. Mobile currently has no `test` script, so include manual smoke-test notes for mobile changes.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commits such as `feat(07-03): ...`, `fix(forecast): ...`, and `docs(07-04): ...`. Use `type(scope): short imperative summary` and keep commits narrowly scoped. PRs should include purpose, impacted areas, test evidence, linked issue or spec when available, screenshots for UI changes, and notes for migrations, env vars, or regenerated datasets.

## Security & Configuration Tips
Copy local settings from `backend/.env.example`, `frontend/.env.example`, and `mobile/.env.example`; do not commit real secrets. Avoid committing `logs/`, `uploads/`, `*.parquet`, or one-off diagnostics unless the change is intentional and documented.
