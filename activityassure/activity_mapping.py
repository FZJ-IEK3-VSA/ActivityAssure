"""
Functions for loading activity mappings and collecting the
activities available therein.
"""

import json
import logging
from pathlib import Path


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


def get_activities_in_mapping(mapping: dict[str, str]) -> list[str]:
    """
    Collects the target activities from a mapping and returns them in
    a sorted list.

    :param mapping: the mapping
    :return: the list of activities
    """
    return sorted(set(mapping.values()))


def load_mapping_and_activities(mapping_path: Path) -> tuple[dict[str, str], list[str]]:
    # load activity mapping
    activity_mapping = load_mapping(mapping_path)
    activities = get_activities_in_mapping(activity_mapping)
    return activity_mapping, activities


def check_activity_lists(
    activities: list[str], validation_activities: list[str]
) -> list[str]:
    """
    Checks if the passed activity lists match. Also returns a
    new activity list, containing all activity types in the same
    order as the validation_activities parameter.
    """
    types_custom = set(activities)
    types_val = set(validation_activities)
    if types_custom != types_val:
        logging.warning(
            "The applied activity mapping does not use the same set of activity types as the "
            "validation data.\n"
            f"Missing activity types: {types_val - types_custom}\n"
            f"Additional activity types: {types_custom - types_val}"
        )
        return validation_activities + list(types_custom - types_val)
    else:
        # order might be different, but content is the same
        return validation_activities
