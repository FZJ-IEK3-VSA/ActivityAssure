"""
Example script for validation the LoadProfileGenerator
"""

import json
import logging
from pathlib import Path
from typing import Any
from activity_validator.hetus_data_processing import (
    activity_profile,
    hetus_constants,
    hetus_translations,
)
from activity_validator.lpgvalidation import comparison_metrics, lpgvalidation


def check_mapping(
    activity_types: list[str], activity_types_val: list[str]
) -> list[str]:
    """
    Checks if the activity types used in the custom mapping here match those
    in the validation data set. Also returns a new activity types list, containing
    all validation activity types in the same order.
    """
    types_custom = set(activity_types)
    types_val = set(activity_types_val)
    if types_custom != types_val:
        logging.warn(
            "The applied activity mapping does not use the same set of activity types as the"
            "validation data.\n"
            f"Missing activity types: {types_val - types_custom}\n"
            f"Additional activity types: {types_custom - types_val}"
        )
        return activity_types_val + list(types_custom - types_val)
    else:
        return activity_types_val


def merge_dicts(dict1: dict[Any, list], dict2: dict[Any, list]) -> dict[Any, list]:
    keys = dict1.keys() | dict2.keys()
    return {k: dict1.get(k, []) + dict2.get(k, []) for k in keys}


def validate_lpg():
    # TODO: some general todos
    # - fix mypy issues
    # - standardize definition of file paths
    # - reevaluate all module-level constants: move to config file?
    # - check all the TODOs everywhere in the project

    # load LPG activity profiles
    input_path = Path("data/lpg/preprocessed")
    output_path = Path("data/lpg/results")
    person_trait_file = Path("data/lpg/person_characteristics.json")
    full_year_profiles = lpgvalidation.load_activity_profiles_from_csv(
        input_path, person_trait_file
    )

    # load activity mapping
    custom_mapping_path = Path("examples/activity_mapping_lpg.json")
    activity_mapping = hetus_translations.load_mapping(custom_mapping_path)
    activity_types = hetus_translations.get_activity_type_list(
        custom_mapping_path, output_base_path=output_path
    )
    activity_types_val = hetus_translations.get_activity_type_list(save_to_output=False)
    activity_types = check_mapping(activity_types, activity_types_val)

    # map and categorize each full-year profile individually
    all_profiles_by_type = {}
    for full_year_profile in full_year_profiles:
        # resample profiles to validation data resolution
        full_year_profile.resample(hetus_constants.RESOLUTION)
        # translate activities to the common set of activity types
        full_year_profile.apply_activity_mapping(activity_mapping)
        # split the full year profiles into single-day profiles
        selected_day_profiles = lpgvalidation.extract_day_profiles(full_year_profile)

        # categorize single-day profiles according to country, person and day type
        profiles_by_type = lpgvalidation.group_profiles_by_type(selected_day_profiles)

        all_profiles_by_type = merge_dicts(all_profiles_by_type, profiles_by_type)

    # load validation data
    validation_data_path = Path("data/validation data sets/full_categorization")
    validation_data_dict = lpgvalidation.load_validation_data(validation_data_path)

    # validate each profile type individually
    for profile_type, profiles in all_profiles_by_type.items():
        # select matching validation data
        validation_data = validation_data_dict[profile_type]
        # calculate and store statistics for validation
        input_data = lpgvalidation.calc_input_data_statistics(profiles, activity_types)
        input_data.save(output_path)
        # calcluate and store comparison metrics
        differences, metrics = comparison_metrics.calc_comparison_metrics(
            validation_data, input_data
        )
        activity_profile.save_df(
            differences, "differences", "diff", profile_type, output_path
        )
        # save metrics as normal, scaled and normalized variants
        metrics.save_as_csv(output_path, profile_type, "normal")
        shares = validation_data.probability_profiles.mean(axis=1)
        metrics.get_scaled(shares).save_as_csv(output_path, profile_type, "scaled")
        _, metrics_normalized = comparison_metrics.calc_comparison_metrics(
            validation_data, input_data, True
        )
        metrics_normalized.save_as_csv(output_path, profile_type, "normalized")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    validate_lpg()
