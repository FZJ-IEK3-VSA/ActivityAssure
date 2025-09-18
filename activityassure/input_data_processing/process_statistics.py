"""Functions for adapting already created sets of activity statistics"""

from activityassure import activity_mapping, categorization_attributes
from activityassure.categorization_attributes import WorkStatus
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationSet

from pathlib import Path


def merge_activities_from_file(
    statistics_path: Path, merging_path: Path, new_path: Path | None = None
):
    """
    Load validation statistics and merges activities according to the specified file.
    The translated statistics are then saved with a new name.

    :param statistics_path: path of validation statistics to adapt
    :param merging_path: path of the merging file to use
    :param new_name: new name for the adapted statistics, by default appends "_mapped"
    """
    # load statistics and merging map and apply the merging
    validation_statistics = ValidationSet.load(statistics_path)
    merge_activities(validation_statistics, merging_path)
    # determine the new file name for the mapped statistics
    new_path = new_path or Path(f"{statistics_path}_mapped")
    # save the mapped statistics
    validation_statistics.save(new_path)


def merge_activities(validation_statistics: ValidationSet, merging_path: Path):
    """
    Merge activities in a validation statistics set according to the specified file.

    :param validation_statistics: the validation statistics to adapt
    :param merging_path: path of the merging file to use
    """
    mapping, _ = activity_mapping.load_mapping_and_activities(merging_path)
    validation_statistics.map_statistics_activities(mapping)


def merge_unemployed_categories_from_file(data_path: Path, result_path: Path):
    """Merge categories for work days and non-working days of unemployed and retired
    people.

    :param data_path: path of the original statistics
    :param result_path: target path for the merged statistics
    """
    # load the statistics
    validation_set = ValidationSet.load(data_path)
    merge_unemployed_categories(validation_set)
    # save the aggregated statistics
    validation_set.save(result_path)


def merge_unemployed_categories(validation_set: ValidationSet):
    """Merge categories for work days and non-working days of unemployed and retired
    people.

    :param validation_set: the statistics to merge
    """
    # combine all 'unemployed' and 'retired' categories which only differ in day type
    WORK_TYPES_TO_MERGE = [WorkStatus.unemployed, WorkStatus.retired]
    mapping = {
        p: ProfileCategory(
            p.country,
            p.sex,
            p.work_status,
            categorization_attributes.DayType.undetermined,
        )
        for p in validation_set.statistics.keys()
        if p.work_status in WORK_TYPES_TO_MERGE
    }
    validation_set.merge_profile_categories(mapping)


def aggregate_to_national_level(validation_data_path: Path, result_path):
    """
    Aggregates statistics of all profile types of the same country. Saves
    the aggreagted per-country statistics as a new validation data set.

    :param validation_data_path: path to the validation statistics to aggregate
    :param result_path: result filepath to save the aggregated statistics
    """
    # load the statistics
    set = ValidationSet.load(validation_data_path)
    # aggregate them to national level
    mapping = {p: ProfileCategory(p.country) for p in set.statistics.keys()}
    set.merge_profile_categories(mapping)
    # save the aggregated statistics
    set.save(result_path)
