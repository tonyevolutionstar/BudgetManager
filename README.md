# BudgetManager

Manage your budget by importing bank statements (CSV or PDF), categorising transactions
(rules → ML → keywords) and visualising spending.

Stack: Python 3.14, Streamlit, pandas, scikit-learn, pdfplumber, Plotly, PostgreSQL (Neon) via SQLAlchemy.

## Setup

```bash
uv sync                      # installs the dependencies from pyproject.toml / uv.lock
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then fill it in (git-ignored)
```

### Database

Run `data/DatabaseSchema.sql` against your PostgreSQL database. It is safe to run repeatedly
(it never drops anything). `data/ResetDatabase.sql` wipes everything.
If your database was created with the **old** schema, run `data/migrations/002_existing_database_hardening.sql` once.

### Login

Every page calls `require_login()` (`src/utils/auth.py`) and **fails closed**: without an `[auth]`
section in `secrets.toml` the app refuses to show anything. For local development only, set
`allow_anonymous = true` under `[app]`. Restrict access with `allowed_emails`.

## Run

```bash
uv run streamlit run Home.py
```

## Data and privacy

* Transactions are saved to `data/csv/transactions.csv`: **keep it out of git** (see `.gitignore`).
* Uploads are limited to 10 MB (`.streamlit/config.toml`) and PDFs to 50 pages.
* PDF parsing is heuristic: after an import, check the warnings (assumed signs, reconciliation).

## Layout

| Path | Purpose |
|------|---------|
| `Home.py`, `pages/` | Streamlit pages |
| `service/` | Importer (`FileImporterService`) and classifier (`ClassifierService`) |
| `data/` | `database.py`, SQL schema/migrations, `bankStatementExtractor.py` |
| `src/repository/` | Database access (one class per table group) |
| `src/utils/` | Date helpers, login gate |

## Tests

```bash
uv run pytest
```