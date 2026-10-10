# Insurance Cost API

Predicts the yearly health insurance charges of a customer and serves the prediction through a FastAPI service on AWS Lambda.

**Stack:** Python · pandas · scikit-learn · FastAPI · pytest · Docker · Terraform · AWS (eu-north-1)

---

## Business problem

An insurer has to set a price for each new customer. If the price is too low, the company loses money. If it is too high, the customer goes to a competitor.
**Question:** *How much will this customer probably cost per year?*
The model uses only facts known before the contract is signed: age, sex, BMI, children, smoker, region.

The raw data is dirty: mixed spellings (`F`, `woman`, `M`…), `$` in `charges`, negative ages and children, and missing values. `src/train.py` cleans it with the rules in `CLAUDE.md`. 1,149 rows are left after cleaning.

---

## Results (5-fold CV, 1,149 rows)

3 models × 2 feature sets (base features, and base + `smoker × bmi`):

| Model | Features | R² | MAE ($) |
|---|---|---|---|
| Gradient Boosting | + smoker×bmi | 0.855 ± 0.031 | 2,538 ± 165 |
| **Gradient Boosting** | **base** | **0.856 ± 0.027** | **2,543 ± 117** |
| Random Forest | base | 0.841 ± 0.030 | 2,659 ± 174 |
| Random Forest | + smoker×bmi | 0.841 ± 0.029 | 2,660 ± 166 |
| Linear Regression | + smoker×bmi | 0.837 ± 0.034 | 2,928 ± 92 |
| Linear Regression | base | 0.743 ± 0.044 | 4,206 ± 203 |

**Chosen model: Gradient Boosting (base features).** MAE **$2,543** (≈ 19% of the mean charge), R² **0.856**.
The interaction version improves MAE by only 0.2%, which is below the 5% rule in `train.py`, so the simpler model is kept.

**Smoker × BMI finding:** smokers with a high BMI cost much more than the two effects added together. For Linear Regression, adding this one feature cuts MAE by 30% ($4,206 → $2,928) and raises R² from 0.74 to 0.84. Tree models learn this interaction by themselves, so the extra feature does not help them.

Predictions have a minimum of **$1,000** (business rule).

---

## AWS architecture (eu-north-1)

```
docker image ─► ECR ─► Lambda (container) + Function URL ─► client
                          │
                          ▼
                CloudWatch logs (7 days) + error alarm ─► SNS ─► email
```

Terraform in `infra/` also creates a monthly AWS budget alert at 5 EUR.

---

## Run locally

```bash
pip install -r requirements.txt
python src/train.py              # cleans data, compares models, saves model.joblib
pytest -q
uvicorn src.app:app --reload     # http://127.0.0.1:8000/docs
```

```bash
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" \
  -d '{"age": 45, "sex": "female", "bmi": 31.2, "children": 2, "smoker": "no", "region": "southeast"}'
```

---

## Deploy

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars   # set alert_email
terraform -chdir=infra init
terraform -chdir=infra apply -target=aws_ecr_repository.app -target=aws_ecr_lifecycle_policy.app
REPO=$(terraform -chdir=infra output -raw ecr_repository_url)
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin "${REPO%%/*}"
docker buildx build --platform linux/amd64 --provenance=false -t "${REPO}:latest" --push .
terraform -chdir=infra apply
curl "$(terraform -chdir=infra output -raw function_url)health"
```

To redeploy after a code change, run the `docker buildx` line again, then run `terraform -chdir=infra apply`. To remove everything, run `terraform -chdir=infra destroy`.

---

## Cost

Everything stays within the AWS free tier (Lambda requests and compute, a small ECR repo, short log retention, one alarm, SNS email). Expected cost at portfolio traffic: **0 €/month**. The 5 EUR budget alert sends an email if something goes wrong.

---

## Next steps

- **CI deployment with GitHub Actions + OIDC:** build and push the image and run `terraform apply` from CI, using a short-lived IAM role instead of stored AWS keys.
- Add a test that fails the build if the chosen model's MAE gets worse.
