"""
This module provides functions for translating HETUS columns and codes to readable names
"""

import json
from enum import EnumType
from pathlib import Path

import pandas as pd

import activity_validator.hetus_data_processing.hetus_columns as col


def load_hetus_activity_codes() -> dict[str, str]:
    """
    Imports the HETUS Activity Coding list from json.
    Contains 1, 2 and 3-digit codes.

    :return: dict mapping each code with its description
    """
    path = (
        Path()
        / "activity_validator"
        / "activity_types"
        / "hetus_activity_codes_2010.json"
    )
    if not path.exists():
        raise RuntimeError(f"The HETUS activity code list is missing: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def aggregate_activities(data: pd.DataFrame, digits: int = 1):
    assert 1 <= digits <= 3, "invalid number of digits for activity aggregation"
    # filter activity columns (Mact1-144)
    a3 = data.filter(like=col.Diary.MAIN_ACTIVITIES_PATTERN)
    # map to the target level
    target = a3.map(lambda x: x[:digits] if isinstance(x, str) else x)
    return target


def extract_activity_names(data: pd.DataFrame) -> pd.DataFrame:
    codes = load_hetus_activity_codes()
    # In general, the codes are hierarchical and complete, meaning that if
    # code 811 exists, then code 81 is its supergroup. However, for group 9
    # there are no two-digit codes. Therefore, if the code is not found, just
    # fall back to the corresponding one-digit code.
    return data.filter(like=col.Diary.MAIN_ACTIVITIES_PATTERN).map(
        lambda x: codes.get(x, codes[x[0]])
    )


def translate_activity_codes_index(data: pd.DataFrame) -> None:
    codes = load_hetus_activity_codes()
    data.index = data.index.map(lambda x: codes.get(x, x))


def translate_column(
    data: pd.DataFrame,
    column: str,
    column_new: str | None = None,
    value_translation: EnumType | dict | None = None,
) -> None:
    """
    Renames a column and changes all values according to a specified enum or dict.
    Can handle normal and (multi-)index columns.

    :param data: the data to translate
    :param column: old name of the column to change
    :param column_new: optional new name of the column, defaults to None
    :param value_translation: translation for the column values; can be an enum type or a dict, defaults to None
    """
    if isinstance(value_translation, EnumType):
        # create a dict that maps all enum int values to names
        value_map = {e.value: e.name for e in value_translation}  # type:ignore
    else:
        value_map = value_translation
    if column in data.index.names:
        # column is part of the (multi-)index
        if value_map is not None:
            i = data.index.names.index(column)
            new_index_level = data.index.levels[i].map(value_map)
            new_index = data.index.set_levels(new_index_level, level=i)
            data.index = new_index
        if column_new:
            # change name of the index level
            data.index.rename({column: column_new}, inplace=True)
    elif column in data.columns:
        # column is a normal column of the dataframe
        if value_map is not None:
            data[column].replace(value_map, inplace=True)
        if column_new:
            data.rename(columns={column: column_new}, inplace=True)
    else:
        assert False, "Column not found"
