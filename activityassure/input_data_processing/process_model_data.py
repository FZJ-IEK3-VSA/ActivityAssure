"""
Functions for the whole input data processing, starting from loading
data files and resulting in a complete validation statistics set.
"""

from datetime import timedelta
from pathlib import Path
from activityassure import activity_mapping, utils
from activityassure.activity_profile import (
    ExpandedActivityProfiles,
    SparseActivityProfile,
)
from activityassure.hetus_data_processing import category_statistics
from activityassure.input_data_processing import load_model_data, prepare_model_data
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationSet, ValidationStatistics


def calc_input_data_statistics(
    profiles: list[SparseActivityProfile], activity_types: list[str]
) -> ValidationStatistics:
    """
    Calculates statistics for the input data of a specific profile category

    :param profiles: sparse activity profiles of the same type
    :param activity_types: list of possible activity names
    :return: the calculated statistics
    """
    frequencies = category_statistics.calc_activity_group_frequencies(profiles)
    durations = category_statistics.calc_activity_group_durations(profiles)
    # convert to expanded format
    profile_set = ExpandedActivityProfiles.from_sparse_profiles(profiles)
    probabilities = category_statistics.calc_probability_profiles(
        profile_set.data, activity_types
    )
    # store all statistics in one object
    input_data = ValidationStatistics(
        profiles[0].profile_type, probabilities, frequencies, durations, len(profiles)
    )
    return input_data


@utils.timing
def calc_statistics_per_category(
    input_data_dict: dict[ProfileCategory, list[SparseActivityProfile]],
    activities: list[str],
) -> ValidationSet:
    """
    Calculates statistics per category

    :param input_data_dict: input activity profiles per category
    :param activities: list of possible activities
    :return: data statistics per category
    """
    # validate each profile type individually
    input_statistics = {}
    for profile_type, profiles in input_data_dict.items():
        # calculate and store statistics for validation
        input_data = calc_input_data_statistics(profiles, activities)
        input_statistics[profile_type] = input_data
    statistics_set = ValidationSet(input_statistics, activities)
    return statistics_set


@utils.timing
def process_model_data(
    input_path: Path,
    mapping_path: Path,
    person_trait_file: Path,
    resolution: timedelta,
    validation_activities: list[str] = [],
    categories_per_person: bool = False,
) -> ValidationSet:
    """
    Processes the input data to produce the validation statistics.

    :param input_path: input data directory
    :param output_path: destination path for validation statistics
    :param mapping_path: path to the activity mapping file
    :param person_trait_file: path to the person trait file
    :param validation_activities: optionally, the activities list of the validation
                                  data can be passed to get the same list, which
                                  makes comparison easier
    :param categories_per_person: if True, the person names will be part of the
                                  person categorization, meaning that each person
                                  will get their own categories; defaults to False
    """
    # load and preprocess all input data
    full_year_profiles = load_model_data.load_activity_profiles_from_csv(
        input_path, person_trait_file, resolution, categories_per_person
    )
    mapping, activities = activity_mapping.load_mapping_and_activities(mapping_path)
    # check if the activity list matches that of the validation statistics
    if validation_activities != activities:
        activities = activity_mapping.check_activity_lists(
            activities, validation_activities
        )
    input_data_dict = prepare_model_data.prepare_input_data(full_year_profiles, mapping)
    # calc and save input data statistics
    statistics_set = calc_statistics_per_category(input_data_dict, activities)
    return statistics_set
