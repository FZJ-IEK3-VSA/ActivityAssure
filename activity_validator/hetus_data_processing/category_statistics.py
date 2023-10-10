"""
Calculates statistics for each category of households, persons or diary entries.
These can then be used for validation.
"""

from collections import Counter
import itertools
import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from activity_validator.hetus_data_processing import hetus_translations
from activity_validator.hetus_data_processing import hetus_constants
from activity_validator.hetus_data_processing import utils
from activity_validator.hetus_data_processing.activity_profile import (
    ActivityProfileEntry,
)


@utils.timing
def collect_activities(data: pd.DataFrame) -> Dict[Any, List[ActivityProfileEntry]]:
    """
    Finds activities in each diary entry, meaning all blocks of time slots with
    the same activity code.

    :param data: HETSU diary data
    :type data: pd.DataFrame
    :return: a dict mapping each diary entry index to the corresponding list of
             activities
    :rtype: Dict[pd.Label, List[Activity]]
    """
    activity_profiles: Dict[Any, List[ActivityProfileEntry]] = {}
    # iterate through all diary entries
    for index, row in data.iterrows():
        activity_profile = []
        start = 0
        # iterate through groups of consecutive slots with the same code
        for code, group in itertools.groupby(row):
            l = list(group)
            length = len(l)
            activity_profile.append(ActivityProfileEntry(code, start, length))
            start += length
        activity_profiles[index] = activity_profile
    return activity_profiles


def calc_activity_group_frequencies(
    category: Tuple[Any], activity_profiles: Dict[Any, List[ActivityProfileEntry]]
) -> None:
    """
    Counts the numbers of occurrences of each activity type per day and calculates
    some statistics on this.

    :param category: data category
    :type category: Tuple[Any]
    :param data: HETUS diary data
    :type data: pd.DataFrame
    """

    # count number of activity name occurrences for each diary entry
    counters = [Counter(a.name for a in p) for p in activity_profiles.values()]
    # create a DataFrame with all frequencies, using 0 for activities that did
    # not occur in some diary entries
    frequencies = pd.DataFrame(counters, dtype=pd.Int64Dtype).fillna(0)
    # save frequency statistics to file
    utils.save_df(frequencies.describe(), "activity_frequencies", "freq", category)

    # Debug: show a boxplot for the frequencies
    # from matplotlib import pyplot as plt
    # ax: plt.Axes = frequencies.boxplot(rot=90)
    # plt.subplots_adjust(top=0.95, bottom=0.5)
    # plt.show()
    # pass


@utils.timing
def calc_activity_group_durations(
    category: Tuple[Any], activity_profiles: Dict[Any, List[ActivityProfileEntry]]
) -> None:
    """Calculates activity duration statistics per activity type"""
    # get an iterable of all activities
    # TODO: calculate AT data separately (different timestep duration)
    activities = itertools.chain.from_iterable(activity_profiles.values())
    durations_by_activity: Dict[str, List[pd.Timedelta]] = {}
    for a in activities:
        # collect durations by activity type, and convert from number of time slots
        # to Timedelta
        durations_by_activity.setdefault(a.name, []).append(
            pd.Timedelta(minutes=a.duration * hetus_constants.MIN_PER_TIME_SLOT)
        )
    # turn into a DataFrame to calculate statistics
    durations_series = [pd.Series(d, name=k) for k, d in durations_by_activity.items()]
    durations = pd.concat(durations_series, axis=1)
    utils.save_df(durations.describe(), "activity_durations", "dur", category)


@utils.timing
def calc_probability_profiles(category: Tuple[Any], data: pd.DataFrame) -> None:
    """
    Calculates activity probability profiles for the occurring activity types
    """
    probabilities = data.apply(lambda x: x.value_counts(normalize=True))
    probabilities.fillna(0.0, inplace=True)
    assert (
        np.isclose(probabilities.sum(), 1.0) | np.isclose(probabilities.sum(), 0.0)
    ).all(), "Calculation error: probabilities are not always 100 % (or 0 % for AT)"
    # save probability profiles to file
    utils.save_df(probabilities, "probability_profiles", "prob", category)


@utils.timing
def calc_statistics_per_category(categories: Dict[Any, pd.DataFrame]) -> None:
    """
    Calculates all required characteristics for each diary category in the
    HETUS data separately

    :param categories: a dict containing DataFrames with HETUS diary data
    :type categories: Dict[Any, pd.DataFrame]
    """
    for cat, data in categories.items():
        # TODO when country is AT, there are only 96 timesteps
        # map to desired activity code level
        a1 = hetus_translations.aggregate_activities(data, 1)
        a1 = hetus_translations.extract_activity_names(a1)

        calc_probability_profiles(cat, a1)

        activity_profiles = collect_activities(a1)
        calc_activity_group_frequencies(cat, activity_profiles)
        calc_activity_group_durations(cat, activity_profiles)

    logging.info(f"Created result files for {len(categories)} categories")
