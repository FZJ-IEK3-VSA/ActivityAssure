"""
Contains functions for comparing validation and model statistics.
"""

import dataclasses
import itertools
import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from activityassure import (
    categorization_attributes,
    comparison_indicators,
    pandas_utils,
    utils,
)
from activityassure.indicator_set import ValidationIndicatorSet
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import (
    ValidationSet,
    ValidationStatistics,
)

from activityassure.comparison_indicators import ValidationIndicators


def get_similar_categories(profile_type: ProfileCategory) -> list[ProfileCategory]:
    """
    Returns a list of all profile types that are similar to the one specified,
    i.e. all profile types, that differ in only one attribute. Also contains
    the specified profile type itself.

    :param profile_type: the profile type for which to collect similar types
    :return: a list of similar profile types
    """
    # make sure the original profile type comes first
    similar = [profile_type]
    similar += [
        dataclasses.replace(profile_type, sex=e) for e in categorization_attributes.Sex
    ]
    work_statuses = [
        categorization_attributes.WorkStatus.full_time,
        categorization_attributes.WorkStatus.part_time,
        categorization_attributes.WorkStatus.retired,
        categorization_attributes.WorkStatus.student,
        categorization_attributes.WorkStatus.unemployed,
    ]
    similar += [dataclasses.replace(profile_type, work_status=e) for e in work_statuses]
    day_types = [
        categorization_attributes.DayType.work,
        categorization_attributes.DayType.no_work,
    ]
    similar += [dataclasses.replace(profile_type, day_type=e) for e in day_types]
    # remove duplicates
    similar = list(set(similar))
    return similar


def all_profile_types_of_same_country(country) -> list[ProfileCategory]:
    """
    Returns a list of all possible profile types for a
    fixed country.

    :return: a list of profile types
    """
    # make sure the original profile type comes first
    sexes = [e for e in categorization_attributes.Sex]
    work_statuses = [
        categorization_attributes.WorkStatus.full_time,
        categorization_attributes.WorkStatus.part_time,
        categorization_attributes.WorkStatus.retired,
        categorization_attributes.WorkStatus.student,
        categorization_attributes.WorkStatus.unemployed,
    ]
    day_types = [
        categorization_attributes.DayType.work,
        categorization_attributes.DayType.no_work,
    ]
    # get all possible combinations; the last attribute is varied first
    combinations: Iterable = itertools.product(
        [country], day_types, work_statuses, sexes
    )
    # change the attribute order so it matches the from_iterable function
    combinations = [(c, s, w, d) for c, d, w, s in combinations]
    profile_types = [ProfileCategory.from_iterable(c) for c in combinations]
    return profile_types


def validate_per_category(
    input_statistics: ValidationSet,
    validation_statistics: ValidationSet,
    output_path: Path,
    ignore_country: bool = False,
) -> dict[str, ValidationIndicatorSet]:
    """
    Compares each category of input data to the same category
    of validation data. Calculates the full set of metrics of
    all variants (default, scaled, normed), and produces one
    metric dict per variant.

    :param input_statistics: input statistics set
    :param validation_statistics: validation statistics set
    :param output_path: base path for result data
    :return: a dict containing the per-category metric dict for each variant
    """
    # validate each profile type individually
    metrics_dict, scaled_dict, normed_dict = {}, {}, {}
    for profile_type, input_data in input_statistics.statistics.items():
        # select matching validation data
        validation_data = validation_statistics.get_matching_statistics(
            profile_type, ignore_country=ignore_country
        )
        if validation_data is None:
            logging.warn(
                f"No matching validation data found for category {profile_type}"
            )
            continue
        # calcluate and store comparison metrics
        _, metrics, scaled, normed = comparison_indicators.calc_all_indicator_variants(
            validation_data, input_data, False, profile_type, output_path
        )
        metrics_dict[profile_type] = metrics
        scaled_dict[profile_type] = scaled
        normed_dict[profile_type] = normed
    default_set = ValidationIndicatorSet(metrics_dict, "default")
    scaled_set = ValidationIndicatorSet(scaled_dict, "scaled")
    normed_set = ValidationIndicatorSet(normed_dict, "normed")
    indicator_dicts = {s.variant: s for s in (default_set, scaled_set, normed_set)}
    # for indicator_dict in indicator_dicts.values():
    #     activity_means = calc_activity_mean_indicators(indicator_dict)
    return indicator_dicts


def validate_similar_categories(
    input_data_dict: dict[ProfileCategory, ValidationStatistics],
    validation_data_dict: dict[ProfileCategory, ValidationStatistics],
) -> dict[
    ProfileCategory, dict[ProfileCategory, comparison_indicators.ValidationIndicators]
]:
    # validate each profile type individually
    metrics_dict = {}
    for profile_type, input_data in input_data_dict.items():
        # select matching validation data
        similar = all_profile_types_of_same_country(profile_type.country)
        dict_per_type = {}
        for similar_type in similar:
            validation_data = validation_data_dict[similar_type]
            # calcluate and store comparison metrics
            _, metrics = comparison_indicators.calc_comparison_indicators(
                validation_data, input_data
            )
            dict_per_type[similar_type] = metrics
        metrics_dict[profile_type] = dict_per_type
    return metrics_dict


def validate_all_combinations(
    input_statistics: ValidationSet,
    validation_statistics: ValidationSet,
) -> dict[
    ProfileCategory, dict[ProfileCategory, comparison_indicators.ValidationIndicators]
]:
    """
    Calculates metrics for each combination of input and validation
    profile type.

    :param input_data_dict: input data statistics, by profile type
    :param validation_data_dict: validation data statistics, by profile type
    :return: nested dict, containing the metrics for each combination; the keys of
             the outer dict are the profile types of the input data, the keys of
             the inner dict refer to the validation data
    """
    # validate each profile type individually
    metrics_dict = {}
    for profile_type, input_data in input_statistics.statistics.items():
        # select matching validation data
        dict_per_type = {}
        for (
            validation_type,
            validation_data,
        ) in validation_statistics.statistics.items():
            # calcluate and store comparison metrics
            try:
                _, metrics = comparison_indicators.calc_comparison_indicators(
                    validation_data, input_data
                )
                dict_per_type[validation_type] = metrics
            except utils.ActValidatorException as e:
                logging.warn(
                    f"Could not compare input data category '{profile_type}' "
                    f"to validation data category '{validation_type}': {e}"
                )
        metrics_dict[profile_type] = dict_per_type
    return metrics_dict


def save_file_per_indicator_per_combination(
    metrics: dict[
        ProfileCategory,
        dict[ProfileCategory, comparison_indicators.ValidationIndicators],
    ],
    output_path: Path,
):
    """
    For a nested dict containing metrics for multiple combinations of profile types,
    creates one file per metric per input profile type. Each file gives an overview
    how this metric behaves for all activity groups for all other profile types the
    input profile type was compared to.

    :param metrics: nested metrics dict
    :param output_path: base output directory
    """
    kpis = dataclasses.fields(comparison_indicators.ValidationIndicators)
    for profile_type, metrics_per_type in metrics.items():
        for kpi in kpis:
            df = pd.DataFrame(
                {p: getattr(m, kpi.name) for p, m in metrics_per_type.items()}
            )
            pandas_utils.save_df(
                df,
                output_path / "metrics" / "all_combinations",
                kpi.name,
                profile_type,
            )


def calc_activity_mean_indicators(
    indicator_set: dict[ProfileCategory, comparison_indicators.ValidationIndicators],
) -> pd.DataFrame:
    dflist = [indicators.to_dataframe() for indicators in indicator_set.values()]
    combined_df = pd.concat(dflist, axis="index")

    activity_means = combined_df.groupby(combined_df.index).mean()

    # add profile category weights TODO: weights of which of the two data sets?

    return activity_means
