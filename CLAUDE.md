# Insurance Cost API

Predicts yearly health insurance charges and serves them via a FastAPI service,
deployed to AWS. Portfolio project for MLOps / data science roles.

## Stack
Python, pandas, scikit-learn, FastAPI, pytest, Docker, Terraform (AWS), GitHub Actions. Deployment target: AWS Lambda (container image) + Function URL. Must stay in the AWS free tier.

## Layout
- data/        raw CSVs – never modify
- notebooks/   exploration only – do not edit unless asked
- src/         train.py (clean + train + save model.joblib), app.py (API)
- tests/       pytest
- infra/       Terraform

## Commands
- Train: `python src/train.py`
- Test: `pytest -q`
- Run API: `uvicorn src.app:app --reload`

## Data rules (known dirty data)
- sex: map F/woman → female, M/man → male; lowercase all categories
- charges: strip "$", cast to float
- drop age <= 0; children = abs(children); drop rows with NaN
- predictions: minimum charge 1000

## Working rules
- Small steps: one feature per task, then run tests, then commit.
- Do not read full CSV files; use `head` or pandas `.info()` / `.describe()`.
- Do not create new files or dependencies without saying why.
- Explain changes briefly in simple English.
- Never commit secrets, .env, AWS keys or model.joblib.