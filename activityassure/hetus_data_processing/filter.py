"""
Functions for filtering HETUS data based on various criteria.
"""

import functools
from typing import Any, Callable, Iterable
import pandas as pd


def filter_combined(
    data: pd.DataFrame, conditions: dict[str, list[Any]]
) -> pd.DataFrame:
    """
    Filters data combining multiple filter conditions which
    each allow a list of values for a specific column.

    :param data: HETUS data to filter
    :param conditions: the filter conditions dict; each key is a
                       column to filter, and the corresponding
                       value is the list of allowed values for
                       this column
    :return: the filtered data
    """
    masks = [data[k].isin(v) for k, v in conditions.items()]
    combined_mask = functools.reduce(lambda m1, m2: m1 & m2, masks)
    return data[combined_mask]


def filter_stats(func: Callable, name, data, *args, **kwargs) -> pd.DataFrame:
    """Calls the specified filter function and prints some filter statistics"""
    result = func(data, *args, **kwargs)
    print(
        f"Filter {name}: {len(result)} / {len(data)} ({100 * len(result) / len(data):.1f} %)"
    )
    return result


def filter_no_data(
    data: pd.DataFrame, columns: str | Iterable[str], invert: bool = False
) -> pd.DataFrame:
    """
    Removes all entries with mnissing data (negative values) in any of the specified columns.
    Alternatively, only returns values with missing data if invert is set to True.

    :param data: general HETUS data
    :param columns: the columns to check for missing data
    :param invert: if True, keeps only entries with missing data instead, defaults to False
    :return: the filtered data
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
    :param index: the index used as filter condition
    :param invert: True if the entries in index should be kept, else false; defaults to True
    :return: the filtered data set
    """
    inindex = data.index.isin(index)
    keep = ~inindex if invert else inindex
    return data.loc[keep]
