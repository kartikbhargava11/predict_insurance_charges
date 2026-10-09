"""API tests. A stub model replaces model.joblib so tests don't need a trained file."""

import pytest
from fastapi.testclient import TestClient

from src.app import MIN_CHARGE, app, get_model

VALID = {"age": 30, "sex": "male", "bmi": 25.0, "children": 1,
         "smoker": "no", "region": "northeast"}


class StubModel:
    def __init__(self, value: float):
        self.value = value
        self.last_input = None

    def predict(self, X):
        self.last_input = X
        return [self.value]


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def use_stub(value: float) -> StubModel:
    stub = StubModel(value)
    app.dependency_overrides[get_model] = lambda: stub
    return stub


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_returns_model_output(client):
    use_stub(12345.678)
    response = client.post("/predict", json=VALID)
    assert response.status_code == 200
    assert response.json() == {"charges": 12345.68}


@pytest.mark.parametrize("raw", [-500.0, 0.0, 999.99])
def test_predict_is_at_least_minimum_charge(client, raw):
    use_stub(raw)
    assert client.post("/predict", json=VALID).json() == {"charges": MIN_CHARGE}


def test_predict_normalises_categories_like_training(client):
    stub = use_stub(5000.0)
    payload = {**VALID, "sex": "F", "smoker": "YES", "region": "SouthEast"}
    assert client.post("/predict", json=payload).status_code == 200
    row = stub.last_input.iloc[0]
    assert (row["sex"], row["smoker"], row["region"]) == ("female", "yes", "southeast")


def test_predict_sends_columns_in_training_order(client):
    stub = use_stub(5000.0)
    client.post("/predict", json=VALID)
    assert list(stub.last_input.columns) == ["age", "bmi", "children", "sex", "smoker", "region"]


@pytest.mark.parametrize("field, bad", [
    ("age", 0), ("age", -5), ("age", 200), ("age", "thirty"),
    ("bmi", 0), ("bmi", 500),
    ("children", -1), ("children", 1.5),
    ("sex", "other"), ("smoker", "maybe"), ("region", "north"),
])
def test_predict_rejects_invalid_values(client, field, bad):
    use_stub(5000.0)
    response = client.post("/predict", json={**VALID, field: bad})
    assert response.status_code == 422


@pytest.mark.parametrize("field", list(VALID))
def test_predict_rejects_missing_fields(client, field):
    use_stub(5000.0)
    payload = {k: v for k, v in VALID.items() if k != field}
    assert client.post("/predict", json=payload).status_code == 422


def test_predict_returns_503_when_model_missing(client):
    app.state.model = None
    response = client.post("/predict", json=VALID)
    assert response.status_code == 503
