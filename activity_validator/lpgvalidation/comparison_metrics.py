"""
Module for calculating comparison metrics using input data and matching
validation data
"""

import numpy as np
import pandas as pd
from activity_validator.lpgvalidation.validation_data import ValidationData


def calc_probability_curves_diff(
    validation: pd.DataFrame, input: pd.DataFrame
) -> pd.DataFrame:
    assert (
        validation.index == input.index and validation.columns == input.columns
    ), "Dataframes have different activity types or timesteps"
    return validation - input


def calc_mae(differences: pd.DataFrame) -> pd.Series:
    return differences.abs().mean(axis=1)


def calc_rmse(differences: pd.DataFrame) -> pd.Series:
    return np.sqrt((differences**2).mean(axis=1))


def calc_comparison_metrics(
    input_data: ValidationData, validation_data: ValidationData
) -> None:
    differences = calc_probability_curves_diff(
        validation_data.probability_profiles, input_data.probability_profiles
    )
    # these KPIs show which activity is represented how well
    mae = calc_mae(differences).sort_values()
    rmes = calc_rmse(differences).sort_values()
