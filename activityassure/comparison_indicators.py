"""
Module for calculating comparison metrics using input data and matching
validation data
"""

from dataclasses import dataclass, fields
import logging
from pathlib import Path
from typing import ClassVar
import numpy as np
import pandas as pd
import scipy  # type: ignore
from activityassure import pandas_utils, utils
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationStatistics


@dataclass
class ValidationIndicators:
    """Stores a set of indicators for a single comparison, e.g., for a single
    activity profile type"""

    mae: pd.Series
    bias: pd.Series
    rmse: pd.Series
    wasserstein: pd.Series
    pearson_corr: pd.Series

    mean_column: ClassVar[str] = "mean"

    def get_scaled(self, scale: pd.Series) -> "ValidationIndicators":
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
        return ValidationIndicators(
            mae,
            bias,
            rmse,
            wasserstein,
            self.pearson_corr,
        )

    def get_indicators_for_activity(self, activity: str) -> dict[str, float]:
        """Returns all indicators for a single activity

        :param activity: the activity to get indicators for
        :raises utils.ActValidatorException: if there are no indicators for the activity
        :return: the indicators for the activity in a dict
        """
        if activity not in self.mae.index:
            raise utils.ActValidatorException("No indicators for {activity} found")
        series_dict = self.get_as_series_dict()
        activity_values = {
            indicator: series[activity] for indicator, series in series_dict.items()
        }
        return activity_values

    def add_metric_means(self) -> None:
        """
        Adds the mean of each KPI across all activities as another
        value.
        """
        assert ValidationIndicators.mean_column not in self.mae.index, (
            f"Cannot add the indicator mean: there is already an activity called {ValidationIndicators.mean_column}"
        )
        self.mae[ValidationIndicators.mean_column] = self.mae.mean()
        self.bias[ValidationIndicators.mean_column] = self.bias.mean()
        self.rmse[ValidationIndicators.mean_column] = self.rmse.mean()
        self.pearson_corr[ValidationIndicators.mean_column] = self.pearson_corr.mean()
        self.wasserstein[ValidationIndicators.mean_column] = self.wasserstein.mean()

    def get_metric_means(self) -> dict[str, float]:
        """
        Gets the mean of each metric across all activity groups to
        obtain metrics for the whole profile type.

        :return: a dict containing name and value of each
                 averaged metric
        """
        series_dict = self.get_as_series_dict()
        means = {indicator: series.mean() for indicator, series in series_dict.items()}
        return means

    def __build_filename(
        self,
        result_directory: Path,
        profile_type: ProfileCategory,
        filename: str = "metrics",
        extension: str = "json",
    ) -> Path:
        result_directory /= "metrics/per_category"
        result_directory.mkdir(parents=True, exist_ok=True)
        filename = profile_type.construct_filename(filename) + f".{extension}"
        filepath = result_directory / filename
        return filepath

    def get_as_series_dict(self) -> dict[str, pd.Series]:
        """
        Collects all indicator Series in a dict, using the indicator name (e.g., mae)
        as key

        :return: a dict containing all indicator Series
        """
        class_fields = fields(ValidationIndicators)
        return {f.name: getattr(self, f.name) for f in class_fields}

    def to_dataframe(self) -> pd.DataFrame:
        columns = self.get_as_series_dict()
        return pd.DataFrame(columns)

    def save_as_csv(
        self, result_directory: Path, profile_type: ProfileCategory, filename: str
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
    return input - validation


def calc_bias(differences: pd.DataFrame) -> pd.Series:
    return differences.mean(axis=1)


def calc_mae(differences: pd.DataFrame) -> pd.Series:
    return differences.abs().mean(axis=1)


def calc_rmse(differences: pd.DataFrame) -> pd.Series:
    return np.sqrt((differences**2).mean(axis=1))  # type: ignore


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


def resample_columns(df, target_cols):
    """
    Resample the columns of a DataFrame to a fixed number of columns,
    using linear interpolation. Just uses the number of columns, does
    not require any time index.

    :param df: the DataFrame to resample
    :param target_cols: the desired number of columns
    :return: the rsampled dataframe
    """
    original_cols = len(df.columns)
    x_old = np.linspace(0, 1, original_cols)
    x_new = np.linspace(0, 1, target_cols)

    # Interpolate each row
    df_resampled = pd.DataFrame(
        np.array([np.interp(x_new, x_old, row) for row in df.to_numpy()]),
        index=df.index,
    )
    return df_resampled


def resample_df_columns_to_match(df1, df2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Resamples the columns of two DataFrames to match each other.
    Always resamples the DataFrame with fewer columns to match the other one.

    :param df1: first dataframe
    :param df2: second dataframe
    :return: the resampled dataframes
    """
    len1 = len(df1.columns)
    len2 = len(df2.columns)
    if len1 == len2:
        # return dataframes unchanged
        return df1, df2
    if len1 > len2:
        # resample df2 to match df1
        return df1, resample_columns(df2, len1)
    # resample df1 to match df2
    return resample_columns(df1, len2), df2


def make_probability_dfs_compatible(
    validation: pd.DataFrame, input: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Checks if two daily probability profiles are compatible and can be
    compared.
    If the indices of the data differ, they are aligned. In case of different
    sets of activities, the union of activities is used and zero rows are added
    for missing activities.

    :param validation: validation probability profiles
    :param input: input probability profiles
    :raises utils.ActValidatorException: if the profiles don't match
    :return: the aligned validation and input profiles
    """
    if len(validation.columns) != len(input.columns):
        logging.info("Resampling probability profile DataFrames column-wise to match.")
        validation, input = resample_df_columns_to_match(validation, input)
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
    return validation, input


def calc_comparison_indicators(
    validation_data: ValidationStatistics,
    input_data: ValidationStatistics,
    normalize_prob_curves: bool = False,
    add_kpi_means: bool = False,
) -> tuple[pd.DataFrame, ValidationIndicators]:
    """
    Caluclates comparison indicators for the two specified datasets.

    :param validation_data: the validation data set
    :param input_data: the input data set
    :param normalize_prob_curves: if True, the input data is normalized to
                                  value range [0, 1], defaults to False
    :param add_kpi_means: if True, the mean of each KPI across all activities
                          is added
    :return: the probability curve difference profiles, and the indicators
    """
    # optionally normalize the probability profiles before calculating metrics
    if normalize_prob_curves:
        prob_profiles_val = normalize(validation_data.probability_profiles)
        prob_profiles_in = normalize(input_data.probability_profiles)
    else:
        prob_profiles_val = validation_data.probability_profiles
        prob_profiles_in = input_data.probability_profiles

    prob_profiles_val, prob_profiles_in = make_probability_dfs_compatible(
        prob_profiles_val, prob_profiles_in
    )
    differences = calc_probability_curves_diff(prob_profiles_val, prob_profiles_in)

    # calc KPIs per activity
    bias = calc_bias(differences)
    mae = calc_mae(differences)
    rmse = calc_rmse(differences)
    pearson_corr = calc_pearson_coeff(prob_profiles_val, prob_profiles_in)
    wasserstein = calc_wasserstein(prob_profiles_val, prob_profiles_in)

    metrics = ValidationIndicators(mae, bias, rmse, wasserstein, pearson_corr)
    if add_kpi_means:
        metrics.add_metric_means()
    return differences, metrics


def calc_all_indicator_variants(
    validation_data: ValidationStatistics,
    input_data: ValidationStatistics,
    save_to_file: bool = True,
    profile_type: ProfileCategory | None = None,
    output_path: Path | None = None,
    add_means: bool = True,
) -> tuple[
    pd.DataFrame, ValidationIndicators, ValidationIndicators, ValidationIndicators
]:
    """
    Calculates all indicator variants (default, scales, normed) for the provided
    combination of validation and input data. Optionally stores each indicator set
    as a file.

    :param validation_data: validation statistics
    :param input_data: input statistics
    :param save_to_file: if True, saves the indicators to file, defaults to True
    :param profile_type: the profile type, only required for saving, defaults to None
    :param output_path: the base output path for saving the indicators, defaults to None
    :param add_means: if True, means across all activities will be added to each set of
                      indicators, defaults to True
    :return: a tuple containing the difference profiles for the activity probabilities
             and the three indicator variants
    """
    # calcluate and store comparison metrics as normal, scaled and normalized
    differences, indicators = calc_comparison_indicators(
        validation_data, input_data, add_kpi_means=False
    )
    # determine the average share of each activity in both datasets for scaling
    shares_val = validation_data.probability_profiles.mean(axis=1)
    shares_in = input_data.probability_profiles.mean(axis=1)
    shares = pd.concat([shares_val, shares_in], axis="columns").mean(axis="columns")
    scaled = indicators.get_scaled(shares)
    # calc metrics as normal, scaled and normalized variants
    if add_means:
        # add metric means only after obtaining the scaled metrics
        indicators.add_metric_means()
        scaled.add_metric_means()
    _, normalized = calc_comparison_indicators(
        validation_data, input_data, True, add_kpi_means=add_means
    )
    if save_to_file:
        assert profile_type is not None, "Must specify a profile type for saving"
        assert output_path is not None, "Must specify an output path for saving"
        pandas_utils.save_df(
            differences, output_path / "differences", "diff", profile_type
        )
        indicators.save_as_csv(output_path, profile_type, "normal")
        scaled.save_as_csv(output_path, profile_type, "scaled")
        normalized.save_as_csv(output_path, profile_type, "normalized")

    return differences, indicators, scaled, normalized
