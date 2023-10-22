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
    assert len(validation.columns) == len(
        input.columns
    ), "Dataframes have different resolutions"
    if not validation.columns.equals(input.columns):
        # resolution is the same, just the names are different
        validation.columns = input.columns
    if not validation.index.equals(input.index):
        # in one of the dataframes not all activity types are present, or
        # the order is different
        # determine common index with all activity types
        common_index = validation.index.union(input.index)
        # add rows full of zeros for missing activity types
        validation = validation.reindex(common_index, fill_value=0)
        input = input.reindex(common_index, fill_value=0)
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
    mae_per_activity = calc_mae(differences).sort_values()
    rmes_per_activity = calc_rmse(differences).sort_values()
