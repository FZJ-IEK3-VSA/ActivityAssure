"""
Functions for preprocessing and grouping activity profiles
according to their category.
"""

import dataclasses
import logging
from activity_validator import categorization_attributes, utils
from activity_validator.activity_profile import (
    ActivityProfileEntry,
    SparseActivityProfile,
)


from datetime import timedelta
from typing import Iterable
from activity_validator.hetus_data_processing import hetus_constants

from activity_validator.hetus_data_processing.attributes import diary_attributes
from activity_validator.profile_category import ProfileCategory


def filter_complete_day_profiles(
    activity_profiles: Iterable[SparseActivityProfile],
) -> list[SparseActivityProfile]:
    """
    Get only all complete day profiles, which are actually 24h long

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


def extract_day_profiles(
    activity_profile: SparseActivityProfile,
    day_offset: timedelta = hetus_constants.PROFILE_OFFSET,
) -> list[SparseActivityProfile]:
    """
    Splits a long SparseActivityProfile into multiple single-day
    SparseActivityProfiles. Filters the resulting profiles to get
    only full 24h profiles with a minimum of 2 activities.

    :param activity_profile: the long activity profile to split
    :param day_offset: the time to use as change of day, as offset
                       from 00:00; defaults to 04:00 (from HETUS)
    :return: the list of single-day profiles
    """
    day_profiles = activity_profile.split_into_day_profiles(day_offset)
    # this also removes profiles with missing activity durations
    day_profiles = filter_complete_day_profiles(day_profiles)
    # remove days with only a single activity (e.g., vacation)
    day_profiles = filter_min_activity_count(day_profiles, 2)
    logging.info(f"Extracted {len(day_profiles)} single-day activity profiles")
    return day_profiles


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


def group_profiles_by_type(
    activity_profiles: list[SparseActivityProfile],
) -> dict[ProfileCategory, list[SparseActivityProfile]]:
    """
    Determines day type for each day profile and groups
    the profiles by their overall type.

    :param activity_profiles: the activity profiles to group
    :return: a dict mapping each profile type to the respective
             profiles
    """
    profiles_by_type: dict[ProfileCategory, list[SparseActivityProfile]] = {}
    for profile in activity_profiles:
        # set day type property
        determine_day_type(profile)
        profiles_by_type.setdefault(profile.profile_type, []).append(profile)
    logging.info(
        f"Grouped {len(activity_profiles)} profiles into {len(profiles_by_type)} categories"
    )
    return profiles_by_type


def prepare_input_data(
    full_year_profiles: list[SparseActivityProfile], activity_mapping: dict[str, str]
) -> dict[ProfileCategory, list[SparseActivityProfile]]:
    # map and categorize each full-year profile individually
    all_profiles_by_type: dict[ProfileCategory, list[SparseActivityProfile]] = {}
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
