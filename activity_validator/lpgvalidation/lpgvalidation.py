"""Main module"""

from datetime import datetime, time, timedelta
import functools
import operator
import os
from typing import Iterable, List


from activity_validator.hetus_data_processing.activity_profile import (
    ActivityProfile,
    Traits,
)
from activity_validator.hetus_data_processing.attributes import diary_attributes

#: activities that should be counted as work for determining work days
WORK_ACTIVITIES = ["1"]
#: minimum working time for a day to be counted as working day
WORKTIME_THRESHOLD = timedelta(hours=3)

#: default time for splitting
DAY_CHANGE_TIME = time(4)


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
    :type activity_profiles: Iterable[ActivityProfile]
    :param min_activities: the minimum number of activities, defaults to 1
    :type min_activities: int, optional
    :return: the profiles that match the condition
    :rtype: list[ActivityProfile]
    """
    return [a for a in activity_profiles if len(a.activities) >= min_activities]


def determine_day_type(activity_profile: ActivityProfile) -> None:
    """
    Determines and sets the 'day type' trait for the activity profile by checking
    the total time spent with work activities.

    :param activity_profile: the activity profile to check
    :type activity_profile: ActivityProfile
    """
    # calculate total working time on this day
    work_sum = functools.reduce(
        operator.add,
        (a.duration for a in activity_profile.activities if a.name in WORK_ACTIVITIES),
    )
    assert (
        work_sum is not None
    ), "Cannot determine day type for profiles with missing durations"
    # TODO: adapt/extend for time step profiles
    day_type = (
        diary_attributes.DayType.work
        if work_sum >= WORKTIME_THRESHOLD
        else diary_attributes.DayType.no_work
    )
    activity_profile.traits.add_trait(diary_attributes.Categories.day_type, day_type)


def categorize_day_profile(activity_profile: ActivityProfile) -> None:
    determine_day_type(activity_profile)


def extract_day_profiles(
    activity_profile: ActivityProfile, day_change_time: time = DAY_CHANGE_TIME
) -> list[ActivityProfile]:
    day_profiles = activity_profile.split_day_profiles(day_change_time)
    # this also removes profiles with missing activity durations
    day_profiles = filter_complete_day_profiles(day_profiles)
    # filter days with only a single activity (e.g., vacation)
    day_profiles = filter_min_activity_count(day_profiles, 1)
    for profile in day_profiles:
        determine_day_type(profile)
    return day_profiles


def filter_relevant_validation_data():
    pass


def compare_to_validation_data(activity_profile):
    pass
