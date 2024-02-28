"""
Defines classes for storing and handling activity profile validation data.
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import ClassVar

import pandas as pd

from activity_validator.profile_category import ProfileType
from activity_validator.hetus_data_processing.pandas_utils import (
    save_df,
    load_df,
    create_result_path,
)


@dataclass
class ValidationStatistics:
    """
    Stores all validation statistics for a single profile type
    """

    profile_type: ProfileType
    probability_profiles: pd.DataFrame
    activity_frequencies: pd.DataFrame
    activity_durations: pd.DataFrame
    category_size: int | None = None

    # subdirectory names for file storage
    PROBABILITY_PROFILE_DIR: ClassVar = "probability_profiles"
    FREQUENCY_DIR: ClassVar = "activity_frequencies"
    DURATION_DIR: ClassVar = "activity_durations"

    def save(self, base_path: Path):
        """
        Saves all contained statistics to separate files

        :param base_path: the base path to store the
                          data at
        """
        save_df(
            self.activity_frequencies,
            ValidationStatistics.FREQUENCY_DIR,
            "freq",
            self.profile_type,
            base_path=base_path,
        )
        save_df(
            self.activity_durations,
            ValidationStatistics.DURATION_DIR,
            "dur",
            self.profile_type,
            base_path=base_path,
        )
        save_df(
            self.probability_profiles,
            ValidationStatistics.PROBABILITY_PROFILE_DIR,
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
        self.activity_frequencies = ValidationStatistics.map_columns(
            self.activity_frequencies, mapping
        )
        self.activity_durations = ValidationStatistics.map_columns(
            self.activity_durations, mapping
        )
        # probability profiles contain one row per activity --> transpose twice
        self.probability_profiles = ValidationStatistics.map_columns(
            self.probability_profiles.T, mapping
        ).T

    @staticmethod
    def load(
        base_path: Path, profile_type: ProfileType, size: int | None = None
    ) -> "ValidationStatistics":
        """
        Loads all data for the specified profile type from the separate
        files.

        :param base_path: the base path where the files are stored
        :param profile_type: the profile type to load
        :param size: the number of activity profiles that were aggregated
                     for these statistics
        :raises RuntimeError: when not all files could be found
        :return: the object containing all data for the specified
                 profile type
        """
        freq_path = create_result_path(
            ValidationStatistics.FREQUENCY_DIR, "freq", profile_type, base_path
        )
        dur_path = create_result_path(
            ValidationStatistics.DURATION_DIR, "dur", profile_type, base_path
        )
        prob_path = create_result_path(
            ValidationStatistics.PROBABILITY_PROFILE_DIR,
            "prob",
            profile_type,
            base_path,
        )
        if not (freq_path.is_file() and dur_path.is_file() and prob_path.is_file()):
            raise RuntimeError(
                f"Did not find all files for profile type {str(profile_type)} in base directory {base_path}"
            )
        freq = load_df(freq_path)
        dur = load_df(dur_path, True)
        prob = load_df(prob_path)
        return ValidationStatistics(profile_type, prob, freq, dur, size)


@dataclass
class ValidationSet:
    """
    A full validation data set, including statistics for all profile
    types and common metadata.
    """

    statistics: dict[ProfileType, ValidationStatistics]
    activities: list[str]

    # directory and file names for file storage
    CATEGORIES_DIR: ClassVar = "categories"
    CATEGORY_SIZES_FILE: ClassVar = "category_sizes.csv"
    ACTIVITIES_DIR: ClassVar = "activities"
    ACTIVITIES_FILE: ClassVar = "activities.json"
    AVAILABLE_ACTIVITIES_KEY: ClassVar = "available activities"

    def filter_categories(self, min_size: int):
        """
        Remove all categories that contain too few profiles.

        :param min_size: the minimum size to keep a category
        """
        total = 0
        deleted = 0
        for pt, stat in self.statistics.items():
            assert stat.category_size is not None, "Missing category size in filtering"
            total += stat.category_size
            if stat.category_size < min_size:
                del self.statistics[pt]
                deleted += 1
        logging.info(f"Removed {deleted} out of {total} categories (too small).")

    def hide_small_category_sizes(self, size_ranges: list[int]):
        """
        Hides the exact category size for smaller categories. The parameter
        size_ranges is a sorted list of numbers, each defining the upper boundary
        of a size range. For each category, the upper boundary of the respective
        range is assigned instead of the exact size.
        Above the highest boundary, exact sizes are kept.

        :param size_ranges: defines the size ranges to apply (e.g., [20, 50])
        """
        assert size_ranges == sorted(
            size_ranges
        ), "Unclear parameter: size_ranges must be sorted"
        hidden = 0
        for stat in self.statistics.values():
            old_size = stat.category_size
            if old_size is None:
                continue
            # find the lowest limit that is larger than the actual size
            new_size = next((n for n in size_ranges if old_size < n), old_size)
            if new_size != old_size:
                hidden += 1
            stat.category_size = new_size
        logging.info(f"Obfuscated category size of {hidden} categories.")

    def map_statistics_activities(self, mapping: dict[str, str]):
        """
        Maps activities to new names and merges them if necessary.

        :param mapping: the mapping to apply
        """
        self.activities = [mapping.get(a, a) for a in self.activities]
        for data in self.statistics.values():
            data.map_activities(mapping)

    def get_category_sizes_df(
        self, format_for_readability: bool = False
    ) -> pd.DataFrame:
        """
        Collects the category sizes for this statistics object in
        a single dataframe.

        :return: a dataframe containing the category sizes
        """
        # get any profile type to determine the attribute names in use
        any_profile_type = next(iter((self.statistics.values()))).profile_type
        names = any_profile_type.get_attribute_names()
        # collect the profile type attributes for each category
        index = pd.MultiIndex.from_tuples(
            [pt.to_tuple() for pt in self.statistics.keys()], names=names
        )
        # collect the category sizes
        sizes = [stat.category_size for stat in self.statistics.values()]
        colname = "Sizes"
        sizes_df = pd.DataFrame({colname: sizes}, index=index)
        if index.nlevels > 1 and format_for_readability:
            # more than one profile type attribute: restructure dataframe for readability
            # this however leads to one index title missing in the csv file, which can then
            # not be loaded anymore
            sizes_df.reset_index(inplace=True)
            cols = list(sizes_df.columns)
            sizes_df = sizes_df.reset_index().pivot(
                index=cols[1:-1], columns=cols[0], values=colname
            )
        return sizes_df

    def save(self, base_path: Path):
        """
        Saves all statistics for different profile types as well as
        corresponding metadata in the specified path.

        :param base_path: base output path
        """
        for stat in self.statistics.values():
            stat.save(base_path)

        # save activities
        path = create_result_path(
            ValidationSet.ACTIVITIES_DIR,
            ValidationSet.ACTIVITIES_FILE,
            base_path=base_path,
            ext="",
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {ValidationSet.AVAILABLE_ACTIVITIES_KEY: self.activities}, f, indent=4
            )

        # save category sizes to file
        category_sizes = self.get_category_sizes_df()
        save_df(
            category_sizes,
            ValidationSet.CATEGORIES_DIR,
            ValidationSet.CATEGORY_SIZES_FILE,
            base_path=base_path,
        )
        # additionally, save the more readable category sizes version
        category_sizes = self.get_category_sizes_df(True)
        save_df(
            category_sizes,
            ValidationSet.CATEGORIES_DIR,
            "category_sizes_readable",
            base_path=base_path,
        )

    @staticmethod
    def load_category_sizes(base_path: Path) -> dict[ProfileType, int]:
        sizes = pd.read_csv(
            base_path / ValidationSet.CATEGORIES_DIR / ValidationSet.CATEGORY_SIZES_FILE
        )
        # the last column contains the sizes, the others the profile type attributes
        pt_names = sizes.columns[:-1]
        category_sizes = {
            ProfileType.from_index_tuple(pt_names, values[:-1]): values[-1]
            for values in sizes.itertuples(index=False)
        }
        return category_sizes

    @staticmethod
    def load_activities(base_path: Path) -> list[str]:
        with open(
            base_path / ValidationSet.ACTIVITIES_DIR / ValidationSet.ACTIVITIES_FILE
        ) as f:
            content = json.load(f)
        return content[ValidationSet.AVAILABLE_ACTIVITIES_KEY]

    @staticmethod
    def load_validation_data_subdir(
        path: Path, as_timedelta: bool = False
    ) -> dict[ProfileType, pd.DataFrame]:
        return {
            ProfileType.from_filename(p): load_df(p, as_timedelta)
            for p in path.iterdir()
            if p.is_file()
        }

    @staticmethod
    def load(base_path: Path) -> "ValidationSet":
        assert base_path.is_dir(), f"Validation data directory not found: {base_path}"
        subdir_path = base_path / ValidationStatistics.PROBABILITY_PROFILE_DIR
        probability_profile_data = ValidationSet.load_validation_data_subdir(
            subdir_path
        )
        subdir_path = base_path / ValidationStatistics.FREQUENCY_DIR
        activity_frequency_data = ValidationSet.load_validation_data_subdir(subdir_path)
        subdir_path = base_path / ValidationStatistics.DURATION_DIR
        activity_duration_data = ValidationSet.load_validation_data_subdir(
            subdir_path, True
        )
        assert (
            probability_profile_data.keys()
            == activity_frequency_data.keys()
            == activity_duration_data.keys()
        ), "Missing data for some of the profile types"

        category_sizes = ValidationSet.load_category_sizes(base_path)
        statistics = {
            profile_type: ValidationStatistics(
                profile_type,
                prob_data,
                activity_frequency_data[profile_type],
                activity_duration_data[profile_type],
                category_sizes[profile_type],
            )
            for profile_type, prob_data in probability_profile_data.items()
        }
        logging.info(f"Loaded statistics for {len(statistics)} profile types")

        # load activities
        activities = ValidationSet.load_activities(base_path)
        return ValidationSet(statistics, activities)
