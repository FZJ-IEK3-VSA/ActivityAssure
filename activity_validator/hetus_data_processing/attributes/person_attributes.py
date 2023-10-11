"""
Calculates additional attributes for persons which can then be used for categorization
"""

from enum import Enum, IntEnum
import logging
import pandas as pd

from activity_validator.hetus_data_processing import utils
import activity_validator.hetus_data_processing.hetus_columns as col
import activity_validator.hetus_data_processing.hetus_values as val
from activity_validator.hetus_data_processing.attributes.diary_attributes import (
    Categories,
)


class WorkStatus(IntEnum):
    full_time = 0
    part_time = 1
    unemployed = 2
    retired = 3
    student = 4

    undetermined = -1
    work_full_or_part = -2
    unemployed_or_retired = -3


MAP_WORKSTATUS = {
    val.WorkStatus.work_full: WorkStatus.full_time,
    val.WorkStatus.work_part: WorkStatus.part_time,
    val.WorkStatus.on_leave: WorkStatus.work_full_or_part,
    val.WorkStatus.unemployed: WorkStatus.unemployed_or_retired,
    val.WorkStatus.student: WorkStatus.student,
}
MAP_LABORSTATUS = {
    val.SelfDeclLaborStatus.employed: WorkStatus.work_full_or_part,
    val.SelfDeclLaborStatus.unemployed: WorkStatus.unemployed,
    val.SelfDeclLaborStatus.student: WorkStatus.student,
    val.SelfDeclLaborStatus.retirement: WorkStatus.retired,
    val.SelfDeclLaborStatus.military_or_community_service: WorkStatus.work_full_or_part,
    val.SelfDeclLaborStatus.domestic_tasks: WorkStatus.unemployed,
    val.SelfDeclLaborStatus.other_inactive: WorkStatus.unemployed,
}
MAP_FULLORPARTTIME = {
    val.FullOrPartTime.full_time: WorkStatus.full_time,
    val.FullOrPartTime.part_time: WorkStatus.part_time,
}


def initial_work_status(row: pd.Series) -> WorkStatus:
    # get values of the relevant columns and map them to the destination enum
    work_status = MAP_WORKSTATUS.get(
        row[col.Person.WORK_STATUS], WorkStatus.undetermined
    )
    labour_status = MAP_LABORSTATUS.get(
        row[col.Person.SELF_DECL_LABOUR_STATUS], WorkStatus.undetermined
    )

    if work_status == labour_status:
        # both columns match
        return work_status

    # if one column is only partly determined, choose the other one
    if work_status >= 0 and labour_status < 0:
        return work_status
    if labour_status >= 0 and work_status < 0:
        return labour_status
    # if one column is undetermined, choose the other one
    if work_status == WorkStatus.undetermined:
        return labour_status
    if labour_status == WorkStatus.undetermined:
        return work_status

    # columns have different values - check if combination is plausible
    if work_status == WorkStatus.unemployed and labour_status == WorkStatus.retired:
        return WorkStatus.retired

    # could not unambiguously determine work status
    return WorkStatus.undetermined


def determine_work_status(row: pd.Series) -> WorkStatus:
    status = initial_work_status(row)
    if status == WorkStatus.work_full_or_part:
        # try to determine if working full or part time using another column
        if row[col.Person.FULL_OR_PART_TIME] > 0:
            pass
        return MAP_FULLORPARTTIME.get(
            row[col.Person.FULL_OR_PART_TIME], WorkStatus.work_full_or_part
        )
    if status == WorkStatus.unemployed_or_retired:
        # try to determine if retired
        # TODO check for retirement
        return WorkStatus.unemployed_or_retired
    return status


@utils.timing
def determine_work_statuses(persondata: pd.DataFrame) -> pd.Series:
    results = persondata.apply(determine_work_status, axis=1)
    results.name = Categories.work_status
    counts = results.value_counts()
    determined = counts[counts.index >= 0].sum()
    logging.info(
        f"Determined working status for {determined} out of "
        f"{len(persondata)} persons ({100 * determined / len(persondata):.1f} %)"
    )
    return results

    # If no information about work is there, check diary entries:
    # For each row, count the number of Work code occurrences and multiply by 10 minutes
    # for each diary entry, determine the work status depending on the worked hours
    # determine the state out of all entries for a person: weekends etc. don't matter,
    # if there are days with work, the person is a worker, all other days are then assumed to be free
    # if the working times differ, use the most frequent one. In doubt, maybe the total share of worked time may help?
