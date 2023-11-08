"""
Module for calculating comparison metrics using input data and matching
validation data
"""

from dataclasses import dataclass, field
import logging
from pathlib import Path
from dataclasses_json import config, dataclass_json  # type: ignore
import numpy as np
import pandas as pd
import scipy  # type: ignore
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.lpgvalidation.validation_data import ValidationData


@dataclass_json
@dataclass
class ValidationMetrics:
    mae: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )
    bias: pd.Series = field(
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
    pearson_corr: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )
    ks_frequency_p: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )
    ks_duration_p: pd.Series = field(
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
        metrics = ValidationMetrics.from_json(json_str)  # type: ignore
        name, profile_type = ProfileType.from_filename(filepath)
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
    return input - validation


def calc_bias(differences: pd.DataFrame) -> pd.Series:
    return differences.mean(axis=1)


def calc_mae(differences: pd.DataFrame) -> pd.Series:
    return differences.abs().mean(axis=1)


def calc_rmse(differences: pd.DataFrame) -> pd.Series:
    return np.sqrt((differences**2).mean(axis=1))


def calc_pearson_coeff(data1: pd.DataFrame, data2: pd.DataFrame) -> pd.Series:
    # when one row is entirely zero, numpy places NAN, which is fine
    with np.errstate(divide="ignore"):
        coeffs = [np.corrcoef(data1.loc[i], data2.loc[i])[0, 1] for i in data1.index]
    return pd.Series(coeffs, index=data1.index)


def ks_test_per_activity(data1: pd.DataFrame, data2: pd.DataFrame) -> pd.Series:
    all_activities = data1.columns.union(data2.columns)
    # Kolmogorov-Smirnov
    pvalues: list = []
    for a in all_activities:
        if a not in data1 or a not in data2:
            pvalues.append(pd.NA)
            continue
        results = scipy.stats.ks_2samp(data1[a], data2[a])
        pvalues.append(results.pvalue)
    return pd.Series(pvalues, index=all_activities)


def calc_comparison_metrics(
    input_data: ValidationData, validation_data: ValidationData
) -> tuple[pd.DataFrame, ValidationMetrics]:
    differences = calc_probability_curves_diff(
        validation_data.probability_profiles, input_data.probability_profiles
    )

    # calc KPIs per activity
    bias = calc_bias(differences)
    mae = calc_mae(differences)
    rmse = calc_rmse(differences)
    pearson_corr = calc_pearson_coeff(
        validation_data.probability_profiles, input_data.probability_profiles
    )

    ks_frequency = ks_test_per_activity(
        validation_data.activity_frequencies, input_data.activity_frequencies
    )
    ks_duration = ks_test_per_activity(
        validation_data.activity_durations, input_data.activity_durations
    )

    return differences, ValidationMetrics(
        mae, bias, rmse, pearson_corr, ks_frequency, ks_duration
    )
