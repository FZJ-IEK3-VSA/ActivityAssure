"""Main module"""

import dataclasses
from datetime import timedelta
import functools
import json
import logging
import operator
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
from activity_validator.hetus_data_processing import activity_profile


from activity_validator.hetus_data_processing.activity_profile import (
    DEFAULT_RESOLUTION,
    ExpandedActivityProfiles,
    SparseActivityProfile,
    ActivityProfileEntry,
    ProfileType,
)
from activity_validator.hetus_data_processing.attributes import diary_attributes
from activity_validator.hetus_data_processing import category_statistics, utils
from activity_validator.hetus_data_processing.hetus_constants import PROFILE_OFFSET
from activity_validator.lpgvalidation.validation_data import ValidationData

#: activities that should be counted as work for determining work days
# TODO find a more flexible way for this
WORK_ACTIVITIES = ["EMPLOYMENT", "work"]
#: minimum working time for a day to be counted as working day
WORKTIME_THRESHOLD = timedelta(hours=3)


def load_person_characteristics(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        traits: dict[str, dict] = json.load(f)
    return {name: ProfileType.from_dict(d) for name, d in traits.items()}  # type: ignore


@utils.timing
def load_activity_profiles_from_csv(
    path: str | Path, person_trait_file: str, resolution: timedelta = DEFAULT_RESOLUTION
) -> list[SparseActivityProfile]:
    """Loads the activity profiles in csv format from the specified folder"""
    if not isinstance(path, Path):
        path = Path(path)
    assert Path(path).is_dir(), f"Directory does not exist: {path}"
    person_traits = load_person_characteristics(person_trait_file)
    activity_profiles = []
    for filepath in path.iterdir():
        if filepath.is_file():
            activity_profile = SparseActivityProfile.load_from_csv(
                filepath, person_traits, resolution
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
    return activity.name in WORK_ACTIVITIES


def determine_day_type(activity_profile: SparseActivityProfile) -> None:
    """
    Determines and sets the day type for the activity profile by checking
    the total time spent with work activities.

    :param activity_profile: the activity profile to check
    """
    durations = [a.duration for a in activity_profile.activities if is_work_activity(a)]
    # calculate total working time on this day
    if len(durations) > 0:
        work_sum = functools.reduce(
            operator.add,
            durations,
        )
    else:
        # no work at all
        work_sum = 0
    assert (
        work_sum is not None
    ), "Cannot determine day type for profiles with missing durations"
    # set the day type depending on the total working time
    day_type = (
        diary_attributes.DayType.work
        if work_sum * activity_profile.resolution >= WORKTIME_THRESHOLD
        else diary_attributes.DayType.no_work
    )
    # set the determined day type for the profile
    new_type = dataclasses.replace(activity_profile.profile_type, day_type=day_type)
    activity_profile.profile_type = new_type


def extract_day_profiles(
    activity_profile: SparseActivityProfile, day_offset: timedelta = PROFILE_OFFSET
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
        f"Grouped {len(activity_profiles)} into {len(profiles_by_type)} profile types"
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


def filter_relevant_validation_data(
    validation_data_dict: dict[ProfileType, ValidationData],
    activity_profiles: SparseActivityProfile,
):
    # TODO: if necessary, also  filter validation data that does not match the
    # ProfileType exactly, but is e.g. from another country
    pass


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
