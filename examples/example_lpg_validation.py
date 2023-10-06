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

# load LPG activity profiles
path = ".\\data\\lpg\\processed"
activity_profiles = lpgvalidation.load_activity_profiles(path)

total_duration = sum([x.duration or timedelta(0) for x in activity_profiles[0].activities], start=timedelta(0))
assert total_duration > timedelta(days=364), f"The total duration of all activities is too short: {total_duration}"