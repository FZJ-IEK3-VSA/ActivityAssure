"""
Example script for validation the LoadProfileGenerator
"""

from datetime import timedelta
import logging
from activity_validator.hetus_data_processing.activity_profile import (
    ActivityProfileEntryTime,
    ActivityProfile,
)
from activity_validator.hetus_data_processing import utils
from activity_validator.lpgvalidation import lpgvalidation


# TODO: some general todos
# - replace all old type annotations like Dict, List, Tuple, etc. with lowercase variants (dict etc.)
# - activity profile in time-step format: no resampling, time step size needs to be specified;
#   class needs additional attributes for resolution and start time
# - test sphinx-autodoc-typehints
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.DEBUG,
    datefmt="%Y-%m-%d %H:%M:%S",
)

# load LPG activity profiles
path = ".\\data\\lpg\\processed"
full_year_profiles = lpgvalidation.load_activity_profiles(path)

full_year_profile = full_year_profiles[0]
# for activity_profile in activity_profiles:

# get single-day profiles
selected_day_profiles = lpgvalidation.extract_day_profiles(full_year_profile)

# Tests
assert len(selected_day_profiles) == 363, "Unexpected number of day profiles"
assert str(selected_day_profiles[-1].activities[-1].start) == "2021-12-30 22:11:00"

profiles_by_type = lpgvalidation.group_profiles_by_type(selected_day_profiles)

validation_data = lpgvalidation.load_validation_data()
relevant_validation_data = lpgvalidation.filter_relevant_validation_data(
    validation_data
)
lpgvalidation.compare_to_validation_data(selected_day_profiles)
