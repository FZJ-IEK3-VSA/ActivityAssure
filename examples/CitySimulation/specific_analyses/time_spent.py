"""
Analyzes differences in time share per activity between LPG and HETUS, using the time spent plot.
"""

from pathlib import Path

from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationSet
from activityassure import categorization_attributes

from activityassure.visualizations import time_statistics


def overwrite_country(data: ValidationSet, new_country: str):
    """Helper function to overwrite the country in all profile categories of
    a data set. This can be useful to compare different data sets for the
    same country.

    :param data: the data set to adapt
    :param new_country: the new country to set
    """
    new_stats = {}
    for k, v in data.statistics.items():
        new_profile = ProfileCategory(new_country, k.sex, k.work_status, k.day_type)
        v.profile_type = new_profile
        new_stats[new_profile] = v
    data.statistics = new_stats


def merge_unemployed_categories(data: ValidationSet):
    # combine all 'unemployed' and 'retired' categories which only differ in day type
    WORK_TYPES_TO_MERGE = [
        categorization_attributes.WorkStatus.unemployed,
        categorization_attributes.WorkStatus.retired,
    ]
    mapping = {
        p: ProfileCategory(
            p.country,
            p.sex,
            p.work_status,
            categorization_attributes.DayType.undetermined,
        )
        for p in data.statistics.keys()
        if p.work_status in WORK_TYPES_TO_MERGE
    }
    data.merge_profile_categories(mapping)


if __name__ == "__main__":
    path1 = Path("data/validation_data_sets/activity_validation_data_set_merged")
    path2 = Path(
        "R:/city_simulation_results/scenario_julich_1week_old/Postprocessed/activityassure_statistics_merged"
    )

    # load validation and LPG statistics, merge unemployed categories and replace the country for the plot
    data1 = ValidationSet.load(path1, "DE")
    merge_unemployed_categories(data1)
    overwrite_country(data1, "TUS")
    data2 = ValidationSet.load(path2, "DE")
    merge_unemployed_categories(data2)
    overwrite_country(data2, "LPG")

    plot_dir = Path()
    time_statistics.plot_total_time_spent(
        data1.statistics, data2.statistics, plot_dir, True
    )
