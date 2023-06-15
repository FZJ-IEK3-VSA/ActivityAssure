"""
Functions for extracting household-level data from a general HETUS data set
"""

import logging
import time
import numpy as np
import pandas as pd

from utils import HetusColumns


def extract_household_data(
    data: pd.DataFrame, select_mode: bool = False
) -> pd.DataFrame:
    """
    Extracts the household-level data from the data set. Produces a
    dataframe that uses country and HID as index.

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
    grouped = data.groupby(HetusColumns.HH.KEY)
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
        f"Extracted {len(grouped_data)} household entries from {len(data)} entries in {time.time() - start:.1f} s"
    )
    return grouped_data


def remove_inconsistent_households(data: pd.DataFrame) -> pd.DataFrame:
    """
    Removes entries with inconsistent household-level data

    :param data: DataFrame with inconsistent household data
    :type data: pd.DataFrame
    :return: DataFrame containing only consistent households
    :rtype: pd.DataFrame
    """
    assert (
        isinstance(data.index, pd.MultiIndex)
        and list(data.index.names) == HetusColumns.HH.KEY
    ), f"Data has to have the following index: {HetusColumns.HH.KEY}"
    # only keep columns on household level
    hhdata = data[HetusColumns.HH.CONTENT_COLUMNS]
    # get numbers of different values per household for each column
    num_values_per_hh = hhdata.groupby(level=HetusColumns.HH.KEY).nunique()  # type: ignore
    inconsistent_columns_per_hh = (num_values_per_hh != 1).sum(axis=1)  # type: ignore
    # create an index that contains all inconsistent households
    inconsistent_households = inconsistent_columns_per_hh[
        inconsistent_columns_per_hh > 0
    ].index
    entries_to_remove = hhdata.index.isin(inconsistent_households)
    consistent_data = hhdata[~entries_to_remove]
    logging.info(f"Removed {len(entries_to_remove)} inconsistent households")
    return consistent_data


def detect_household_level_columns(data: pd.DataFrame) -> pd.Index:
    """
    Analysis-function for checking which columns are actually on household
    level and thus always have the same value for all entries belonging to 
    the same household.
    Can be used to check for which hosehold level columns the data
    is acutally consistent acrossall entries.

    :param data: hetus data
    :type data: pd.DataFrame
    :return: index containing all columns on household level
    :rtype: pd.Index
    """
    # count how many different values for each column there are within a single household
    num_values_per_hh = data.groupby(HetusColumns.HH.KEY).nunique()
    # get the columns that always have the same value within a single household
    hh_data = (num_values_per_hh == 1).all(axis=0)  # type: ignore
    hh_data = hh_data.loc[hh_data == True]
    return hh_data.index


def show_inconsistent_households(data: pd.DataFrame):
    """
    Analysis-function for showing inconsistencies in the data regarding households,
    i.e. where several entries belonging to the same household contain different 
    values for household-level columns.

    :param data: the data to check
    :type data: pd.DataFrame
    """
    hhdata = data[HetusColumns.HH.COLUMNS]
    num_values_per_hh = hhdata.groupby(HetusColumns.HH.KEY).nunique()
    inconsistent_hh_per_column = (num_values_per_hh != 1).sum(axis=0)  # type: ignore
    print(f"Inconsistencies per column: \n{inconsistent_hh_per_column}")
    inconsistent_columns_per_hh = (num_values_per_hh != 1).sum(axis=1)  # type: ignore
    inconsistent_households = inconsistent_columns_per_hh[
        inconsistent_columns_per_hh > 0
    ]
    print(
        f"Households with inconsistencies: {len(inconsistent_households)} of {len(data)}"
        f"\n{inconsistent_households}"
    )
    return inconsistent_hh_per_column, inconsistent_households
    


def get_household_data(data: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts the data on household-level from the specified data set.
    Removes entries with inconsistent data.

    :param data: general HETUS data set
    :type data: pd.DataFrame
    :return: data set on households
    :rtype: pd.DataFrame
    """
    data = data[HetusColumns.HH.COLUMNS].set_index(HetusColumns.HH.KEY)
    data = remove_inconsistent_households(data)
    hhdata = extract_household_data(data, False)
    logging.info(f"Extracted data on {len(hhdata)} households.")
    return hhdata
