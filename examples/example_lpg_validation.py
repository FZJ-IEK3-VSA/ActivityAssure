"""
Example script for validation the LoadProfileGenerator
"""

import logging
import pathlib
from activity_validator.lpgvalidation import lpgvalidation

if __name__ == "__main__":
    # TODO: some general todos
    # - fix mypy issues
    # - activity profile in time-step format: no resampling, time step size needs to be specified;
    #   class needs additional attributes for resolution and start time
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # load LPG activity profiles
    path = pathlib.Path() / "data" / "lpg" / "processed"
    person_trait_file = pathlib.Path() / "data" / "lpg" / "person_characteristics.json"
    full_year_profiles = lpgvalidation.load_activity_profiles_from_csv(
        path, person_trait_file
    )

    # TODO: activity mapping

    for full_year_profile in full_year_profiles:
        # split the full year profiles into single-day profiles
        selected_day_profiles = lpgvalidation.extract_day_profiles(full_year_profile)

        # Tests
        assert len(selected_day_profiles) == 363, "Unexpected number of day profiles"
        assert (
            selected_day_profiles[-1].activities[-1].start == 524051 - 377
        ), "Start of last activity is incorrect"

        profiles_by_type = lpgvalidation.group_profiles_by_type(selected_day_profiles)

        validation_data_dict = lpgvalidation.load_validation_data()

        for profile_type, profiles in profiles_by_type.items():
            validation_data = validation_data_dict[profile_type]

            lpgvalidation.compare_to_validation_data(profiles, validation_data)

            break
        break
