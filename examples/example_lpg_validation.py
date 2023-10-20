"""
Example script for validation the LoadProfileGenerator
"""

import logging
from pathlib import Path
from activity_validator.hetus_data_processing import hetus_translations
from activity_validator.lpgvalidation import comparison_metrics, lpgvalidation

if __name__ == "__main__":
    # TODO: some general todos
    # - fix mypy issues
    # - standardize definition of file paths

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # load LPG activity profiles
    input_path = Path("data/lpg/processed")
    person_trait_file = Path("data/lpg/person_characteristics.json")
    full_year_profiles = lpgvalidation.load_activity_profiles_from_csv(
        input_path, person_trait_file
    )

    # resample profiles to validation data resolution

    # load activity mapping
    custom_mapping_path = Path("examples/activity_mapping_lpg.json")
    activity_mapping = hetus_translations.load_mapping(custom_mapping_path)

    # load validation data
    validation_data_dict = lpgvalidation.load_validation_data(
        Path("data/validation DE")
    )

    output_path = Path("data/lpg/results")
    # validate each full-year profile individually
    for full_year_profile in full_year_profiles:
        # translate activities to the common set of activity types
        full_year_profile.apply_activity_mapping(activity_mapping)
        # split the full year profiles into single-day profiles
        selected_day_profiles = lpgvalidation.extract_day_profiles(full_year_profile)

        # Tests
        assert len(selected_day_profiles) == 336, "Unexpected number of day profiles"
        assert (
            selected_day_profiles[-1].activities[-1].start == 524051 - 377
        ), "Start of last activity is incorrect"

        # categorize single-day profiles according to country, person and day type
        profiles_by_type = lpgvalidation.group_profiles_by_type(selected_day_profiles)

        # validate each profile type individually
        for profile_type, profiles in profiles_by_type.items():
            validation_data = validation_data_dict[profile_type]
            input_data = lpgvalidation.calc_input_data_statistics(profiles, output_path)
            comparison_metrics.calc_comparison_metrics(input_data, validation_data)

            break
        break
