"""
Calculates statistics for each category of households, persons or diary entries.
These can then be used for validation.
"""

from collections import Counter
import itertools
import logging
from dataclasses import dataclass
import os
from typing import Any, Dict, List, Optional, Tuple

import hetus_columns as col
import hetus_translations
import numpy as np
import pandas as pd
import utils


@dataclass
class Activity:
    """
    Simple class for storing an activity, i.e. a consecutive block
    of diary time slots with the same code.
    """

    #: activity name or code
    name: str
    #: 0-based index of activity start
    start: int
    #: lenght of activity in time slots
    lenght: int


@utils.timing
def collect_activities(data: pd.DataFrame) -> Dict[Any, List[Activity]]:
    """
    Finds activities in each diary entry, meaning all blocks of time slots with
    the same activity code.

    :param data: HETSU diary data
    :type data: pd.DataFrame
    :return: a dict mapping each diary entry index to the corresponding list of
             activities
    :rtype: Dict[pd.Label, List[Activity]]
    """
    activity_profiles: Dict[Any, List[Activity]] = {}
    # iterate through all diary entries
    for index, row in data.iterrows():
        activity_profile = []
        start = 0
        # iterate through groups of consecutive slots with the same code
        for code, group in itertools.groupby(row):
            l = list(group)
            length = len(l)
            activity_profile.append(Activity(code, start, length))
            start += length
        activity_profiles[index] = activity_profile
    return activity_profiles


def calc_activity_group_frequencies(category: Tuple[Any], data: pd.DataFrame) -> None:
    """
    Counts the numbers of occurrences of each activity type per day and calculates
    some statistics on this.

    :param category: data category
    :type category: Tuple[Any]
    :param data: HETUS diary data
    :type data: pd.DataFrame
    """
    activity_profiles = collect_activities(data)

    # count number of activity name occurrences for each diary entry
    counters = [Counter(a.name for a in p) for p in activity_profiles.values()]
    # create a DataFrame with all frequencies, using 0 for activities that did
    # not occur in some diary entries
    frequencies = pd.DataFrame(counters, dtype=pd.Int64Dtype).fillna(0)
    # save frequency statistics to file
    utils.save_file(frequencies.describe(), "activity_frequencies", "freq", category)


def calc_activity_group_durations(category: Tuple[Any], data: pd.DataFrame) -> None:
    pass


def calc_probability_profiles(category: Tuple[Any], data: pd.DataFrame) -> None:
    probabilities = data.apply(lambda x: x.value_counts(normalize=True))
    probabilities.fillna(0.0, inplace=True)
    assert (
        np.isclose(probabilities.sum(), 1.0) | np.isclose(probabilities.sum(), 0.0)
    ).all(), "Calculation error: probabilities are not always 100 % (or 0 % for AT)"

    # save probability profiles to file
    utils.save_file(probabilities, "probability_profiles", "prob", category)


def calc_statistics_per_category(categories: Dict[Any, pd.DataFrame]) -> None:
    for cat, data in categories.items():
        # TODO when country is AT, there are only 96 timesteps
        # map to desired activity code level
        a1 = hetus_translations.aggregate_activities(data, 1)
        a1 = hetus_translations.extract_activity_names(a1)

        calc_probability_profiles(cat, a1)
        calc_activity_group_frequencies(cat, a1)

    logging.info(f"Created result files for {len(categories)} categories")
