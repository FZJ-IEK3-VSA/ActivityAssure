"""
Defines classes for storing and handling activity profile validation data.
"""

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import ClassVar

import pandas as pd

from activity_validator import utils
from activity_validator.categorization_attributes import Country, DayType
from activity_validator.profile_category import PersonProfileCategory, ProfileCategory
from activity_validator.pandas_utils import (
    save_df,
    load_df,
    create_result_path,
)


@dataclass
class ValidationStatistics:
    """
    Stores all validation statistics for a single profile type
    """

    profile_type: ProfileCategory
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
        base_path: Path, profile_type: ProfileCategory, size: int | None = None
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

    statistics: dict[ProfileCategory, ValidationStatistics]
    activities: list[str]

    # directory and file names for file storage
    CATEGORIES_DIR: ClassVar = "categories"
    CATEGORY_SIZES_FILE: ClassVar = "category_sizes.csv"
    ACTIVITIES_DIR: ClassVar = "activities"
    ACTIVITIES_FILE: ClassVar = "activities.json"
    AVAILABLE_ACTIVITIES_KEY: ClassVar = "available activities"

    def get_matching_statistics(
        self, category: ProfileCategory
    ) -> ValidationStatistics | None:
        """
        Returns matching category statistics for comparison. If not
        exactly the same category is present and the category included
        a person name, looks for the same category without person name.

        :param category: the category to match
        :return: the matching statistics, if there are any
        """
        if category in self.statistics:
            # return the same category if it exists
            return self.statistics[category]
        if isinstance(category, PersonProfileCategory):
            ppc = category.get_category_without_person()
            return self.statistics.get(ppc, None)
        return None

    def filter_categories(self, min_size: int):
        """
        Remove all categories that contain too few profiles.

        :param min_size: the minimum size to keep a category
        """
        total = len(self.statistics)
        to_delete = []
        # identify categories that are too small
        for category, stat in self.statistics.items():
            assert stat.category_size is not None, "Missing category size in filtering"
            if stat.category_size < min_size:
                to_delete.append(category)
        # delete the categories afterwards
        for category in to_delete:
            del self.statistics[category]
        logging.info(f"Removed {len(to_delete)} out of {total} categories (too small).")

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

    def get_category_sizes_df(self, attribute_for_pivot: str = "") -> pd.DataFrame:
        """
        Collects the category sizes for this statistics object in
        a single dataframe. Optionally, an attribute for pivoting the data can be
        chosen to allow comparing some categories more easily.

        :param attribute_for_pivot: optionally, specifies an attribute for pivoting;
                                    its values will each create their own column in
                                    the sizes dataframe, making it more readable
        :return: a dataframe containing the category sizes
        """
        # get any profile type to determine the attribute names in use
        any_profile_type = next(iter((self.statistics.values()))).profile_type
        names = any_profile_type.get_attribute_names()
        # collect the profile type attributes for each category
        index = pd.MultiIndex.from_tuples(
            [pt.to_list() for pt in self.statistics.keys()], names=names
        )
        # collect the category sizes
        sizes = [stat.category_size for stat in self.statistics.values()]
        colname = "Sizes"
        sizes_df = pd.DataFrame({colname: sizes}, index=index)
        if index.nlevels > 1 and attribute_for_pivot:
            # more than one profile type attribute: restructure dataframe for readability
            # this however leads to one index title missing in the csv file, which can then
            # not be loaded anymore
            sizes_df.reset_index(inplace=True)
            cols = list(sizes_df.columns)
            assert (
                attribute_for_pivot in cols
            ), f"Invalid attribute for pivot: {attribute_for_pivot}"
            cols.remove(attribute_for_pivot)
            cols.remove(colname)
            sizes_df = sizes_df.pivot(
                index=cols, columns=attribute_for_pivot, values=colname
            )
        return sizes_df

    @utils.timing
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

        # save category sizes to file; this version is used to load the sizes
        category_sizes = self.get_category_sizes_df()
        save_df(
            category_sizes,
            ValidationSet.CATEGORIES_DIR,
            ValidationSet.CATEGORY_SIZES_FILE,
            base_path=base_path,
        )
        # additionally, save a more readable category sizes version
        category_sizes = self.get_category_sizes_df(Country.title())
        save_df(
            category_sizes,
            ValidationSet.CATEGORIES_DIR,
            "category_sizes_readable",
            base_path=base_path,
        )
        # additionally, save another version to compare the distribution of day types
        category_sizes = self.get_category_sizes_df(DayType.title())
        save_df(
            category_sizes,
            ValidationSet.CATEGORIES_DIR,
            "category_sizes_day_type",
            base_path=base_path,
        )

    @staticmethod
    def load_category_sizes(base_path: Path) -> dict[ProfileCategory, int]:
        sizes = pd.read_csv(
            base_path / ValidationSet.CATEGORIES_DIR / ValidationSet.CATEGORY_SIZES_FILE
        )
        # the last column contains the sizes, the others the profile type attributes
        pt_names = sizes.columns[:-1]
        category_sizes = {
            ProfileCategory.from_index_tuple(pt_names, values[:-1]): values[-1]
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
    ) -> dict[ProfileCategory, pd.DataFrame]:
        return {
            ProfileCategory.from_filename(p): load_df(p, as_timedelta)
            for p in path.iterdir()
            if p.is_file()
        }

    @utils.timing
    @staticmethod
    def load(base_path: Path) -> "ValidationSet":
        assert base_path.is_dir(), f"Statistics directory not found: {base_path}"
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
        ), "Missing statistics for some of the profile categories"

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
        logging.info(f"Loaded statistics for {len(statistics)} profile categories")

        # load activities
        activities = ValidationSet.load_activities(base_path)
        return ValidationSet(statistics, activities)
