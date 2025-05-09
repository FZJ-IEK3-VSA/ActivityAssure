"""
Defines classes for storing and handling activity profile validation data.
"""

from collections import defaultdict
from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Callable, ClassVar, Iterable

import numpy as np
import pandas as pd

from activityassure import utils
from activityassure.categorization_attributes import Country, DayType
from activityassure.profile_category import PersonProfileCategory, ProfileCategory
from activityassure.pandas_utils import (
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
    category_weight: float | None = None

    # subdirectory names for file storage
    PROBABILITY_PROFILE_DIR: ClassVar = "probability_profiles"
    FREQUENCY_DIR: ClassVar = "activity_frequencies"
    DURATION_DIR: ClassVar = "activity_durations"

    def __post_init__(self):
        # check activity lists in all dataframes
        if not (
            set(self.probability_profiles.index)
            == set(self.activity_frequencies.columns)
            == set(self.activity_durations.columns)
        ):
            logging.info(
                f"Activity lists in {self.profile_type} did not match. Extending to make them consistent."
            )
            # determine the total lsit of activities
            activities = list(
                self.probability_profiles.index.union(
                    self.activity_frequencies.columns
                ).union(self.activity_durations.columns)
            )
            self.extend_for_missing_activities(activities)

        # check if all dataframes are normalized
        # use a larger tolerance to allow for rounding errors when merging categories with weights
        tolerance = 1e-4
        assert np.isclose(self.activity_frequencies.sum(), 1, atol=tolerance).all()
        assert np.isclose(self.activity_durations.sum(), 1, atol=tolerance).all()
        assert (
            np.isclose(self.probability_profiles.sum(), 1, atol=tolerance)
            | np.isclose(self.probability_profiles.sum(), 0, atol=tolerance)
        ).all()

    def has_weight(self) -> bool:
        """
        Returns whether a weight is set for this profile category.

        :return: True if a weight is set, False otherwise
        """
        return self.category_weight is not None and not pd.isna(self.category_weight)

    def get_weight(self) -> float:
        """
        Returns the weight of the profile category. If no weight is set, 1 is returned.

        :return: the weight of the profile category
        """
        if self.has_weight():
            return self.category_weight  # type: ignore[return-value]
        return 1

    def get_activities(self) -> list[str]:
        """
        Returns the list of activities for this profile category.

        :return: the list of activities
        """
        return self.probability_profiles.index.tolist()

    def extend_for_missing_activities(self, activities: list[str]):
        """
        Extends the statistics dataframes to include missing activities. The
        statistics are adapted assuming that the new activities never occurred for
        this category.
        Any activities not specified in the list are still kept in the dataframes.

        :param activities: the full list of activities to include
        """
        # determine which activities are new for which dataframes (freq and duration should be the same)
        new_for_freq = self.activity_frequencies.columns.symmetric_difference(
            activities
        )
        new_for_prob = self.probability_profiles.index.symmetric_difference(activities)
        if len(new_for_freq) == 0 and len(new_for_prob) == 0:
            # no new activities to add
            return
        # determine the full set of activities, including both old and new ones, keeping the original order
        combined_activities = self.probability_profiles.index.append(new_for_prob)

        # add new activities with probability 0 (as these activities never occurred)
        self.probability_profiles = self.probability_profiles.reindex(
            combined_activities, fill_value=0
        )

        # the activity durations cannot be extended, as no matching activity durations exist

        # extend the activity frequencies
        freq = self.activity_frequencies.reindex(
            columns=combined_activities, fill_value=0
        )
        # add a row for frequency 0 if it does not exist yet
        freq = freq.reindex(freq.index.union([0]), fill_value=0)
        # set the probability for frequency 0 to 100% for the new activities
        freq.loc[0, new_for_freq] = 1.0
        self.activity_frequencies = freq

    def save(self, base_path: Path):
        """
        Saves all contained statistics to separate files

        :param base_path: the base path to store the
                          data at
        """
        save_df(
            self.activity_frequencies,
            base_path / ValidationStatistics.FREQUENCY_DIR,
            "freq",
            self.profile_type,
        )
        save_df(
            self.activity_durations,
            base_path / ValidationStatistics.DURATION_DIR,
            "dur",
            self.profile_type,
        )
        save_df(
            self.probability_profiles,
            base_path / ValidationStatistics.PROBABILITY_PROFILE_DIR,
            "prob",
            self.profile_type,
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
            base_path / ValidationStatistics.FREQUENCY_DIR, "freq", profile_type
        )
        dur_path = create_result_path(
            base_path / ValidationStatistics.DURATION_DIR, "dur", profile_type
        )
        prob_path = create_result_path(
            base_path / ValidationStatistics.PROBABILITY_PROFILE_DIR,
            "prob",
            profile_type,
        )
        if not (freq_path.is_file() and dur_path.is_file() and prob_path.is_file()):
            raise RuntimeError(
                f"Did not find all files for profile type {str(profile_type)} in base directory "
                f"{base_path}"
            )
        freq = load_df(freq_path)
        dur = load_df(dur_path, True)
        prob = load_df(prob_path)
        return ValidationStatistics(profile_type, prob, freq, dur, size)

    @staticmethod
    def merge_statistics(
        statistics: Iterable["ValidationStatistics"],
        profile_type: ProfileCategory,
    ) -> "ValidationStatistics":
        """
        Merges multiple ValidationStatistics into one.
        The resulting statistics contain the weighted averages of all activity frequencies, durations,
        and probability profiles.

        :param statistics: the statistics to merge
        :param profile_type: the profile category of the resulting statistics
        :return: the merged statistics
        """
        # collect the combined list of activities
        activities = {act for stat in statistics for act in stat.get_activities()}
        # extend the statistics to ensure they all include the same activities
        for stat in statistics:
            stat.extend_for_missing_activities(list(activities))

        total_weight = sum(stat.get_weight() for stat in statistics)
        durations = []
        frequencies = []
        probabilities = []
        for stat in statistics:
            factor = stat.get_weight() / total_weight
            dur = stat.activity_durations * factor
            durations.append(dur)
            freq = stat.activity_frequencies * factor
            frequencies.append(freq)
            prob = stat.probability_profiles * factor
            probabilities.append(prob)

        merged_dur = pd.concat(durations).groupby(level=0).sum()
        # durations need to be normalized in case activities were missing in some categories
        merged_dur = merged_dur / merged_dur.sum()
        merged_freq = pd.concat(frequencies).groupby(level=0).sum()
        merged_prob = pd.concat(probabilities).groupby(level=0).sum()
        total_size = sum(stat.category_size or 1 for stat in statistics)
        return ValidationStatistics(
            profile_type, merged_prob, merged_freq, merged_dur, total_size, total_weight
        )


@dataclass
class ValidationSet:
    """
    A full validation data set, including statistics for all profile
    types and common metadata.

    When saving a ValidationSet, it is stored as a directory. The data from
    each contained statistics object is stored in multiple files, and common
    information on all statistics objects, e.g. sizes and weights, is collected
    and stored in single DataFrame csv files, to give a better overview.
    """

    statistics: dict[ProfileCategory, ValidationStatistics]
    activities: list[str]

    # directory and file names for file storage
    CATEGORIES_DIR: ClassVar = "categories"
    CATEGORY_SIZES_FILE: ClassVar = "category_sizes.csv"
    CATEGORY_WEIGHTS_FILE: ClassVar = "category_weights.csv"
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
        assert size_ranges == sorted(size_ranges), (
            "Unclear parameter: size_ranges must be sorted"
        )
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
        translated = [mapping.get(a, a) for a in self.activities]
        # remove duplicates while keeping order
        self.activities = list(dict.fromkeys(translated))
        for data in self.statistics.values():
            data.map_activities(mapping)

    def merge_profile_categories(self, mapping: dict[ProfileCategory, ProfileCategory]):
        """
        Merge multiple profile categories into one. The mapping is a dict that maps each profile category
        to merge to its respective target category. The target category must not exist yet.

        :param mapping: dict mapping old categories to new categories
        :raises ActValidatorException: if the validation set has inconsistent weights
        """
        # group all current categories by their common new category
        category_groups = defaultdict(list)
        for old_category, new_category in mapping.items():
            assert old_category in self.statistics, (
                f"Invalid mapping: category {old_category} not found"
            )
            assert new_category not in self.statistics, (
                f"Invalid mapping: statistics for the target category {new_category} already exist"
            )
            category_groups[new_category].append(old_category)

        # check if weight are set consistently
        weights_set = [stat.has_weight() for stat in self.statistics.values()]
        if any(weights_set) and not all(weights_set):
            raise utils.ActValidatorException(
                "Cannot merge profile categories, because some categories have weights, and others do not."
            )

        # merge each group of statistics
        for new_category, old_categories in category_groups.items():
            statistics_to_merge = [self.statistics[cat] for cat in old_categories]
            merged = ValidationStatistics.merge_statistics(
                statistics_to_merge, new_category
            )
            # remove the old categories from the statistics dict
            for cat in old_categories:
                del self.statistics[cat]
            # add the new category to the statistics dict
            self.statistics[new_category] = merged

    def pivot_dataframe(
        self, data: pd.DataFrame, attribute_for_pivot: str
    ) -> pd.DataFrame:
        """
        Pivots the DataFrame if it has a MultiIndex and only one column, so that one of the index
        levels is instead represented in the form of columns. This is helpful to make long
        DataFrames with a single column more readable.
        The name of the attribute used for pivoting is however not contained in the resulting
        csv file anymore, so a file created from the resulting DataFrame cannot be loaded again.

        :param data: the DataFrame to transform
        :param attribute_for_pivot: the attribute in the index to move to columns
        :return: the transformed DataFrame
        """
        assert len(data.columns) == 1, "DataFrame must have one column only"
        colname = data.columns[0]
        if data.index.nlevels == 1 or attribute_for_pivot not in data.index.names:
            logging.warning(
                f"The DataFrame only has one index level or the attribute '{attribute_for_pivot}'"
                "is not part of the categorization. Returning the unpivoted dataframe instead."
            )
            return data
        # this however leads to one index title missing in the csv file, which can then
        # not be loaded anymore
        data_reset = data.reset_index()
        cols = list(data_reset.columns)
        assert attribute_for_pivot in cols, (
            f"Invalid attribute for pivot: {attribute_for_pivot}"
        )
        cols.remove(attribute_for_pivot)
        cols.remove(colname)
        transformed = data_reset.pivot(
            index=cols, columns=attribute_for_pivot, values=colname
        )
        return transformed

    def get_category_info_dataframe(
        self, column_name: str, func: Callable[[ValidationStatistics], Any]
    ) -> pd.DataFrame:
        """
        Collects a specific value (e.g. size) for each profile category and combines
        all values in a single dataframe.

        :param column_name: the name of the value, used as column header
        :param func: the function to get the value; is called on each ValidationStatistics
                     object separately
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
        sizes = [func(stat) for stat in self.statistics.values()]
        sizes_df = pd.DataFrame({column_name: sizes}, index=index)
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
            base_path / ValidationSet.ACTIVITIES_DIR,
            ValidationSet.ACTIVITIES_FILE,
            ext="",
        )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {ValidationSet.AVAILABLE_ACTIVITIES_KEY: self.activities}, f, indent=4
            )

        # save category sizes and weights to file; this version is used to load the sizes
        category_sizes = self.get_category_info_dataframe(
            "Sizes", lambda stat: stat.category_size
        )
        category_weights = self.get_category_info_dataframe(
            "Weights", lambda stat: stat.category_weight
        )
        save_df(
            category_sizes,
            base_path / ValidationSet.CATEGORIES_DIR,
            ValidationSet.CATEGORY_SIZES_FILE,
        )
        save_df(
            category_weights,
            base_path / ValidationSet.CATEGORIES_DIR,
            ValidationSet.CATEGORY_WEIGHTS_FILE,
        )
        # additionally, save a more readable category sizes version
        category_sizes_readable = self.pivot_dataframe(category_sizes, Country.title())
        save_df(
            category_sizes_readable,
            base_path / ValidationSet.CATEGORIES_DIR,
            "category_sizes_readable",
        )
        # additionally, save another version to compare the distribution of day types
        category_sizes_day_type = self.pivot_dataframe(category_sizes, DayType.title())
        save_df(
            category_sizes_day_type,
            base_path / ValidationSet.CATEGORIES_DIR,
            "category_sizes_day_type",
        )

    @staticmethod
    def load_category_info_dataframe(path: Path) -> dict[ProfileCategory, int]:
        """
        Loads a DataFrame from csv which contains one value per profile category.
        The value can e.g. be a size or a weight. Returns a dict for easy access.

        :param path: path of the csv file
        :return: a dict mapping each profile category to its value from the file
        """
        data = pd.read_csv(path)
        # the last column contains the values, the others the profile type attributes
        pt_names = data.columns[:-1]
        values = {
            ProfileCategory.from_index_tuple(pt_names, values[:-1]): values[-1]
            for values in data.itertuples(index=False)
        }
        return values

    @staticmethod
    def load_activities(base_path: Path) -> list[str]:
        """
        Loads the list of available activities from the json file.

        :param base_path: base path of the data set
        :return: list of activities
        """
        with open(
            base_path / ValidationSet.ACTIVITIES_DIR / ValidationSet.ACTIVITIES_FILE
        ) as f:
            content = json.load(f)
        return content[ValidationSet.AVAILABLE_ACTIVITIES_KEY]

    @staticmethod
    def load_validation_data_subdir(
        path: Path, as_timedelta: bool = False
    ) -> dict[ProfileCategory, pd.DataFrame]:
        """
        Loads all statistics from one subdirectory of the data set, e.g.
        only the activity frequencies.

        :param path: the full path of the subdirectory to load
        :param as_timedelta: whether the data to load contains time data (should be True for
                             durations); defaults to False
        :return: a dict of loaded statistics DataFrames, one per profile category
        """
        return {
            ProfileCategory.from_filename(p): load_df(p, as_timedelta)
            for p in path.iterdir()
            if p.is_file()
        }

    @utils.timing
    @staticmethod
    def load(base_path: Path) -> "ValidationSet":
        assert base_path.is_dir(), f"Statistics directory not found: {base_path}"
        # load the statistics per profile category
        prob_path = base_path / ValidationStatistics.PROBABILITY_PROFILE_DIR
        freq_path = base_path / ValidationStatistics.FREQUENCY_DIR
        dur_path = base_path / ValidationStatistics.DURATION_DIR
        prob_data = ValidationSet.load_validation_data_subdir(prob_path)
        freq_data = ValidationSet.load_validation_data_subdir(freq_path)
        dur_data = ValidationSet.load_validation_data_subdir(dur_path, True)

        # load further info (size, weight) from single csv files
        sizes_path = (
            base_path / ValidationSet.CATEGORIES_DIR / ValidationSet.CATEGORY_SIZES_FILE
        )
        weights_path = (
            base_path
            / ValidationSet.CATEGORIES_DIR
            / ValidationSet.CATEGORY_WEIGHTS_FILE
        )
        category_sizes = ValidationSet.load_category_info_dataframe(sizes_path)
        category_weights = ValidationSet.load_category_info_dataframe(weights_path)

        assert (
            prob_data.keys()
            == freq_data.keys()
            == dur_data.keys()
            == category_sizes.keys()
            == category_weights.keys()
        ), "Missing statistics for some of the profile categories"

        # assemble the ValidationStatistics objects from the data dicts
        statistics = {
            profile_type: ValidationStatistics(
                profile_type,
                prob_data[profile_type],
                freq_data[profile_type],
                dur_data[profile_type],
                category_sizes[profile_type],
                category_weights[profile_type],
            )
            for profile_type in prob_data.keys()
        }
        logging.info(f"Loaded statistics for {len(statistics)} profile categories")

        # load activity list
        activities = ValidationSet.load_activities(base_path)
        return ValidationSet(statistics, activities)
