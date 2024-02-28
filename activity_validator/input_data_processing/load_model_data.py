"""
Functions for loading activity profile data and the respective
person characteristics.
"""

import logging
from activity_validator import activity_profile, utils
from activity_validator.activity_profile import SparseActivityProfile
from datetime import timedelta
from pathlib import Path
from activity_validator.profile_category import ProfileCategory

import json


def load_person_characteristics(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        traits: dict[str, dict] = json.load(f)
    return {name: ProfileCategory.from_dict(d) for name, d in traits.items()}  # type: ignore


def get_person_traits(
    person_traits: dict[str, ProfileCategory], filename: str | Path
) -> ProfileCategory:
    """
    Extracts the person name from the path of an activity profile file
    and returns the matching ProfileType object with the person
    characteristics.

    :param person_traits: the person trait dict
    :param filepath: path of the activity profile file, contains the
                     name of the person
    :raises RuntimeError: when no characteristics for the person were
                          found
    :return: the characteristics of the person
    """
    name = Path(filename).stem.split("_")[0]
    if name not in person_traits:
        raise RuntimeError(f"No person characteristics found for '{name}'")
    return person_traits[name]


@utils.timing
def load_activity_profiles_from_csv(
    path: str | Path,
    person_trait_file: str,
    resolution: timedelta = activity_profile.DEFAULT_RESOLUTION,
) -> list[SparseActivityProfile]:
    """Loads the activity profiles in csv format from the specified folder"""
    if not isinstance(path, Path):
        path = Path(path)
    assert Path(path).is_dir(), f"Directory does not exist: {path}"
    person_traits = load_person_characteristics(person_trait_file)
    activity_profiles = []
    for filepath in path.iterdir():
        if filepath.is_file():
            profile_type = get_person_traits(person_traits, filepath)
            activity_profile = SparseActivityProfile.load_from_csv(
                filepath, profile_type, resolution
            )
            activity_profiles.append(activity_profile)
    logging.info(f"Loaded {len(activity_profiles)} activity profiles")
    return activity_profiles
