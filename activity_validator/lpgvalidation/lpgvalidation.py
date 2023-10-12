"""Main module"""

from datetime import time, timedelta
import functools
import logging
import operator
import os
import pathlib
from typing import Iterable, List

import pandas as pd


from activity_validator.hetus_data_processing.activity_profile import (
    ActivityProfile,
    ActivityProfileEntry,
    ActivityProfileEntryTime,
    ProfileType,
)
from activity_validator.hetus_data_processing.attributes import diary_attributes
from activity_validator.hetus_data_processing import category_statistics, utils
from activity_validator.lpgvalidation.validation_data import ValidationData

#: activities that should be counted as work for determining work days
WORK_ACTIVITIES = ["EMPLOYMENT", "work as teacher"]
#: minimum working time for a day to be counted as working day
WORKTIME_THRESHOLD = timedelta(hours=3)

#: default time for splitting
DAY_CHANGE_TIME = time(4)


@utils.timing
def load_activity_profiles(dir: str) -> List[ActivityProfile]:
    """Loads the activity profiles in json format from the specified folder"""
    # TODO: alternatively load from csvs (compact or expanded format)
    activity_profiles = []
    for filename in os.listdir(dir):
        path = os.path.join(dir, filename)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                file_content = f.read()
                activity_profile = ActivityProfile.from_json(file_content)  # type: ignore
                activity_profiles.append(activity_profile)
    logging.info(f"Loaded {len(activity_profiles)} activity profiles")
    return activity_profiles


def filter_complete_day_profiles(
    activity_profiles: Iterable[ActivityProfile],
) -> list[ActivityProfile]:
    """
    Get only all complete day profiles, which are actually 24 h long

    :param activity_profiles: the profiles to filter
    :type activity_profiles: Iterable[ActivityProfile]
    :return: the profiles that match the condition
    :rtype: list[ActivityProfile]
    """
    return [a for a in activity_profiles if a.total_duration() == timedelta(days=1)]


def filter_min_activity_count(
    activity_profiles: Iterable[ActivityProfile],
    min_activities: int = 1,
) -> list[ActivityProfile]:
    """
    Get only all day profiles with a minimum number of activities

    :param activity_profiles: the profiles to filter
    :param min_activities: the minimum number of activities, defaults to 1
    :return: the profiles that match the condition
    """
    return [a for a in activity_profiles if len(a.activities) >= min_activities]


def is_work_activity(activity: ActivityProfileEntryTime | ActivityProfileEntry) -> bool:
    """
    Checks if an activity is a work activity.

    :param activity: the activity to check
    :type activity: ActivityProfileEntryTime | ActivityProfileEntry
    :return: True if the activity is a work activity, else False
    :rtype: bool
    """
    return activity.name in WORK_ACTIVITIES


def determine_day_type(activity_profile: ActivityProfile) -> None:
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
        # TODO adapt for time step profiles
        work_sum = timedelta()
    assert (
        work_sum is not None
    ), "Cannot determine day type for profiles with missing durations"
    # set the day type depending on the total working time
    # TODO: adapt for time step profiles
    day_type = (
        diary_attributes.DayType.work
        if work_sum >= WORKTIME_THRESHOLD
        else diary_attributes.DayType.no_work
    )
    activity_profile.profile_type.day_type = day_type


def extract_day_profiles(
    activity_profile: ActivityProfile, day_change_time: time = DAY_CHANGE_TIME
) -> list[ActivityProfile]:
    day_profiles = activity_profile.split_day_profiles(day_change_time)
    # this also removes profiles with missing activity durations
    day_profiles = filter_complete_day_profiles(day_profiles)
    # filter days with only a single activity (e.g., vacation)
    day_profiles = filter_min_activity_count(day_profiles, 1)
    logging.info(f"Extracted {len(day_profiles)} single-day activity profiles")
    return day_profiles


def group_profiles_by_type(
    activity_profiles: list[ActivityProfile],
) -> dict[ProfileType, list[ActivityProfile]]:
    """
    Determines day type for each day profile and groups
    the profiles by their overall type.

    :param activity_profiles: the activity profiles to group
    :type activity_profiles: list[ActivityProfile]
    :return: a dict mapping each profile type to the respective
             profiles
    :rtype: dict[ProfileType, list[ActivityProfile]]
    """
    profiles_by_type: dict[ProfileType, list[ActivityProfile]] = {}
    for profile in activity_profiles:
        # set day type property
        determine_day_type(profile)
        profiles_by_type.setdefault(profile.profile_type, []).append(profile)
    logging.info(
        f"Grouped {len(activity_profiles)} into {len(profiles_by_type)} profile types"
    )
    return profiles_by_type


def load_validation_data_subdir(path: pathlib.Path) -> dict[tuple, pd.DataFrame]:
    return dict(utils.load_df(p) for p in path.iterdir() if p.is_file())


def load_validation_data(
    path: pathlib.Path = utils.VALIDATION_DATA_PATH,
) -> dict[ProfileType, ValidationData]:
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
    activity_duration_data = load_validation_data_subdir(subdir_path)
    logging.info(
        f"Loaded activity durations for {len(activity_duration_data)} profile types"
    )
    assert (
        probability_profile_data.keys()
        == activity_frequency_data.keys()
        == activity_duration_data.keys()
    ), "Missing data for some of the profile types"
    # TODO: convert profile_type from tuple to class ProfileType
    return {
        (p := ProfileType.from_strs(category)): ValidationData(
            p,
            prob_data,
            activity_frequency_data[category],
            activity_duration_data[category],
        )
        for category, prob_data in probability_profile_data.items()
    }


def filter_relevant_validation_data(
    validation_data_dict: dict[ProfileType, ValidationData],
    activity_profiles: ActivityProfile,
):
    # TODO: if necessary, also  filter validation data that does not match the
    # ProfileType exactly, but is e.g. from another country
    pass


def compare_to_validation_data(
    profiles: list[ActivityProfile], validation_data: ValidationData
):
    # TODO: calculator class, die die calc-Methoden erhählt und den Result path speichert
    category_statistics.calc_activity_group_frequencies(
        profiles[0].profile_type.to_tuple(), (p.activities for p in profiles)
    )
