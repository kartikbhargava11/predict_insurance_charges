"""Each dirty-data rule from CLAUDE.md must be fixed by clean_data()."""

import numpy as np
import pandas as pd
import pytest

from src.train import add_smoker_bmi, clean_data


def make_row(**overrides) -> dict:
    row = {"age": 30.0, "sex": "male", "bmi": 25.0, "children": 1.0,
           "smoker": "no", "region": "northeast", "charges": "5000.0"}
    row.update(overrides)
    return row


def clean_rows(*rows) -> pd.DataFrame:
    return clean_data(pd.DataFrame(list(rows)))


@pytest.mark.parametrize("raw, expected", [
    ("F", "female"), ("woman", "female"), ("Female", "female"),
    ("M", "male"), ("man", "male"), ("MALE", "male"),
])
def test_sex_is_mapped_to_female_or_male(raw, expected):
    assert clean_rows(make_row(sex=raw))["sex"].tolist() == [expected]


@pytest.mark.parametrize("col, raw, expected", [
    ("region", "Southeast", "southeast"),
    ("region", "NorthWest", "northwest"),
    ("smoker", "Yes", "yes"),
])
def test_categories_are_lowercased(col, raw, expected):
    assert clean_rows(make_row(**{col: raw}))[col].tolist() == [expected]


def test_charges_dollar_sign_is_stripped_and_cast_to_float():
    df = clean_rows(make_row(charges="$4449.462"), make_row(charges="1725.5523"))
    assert df["charges"].dtype == float
    assert df["charges"].tolist() == [4449.462, 1725.5523]


@pytest.mark.parametrize("age", [0.0, -5.0])
def test_rows_with_age_zero_or_negative_are_dropped(age):
    df = clean_rows(make_row(age=age), make_row(age=40.0))
    assert df["age"].tolist() == [40.0]


def test_negative_children_become_positive():
    df = clean_rows(make_row(children=-3.0), make_row(children=2.0))
    assert df["children"].tolist() == [3.0, 2.0]


@pytest.mark.parametrize("col, missing", [
    ("age", np.nan), ("sex", np.nan), ("bmi", np.nan), ("children", np.nan),
    ("smoker", np.nan), ("region", np.nan), ("charges", np.nan),
    ("charges", "$nan"),  # appears in the raw CSV
])
def test_rows_with_missing_values_are_dropped(col, missing):
    df = clean_rows(make_row(**{col: missing}), make_row())
    assert len(df) == 1
    assert not df.isna().any().any()


def test_clean_works_without_charges_column():
    # The API will clean inputs that have no target column.
    df = clean_data(pd.DataFrame([make_row()]).drop(columns="charges"))
    assert "charges" not in df and len(df) == 1


def test_clean_does_not_modify_input():
    raw = pd.DataFrame([make_row(sex="F", charges="$100")])
    before = raw.copy()
    clean_data(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_smoker_bmi_is_bmi_for_smokers_and_zero_otherwise():
    df = clean_rows(make_row(smoker="Yes", bmi=31.0), make_row(smoker="no", bmi=22.0))
    assert add_smoker_bmi(df)["smoker_bmi"].tolist() == [31.0, 0.0]
