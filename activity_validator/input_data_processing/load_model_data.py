"""
Functions for loading activity profile data and the respective
person characteristics.
"""

import logging
from activity_validator import utils
from activity_validator.activity_profile import SparseActivityProfile
from datetime import timedelta
from pathlib import Path
from activity_validator.profile_category import ProfileCategory

import json


def load_person_characteristics(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        traits: dict[str, dict] = json.load(f)
    return {name: ProfileCategory.from_dict(d) for name, d in traits.items()}  # type: ignore


def get_person_from_filename(file: Path) -> str:
    """
    Extracts the person name from the path of an activity profile file

    :param file: the path of an activity profile file
    :return: the person name the profile belongs to
    """
    return file.stem.split("_")[0]


def get_person_traits(
    person_traits: dict[str, ProfileCategory],
    person: str,
    include_person_in_category: bool = False,
) -> ProfileCategory:
    """
    Returns the matching ProfileCategory object with the person
    characteristics for a specific person.

    :param person_traits: the person trait dict
    :param person: name of the person
    :raises RuntimeError: when no characteristics for the person were
                          found
    :return: the characteristics of the person
    """
    if person not in person_traits:
        raise RuntimeError(f"No person characteristics found for '{person}'")
    category = person_traits[person]
    if include_person_in_category:
        category = category.to_personal_category(person)
    return category


@utils.timing
def load_activity_profiles_from_csv(
    path: Path,
    person_trait_file: str,
    resolution: timedelta,
    categories_per_person: bool = False,
) -> list[SparseActivityProfile]:
    """Loads the activity profiles in csv format from the specified folder"""
    assert Path(path).is_dir(), f"Directory does not exist: {path}"
    person_traits = load_person_characteristics(person_trait_file)
    activity_profiles = []
    for filepath in path.iterdir():
        if filepath.is_file():
            person = get_person_from_filename(
                filepath,
            )
            profile_type = get_person_traits(
                person_traits, person, categories_per_person
            )
            activity_profile = SparseActivityProfile.load_from_csv(
                filepath, profile_type, resolution
            )
            activity_profiles.append(activity_profile)
    logging.info(f"Loaded {len(activity_profiles)} activity profiles")
    return activity_profiles
