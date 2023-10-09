"""
Example script for validation the LoadProfileGenerator
"""

from datetime import timedelta
from activity_validator.hetus_data_processing.activity_profile import (
    ActivityProfileEntryTime,
    ActivityProfile,
)
import activity_validator.hetus_data_processing.utils
from activity_validator.lpgvalidation import lpgvalidation


# TODO: some general todos
# - replace all old type annotations like Dict, List, Tuple, etc. with lowercase variants (dict etc.)
# - activity profile in time-step format: no resampling, time step size needs to be specified;
#   class needs additional attributes for resolution and start time

# load LPG activity profiles
path = ".\\data\\lpg\\processed"
full_year_profiles = lpgvalidation.load_activity_profiles(path)

total_duration = full_year_profiles[0].total_duration()
assert total_duration > timedelta(
    days=364
), f"The total duration of all activities is too short: {total_duration}"

full_year_profile = full_year_profiles[0]
# for activity_profile in activity_profiles:

# get single-day profiles
selected_day_profiles = lpgvalidation.extract_day_profiles(full_year_profile)
