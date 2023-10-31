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
from activity_validator.lpgvalidation.validation_data import ValidationData


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
    counters = [Counter(a.name for a in p.activities) for p in activity_profiles]
    # create a DataFrame with all frequencies, using 0 for activities that did
    # not occur in some diary entries
    frequencies = pd.DataFrame(counters, dtype=pd.Int64Dtype()).fillna(0)
    return frequencies  # .describe()

    # Debug: show a boxplot for the frequencies
    # from matplotlib import pyplot as plt
    # ax: plt.Axes = frequencies.boxplot(rot=90)
    # plt.subplots_adjust(top=0.95, bottom=0.5)
    # plt.show()
    # pass


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
    activities = itertools.chain.from_iterable(p.activities for p in activity_profiles)
    durations_by_activity: dict[str, list[timedelta]] = {}
    for a in activities:
        # collect durations by activity type, and convert from number of time slots
        # to Timedelta
        durations_by_activity.setdefault(a.name, []).append(a.duration * resolution)
    # turn into a DataFrame to calculate statistics (list comprehension is necessary
    # due to different list lengths)
    durations_series = [pd.Series(d, name=k) for k, d in durations_by_activity.items()]
    durations = pd.concat(durations_series, axis=1)
    return durations  # .describe()


@utils.timing
def calc_probability_profiles(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates activity probability profiles for the occurring activity types

    :param data: HETUS diary data
    :return: probability profiles for all activity types
    """
    probabilities = data.apply(lambda x: x.value_counts(normalize=True))
    probabilities.fillna(0.0, inplace=True)
    assert (
        np.isclose(probabilities.sum(), 1.0) | np.isclose(probabilities.sum(), 0.0)
    ).all(), "Calculation error: probabilities are not always 100 % (or 0 % for AT)"
    return probabilities


@utils.timing
def calc_statistics_per_category(profile_sets: list[ExpandedActivityProfiles]) -> None:
    """
    Calculates all required characteristics for each diary category in the
    HETUS data separately

    :param categories: a list of expanded activity profile collections, each for
                       one category
    """
    for profile_set in profile_sets:
        # extract only the activity data
        profile_set.data = profile_set.data.filter(
            like=col.Diary.MAIN_ACTIVITIES_PATTERN
        )
        probabilities = calc_probability_profiles(profile_set.data)
        # convert to sparse format to calculate more statistics
        activity_profiles = profile_set.create_sparse_profiles()
        frequencies = calc_activity_group_frequencies(activity_profiles)
        durations = calc_activity_group_durations(activity_profiles)
        vd = ValidationData(
            profile_set.profile_type, probabilities, frequencies, durations
        )
        vd.save(activity_profile.VALIDATION_DATA_PATH)

    logging.info(f"Created result files for {len(profile_sets)} categories")
