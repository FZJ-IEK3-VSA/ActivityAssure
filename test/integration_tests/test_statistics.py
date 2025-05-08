"""
Contains functions for testing the validity of statistics objects
"""

from activityassure.validation_statistics import ValidationStatistics


def check_validation_statistics_size(
    statistics: ValidationStatistics, activities: list[str]
):
    """
    Checks if the rows/columns of the statistics dataframes match the activities

    :param statistics: statistics object
    :param activities: activities list
    """
    assert list(statistics.probability_profiles.index) == activities, (
        "Wrong probabilities row labels"
    )
    assert set(statistics.activity_durations.columns).issubset(activities), (
        "Wrong durations column labels"
    )
    assert set(statistics.activity_frequencies.columns).issubset(activities), (
        "Wrong frequencies column labels"
    )
