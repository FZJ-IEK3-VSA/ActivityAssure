"""
Module for calculating comparison metrics using input data and matching
validation data
"""

from dataclasses import dataclass, field, fields
from datetime import timedelta
import logging
from pathlib import Path
from dataclasses_json import config, dataclass_json  # type: ignore
import numpy as np
import pandas as pd
import scipy
from activity_validator.hetus_data_processing import activity_profile, utils  # type: ignore
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
    wasserstein: pd.Series = field(
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
        """
        Scales the distance metrics according to the provided scaling
        value for each activity. Does not scale metrics that do not
        depend on absolute values, such as the correlation coefficient.

        :param scale: the scaling value for each activity type
        :return: a new metrics object with scaled measures
        """
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

    def add_metric_means(self) -> None:
        """
        Adds the mean of each KPI across all activities as another
        value.
        """
        means_idx = "mean"
        assert (
            means_idx not in self.mae.index
        ), f"Cannot add the KPI mean: there is already an activity called {means_idx}"
        self.mae[means_idx] = self.mae.mean()
        self.bias[means_idx] = self.bias.mean()
        self.rmse[means_idx] = self.rmse.mean()
        self.pearson_corr[means_idx] = self.pearson_corr.mean()
        self.wasserstein[means_idx] = self.wasserstein.mean()
        self.diff_of_max[means_idx] = self.diff_of_max.mean()

    def get_metric_means(self) -> dict[str, float]:
        """
        Gets the mean of each metric across all activity groups to
        obtain metrics for the whole profile type.

        :return: a dict containing name and value of each
                 averaged metric
        """
        metric_means = {
            "mae": self.mae.mean(),
            "bias": self.bias.abs().mean(),
            "rmse": self.rmse.mean(),
            "pearson correlation": self.pearson_corr.mean(),
            "wasserstein": self.wasserstein.mean(),
            "max difference": self.diff_of_max.abs().mean(),
        }
        return metric_means

    def __build_filename(
        self,
        result_directory: Path,
        profile_type: ProfileType,
        filename: str = "metrics",
        extension: str = "json",
    ) -> Path:
        result_directory /= "metrics/per_category"
        result_directory.mkdir(parents=True, exist_ok=True)
        filename = profile_type.construct_filename(filename) + f".{extension}"
        filepath = result_directory / filename
        return filepath

    def save_as_json(self, result_directory: Path, profile_type: ProfileType) -> None:
        filepath = self.__build_filename(result_directory, profile_type)
        with open(filepath, "w", encoding="utf-8") as f:
            json_str = self.to_json()  # type: ignore
            f.write(json_str)
        logging.debug(f"Created metrics file {filepath}")

    @staticmethod
    def load_from_json(
        filepath: Path,
    ) -> tuple[ProfileType | None, "ValidationMetrics"]:
        with open(filepath) as f:
            json_str = f.read()
        metrics = ValidationMetrics.from_json(json_str)  # type: ignore
        name, profile_type = ProfileType.from_filename(filepath)
        logging.debug(f"Loaded metrics file {filepath}")
        return profile_type, metrics

    def to_dataframe(self) -> pd.DataFrame:
        class_fields = fields(ValidationMetrics)
        columns = {f.name: getattr(self, f.name) for f in class_fields}
        return pd.DataFrame(columns)

    def save_as_csv(
        self, result_directory: Path, profile_type: ProfileType, filename: str
    ) -> None:
        filepath = self.__build_filename(
            result_directory, profile_type, filename, "csv"
        )
        df = self.to_dataframe()
        df.to_csv(filepath)
        logging.debug(f"Created metrics csv file {filepath}")


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
    if len(validation.columns) != len(input.columns):
        raise utils.ActValidatorException("Dataframes have different resolutions")
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


def normalize(data: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes each row in a dataframe individually
    to value range [0, 1].

    :param data: the data
    :return: the normalized data
    """
    minimum = data.min(axis=1)
    maximum = data.max(axis=1)
    val_range = maximum - minimum
    without_offset = data.subtract(minimum, axis=0)
    normalized = without_offset.divide(val_range, axis=0)
    # rows where the value range was 0 now contain NaN -  take
    # the values without offset
    normalized = normalized.combine_first(without_offset)
    for label, row in normalized.iterrows():
        assert (np.isclose(row.min(), 0) and np.isclose(row.max(), 1)) or all(
            row == row.iloc[0]
        ), "Bug in normalization"
    return normalized


def calc_comparison_metrics(
    validation_data: ValidationData,
    input_data: ValidationData,
    normalize_prob_curves: bool = False,
    add_kpi_means: bool = False,
) -> tuple[pd.DataFrame, ValidationMetrics]:
    """
    Caluclates comparison metrics for the two specified datasets.

    :param validation_data: the validation data set
    :param input_data: the input data set
    :param normalize_prob_curves: if True, the input data is normalized to
                                  value range [0, 1], defaults to False
    :param add_kpi_means: if True, the mean of each KPI across all activities
                          is added
    :return: the probability curve difference profiles, and the metrics
    """
    # optionally normalize the probability profiles before calculating metrics
    if normalize_prob_curves:
        prob_profiles_val = normalize(validation_data.probability_profiles)
        prob_profiles_in = normalize(input_data.probability_profiles)
    else:
        prob_profiles_val = validation_data.probability_profiles
        prob_profiles_in = input_data.probability_profiles
    differences = calc_probability_curves_diff(prob_profiles_val, prob_profiles_in)

    # calc KPIs per activity
    bias = calc_bias(differences)
    mae = calc_mae(differences)
    rmse = calc_rmse(differences)
    pearson_corr = calc_pearson_coeff(prob_profiles_val, prob_profiles_in)
    wasserstein = calc_wasserstein(prob_profiles_val, prob_profiles_in)
    # calc difference of respective maximums
    max_diff = prob_profiles_in.max(axis=1) - prob_profiles_val.max(axis=1)
    time_of_max_diff = calc_time_of_max_diff(prob_profiles_val, prob_profiles_in)

    metrics = ValidationMetrics(
        mae, bias, rmse, wasserstein, pearson_corr, max_diff, time_of_max_diff
    )
    if add_kpi_means:
        metrics.add_metric_means()
    return differences, metrics


def calc_all_metric_variants(
    validation_data: ValidationData,
    input_data: ValidationData,
    save_to_file: bool = True,
    profile_type: ProfileType | None = None,
    output_path: Path | None = None,
) -> tuple[pd.DataFrame, ValidationMetrics, ValidationMetrics, ValidationMetrics]:
    # calcluate and store comparison metrics as normal, scaled and normalized
    differences, metrics = calc_comparison_metrics(
        validation_data, input_data, add_kpi_means=False
    )
    # calc metrics as normal, scaled and normalized variants
    shares = validation_data.probability_profiles.mean(axis=1)
    scaled = metrics.get_scaled(shares)
    # add metric means only after obtaining the scaled metrics
    metrics.add_metric_means()
    scaled.add_metric_means()
    _, normalized = calc_comparison_metrics(
        validation_data, input_data, True, add_kpi_means=True
    )
    if save_to_file:
        assert profile_type is not None, "Must specify a profile type for saving"
        assert output_path is not None, "Must specify an output path for saving"
        activity_profile.save_df(
            differences, "differences", "diff", profile_type, output_path
        )
        metrics.save_as_csv(output_path, profile_type, "normal")
        scaled.save_as_csv(output_path, profile_type, "scaled")
        normalized.save_as_csv(output_path, profile_type, "normalized")

    return differences, metrics, scaled, normalized
