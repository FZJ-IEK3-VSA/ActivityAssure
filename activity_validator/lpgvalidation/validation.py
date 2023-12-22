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
    activity_profile,
    hetus_translations,
    hetus_constants,
    category_statistics,
    utils,
)

from activity_validator.hetus_data_processing.activity_profile import (
    ExpandedActivityProfiles,
    SparseActivityProfile,
    ActivityProfileEntry,
    ProfileType,
)
from activity_validator.hetus_data_processing.attributes import (
    diary_attributes,
    person_attributes,
)
from activity_validator.lpgvalidation import comparison_metrics
from activity_validator.lpgvalidation.validation_data import ValidationData


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


@utils.timing
def load_activity_profiles_from_json(path: str | Path) -> list[SparseActivityProfile]:
    """Loads the activity profiles in json format from the specified folder"""
    if not isinstance(path, Path):
        path = Path(path)
    assert Path(path).is_dir(), f"Directory does not exist: {path}"
    activity_profiles = []
    # collect all files in the directory
    for filepath in path.iterdir():
        if filepath.is_file():
            with open(filepath, encoding="utf-8") as f:
                file_content = f.read()
                activity_profile = SparseActivityProfile.from_json(file_content)  # type: ignore
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
        diary_attributes.DayType.work
        if work_sum * activity_profile.resolution >= diary_attributes.WORKTIME_THRESHOLD
        else diary_attributes.DayType.no_work
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


def load_validation_data_subdir(
    path: Path, as_timedelta: bool = False
) -> dict[ProfileType, pd.DataFrame]:
    return dict(
        activity_profile.load_df(p, as_timedelta) for p in path.iterdir() if p.is_file()
    )


@utils.timing
def load_validation_data(
    path: Path = activity_profile.VALIDATION_DATA_PATH,
) -> dict[ProfileType, ValidationData]:
    assert path.is_dir(), f"Validation data directory not found: {path}"
    subdir_path = path / "probability_profiles"
    probability_profile_data = load_validation_data_subdir(subdir_path)
    logging.info(
        f"Loaded probability profiles for {len(probability_profile_data)} profile types"
    )
    subdir_path = path / "activity_frequencies"
    activity_frequency_data = load_validation_data_subdir(subdir_path)
    logging.info(
        f"Loaded activity frequencies for {len(activity_frequency_data)} profile types"
    )
    subdir_path = path / "activity_durations"
    activity_duration_data = load_validation_data_subdir(subdir_path, True)
    logging.info(
        f"Loaded activity durations for {len(activity_duration_data)} profile types"
    )
    assert (
        probability_profile_data.keys()
        == activity_frequency_data.keys()
        == activity_duration_data.keys()
    ), "Missing data for some of the profile types"
    return {
        profile_type: ValidationData(
            profile_type,
            prob_data,
            activity_frequency_data[profile_type],
            activity_duration_data[profile_type],
        )
        for profile_type, prob_data in probability_profile_data.items()
    }


def calc_input_data_statistics(
    profiles: list[SparseActivityProfile], activity_types: list[str]
) -> ValidationData:
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
    input_data = ValidationData(
        profiles[0].profile_type, probabilities, frequencies, durations
    )
    return input_data


def check_mapping(
    activity_types: list[str], activity_types_val: list[str]
) -> list[str]:
    """
    Checks if the activity types used in the custom mapping here match those
    in the validation data set. Also returns a new activity types list, containing
    all validation activity types in the same order.
    """
    types_custom = set(activity_types)
    types_val = set(activity_types_val)
    if types_custom != types_val:
        logging.warn(
            "The applied activity mapping does not use the same set of activity types as the"
            "validation data.\n"
            f"Missing activity types: {types_val - types_custom}\n"
            f"Additional activity types: {types_custom - types_val}"
        )
        return activity_types_val + list(types_custom - types_val)
    else:
        return activity_types_val


def load_mapping(
    mapping_path: Path, output_path: Path | None = None
) -> tuple[dict[str, str], list[str]]:
    # load activity mapping
    activity_mapping = hetus_translations.load_mapping(mapping_path)
    activity_types = hetus_translations.get_activity_type_list(
        mapping_path, output_base_path=output_path
    )
    activity_types_val = hetus_translations.get_activity_type_list(save_to_output=False)
    activity_types = check_mapping(activity_types, activity_types_val)
    return activity_mapping, activity_types


def prepare_input_data(
    full_year_profiles: list[SparseActivityProfile], activity_mapping: dict[str, str]
) -> dict[ProfileType, list[SparseActivityProfile]]:
    # map and categorize each full-year profile individually
    all_profiles_by_type: dict[ProfileType, list[SparseActivityProfile]] = {}
    for full_year_profile in full_year_profiles:
        # resample profiles to validation data resolution
        full_year_profile.resample(hetus_constants.RESOLUTION)
        # translate activities to the common set of activity types
        full_year_profile.apply_activity_mapping(activity_mapping)
        # split the full year profiles into single-day profiles
        selected_day_profiles = extract_day_profiles(full_year_profile)

        # categorize single-day profiles according to country, person and day type
        profiles_by_type = group_profiles_by_type(selected_day_profiles)

        all_profiles_by_type = utils.merge_dicts(all_profiles_by_type, profiles_by_type)
    return all_profiles_by_type


@utils.timing
def calc_statistics_per_category(
    input_data_dict: dict[ProfileType, list[SparseActivityProfile]],
    output_path: Path,
    activity_types: list[str],
) -> dict[ProfileType, ValidationData]:
    """
    Calculates statistics per category

    :param input_data_dict: input activity profiles per category
    :param output_path: base path for result data
    :param activity_types: list of possible activity types
    :return: data statistics per category
    """
    # validate each profile type individually
    input_statistics = {}
    for profile_type, profiles in input_data_dict.items():
        # calculate and store statistics for validation
        input_data = calc_input_data_statistics(profiles, activity_types)
        input_data.save(output_path)
        input_statistics[profile_type] = input_data
    return input_statistics


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
    similar += [dataclasses.replace(profile_type, sex=e) for e in person_attributes.Sex]
    work_statuses = [
        person_attributes.WorkStatus.full_time,
        person_attributes.WorkStatus.part_time,
        person_attributes.WorkStatus.retired,
        person_attributes.WorkStatus.student,
        person_attributes.WorkStatus.unemployed,
    ]
    similar += [dataclasses.replace(profile_type, work_status=e) for e in work_statuses]
    day_types = [diary_attributes.DayType.work, diary_attributes.DayType.no_work]
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
    sexes = [e for e in person_attributes.Sex]
    work_statuses = [
        person_attributes.WorkStatus.full_time,
        person_attributes.WorkStatus.part_time,
        person_attributes.WorkStatus.retired,
        person_attributes.WorkStatus.student,
        person_attributes.WorkStatus.unemployed,
    ]
    day_types = [diary_attributes.DayType.work, diary_attributes.DayType.no_work]
    combinations: Iterable = itertools.product(
        [country], day_types, work_statuses, sexes
    )
    combinations = [(c, s, w, d) for c, d, w, s in combinations]
    profile_types = [ProfileType.from_iterable(c) for c in combinations]
    return profile_types


def validate_per_category(
    input_data_dict: dict[ProfileType, ValidationData],
    validation_data_dict: dict[ProfileType, ValidationData],
    output_path: Path,
) -> dict[ProfileType, comparison_metrics.ValidationMetrics]:
    """
    Compares each category of input data to the same category
    of validation data.

    :param input_data_dict: input data per profile type
    :param validation_data_dict: validation data per profile type
    :param output_path: base path for result data
    :return: calculated comparison metrics per category
    """
    # validate each profile type individually
    metrics_dict = {}
    for profile_type, input_data in input_data_dict.items():
        # select matching validation data
        validation_data = validation_data_dict[profile_type]
        # calcluate and store comparison metrics
        _, metrics, _, _ = comparison_metrics.calc_all_metric_variants(
            validation_data, input_data, True, profile_type, output_path
        )
        metrics_dict[profile_type] = metrics
    return metrics_dict


def validate_similar_categories(
    input_data_dict: dict[ProfileType, ValidationData],
    validation_data_dict: dict[ProfileType, ValidationData],
) -> dict[ProfileType, dict[ProfileType, comparison_metrics.ValidationMetrics]]:
    # validate each profile type individually
    metrics_dict = {}
    for profile_type, input_data in input_data_dict.items():
        # select matching validation data
        similar = all_profile_types_of_same_country(profile_type.country)
        dict_per_type = {}
        for similar_type in similar:
            validation_data = validation_data_dict[similar_type]
            # calcluate and store comparison metrics
            _, metrics = comparison_metrics.calc_comparison_metrics(
                validation_data, input_data
            )
            dict_per_type[similar_type] = metrics
        metrics_dict[profile_type] = dict_per_type
    return metrics_dict


def validate_all_combinations(
    input_data_dict: dict[ProfileType, ValidationData],
    validation_data_dict: dict[ProfileType, ValidationData],
) -> dict[ProfileType, dict[ProfileType, comparison_metrics.ValidationMetrics]]:
    """
    Calculates metrics for each combination of input and validation
    profile type.

    :param input_data_dict: input data statistics, by profile type
    :param validation_data_dict: validation data statistics, by profile type
    :return: nested dict, containing the metrics for each combination
    """
    # validate each profile type individually
    metrics_dict = {}
    for profile_type, input_data in input_data_dict.items():
        # select matching validation data
        dict_per_type = {}
        for validation_type, validation_data in validation_data_dict.items():
            # calcluate and store comparison metrics
            _, metrics = comparison_metrics.calc_comparison_metrics(
                validation_data, input_data
            )
            dict_per_type[validation_type] = metrics
        metrics_dict[profile_type] = dict_per_type
    return metrics_dict


def save_file_per_metrics_per_combination(
    metrics: dict[ProfileType, dict[ProfileType, comparison_metrics.ValidationMetrics]],
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
    for profile_type, metrics_per_type in metrics.items():
        kpis = dataclasses.fields(comparison_metrics.ValidationMetrics)
        for kpi in kpis:
            df = pd.DataFrame(
                {p: getattr(m, kpi.name) for p, m in metrics_per_type.items()}
            )
            activity_profile.save_df(df, "metrics", kpi.name, profile_type, output_path)
