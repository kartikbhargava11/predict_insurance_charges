"""FastAPI service that predicts yearly insurance charges from model.joblib."""

from contextlib import asynccontextmanager
from typing import Literal

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from src.train import CATEGORICAL, MODEL_PATH, NUMERIC, SEX_ALIASES

MIN_CHARGE = 1000.0


class Customer(BaseModel):
    age: float = Field(gt=0, le=120)
    sex: Literal["female", "male"]
    bmi: float = Field(gt=0, le=100)
    children: int = Field(ge=0, le=20)
    smoker: Literal["yes", "no"]
    region: Literal["northeast", "northwest", "southeast", "southwest"]

    # Same normalisation as training: lowercase categories, map F/woman/M/man.
    @field_validator("sex", "smoker", "region", mode="before")
    @classmethod
    def normalise(cls, value, info):
        if not isinstance(value, str):
            return value
        value = value.strip().lower()
        return SEX_ALIASES.get(value, value) if info.field_name == "sex" else value


class Prediction(BaseModel):
    charges: float


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
    yield


app = FastAPI(title="Insurance Cost API", lifespan=lifespan)


def get_model(request: Request):
    model = getattr(request.app.state, "model", None)
    if model is None:
        raise HTTPException(503, "Model not loaded. Run `python src/train.py` first.")
    return model


@app.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "model_loaded": getattr(request.app.state, "model", None) is not None}


@app.post("/predict")
def predict(customer: Customer, model=Depends(get_model)) -> Prediction:
    X = pd.DataFrame([customer.model_dump()])[NUMERIC + CATEGORICAL]
    charges = max(float(model.predict(X)[0]), MIN_CHARGE)
    return Prediction(charges=round(charges, 2))
