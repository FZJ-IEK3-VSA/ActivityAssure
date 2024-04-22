"""
Calculates additional attributes for HETUS diary entries which can
then be used for categorization.
"""

from datetime import timedelta
import logging
import pandas as pd

import activity_validator.hetus_data_processing.hetus_column_names as col
import activity_validator.hetus_data_processing.hetus_column_values as val
from activity_validator.hetus_data_processing import hetus_constants
from activity_validator.categorization_attributes import (
    DayType,
)
from activity_validator import utils


MAP_DAYTYPE = {
    val.DayType.work: DayType.work,
    val.DayType.school: DayType.work,
    val.DayType.day_off: DayType.no_work,
    val.DayType.sick: DayType.no_work,
    val.DayType.vacation: DayType.no_work,
    val.DayType.on_leave: DayType.no_work,
}
MAP_EMPLOYEDSTUDENT = {
    val.EmployedStudent.yes: DayType.work,
    val.EmployedStudent.no: DayType.no_work,
}

#: activities that should be counted as work for determining work days
# TODO find a more flexible way for this
WORK_ACTIVITIES = ["work", "education"]
#: minimum working time for a day to be counted as working day
WORKTIME_THRESHOLD = timedelta(hours=3)


def determine_day_type(row: pd.Series) -> DayType:
    """
    Determines the day type for a single diary.

    :param row: the diary row
    :return: the determined day type
    """
    # get values of the relevant columns and map them to the destination enum
    if row[col.Diary.DAYTYPE] >= 0:
        return MAP_DAYTYPE[row[col.Diary.DAYTYPE]]
    if row[col.Diary.EMPLOYED_STUDENT] >= 0:
        return MAP_EMPLOYEDSTUDENT[row[col.Diary.EMPLOYED_STUDENT]]
    return DayType.undetermined


@utils.timing
def determine_day_types(data: pd.DataFrame) -> pd.Series:
    """
    Determines the day type for each diary entry

    :param data: HETUS data
    :return: day type for each diary entry
    """
    # determine the working time threshold for deciding on the day type
    country = data.index.get_level_values(col.Country.ID)[0]
    min_time_slots = WORKTIME_THRESHOLD / hetus_constants.get_resolution(country)
    # get the number of work time slots per diary entry
    activities = col.get_activity_data(data)
    work_time_slot_numbers = activities[activities.isin(WORK_ACTIVITIES)].count(axis=1)
    # determine day type based on number of work activity entries
    work = work_time_slot_numbers > min_time_slots
    day_types = pd.Series(index=work_time_slot_numbers.index, dtype=str)
    day_types.loc[work] = DayType.work
    day_types.loc[~work] = DayType.no_work

    day_types.name = DayType.title()
    counts = day_types.value_counts()
    determined = counts[counts.index != DayType.undetermined].sum()
    logging.info(
        f"Determined day type for {determined} out of "
        f"{len(data)} diary entries ({100 * determined / len(data):.1f} %)"
    )
    # print_day_type_weekday_overview(data, day_types)
    return day_types
