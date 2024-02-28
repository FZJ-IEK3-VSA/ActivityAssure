"""Main module"""

import dataclasses
from datetime import timedelta
import itertools
import json
import logging
from pathlib import Path
from typing import Iterable

import pandas as pd
from activity_validator.hetus_data_processing import (
    hetus_constants,
    category_statistics,
    pandas_utils,
    utils,
)

from activity_validator.hetus_data_processing.profile_category import ProfileType
from activity_validator.hetus_data_processing.attributes import (
    diary_attributes,
)
from activity_validator import (
    activity_profile,
    categorization_attributes,
    comparison_indicators,
)
from activity_validator.activity_profile import (
    ExpandedActivityProfiles,
    SparseActivityProfile,
    ActivityProfileEntry,
)
from activity_validator.validation_statistics import (
    ValidationStatistics,
    ValidationSet,
)
from activity_validator import activity_mapping


def load_person_characteristics(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        traits: dict[str, dict] = json.load(f)
    return {name: ProfileType.from_dict(d) for name, d in traits.items()}  # type: ignore


def get_person_traits(
    person_traits: dict[str, ProfileType], filename: str | Path
) -> ProfileType:
    """
    Extracts the person name from the path of an activity profile file
    and returns the matching ProfileType object with the person
    characteristics.

    :param person_traits: the person trait dict
    :param filepath: path of the activity profile file, contains the
                     name of the person
    :raises RuntimeError: when no characteristics for the person were
                          found
    :return: the characteristics of the person
    """
    name = Path(filename).stem.split("_")[0]
    if name not in person_traits:
        raise RuntimeError(f"No person characteristics found for '{name}'")
    return person_traits[name]


@utils.timing
def load_activity_profiles_from_csv(
    path: str | Path,
    person_trait_file: str,
    resolution: timedelta = activity_profile.DEFAULT_RESOLUTION,
) -> list[SparseActivityProfile]:
    """Loads the activity profiles in csv format from the specified folder"""
    if not isinstance(path, Path):
        path = Path(path)
    assert Path(path).is_dir(), f"Directory does not exist: {path}"
    person_traits = load_person_characteristics(person_trait_file)
    activity_profiles = []
    for filepath in path.iterdir():
        if filepath.is_file():
            profile_type = get_person_traits(person_traits, filepath)
            activity_profile = SparseActivityProfile.load_from_csv(
                filepath, profile_type, resolution
            )
            activity_profiles.append(activity_profile)
    logging.info(f"Loaded {len(activity_profiles)} activity profiles")
    return activity_profiles


def filter_complete_day_profiles(
    activity_profiles: Iterable[SparseActivityProfile],
) -> list[SparseActivityProfile]:
    """
    Get only all complete day profiles, which are actually 24 h long

    :param activity_profiles: the profiles to filter
    :return: the profiles that match the condition
    """
    return [a for a in activity_profiles if a.duration() == timedelta(days=1)]


def filter_min_activity_count(
    activity_profiles: Iterable[SparseActivityProfile],
    min_activities: int = 1,
) -> list[SparseActivityProfile]:
    """
    Get only all day profiles with a minimum number of activities

    :param activity_profiles: the profiles to filter
    :param min_activities: the minimum number of activities, defaults to 1
    :return: the profiles that match the condition
    """
    return [a for a in activity_profiles if len(a.activities) >= min_activities]


def is_work_activity(activity: ActivityProfileEntry) -> bool:
    """
    Checks if an activity is a work activity.

    :param activity: the activity to check
    :return: True if the activity is a work activity, else False
    """
    return activity.name in diary_attributes.WORK_ACTIVITIES


def determine_day_type(activity_profile: SparseActivityProfile) -> None:
    """
    Determines and sets the day type for the activity profile by checking
    the total time spent with work activities.

    :param activity_profile: the activity profile to check
    """
    durations = [a.duration for a in activity_profile.activities if is_work_activity(a)]
    # calculate total working time on this day
    work_sum = sum(durations)
    assert (
        work_sum is not None
    ), "Cannot determine day type for profiles with missing durations"
    # set the day type depending on the total working time
    day_type = (
        categorization_attributes.DayType.work
        if work_sum * activity_profile.resolution >= diary_attributes.WORKTIME_THRESHOLD
        else categorization_attributes.DayType.no_work
    )
    # set the determined day type for the profile
    new_type = dataclasses.replace(activity_profile.profile_type, day_type=day_type)
    activity_profile.profile_type = new_type


def extract_day_profiles(
    activity_profile: SparseActivityProfile,
    day_offset: timedelta = hetus_constants.PROFILE_OFFSET,
) -> list[SparseActivityProfile]:
    day_profiles = activity_profile.split_into_day_profiles(day_offset)
    # this also removes profiles with missing activity durations
    day_profiles = filter_complete_day_profiles(day_profiles)
    # remove days with only a single activity (e.g., vacation)
    day_profiles = filter_min_activity_count(day_profiles, 2)
    logging.info(f"Extracted {len(day_profiles)} single-day activity profiles")
    return day_profiles


def group_profiles_by_type(
    activity_profiles: list[SparseActivityProfile],
) -> dict[ProfileType, list[SparseActivityProfile]]:
    """
    Determines day type for each day profile and groups
    the profiles by their overall type.

    :param activity_profiles: the activity profiles to group
    :return: a dict mapping each profile type to the respective
             profiles
    """
    profiles_by_type: dict[ProfileType, list[SparseActivityProfile]] = {}
    for profile in activity_profiles:
        # set day type property
        determine_day_type(profile)
        profiles_by_type.setdefault(profile.profile_type, []).append(profile)
    logging.info(
        f"Grouped {len(activity_profiles)} profiles into {len(profiles_by_type)} categories"
    )
    return profiles_by_type


def calc_input_data_statistics(
    profiles: list[SparseActivityProfile], activity_types: list[str]
) -> ValidationStatistics:
    """
    Calculates statistics for the input data of a specific profile type

    :param profiles: sparse activity profiles of the same type
    :param activity_types: list of possible activity names
    :return: the calculated statistics
    """
    frequencies = category_statistics.calc_activity_group_frequencies(profiles)
    durations = category_statistics.calc_activity_group_durations(profiles)
    # convert to expanded format
    profile_set = ExpandedActivityProfiles.from_sparse_profiles(profiles)
    probabilities = category_statistics.calc_probability_profiles(
        profile_set.data, activity_types
    )
    # store all statistics in one object
    input_data = ValidationStatistics(
        profiles[0].profile_type, probabilities, frequencies, durations, len(profiles)
    )
    return input_data


def prepare_input_data(
    full_year_profiles: list[SparseActivityProfile], activity_mapping: dict[str, str]
) -> dict[ProfileType, list[SparseActivityProfile]]:
    # map and categorize each full-year profile individually
    all_profiles_by_type: dict[ProfileType, list[SparseActivityProfile]] = {}
    empty_profiles = 0
    for full_year_profile in full_year_profiles:
        logging.debug(f"Preparing profile from file {full_year_profile.filename}")
        # skip empty profiles
        if not full_year_profile.activities or len(full_year_profile.activities) < 5:
            logging.warn(f"Skipping empty/short profile {full_year_profile.filename}")
            continue
        # resample profiles to validation data resolution
        full_year_profile.resample(hetus_constants.RESOLUTION)
        # translate activities to the common set of activity types
        full_year_profile.apply_activity_mapping(activity_mapping)
        # split the full year profiles into single-day profiles
        selected_day_profiles = extract_day_profiles(full_year_profile)

        # categorize single-day profiles according to country, person and day type
        profiles_by_type = group_profiles_by_type(selected_day_profiles)

        all_profiles_by_type = utils.merge_dicts(all_profiles_by_type, profiles_by_type)
    if empty_profiles > 0:
        logging.warn(f"Skipped {empty_profiles} empty/short profiles.")
    return all_profiles_by_type


@utils.timing
def calc_statistics_per_category(
    input_data_dict: dict[ProfileType, list[SparseActivityProfile]],
    activities: list[str],
) -> ValidationSet:
    """
    Calculates statistics per category

    :param input_data_dict: input activity profiles per category
    :param activities: list of possible activities
    :return: data statistics per category
    """
    # validate each profile type individually
    input_statistics = {}
    for profile_type, profiles in input_data_dict.items():
        # calculate and store statistics for validation
        input_data = calc_input_data_statistics(profiles, activities)
        input_statistics[profile_type] = input_data
    statistics_set = ValidationSet(input_statistics, activities)
    return statistics_set


@utils.timing
def process_model_data(
    input_path: Path,
    custom_mapping_path: Path,
    person_trait_file: Path,
    validation_activities: list[str] = [],
) -> ValidationSet:
    """
    Processes the input data to produce the validation statistics.

    :param input_path: input data directory
    :param output_path: destination path for validation statistics
    :param custom_mapping_path: path of the activity mapping file
    :param person_trait_file: path of the person trait file
    :param validation_activities: optionally, the activities list of the validation
                                  data can be passed to get the same list, which
                                  makes comparison easier
    """
    # load and preprocess all input data
    full_year_profiles = load_activity_profiles_from_csv(input_path, person_trait_file)
    mapping, activities = activity_mapping.load_mapping_and_activities(
        custom_mapping_path
    )
    if validation_activities != activities:
        activities = activity_mapping.check_activity_lists(
            activities, validation_activities
        )
    input_data_dict = prepare_input_data(full_year_profiles, mapping)
    # calc and save input data statistics
    statistics_set = calc_statistics_per_category(input_data_dict, activities)
    return statistics_set


def get_similar_categories(profile_type: ProfileType) -> list[ProfileType]:
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


def all_profile_types_of_same_country(country) -> list[ProfileType]:
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
    combinations: Iterable = itertools.product(
        [country], day_types, work_statuses, sexes
    )
    combinations = [(c, s, w, d) for c, d, w, s in combinations]
    profile_types = [ProfileType.from_iterable(c) for c in combinations]
    return profile_types


def get_metric_means(
    metrics_dict: dict[ProfileType, comparison_indicators.ValidationIndicators],
    output_path: Path | None = None,
) -> pd.DataFrame:
    """
    Calculates all metric means and returns and optionally saves them as a
    single dataframe.

    :param metrics_dict: a dict containing metrics for each profile type
    :param output_path: base output directory
    :return: dataframe with all metric sums
    """
    sums = pd.DataFrame({p: m.get_metric_means() for p, m in metrics_dict.items()})
    if output_path is not None:
        pandas_utils.save_df(sums.T, "metrics", "metric_means", base_path=output_path)
    return sums.T


def metrics_dict_to_df(
    metrics: dict[ProfileType, comparison_indicators.ValidationIndicators]
) -> pd.DataFrame:
    """
    Convert the per-category metrics dict to a single dataframe
    containing all KPIs, means and per activity.

    :param metrics: the metrics dict
    :return: the KPI dataframe
    """
    dataframes = {pt: v.to_dataframe() for pt, v in metrics.items()}
    combined = pd.concat(dataframes.values(), keys=dataframes.keys())
    return combined


def validate_per_category(
    input_statistics: ValidationSet,
    validation_statistics: ValidationSet,
    output_path: Path,
) -> dict[str, dict[ProfileType, comparison_indicators.ValidationIndicators]]:
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
        validation_data = validation_statistics.statistics[profile_type]
        # calcluate and store comparison metrics
        _, metrics, scaled, normed = comparison_indicators.calc_all_indicator_variants(
            validation_data, input_data, False, profile_type, output_path
        )
        metrics_dict[profile_type] = metrics
        scaled_dict[profile_type] = scaled
        normed_dict[profile_type] = normed
    return {"default": metrics_dict, "scaled": scaled_dict, "normed": normed_dict}


def validate_similar_categories(
    input_data_dict: dict[ProfileType, ValidationStatistics],
    validation_data_dict: dict[ProfileType, ValidationStatistics],
) -> dict[ProfileType, dict[ProfileType, comparison_indicators.ValidationIndicators]]:
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
    input_data_dict: dict[ProfileType, ValidationStatistics],
    validation_data_dict: dict[ProfileType, ValidationStatistics],
) -> dict[ProfileType, dict[ProfileType, comparison_indicators.ValidationIndicators]]:
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
    for profile_type, input_data in input_data_dict.items():
        # select matching validation data
        dict_per_type = {}
        for validation_type, validation_data in validation_data_dict.items():
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


def save_file_per_metrics_per_combination(
    metrics: dict[
        ProfileType, dict[ProfileType, comparison_indicators.ValidationIndicators]
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
                df, "metrics/all_combinations", kpi.name, profile_type, output_path
            )
