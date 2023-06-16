"""
Functions for extracting household-level data from a general HETUS data set
"""

import logging
import time
from typing import List, Tuple, Type
import numpy as np
import pandas as pd

import hetus_columns as col
import filter


def limit_to_columns_by_level(data: pd.DataFrame, level: Type[col.HetusLevel]) -> pd.DataFrame:
    """
    Resets the index and removes all index and content columns that are
    below the specified level, but keeps all rows (meaning there can be
    multiple rows per group).

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :return: data set containing only columns that are relevant on the
             desired level
    :rtype: pd.DataFrame
    """
    # remove index and content columns below the specified level
    hhdata = data.reset_index().set_index(level.KEY)[level.CONTENT]
    return hhdata


def group_rows_by_level(
    data: pd.DataFrame, level: Type[col.HetusLevel], select_mode: bool = False
) -> pd.DataFrame:
    """
    Extracts the household-level data from the data set. Produces a
    dataframe that uses year, country and HID as index.

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :param select_mode: if True, uses the most frequent value for all
                        household level data, else the first value,
                        defaults to False
    :type select_mode: bool, optional
    :return: household-level data set
    :rtype: pd.DataFrame
    """
    start = time.time()
    # select household level columns and set country and HID as index
    grouped = data.groupby(level.KEY)
    if select_mode:
        # select the most frequent value out of each group; this is better if there are different values per
        # group; this method is much slower than the one below
        grouped_data = grouped.agg(
            lambda x: (x.value_counts().index[0]) if len(x) > 0 else np.nan
        )
    else:
        # assume all values in the group are equal and simply select the first one
        grouped_data = grouped.first()
    logging.info(
        f"Extracted {len(grouped_data)} groups on {level.NAME} level "
        f"from {len(data)} entries in {time.time() - start:.1f} s"
    )
    return grouped_data


def get_consistent_groups(data: pd.DataFrame, level: Type[col.HetusLevel]) -> pd.Index:
    """
    Returns households without inconsistent household-level data, e.g., where multiple
    diary entries for the same household specify different household sizes.

    :param data: DataFrame with inconsistent household data
    :type data: pd.DataFrame
    :return: Index containing only consistent households
    :rtype: pd.Index
    """
    # only keep columns on household level
    data = data[level.CONTENT]
    # get numbers of different values per household for each column
    num_values_per_hh = data.groupby(level=level.KEY).nunique()  # type: ignore
    inconsistent_columns_per_hh = (num_values_per_hh != 1).sum(axis=1)  # type: ignore
    # create an index that contains all consistent households
    consistent_households = inconsistent_columns_per_hh[
        inconsistent_columns_per_hh == 0
    ].index
    logging.info(
        f"Out of {len(num_values_per_hh)} groups on {level.NAME} level, "
        f"{len(num_values_per_hh) - len(consistent_households)} are inconsistent."
    )
    return consistent_households


def get_complete_households(data: pd.DataFrame) -> pd.Index:
    """
    Returns a new dataframe, containing only complete households, meaning
    households where each inhabitant took part in the survey.

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :return: complete households
    :rtype: pd.DataFrame
    """
    data = data.reset_index().set_index(col.HH.KEY)
    # group by household
    hhsizes = data[col.HH.SIZE].groupby(level=col.HH.KEY).first()  # type: ignore
    # get the number of survey participants per household
    participants_per_hh = data[col.Person.ID].groupby(level=col.HH.KEY).nunique()  # type: ignore
    merged = pd.concat([hhsizes, participants_per_hh], axis=1)
    # get households where the size matches the number of participants
    complete = merged[merged[col.Person.ID] == merged[col.HH.SIZE]].index
    logging.info(
        f"Out of {len(merged)} households, {len(merged) - len(complete)} are incomplete."
    )
    return complete


def get_usable_household_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts the data on household-level from the specified data set.
    Removes entries with incomplete or inconsistent data.

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :return: cleaned full data set and household data set
    :rtype: Tuple[pd.DataFrame, pd.DataFrame]
    """
    level = col.HH
    data = filter.filter_by_index(data, get_complete_households(data))
    data = filter.filter_by_index(data, get_consistent_groups(data, level))
    hhdata = limit_to_columns_by_level(data, level)
    hhdata = group_rows_by_level(hhdata, level, False)
    return data, hhdata

def get_usable_person_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    level = col.Person
    data = filter.filter_by_index(data, get_consistent_groups(data, level))
    persondata = limit_to_columns_by_level(data, level)
    persondata = group_rows_by_level(persondata, level, False)
    return data, persondata
