"""
Functions for filtering HETUS data based on various criteria
"""


import functools
from typing import Any, Callable, Dict, Iterable, List, Union
import pandas as pd

import hetus_columns as col
from hetus_values import DayType
from utils import timing

# TODO: for separating dataframes instead of just dropping unmatching columns, groupby can be used


@timing
def filter_discrete(
    data: pd.DataFrame, column: str, allowed_values: List[int]
) -> pd.DataFrame:
    return data[data[column].isin(allowed_values)]


def filter_by_weekday(data: pd.DataFrame, day_types: List[DayType]) -> pd.DataFrame:
    return filter_discrete(data, col.Diary.WEEKDAY, day_types)


def filter_by_month(data: pd.DataFrame, months: List[int]) -> pd.DataFrame:
    return filter_discrete(data, col.Diary.MONTH, months)


# @timing
def filter_combined(
    data: pd.DataFrame, conditions: Dict[str, List[Any]]
) -> pd.DataFrame:
    masks = [data[k].isin(v) for k, v in conditions.items()]
    combined_mask = functools.reduce(lambda m1, m2: m1 & m2, masks)
    return data[combined_mask]


def filter_stats(func: Callable, name, data, *args, **kwargs) -> pd.DataFrame:
    """Calls filter_combined and prints some filter statistics"""
    result = func(data, *args, **kwargs)
    print(
        f"Filter {name}: {len(result)} / {len(data)} ({100 * len(result) / len(data):.1f} %)"
    )
    return result


def filter_no_data(
    data: pd.DataFrame, columns: Union[str, Iterable[str]], invert: bool = False
) -> pd.DataFrame:
    """
    Removes all entries with mnissing data (negative values) in any of the specified columns.
    Alternatively, only returns values with missing data if invert is set to True.

    :param data: general HETUS data
    :type data: pd.DataFrame
    :param columns: the columns to check for missing data
    :type columns: Union[str, Iterable[str]]
    :param invert: if True, keeps only entries with missing data instead, defaults to False
    :type invert: bool, optional
    :return: the filtered data
    :rtype: pd.DataFrame
    """
    if isinstance(columns, str):
        columns = [columns]
    masks = [data[c] >= 0 for c in columns]
    combined_mask = functools.reduce(lambda m1, m2: m1 | m2, masks)
    if invert:
        combined_mask = ~combined_mask
    return data[combined_mask]


def filter_by_index(
    data: pd.DataFrame, index: pd.Index, invert: bool = False
) -> pd.DataFrame:
    """
    Filters a data set using a separate index. The keep_entries parameter determines which part of
    the data is kept, either the part that is contained in the index, or the rest.

    :param data: the data to filter
    :type data: pd.DataFrame
    :param index: the index used as filter condition
    :type index: pd.Index
    :param invert: True if the entries in index should be kept, else false; defaults to True
    :type invert: bool, optional
    :return: the filtered data set
    :rtype: pd.DataFrame
    """
    inindex = data.index.isin(index)
    keep = ~inindex if invert else inindex
    return data.loc[keep]
