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

    @staticmethod
    def map_columns(data: pd.DataFrame, mapping: dict):
        """
        Maps column names of a dataframe to new names. If
        two or more column names are mapped to the same new
        name, the colums are added.

        :param data: the data to rename
        :param mapping: the mapping to apply
        :return: the renamed data
        """
        # rename the columns, which might result in some with identical name
        data.rename(columns=mapping, inplace=True)
        # calculate the sum of all columns with the same name
        data = data.T.groupby(level=0).sum().T
        return data

    def map_activities(self, mapping: dict):
        """
        Renames and if necessary merges activities.

        :param mapping: a dict that maps old activity names to new names
        """
        self.activity_frequencies = ValidationData.map_columns(
            self.activity_frequencies, mapping
        )
        self.activity_durations = ValidationData.map_columns(
            self.activity_durations, mapping
        )
        # probability profiles contain one row per activity --> transpose twice
        self.probability_profiles = ValidationData.map_columns(
            self.probability_profiles.T, mapping
        ).T

    @staticmethod
    def load(
        base_path: Path, profile_type: activity_profile.ProfileType
    ) -> "ValidationData":
        """
        Loads all data for the specified profile type from the separate
        files.

        :param base_path: the base path where the files are stored
        :param profile_type: the profile type to load
        :raises RuntimeError: when not all files could be found
        :return: the object containing all data for the specified
                 profile type
        """
        freq_path = activity_profile.create_result_path(
            "activity_frequencies", "freq", profile_type, base_path
        )
        dur_path = activity_profile.create_result_path(
            "activity_durations", "dur", profile_type, base_path
        )
        prob_path = activity_profile.create_result_path(
            "probability_profiles", "prob", profile_type, base_path
        )
        if not (freq_path.is_file() and dur_path.is_file() and prob_path.is_file()):
            raise RuntimeError(
                f"Did not find all files for profile type {str(profile_type)} in base directory {base_path}"
            )
        _, freq = activity_profile.load_df(freq_path)
        _, dur = activity_profile.load_df(dur_path, True)
        _, prob = activity_profile.load_df(prob_path)
        return ValidationData(profile_type, prob, freq, dur)
