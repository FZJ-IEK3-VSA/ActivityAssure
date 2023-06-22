"""
Functions for filtering HETUS data based on various criteria
"""


import functools
from typing import Dict, List, Union
import pandas as pd

import hetus_columns as col
from utils import DayType, timing

#TODO: for separating dataframes instead of just dropping unmatching columns, groupby can be used

@timing
def filter_discrete(data: pd.DataFrame, column: str, allowed_values: List[int]) -> pd.DataFrame:
    return data[data[column].isin(allowed_values)]

def filter_by_weekday(data: pd.DataFrame, day_types: List[DayType]) -> pd.DataFrame:
    return filter_discrete(data, col.Diary.WEEKDAY, day_types)


def filter_by_month(data: pd.DataFrame, months: List[int]) -> pd.DataFrame:
    return filter_discrete(data, col.Diary.MONTH, months)


@timing
def filter_combined(data: pd.DataFrame, conditions: Dict[str, List[int]]) -> pd.DataFrame:
    masks = [data[k].isin(v) for k, v in conditions.items()]
    combined_mask = functools.reduce(lambda m1, m2: m1 & m2, masks)
    return data[combined_mask]


def filter_stats(data: pd.DataFrame, conditions: Dict[str, List[int]], name: str = None) -> pd.DataFrame:
    """Calls filter_combined and prints some filter statistics"""
    result = filter_combined(data, conditions)
    print(f"Applied filter: {name or conditions}")
    print(f"Matching: {len(result)} / {len(data)} ({100 * len(result) / len(data):.1f} %)")
    return result


def filter_by_index(
    data: pd.DataFrame, index: pd.Index, keep_entries: bool = True
) -> pd.DataFrame:
    """
    Filters a data set using a separate index. The keep_entries parameter determines which part of
    the data is kept, either the part that is contained in the index, or the rest.

    :param data: the data to filter
    :type data: pd.DataFrame
    :param index: the index used as filter condition
    :type index: pd.Index
    :param keep_entries: True if the entries in index should be kept, else false; defaults to True
    :type keep_entries: bool, optional
    :return: the filtered data set
    :rtype: pd.DataFrame
    """
    inindex = data.index.isin(index)
    keep = inindex if keep_entries else ~inindex
    return data.loc[keep]
