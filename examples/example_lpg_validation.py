"""
Example script for validation the LoadProfileGenerator
"""

import logging
import pathlib
from activity_validator.lpgvalidation import lpgvalidation

if __name__ == "__main__":
    # TODO: some general todos
    # - replace all old type annotations like Dict, List, Tuple, etc. with lowercase variants (dict etc.)
    # - remove all type info from docstrings (not needed anymore)
    # - activity profile in time-step format: no resampling, time step size needs to be specified;
    #   class needs additional attributes for resolution and start time
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # load LPG activity profiles
    path = pathlib.Path() / "data" / "lpg" / "processed"
    full_year_profiles = lpgvalidation.load_activity_profiles(path)

    for full_year_profile in full_year_profiles:
        # split the full year profiles into single-day profiles
        selected_day_profiles = lpgvalidation.extract_day_profiles(full_year_profile)

        # Tests
        assert len(selected_day_profiles) == 363, "Unexpected number of day profiles"
        assert (
            str(selected_day_profiles[-1].activities[-1].start) == "2021-12-30 22:11:00"
        )

        profiles_by_type = lpgvalidation.group_profiles_by_type(selected_day_profiles)

        validation_data_dict = lpgvalidation.load_validation_data()

        for profile_type, profiles in profiles_by_type.items():
            validation_data = validation_data_dict[profile_type]

            lpgvalidation.compare_to_validation_data(profiles, validation_data)

            break
        break
