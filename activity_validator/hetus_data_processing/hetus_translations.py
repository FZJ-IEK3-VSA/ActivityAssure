"""
This module provides functions for translating HETUS columns and codes to readable names
"""

import json
from enum import EnumType
import logging
from pathlib import Path

import pandas as pd
from activity_validator.hetus_data_processing.activity_profile import create_result_path

import activity_validator.hetus_data_processing.hetus_columns as col

HETUS_CODES_PATH = Path(
    "activity_validator/activity_types/hetus_activity_codes_2010.json"
)
HETUS_MAPPING_PATH = Path("activity_validator/activity_types/mapping_hetus.json")


def load_mapping(path: Path) -> dict[str, str]:
    """
    Loads an activity mapping from a json file.

    :param path: mapping file path
    :raises RuntimeError: if the file does not exist
    :return: the mapping dict
    """
    if not path.exists():
        raise RuntimeError(f"Missing mapping file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_hetus_activity_codes() -> dict[str, str]:
    """
    Imports the HETUS Activity Coding list from json.
    Contains 1, 2 and 3-digit codes.

    :return: dict mapping each code with its description
    """
    return load_mapping(HETUS_CODES_PATH)


def aggregate_activities(data: pd.DataFrame, digits: int = 1):
    assert 1 <= digits <= 3, "invalid number of digits for activity aggregation"
    # filter activity columns (Mact1-144)
    activity = data.filter(like=col.Diary.MAIN_ACTIVITIES_PATTERN)
    # map to the target level
    target = activity.map(lambda x: x[:digits] if isinstance(x, str) else x)  # type: ignore
    return target


def extract_activity_data(data: pd.DataFrame) -> pd.DataFrame:
    codes = load_hetus_activity_codes()
    # In general, the codes are hierarchical and complete, meaning that if
    # code 811 exists, then code 81 is its supergroup. However, for group 9
    # there are no two-digit codes. Therefore, if the code is not found, just
    # fall back to the corresponding one-digit code.
    return data.filter(like=col.Diary.MAIN_ACTIVITIES_PATTERN).map(  # type: ignore
        lambda x: codes.get(x, codes[x[0]])
    )


def save_final_activity_types() -> list[str]:
    """
    Saves the ultimately (i.e., after applying the mappings) available
    activity types in a json file. This can be used to countercheck
    which activities did not occur at all in a profile.

    :return: the list of activity names
    """
    mapping = load_mapping(HETUS_MAPPING_PATH)
    activity_types = list(set(mapping.values()))
    path = create_result_path("activities", "available_activity_types", ext="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"activity types": activity_types}, f)
    logging.info(f"Created activity types file: {path}")
    return activity_types


def get_combined_mapping() -> dict[str, str]:
    """
    Loads the HETUS activity mapping and the custom
    activity mapping and combines them into one dict
    that allows immediate translation from HETUS code
    to custom activity category.

    :return: combined activity mapping
    """
    codes = load_hetus_activity_codes()
    mapping = load_mapping(HETUS_MAPPING_PATH)
    # combine the two mapping steps in a single dict (only 3-digit HETUS codes)
    combined = {code: mapping[name] for code, name in codes.items() if name in mapping}
    return combined


def translate_activity_codes(data: pd.DataFrame) -> None:
    """
    Applies the HETUS activity mapping and the custom activity
    category mapping, both stored in separate json files.
    Thus, the 3-digit HETUS activity codes are first translated
    to the respective activity names, which are then grouped
    according to the custom mapping.
    The translation works inplace.

    :param data: HETUS diary data
    :return: data with mapped activity names
    """
    # HETUS data contains activity codes which can be mapped to the
    # corresponding activity names, which can in turn be mapped using
    # the defined activity type mapping
    combined = get_combined_mapping()
    activity = data.filter(like=col.Diary.MAIN_ACTIVITIES_PATTERN)
    data.loc[:, activity.columns] = activity.replace(combined)


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
        assert value_translation is not None, "No translation specified"
        value_map = value_translation
    if column in data.index.names:
        # column is part of the (multi-)index
        if value_map is not None:
            i = data.index.names.index(column)
            new_index_level = data.index.levels[i].map(value_map)  # type: ignore
            new_index = data.index.set_levels(new_index_level, level=i)  # type: ignore
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
