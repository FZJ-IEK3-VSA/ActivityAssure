"""
Module for calculating comparison metrics using input data and matching
validation data
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
from dataclasses_json import config, dataclass_json
import numpy as np
import pandas as pd
from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.lpgvalidation.validation_data import ValidationData


@dataclass_json
@dataclass
class ValidationMetrics:
    mea: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )
    rmse: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )

    def save(self, result_directory: Path, profile_type: ProfileType) -> None:
        result_directory /= "metrics"
        result_directory.mkdir(parents=True, exist_ok=True)
        filename = profile_type.construct_filename("metrics") + ".json"
        filepath = result_directory / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json_str = self.to_json()  # type: ignore
            f.write(json_str)
        logging.debug(f"Created metrics file {filepath}")

    @staticmethod
    def load(filepath: Path) -> tuple[ProfileType | None, "ValidationMetrics"]:
        with open(filepath) as f:
            json_str = f.read()
        name, profile_type = ProfileType.from_filename(filepath)
        metrics = ValidationMetrics.from_json(json_str)  # type: ignore
        logging.debug(f"Loaded metrics file {filepath}")
        return profile_type, metrics


def calc_probability_curves_diff(
    validation: pd.DataFrame, input: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculates the difference between two daily probability profiles.
    Aligns columns and indices if necessary.

    :param validation: validation data probability profiles
    :param input: input data probability profiles
    :return: difference of validation and input data
    """
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
) -> ValidationMetrics:
    differences = calc_probability_curves_diff(
        validation_data.probability_profiles, input_data.probability_profiles
    )
    # these KPIs show which activity is represented how well
    mae_per_activity = calc_mae(differences).sort_values()
    rmse_per_activity = calc_rmse(differences).sort_values()
    return ValidationMetrics(mae_per_activity, rmse_per_activity)
