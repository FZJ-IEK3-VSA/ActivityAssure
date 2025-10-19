"""Utility functions for handling load profiles"""

from datetime import timedelta
from typing import TypeVar

import pandas as pd


#: type annotation for a dataframe or series
T_PD_DATA = TypeVar("T_PD_DATA", pd.Series, pd.DataFrame)


def rename_suffix(data: T_PD_DATA, old_suffix: str, new_suffix: str) -> None:
    """Replaces a suffix in all column names of a pandas data object inplace, where it
    occurs.

    :param data: the str to change
    :param old_suffix: the suffix to replace
    :param new_suffix: the new suffix to use instead
    """

    # define a function to replace the suffix in an str if it is present
    def replace_name(col):
        if not col:
            return col
        return (
            col.removesuffix(old_suffix) + new_suffix
            if col.endswith(old_suffix)
            else col
        )

    # apply the replacement function to the data
    if isinstance(data, pd.DataFrame):
        data.rename(
            columns=replace_name,
            inplace=True,
        )
    else:
        data.name = replace_name(data.name)


def timedelta_to_hours(td: timedelta) -> float:
    """Convert a timedelta to a float value in hours"""
    return td.total_seconds() / 3600


def get_resolution(data: pd.DataFrame | pd.Series) -> pd.Timedelta:
    """Returns the resolution of a pandas data object with a time index.
    Checks whether the resolution is consistent.

    :param data: the data object
    :return: the temporal resolution of the data
    """
    time_differences = data.index.diff().dropna()  # type: ignore
    assert len(set(time_differences)) == 1, "Index of data is not equidistant"
    return time_differences[0]


def kwh_to_w(
    data: T_PD_DATA, rename: bool = True, resolution: timedelta | None = None
) -> T_PD_DATA:
    """Convert profiles from unit kWh to W. Requires a time index to determine
    the profile resolution.

    :param data: the data in kWh to convert
    :param rename: if True, checks for units in column headers, and adapts them, defaults to True
    :param resolution: if given, uses it for conversion; if None, tries to determine
                       the resolution automatically from the index
    :return: the converted profiles in W
    """
    resolution = resolution or get_resolution(data)
    res_in_h = timedelta_to_hours(resolution)
    factor = 1000 / res_in_h
    converted = data * factor
    if rename:
        rename_suffix(converted, "[kWh]", "[W]")
    return converted


def w_to_kwh(data: T_PD_DATA, rename: bool = True) -> T_PD_DATA:
    """Convert profiles from unit W to kWh. Requires a time index to determine
    the profile resolution.

    :param data: the data in W to convert
    :param rename: if True, checks for units in column headers, and adapts them, defaults to True
    :return: the converted profiles in kWh
    """
    resolution = get_resolution(data)
    res_in_h = timedelta_to_hours(resolution)
    factor = res_in_h / 100
    converted = data * factor
    if rename:
        rename_suffix(converted, "[W]", "[kWh]")
    return converted
