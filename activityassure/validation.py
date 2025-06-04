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
    validation,
)
from activityassure.indicator_set import ValidationIndicatorSet
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import (
    ValidationSet,
    ValidationStatistics,
)
from activityassure.visualizations import indicator_heatmaps


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
            logging.warning(
                f"No matching validation data found for category {profile_type}"
            )
            continue
        # calcluate and store comparison metrics
        _, metrics, scaled, normed = comparison_indicators.calc_all_indicator_variants(
            validation_data, input_data, False, profile_type, output_path
        )
        profile_type = (
            profile_type if not ignore_country else profile_type.to_base_category()
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


@utils.timing
def default_validation(model_path: Path, validation_path: Path):
    """
    Default validation routine. Loads model and validation statistics
    and compares matching categories individually by generating
    indicators and heatmaps.

    :param model_path: path of the model statistics dataset
    :param validation_path: path of the validation dataset
    """
    # load LPG statistics and validation statistics
    input_statistics = ValidationSet.load(model_path)
    validation_statistics = ValidationSet.load(validation_path)

    # compare input and validation data statistics per profile category
    indicator_set_variants = validation.validate_per_category(
        input_statistics, validation_statistics, model_path
    )
    validation_result_path = model_path / "validation_results"

    # save indicators and heatmaps for each indicator variant
    for variant_name, indicator_set in indicator_set_variants.items():
        result_subdir = validation_result_path / variant_name
        metrics_df = indicator_set.save(result_subdir / "indicators_per_category")

        # plot heatmaps to compare indicator values
        plot_path = result_subdir / "heatmaps"
        indicator_heatmaps.plot_indicators_by_profile_type(metrics_df, plot_path)
        indicator_heatmaps.plot_indicators_by_activity(metrics_df, plot_path)
        indicator_heatmaps.plot_profile_type_by_activity(metrics_df, plot_path)
