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

Run `data/DatabaseSchema.sql` against your PostgreSQL database. **Warning: the current script starts with DROP TABLE statements and resets existing data.**
Use it only on a new or disposable database. This repository does not currently contain the
reset script or hardening migration mentioned in earlier instructions. Back up an existing
database before any schema changes.

## Run

```bash
uv run streamlit run Home.py
```

## Automatic categories

For each transaction the app looks for evidence, in this order:
1. **learned**: the same description (ignoring digits, dates, punctuation and accents) was categorised by you before;
2. **keywords**: `categories` in `data/bankStatementExtractor.py`;
3. **ml**: a model trained on your stored corrections (needs 20+ samples in 2+ categories), only for rows no keyword matched;
4. otherwise an existing category of yours is kept, or the row becomes "Others".

* **Home → Import**: "Categorise automatically after import" (on by default).
* **Home → Automatic categories**: preview, correct any suggestion, then **Apply categories**.
  "Uncategorised only" keeps categories you set yourself; "All transactions" re-evaluates every row.
* **Home → Learned corrections**: review what was learned and forget any entry.
* **Dashboard**: a banner with a one-click button while some transactions still use non-app categories.
* **Transactions**: the category you choose for a manual entry is learned too.

Learning is stored in the `MLTrainingSample` table: your corrections (`manual`) and the suggestions you accept
(`confirmed_rule` / `confirmed_ml`). Automatic runs (after an import, the Dashboard button) are never saved.
Imported transactions and category changes are saved atomically to the personal CSV and
restored when a new Home session starts. Learning samples remain in the database.
The CSV is a single-user local file; it is not a multi-user storage or account-isolation mechanism.
The migration `data/migrations/003_ml_training_sample_unique.sql` is not currently included in this repository.

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


## Regression checks

Run `uv run python -m unittest discover -s tests -v`. The tests cover finite database
amounts, PDF file-like input, CSV errors and roundtrips, preservation of custom category
names, first-run recovery and custom date filtering. No live database is required.
