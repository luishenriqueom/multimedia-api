Setup and use Alembic migrations

Prerequisites

- Have `DATABASE_URL` set in your environment (or in `.env`). The project default is:
  `postgresql://postgres:postgres@localhost:5432/multimedia`
- Install Python deps: `pip install -r requirements.txt`

Common commands (run from project root)

- Create an autogenerate revision (captures model changes):
  `alembic revision --autogenerate -m "create tables"`

- Apply migrations to the database:
  `alembic upgrade head`

- Show current revision:
  `alembic current`

Notes

- `alembic` reads `alembic.ini` and `alembic/env.py`. `env.py` will import `DATABASE_URL` from `app.config` and `Base` from `app.database` to autogenerate migrations from your models.
- If Alembic cannot import `app`, ensure you run commands from the project root where the `app` package is located.
