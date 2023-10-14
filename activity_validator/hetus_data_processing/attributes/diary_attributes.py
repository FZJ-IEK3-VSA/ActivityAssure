"""
Calculates additional attributes for diary entries which can then be used for categorization
"""

from enum import StrEnum  # type: ignore
import logging
import pandas as pd

import activity_validator.hetus_data_processing.hetus_columns as col
import activity_validator.hetus_data_processing.hetus_values as val
from activity_validator.hetus_data_processing import utils


class DayType(StrEnum):
    """
    Specifies the day type of a diary entry
    """

    work = "work"
    no_work = "no work"

    undetermined = "undetermined"

    @staticmethod
    def title() -> str:
        return "day type"


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


def determine_day_type(row: pd.Series) -> DayType:
    # get values of the relevant columns and map them to the destination enum
    if row[col.Diary.DAYTYPE] >= 0:
        return MAP_DAYTYPE[row[col.Diary.DAYTYPE]]
    if row[col.Diary.EMPLOYED_STUDENT] >= 0:
        return MAP_EMPLOYEDSTUDENT[row[col.Diary.EMPLOYED_STUDENT]]

    # TODO: if necessary, check working time on this diary entry
    return DayType.undetermined


def print_day_type_weekday_overview(data: pd.DataFrame, day_types: pd.Series):
    """
    Prints an overview on how many work and non-work days were determined depending
    on the weekday.

    :param data: HETUS data
    :param day_types: determined day types
    """
    weekday_map = {i: "weekday" for i in range(2, 7)}
    weekday_map[1] = "sunday"
    weekday_map[7] = "saturday"
    weekdays = data[col.Diary.WEEKDAY].map(weekday_map)
    merged = pd.concat([weekdays, day_types], axis=1)
    print(merged.groupby([col.Diary.WEEKDAY, DayType.title()]).size())


@utils.timing
def determine_day_types(data: pd.DataFrame) -> pd.Series:
    """
    Determines the day type for each diary entry

    :param data: HETUS data
    :return: day type for each diary entry
    """
    day_types = data.apply(determine_day_type, axis=1)
    day_types.name = DayType.title()
    counts = day_types.value_counts()
    determined = counts[counts.index != DayType.undetermined].sum()
    logging.info(
        f"Determined day type for {determined} out of "
        f"{len(data)} diary entries ({100 * determined / len(data):.1f} %)"
    )
    # print_day_type_weekday_overview(data, day_types)
    return day_types
