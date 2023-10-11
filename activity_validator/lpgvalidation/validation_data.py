"""
Defines classes for storing and handling activity profile validation data.
"""

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from activity_validator.hetus_data_processing import activity_profile


@dataclass
class ValidationData:
    profile_type: activity_profile.ProfileType | tuple
    probability_profiles: pd.DataFrame
    activity_frequencies: pd.DataFrame
    activity_durations: pd.DataFrame
