"""
Example script for validation the LoadProfileGenerator
"""

import json
import logging
from pathlib import Path
from activity_validator.hetus_data_processing import (
    activity_profile,
    hetus_constants,
    hetus_translations,
)
from activity_validator.lpgvalidation import comparison_metrics, lpgvalidation


def check_mapping(activity_types: list[str], validation_path: Path):
    """
    Checks if the activity types used in the custom mapping here match those
    in the validation data set.
    """
    # load HETUS activity types
    path = activity_profile.create_result_path(
        "activities", "available_activity_types", base_path=validation_path, ext="json"
    )
    with open(path) as f:
        activity_types_valid = json.load(f)["activity types"]
    assert set(activity_types) == set(activity_types_valid), (
        "The activity mapping does not use the same set of activity types as the"
        "validation data"
    )
    assert (
        activity_types == activity_types_valid
    ), "The mappings result in a different activity type order"


def validate_lpg():
    # TODO: some general todos
    # - fix mypy issues
    # - standardize definition of file paths
    # - reevaluate all module-level constants: move to config file?
    # - check all the TODOs everywhere in the project

    # load LPG activity profiles
    input_path = Path("data/lpg/processed")
    output_path = Path("data/lpg/results")
    person_trait_file = Path("data/lpg/person_characteristics.json")
    full_year_profiles = lpgvalidation.load_activity_profiles_from_csv(
        input_path, person_trait_file
    )

    # load validation data
    validation_data_path = Path("data/validation_data DE")
    validation_data_dict = lpgvalidation.load_validation_data(validation_data_path)

    # load activity mapping
    custom_mapping_path = Path("examples/activity_mapping_lpg.json")
    activity_mapping = hetus_translations.load_mapping(custom_mapping_path)
    # TODO: LPG mapping is missing "eat", so skip this check for now
    # activity_types = hetus_translations.save_final_activity_types(
    #     custom_mapping_path, output_path
    # )
    # check_mapping(activity_types, validation_data_path)
    activity_types = hetus_translations.save_final_activity_types()

    # validate each full-year profile individually
    for full_year_profile in full_year_profiles:
        # resample profiles to validation data resolution
        full_year_profile.resample(hetus_constants.RESOLUTION)
        # translate activities to the common set of activity types
        full_year_profile.apply_activity_mapping(activity_mapping)
        # split the full year profiles into single-day profiles
        selected_day_profiles = lpgvalidation.extract_day_profiles(full_year_profile)

        # Tests
        assert len(selected_day_profiles) == 336, "Unexpected number of day profiles"

        # categorize single-day profiles according to country, person and day type
        profiles_by_type = lpgvalidation.group_profiles_by_type(selected_day_profiles)

        # validate each profile type individually
        for profile_type, profiles in profiles_by_type.items():
            # select matching validation data
            validation_data = validation_data_dict[profile_type]
            # calculate and store statistics for validation
            input_data = lpgvalidation.calc_input_data_statistics(
                profiles, activity_types
            )
            input_data.save(output_path)
            # calcluate and store comparison metrics
            differences, metrics = comparison_metrics.calc_comparison_metrics(
                validation_data, input_data
            )
            activity_profile.save_df(
                differences, "differences", "diff", profile_type, output_path
            )
            metrics.save(output_path, profile_type)
            return input_data, validation_data


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    validate_lpg()
