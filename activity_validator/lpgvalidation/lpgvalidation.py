"""Main module"""

from datetime import datetime, time, timedelta
import os
from typing import Iterable, List


from activity_validator.hetus_data_processing.activity_profile import (
    ActivityProfile,
    Traits,
)

#: activities that should be counted as work for determining work days
WORK_ACTIVITIES = ["1"]

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
    return [a for a in activity_profiles if a.total_duration() == timedelta(days=1)]


def filter_min_activity_count(
    activity_profiles: Iterable[ActivityProfile],
    min_activities: int = 1,
) -> list[ActivityProfile]:
    return [a for a in activity_profiles if len(a.activities) >= min_activities]


def categorize_day_profile(
    activity_profiles: ActivityProfile,
) -> Traits:
    pass  # TODO


def extract_day_profiles(
    activity_profile: ActivityProfile, day_change_time: time = DAY_CHANGE_TIME
) -> dict[Traits, list[ActivityProfile]]:
    day_profiles = activity_profile.split_day_profiles(day_change_time)
    day_profiles = filter_complete_day_profiles(day_profiles)
    # filter days with only a single activity (e.g., vacation)
    day_profiles = filter_min_activity_count(day_profiles, 1)


def filter_relevant_validation_data():
    pass


def compare_to_validation_data(activity_profile):
    pass
