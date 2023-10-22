"""
Defines classes for storing and handling activity profile validation data.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from activity_validator.hetus_data_processing import activity_profile


@dataclass
class ValidationData:
    profile_type: activity_profile.ProfileType
    probability_profiles: pd.DataFrame
    activity_frequencies: pd.DataFrame
    activity_durations: pd.DataFrame

    def save(self, base_path: Path):
        """
        Saves all contained data to separate files

        :param base_path: the base path to store the
                          data at
        """
        activity_profile.save_df(
            self.activity_frequencies,
            "activity_frequencies",
            "freq",
            self.profile_type,
            base_path=base_path,
        )
        activity_profile.save_df(
            self.activity_durations,
            "activity_durations",
            "dur",
            self.profile_type,
            base_path=base_path,
        )
        activity_profile.save_df(
            self.probability_profiles,
            "probability_profiles",
            "prob",
            self.profile_type,
            base_path=base_path,
        )
