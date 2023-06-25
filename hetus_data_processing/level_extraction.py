"""
Functions for extracting data on a specific level from a general HETUS data set
"""

import logging
import time
from typing import List, Tuple, Type
import numpy as np
import pandas as pd

import hetus_columns as col
import filter


def limit_to_columns_by_level(
    data: pd.DataFrame, level: Type[col.HetusLevel]
) -> pd.DataFrame:
    """
    Resets the index and removes all index and content columns that are
    below the specified level, but keeps all rows (meaning there can be
    multiple rows per group).
    E.g., when choosing the household level, only keeps colums that
    contain information on household level, removing information
    on person and diary level.

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :param level: the desired level
    :type level: Type[col.HetusLevel]
    :return: data set containing only columns that are relevant on the
             desired level
    :rtype: pd.DataFrame
    """
    # remove index and content columns below the specified level
    limited_data = data.reset_index().set_index(level.KEY)[level.CONTENT]
    return limited_data


def group_rows_by_level(
    data: pd.DataFrame, level: Type[col.HetusLevel], agg_mode: bool = False
) -> pd.DataFrame:
    """
    Groups the data by the specified level.
    E.g., when choosing the household level, this creates a dataframe
    with one entry per household. The aggregation method can be chosen
    through the agg_mode parameter.

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :param level: the desired level
    :type level: Type[col.HetusLevel]
    :param agg_mode: if True, uses the mode (most frequent value) for all
                        group level data, else the first value,
                        defaults to False
    :type agg_mode: bool, optional
    :return: group-level data set
    :rtype: pd.DataFrame
    """
    start = time.time()
    # select relevant columns and set country and HID as index
    grouped = data.groupby(level.KEY)
    if agg_mode:
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
    Returns only entries on the desired level without inconsistent data.
    E.g., when choosing the household level, removes entries that specify
    contradicting household sizes for the same household.

    :param data: DataFrame with inconsistent household data
    :type data: pd.DataFrame
    :param level: the desired level
    :type level: Type[col.HetusLevel]
    :return: Index containing only consistent households
    :rtype: pd.Index
    """
    # only keep columns on the specified level
    data = data[level.CONTENT]
    # get numbers of different values per group for each column
    num_values_per_group = data.groupby(level=level.KEY).nunique(dropna=False)  # type: ignore
    inconsistent_columns_per_group = (num_values_per_group != 1).sum(axis=1)  # type: ignore
    
    # create an index that contains all consistent groups
    consistent_groups = inconsistent_columns_per_group[
        inconsistent_columns_per_group == 0
    ].index
    logging.info(
        f"Out of {len(num_values_per_group)} groups on {level.NAME} level, "
        f"{len(num_values_per_group) - len(consistent_groups)} are inconsistent."
    )
    return consistent_groups


def get_inconsistent_columns(data: pd.DataFrame, level: Type[col.HetusLevel]) -> pd.Series:
    """
    Returns the number of inconsistencies per column on the specified level. Removes
    columns without inconsistencies.

    :param data: general HETUS data
    :type data: pd.DataFrame
    :param level: the level to check for inconsistencies
    :type level: Type[col.HetusLevel]
    :return: a Series containing the number of groups with inconsistent per column
    :rtype: pd.Series
    """
    data = data[level.CONTENT]
    # get numbers of different values per household for each column
    num_values_per_group = data.groupby(level=level.KEY).nunique()  # type: ignore
    inconsistencies_per_col = (num_values_per_group != 1).sum()  # type: ignore
    return inconsistencies_per_col[inconsistencies_per_col > 0]



def get_usable_data_by_level(
    data: pd.DataFrame, level: Type[col.HetusLevel]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts the usable data on the specified level. Exlcudes inconsistent entries.

    :param data: general HETUS data
    :type data: pd.DataFrame
    :param level: the level on which the data will be extracted
    :type level: Type[col.HetusLevel]
    :return: filtered full data set and level-specific data set
    :rtype: Tuple[pd.DataFrame, pd.DataFrame]
    """
    data = filter.filter_by_index(data, get_consistent_groups(data, level))
    persondata = limit_to_columns_by_level(data, level)
    persondata = group_rows_by_level(persondata, level, False)
    return data, persondata


# --- Level Specific Functions ---


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
    :return: filtered full data set and household data set
    :rtype: Tuple[pd.DataFrame, pd.DataFrame]
    """
    data = filter.filter_by_index(data, get_complete_households(data))
    return get_usable_data_by_level(data, col.HH)


def get_usable_person_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extracts the data on person-level from the data set.
    Removes inconsisten entries.

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :return: filtered full data set and person data set
    :rtype: Tuple[pd.DataFrame, pd.DataFrame]
    """
    return get_usable_data_by_level(data, col.Person)
