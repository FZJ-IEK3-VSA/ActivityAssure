"""
This module provides functions for translating HETUS columns and codes to readable names.
"""

from pathlib import Path

import pandas as pd

from activityassure import activity_mapping
import activityassure.hetus_data_processing.hetus_column_names as col

#: path of the HETUS code file that maps each HETUS activity code to the
#  corresponding activity name
HETUS_CODES_PATH = Path("activityassure/activities/hetus_activity_codes_2010.json")
#: path of the HETUS mapping file that maps each HETUS activity name to an
#  activity of the joint activity set
HETUS_MAPPING_PATH = Path("activityassure/activities/mapping_hetus.json")


def get_aggregate_activity_codes(data: pd.DataFrame, digits: int = 1):
    """
    Returns the activity columns, with all activity codes transformed
    to the desired level (1, 2 or 3 digit codes).

    :param data: HETUS data
    :param digits: the code digits to use, defaults to 1
    :return: activity data at the desired code level
    """
    assert 1 <= digits <= 3, "invalid number of digits for activity aggregation"
    # filter activity columns (Mact1-144)
    activity = col.get_activity_data(data)
    # map to the target level
    target = activity.map(lambda x: x[:digits] if isinstance(x, str) else x)  # type: ignore
    return target


def load_hetus_activity_codes() -> dict[str, str]:
    """
    Imports the HETUS Activity Coding list from json.
    Contains 1, 2 and 3-digit codes.

    :return: dict mapping each code with its description
    """
    return activity_mapping.load_mapping(HETUS_CODES_PATH)


def get_combined_hetus_mapping() -> dict[str, str]:
    """
    Loads the HETUS activity code mapping and the joint
    activity mapping and combines them into one dict
    that allows immediate translation from HETUS code
    to joint activity group.

    :return: combined activity mapping
    """
    codes = load_hetus_activity_codes()
    mapping = activity_mapping.load_mapping(HETUS_MAPPING_PATH)
    # combine the two mapping steps in a single dict (only 3-digit HETUS codes)
    combined = {code: mapping[name] for code, name in codes.items() if name in mapping}
    return combined


def translate_activity_codes(data: pd.DataFrame) -> list[str]:
    """
    Applies the HETUS activity mapping and the custom activity
    category mapping, both stored in separate json files.
    Thus, the 3-digit HETUS activity codes are first translated
    to the respective activity names, which are then grouped
    according to the custom mapping.
    The translation works inplace.

    :param data: HETUS diary data
    :return: the final list of activities that can occur
    """
    # HETUS data contains activity codes which can be mapped to the
    # corresponding activity names, which can in turn be mapped using
    # the defined activity type mapping
    combined = get_combined_hetus_mapping()
    activity = col.get_activity_data(data)
    data.loc[:, activity.columns] = activity.replace(combined)
    return activity_mapping.get_activities_in_mapping(combined)
