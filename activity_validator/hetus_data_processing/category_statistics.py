"""
Calculates statistics for each category of households, persons or diary entries.
These can then be used for validation.
"""

from collections import Counter
from datetime import timedelta
import itertools
import logging
from typing import Iterable
import numpy as np
import pandas as pd

import activity_validator.hetus_data_processing.hetus_columns as col
from activity_validator.hetus_data_processing import utils
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import (
    ExpandedActivityProfiles,
    SparseActivityProfile,
)
from activity_validator.lpgvalidation.validation_data import (
    ValidationStatistics,
    ValidationSet,
)


def calc_value_counts(data: pd.DataFrame) -> pd.DataFrame:
    """
    Counts number of occurrences of each value, for all columns
    separately.

    :param data: input data
    :return: DataFrame containing value counts for each column
    """
    counts_per_col = {c: data[c].value_counts(normalize=True) for c in data.columns}
    for column, col_counts in counts_per_col.items():
        # keep the original column names
        col_counts.name = column
    counts = pd.concat(counts_per_col.values(), axis=1)
    counts.fillna(0, inplace=True)
    counts.sort_index(inplace=True)
    return counts


@utils.timing
def calc_activity_group_frequencies(
    activity_profiles: Iterable[SparseActivityProfile],
) -> pd.DataFrame:
    """
    Counts the numbers of occurrences of each activity type per day
    and calculates statistics on this.

    :param activity_profiles: Iterable of activty lists
    :return: activity frequency statistics
    """
    # count number of activity name occurrences for each diary entry
    counters = [
        Counter(a.name for a in p.get_merged_activity_list()) for p in activity_profiles
    ]
    # create a DataFrame with all frequencies, using 0 for activities that did
    # not occur in some diary entries
    frequencies = pd.DataFrame(counters, dtype=pd.Int64Dtype()).fillna(0)
    counts = calc_value_counts(frequencies)
    return counts


@utils.timing
def calc_activity_group_durations(
    activity_profiles: list[SparseActivityProfile],
) -> pd.DataFrame:
    """
    Calculates activity duration statistics per activity type

    :param activity_profiles: Iterable of activty lists
    :return: activty duration statistics
    """
    # determine the profile resolution (must be the same for all profiles)
    resolution = activity_profiles[0].resolution
    assert all(
        p.resolution == resolution for p in activity_profiles
    ), "Not all profiles have the same resolution"
    # get an iterable of all activities
    durations_by_activity: dict[str, list[timedelta]] = {}
    for activity_profile in activity_profiles:
        # use the merged activity list to take the day split into account and get
        # more realistic durations for sleep etc.
        activities = activity_profile.get_merged_activity_list()
        for a in activities:
            # collect durations by activity type, and convert from number of time slots
            # to Timedelta
            durations_by_activity.setdefault(a.name, []).append(a.duration * resolution)
    # turn into a DataFrame (list comprehension is necessary due to different list lengths)
    durations_series = [pd.Series(d, name=k) for k, d in durations_by_activity.items()]
    durations = pd.concat(durations_series, axis=1)
    counts = calc_value_counts(durations)
    return counts


@utils.timing
def calc_probability_profiles(
    data: pd.DataFrame, activity_types: list[str]
) -> pd.DataFrame:
    """
    Calculates activity probability profiles for the occurring activity types

    :param data: HETUS diary data
    :param activity_types: list of possible activity types
    :return: probability profiles for all activity types
    """
    probabilities = data.apply(lambda x: x.value_counts(normalize=True))
    probabilities.fillna(0.0, inplace=True)
    assert (
        np.isclose(probabilities.sum(), 1.0) | np.isclose(probabilities.sum(), 0.0)
    ).all(), "Calculation error: probabilities are not always 100 % (or 0 % for AT)"
    # add rows of zeros for any activity type that did not occur at all
    probabilities = probabilities.reindex(pd.Index(activity_types), fill_value=0)
    return probabilities


@utils.timing
def calc_statistics_per_category(
    profile_sets: list[ExpandedActivityProfiles], activity_types: list[str]
) -> ValidationSet:
    """
    Calculates all required characteristics for each diary category in the
    HETUS data separately

    :param categories: a list of expanded activity profile collections, each for
                       one category
    :param activity_types: list of possible activity types
    """
    statistics = {}
    for profile_set in profile_sets:
        # extract only the activity data
        profile_set.data = col.get_activity_data(profile_set.data)
        probabilities = calc_probability_profiles(profile_set.data, activity_types)
        # convert to sparse format to calculate more statistics
        activity_profiles = profile_set.create_sparse_profiles()
        frequencies = calc_activity_group_frequencies(activity_profiles)
        durations = calc_activity_group_durations(activity_profiles)
        vs = ValidationStatistics(
            profile_set.profile_type,
            probabilities,
            frequencies,
            durations,
            profile_set.get_profile_count(),
        )
        statistics[profile_set.profile_type] = vs
    logging.info(f"Created result files for {len(profile_sets)} categories")
    statistics_set = ValidationSet(statistics, activity_types)
    return statistics_set
