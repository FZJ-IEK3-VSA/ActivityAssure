"""
Calculates statistics for each category of households, persons or diary entries.
These can then be used for validation.
"""

from collections import Counter
from datetime import timedelta
import logging
from typing import Iterable
import numpy as np
import pandas as pd

from activity_validator import utils
from activity_validator.activity_profile import (
    ExpandedActivityProfiles,
    SparseActivityProfile,
)
from activity_validator.validation_statistics import (
    ValidationStatistics,
    ValidationSet,
)


def calc_value_distributions(data: pd.DataFrame) -> pd.DataFrame:
    """
    Counts number of occurrences of each value, for all columns
    separately.

    :param data: input data
    :return: DataFrame containing value distributions for each column
    """
    counts_per_col = {c: data[c].value_counts(normalize=True) for c in data.columns}
    for column, col_counts in counts_per_col.items():
        # keep the original column names
        col_counts.name = column
    counts = pd.concat(counts_per_col.values(), axis=1)
    counts.fillna(0, inplace=True)
    counts.sort_index(inplace=True)
    return counts


def calc_weighed_value_distributions(
    data: pd.DataFrame, weights: pd.DataFrame | pd.Series | None = None
) -> pd.DataFrame:
    """
    Counts number of occurrences of each value, for all columns
    separately, optionally taking into account individual weights per row
    or per value.

    :param data: input data
    :param weights: weight for the data; can be a Series (on weight per data row)
                    or a DataFrame (one weight per data element), or None to apply
                    no weights
    :return: DataFrame containing value distributions for each column
    """
    if weights is None or weights.isna().all(axis=None):
        # no weights - simply count occurrences of values per column
        probabilities = data.apply(lambda x: x.value_counts(normalize=True))
    else:
        # take the weights into account
        if isinstance(weights, pd.Series):
            # the same weight for each row of data
            assert data.index.equals(weights.index), "Weights don't match data"

            def func(c):
                return weights.groupby(c).sum()
        else:
            # individual weight for each element of data
            assert data.shape == weights.shape, "Weights don't match data"

            def func(c):
                return weights[c.name].groupby(c).sum()

        # get sum of weights per unique value, per column
        counts = data.apply(func)
        # convert to probabilities
        probabilities = counts / counts.sum()
    # remove NA and sort by values
    probabilities.fillna(0, inplace=True)
    probabilities.sort_index(inplace=True)
    return probabilities


@utils.timing
def calc_activity_group_frequencies(
    activity_profiles: Iterable[SparseActivityProfile],
) -> pd.DataFrame:
    """
    Calculates how often each activity is carried out each day.

    :param activity_profiles: Iterable of activty lists
    :return: activity frequency value counts
    """
    # count number of activity name occurrences for each diary entry
    counters = [
        Counter(a.name for a in p.get_merged_activity_list()) for p in activity_profiles
    ]
    # create a DataFrame with all frequencies, using 0 for activities that did
    # not occur in some diary entries
    frequencies = pd.DataFrame(counters, dtype=pd.Int64Dtype()).fillna(0)
    # collect the weights; each weight belongs to the corresponding row in frequencies
    weights = pd.Series((p.weight for p in activity_profiles))
    counts = calc_weighed_value_distributions(frequencies, weights)
    return counts


@utils.timing
def calc_activity_group_durations(
    activity_profiles: list[SparseActivityProfile],
) -> pd.DataFrame:
    """
    Calculates activity durations per activity type.

    :param activity_profiles: Iterable of activty lists
    :return: activty duration value counts
    """
    # determine the profile resolution (must be the same for all profiles)
    resolution = activity_profiles[0].resolution
    assert all(
        p.resolution == resolution for p in activity_profiles
    ), "Not all profiles have the same resolution"
    # collect the durations of all activities, and the corresponding profile weights
    durations_by_activity: dict[str, list[timedelta]] = {}
    weight_per_duration: dict[str, list[float | None]] = {}
    for activity_profile in activity_profiles:
        # use the merged activity list to take the day split into account and get
        # more realistic durations for sleep etc.
        activities = activity_profile.get_merged_activity_list()
        for a in activities:
            # collect durations by activity type, and convert from number of time slots
            # to timedelta
            durations_by_activity.setdefault(a.name, []).append(a.duration * resolution)
            weight_per_duration.setdefault(a.name, []).append(activity_profile.weight)
    # turn into a DataFrame (list comprehension is necessary due to different list lengths)
    durations_series = [pd.Series(d, name=k) for k, d in durations_by_activity.items()]
    weights_series = [pd.Series(d, name=k) for k, d in weight_per_duration.items()]
    # create a dataframe containing all durations, and one in the same shape containing the
    # corresponding weight for each element in the durations dataframe
    durations = pd.concat(durations_series, axis=1)
    weights = pd.concat(weights_series, axis=1)
    counts = calc_weighed_value_distributions(durations, weights)
    return counts


@utils.timing
def calc_probability_profiles(
    data: pd.DataFrame, activity_types: list[str], weights: pd.Series | None = None
) -> pd.DataFrame:
    """
    Calculates the daily activity probability profile for each activity type.

    :param data: HETUS diary data
    :param activity_types: list of possible activity types
    :return: probability profiles for all activity types
    """
    probabilities = calc_weighed_value_distributions(data, weights)
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
    HETUS data separately.

    :param categories: a list of expanded activity profile collections, each for
                       one category
    :param activity_types: list of possible activity types
    """
    statistics = {}
    for profile_set in profile_sets:
        probabilities = calc_probability_profiles(
            profile_set.data, activity_types, profile_set.weights
        )
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
