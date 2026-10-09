# Predicting Health Insurance Charges
 
A machine learning project that predicts the yearly medical costs of health insurance customers, and turns the results into business recommendations for pricing and prevention.
 
**Tools:** Python · pandas · NumPy · scikit-learn
**Model:** Linear Regression · **Result:** R² = **0.745** (5-fold cross-validation)
 
---
 
## 1. Business Problem
 
A health insurance company has to decide how much each customer pays.
 
- **Price too low:** the medical costs are higher than the premiums, so the company loses money.
- **Price too high:** customers move to a competitor.
**Key question:** *How much will a new customer probably cost us per year?*
 
The model answers this question using only information that is known **before** the contract is signed: age, sex, BMI, number of children, smoking status and region.
 
---
 
## 2. Dataset
 
| Column | Description |
|---|---|
| `age` | Age of the primary beneficiary |
| `sex` | Gender of the insurance contractor |
| `bmi` | Body mass index |
| `children` | Number of dependents covered by the plan |
| `smoker` | Smoker (yes / no) |
| `region` | Residential area in the US (4 regions) |
| `charges` | Individual medical costs billed by the insurance (**target**) |
 
- `insurance.csv` is used for training and evaluation.
- `validation_dataset.csv` contains new customers without `charges`. The model predicts their costs.
---
 
## 3. Data Quality Check
 
Before modelling, I checked the raw data. It had several typical real-world problems:
 
| Problem | What I found |
|---|---|
| Missing values | 66 missing values in every feature column and 54 in `charges` |
| Inconsistent categories in `sex` | 6 spellings for 2 values: `female`, `woman`, `F`, `male`, `man`, `M` |
| Inconsistent categories in `region` | Mixed upper and lower case, e.g. `Southeast` and `southeast` |
| Impossible values in `age` | Minimum of **-64** |
| Impossible values in `children` | Minimum of **-4** |
| Wrong data type in `charges` | Stored as text because some values have a `$` sign, e.g. `$4449.462` |
 
Without cleaning, the model would treat `Southeast` and `southeast` as two different regions, and it could not use `charges` at all.
 
---
 
## 4. Data Cleaning
 
```python
df = insurance.copy()
 
# Standardise categories
df["sex"] = df["sex"].str.lower().replace({"m": "male", "man": "male",
                                           "f": "female", "woman": "female"})
df["smoker"] = df["smoker"].str.lower()
df["region"] = df["region"].str.lower()
 
# Convert charges to numbers
df["charges"] = df["charges"].astype(str).str.replace("$", "", regex=False).astype(float)
 
# Handle impossible values
df = df[df["age"] > 0]
df["children"] = df["children"].abs()
 
# Remove missing values
df = df.dropna()
```
 
**Decisions and reasons:**
 
- **Negative ages → rows removed.** The correct value cannot be known for sure, so guessing would add wrong information.
- **Negative children → converted to positive.** This is most likely a sign error, and the value range (0–5) stays realistic. Setting the values to 0 or removing the rows would also be valid choices.
- **Missing values → rows removed.** These rows had almost no usable information.
In a real company, I would confirm these decisions with the owner of the data source.
 
---
 
## 5. Model
 
**Steps:**
 
1. Turn the text columns into numbers with one-hot encoding (`pd.get_dummies`, `drop_first=True`).
2. Train a **Linear Regression** model.
3. Evaluate it with **5-fold cross-validation** using the R² score.
```python
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import cross_val_score
 
X = pd.get_dummies(df.drop(columns="charges"), drop_first=True)
y = df["charges"]
 
model = LinearRegression()
r2_score = cross_val_score(model, X, y, cv=5, scoring="r2").mean()
model.fit(X, y)
```
 
**Why Linear Regression?**
It is easy to explain to business stakeholders. Each coefficient shows directly how many dollars a factor adds to the yearly costs.
 
---
 
## 6. Results
 
### Model performance
 
| Metric | Value | Requirement |
|---|---|---|
| R² (5-fold CV) | **0.745** | > 0.65 ✅ |
 
**What R² means:** The model explains about **75%** of the differences in costs between customers. An R² of 0 would mean the model is no better than guessing the average, and an R² of 1 would mean a perfect prediction.
 
### What drives the costs? (coefficients)
 
Each value shows the change in **yearly charges ($)** when only that one factor changes and everything else stays the same.
 
| Factor | Effect on yearly costs |
|---|---|
| **Smoker** | **+ $23,978** |
| Each additional child | + $402 |
| Each additional BMI point | + $327 |
| Each additional year of age | + $262 |
| Male (vs. female) | − $183 |
| Region northwest (vs. northeast) | − $271 |
| Region southeast (vs. northeast) | − $740 |
| Region southwest (vs. northeast) | − $861 |
 
*Reference group: female, region northeast.*
 
### Key findings
 
1. **Smoking is by far the strongest cost driver.** A smoker costs about **$24,000 more per year** than an otherwise identical non-smoker. Reaching the same extra cost through age alone would take about 90 additional years (23,978 ÷ 262 ≈ 91).
2. **Age, BMI and children raise costs gradually.** For example, a customer who is 10 years older costs about $2,600 more per year.
3. **Sex and region have only a small effect** compared with smoking.
---
 
## 7. Predictions for New Customers
 
The trained model predicts `predicted_charges` for every customer in `validation_dataset.csv`.
 
- The new data is cleaned the **same way** as the training data.
- Its columns are aligned with the training columns (`reindex`), so the model gets exactly the same inputs.
- **Business rule:** a minimum charge of **$1,000** is applied with `clip(lower=1000)`, because a linear model can predict very low or even negative values, and a real price list cannot.
```python
X_val = pd.get_dummies(val, drop_first=True).reindex(columns=X.columns, fill_value=0)
validation_data["predicted_charges"] = model.predict(X_val)
validation_data["predicted_charges"] = validation_data["predicted_charges"].clip(lower=1000)
```
 
---
 
## 8. Business Recommendations
 
| Finding | Recommended action | Business value |
|---|---|---|
| The model explains 75% of cost differences | Use it as a starting point for risk-based pricing | Prices closer to real costs, which means fewer losses |
| Smoking adds about $24,000 per year | Offer a stop-smoking program | Lower future claims and healthier customers |
| BMI raises costs | Offer wellness and fitness programs | Long-term cost reduction |
| Costs rise with age | Plan reserves for an ageing customer base | Better financial planning |
 
**Example of a business case** (illustrative assumptions):
If a stop-smoking program costs $1,000 per participant and only 1 in 10 participants quits, the expected saving is about $2,400 per participant per year, so the program would pay for itself.
 
**Regulation note:** In practice, insurers are not always allowed to use every variable for pricing. In the US individual health insurance market, for example, prices may not differ by sex, and the extra charge for tobacco use is limited. Any real pricing model must be checked against the applicable law.
 
---
 
## 9. Limitations and Next Steps
 
- **Interactions:** Linear Regression assumes that the factors simply add up. In this data, smokers with a high BMI are likely much more expensive than the two effects added together. Next step: add a `smoker × BMI` feature or try a **Random Forest** or **Gradient Boosting** model.
- **Trade-off:** Linear model = easy to explain. Tree-based models = usually more accurate, but harder to explain.
- **More data:** medical history and claims history could improve the predictions, if they are allowed for pricing.
- **Error in dollars:** add RMSE / MAE to show the typical prediction error in dollars per customer.
---
 
## 10. What This Project Shows
 
- **Data cleaning** of messy real-world data (missing values, inconsistent categories, impossible values, wrong data types)
- **Feature encoding** for categorical variables
- **Regression modelling** and **cross-validation**
- **Interpreting a model** in business terms (coefficients → dollars)
- **Turning results into decisions:** pricing, prevention programs, business cases and regulatory awareness
---
 
## How to Run
 
```bash
pip install pandas numpy scikit-learn
jupyter notebook notebook.ipynb
```
 
Project files:
 
```
├── insurance.csv
├── validation_dataset.csv
├── notebook.ipynb
└── README.md
```
 
