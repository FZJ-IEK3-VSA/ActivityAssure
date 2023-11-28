"""
Module for calculating comparison metrics using input data and matching
validation data
"""

from dataclasses import dataclass, field
from datetime import timedelta
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
    wasserstein: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )
    diff_of_max: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )
    timediff_of_max: pd.Series = field(
        metadata=config(
            encoder=lambda s: s.to_json(),
            decoder=lambda s: pd.read_json(s, typ="series"),
        )
    )

    def get_scaled(self, scale: pd.Series) -> "ValidationMetrics":
        mae = self.mae.divide(scale, axis=0)
        bias = self.bias.divide(scale, axis=0)
        rmse = self.rmse.divide(scale, axis=0)
        wasserstein = self.wasserstein.divide(scale, axis=0)
        return ValidationMetrics(
            mae,
            bias,
            rmse,
            self.pearson_corr,
            wasserstein,
            self.diff_of_max,
            self.timediff_of_max,
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
    with np.errstate(divide="ignore", invalid="ignore"):
        coeffs = [data1.loc[i].corr(data2.loc[i]) for i in data1.index]
    return pd.Series(coeffs, index=data1.index)


def calc_wasserstein(data1: pd.DataFrame, data2: pd.DataFrame) -> pd.Series:
    distances = [
        scipy.stats.wasserstein_distance(data1.loc[i], data2.loc[i])
        for i in data1.index
    ]
    return pd.Series(distances, index=data1.index)


def get_max_position(data: pd.DataFrame) -> pd.Series:
    max_index = data.idxmax(axis=1)
    max_pos = max_index.apply(lambda x: data.columns.get_loc(x))
    return max_pos


def circular_difference(diff, max_value):
    half_max = max_value / 2
    if diff > 0:
        return diff if diff <= half_max else diff - max_value
    return diff if diff >= -half_max else diff + max_value


def calc_time_of_max_diff(data1: pd.DataFrame, data2: pd.DataFrame) -> pd.Series:
    max_pos1 = get_max_position(data1)
    max_pos2 = get_max_position(data2)
    diff = max_pos2 - max_pos1
    length = len(data1.columns)
    # take day-wrap into account: calculate the appropriate distance
    capped_diff = diff.apply(lambda d: circular_difference(d, length))
    difftime = capped_diff.apply(lambda d: timedelta(days=d / length))
    return difftime


def ks_test_per_activity(data1: pd.DataFrame, data2: pd.DataFrame) -> pd.Series:
    """
    Calculates the kolmogorov smirnov test for each common column in
    the passed DataFrames.

    :param data1: first dataset
    :param data2: second dataset
    :return: Series containing the resulting pvalue for each column
    """
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
    validation_data: ValidationData, input_data: ValidationData
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
    wasserstein = calc_wasserstein(
        validation_data.probability_profiles, input_data.probability_profiles
    )
    # calc difference of respective maximums
    max_diff = input_data.probability_profiles.max(
        axis=1
    ) - validation_data.probability_profiles.max(axis=1)
    time_of_max_diff = calc_time_of_max_diff(
        validation_data.probability_profiles, input_data.probability_profiles
    )

    return differences, ValidationMetrics(
        mae, bias, rmse, pearson_corr, wasserstein, max_diff, time_of_max_diff
    )
