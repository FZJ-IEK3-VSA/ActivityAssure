"""
Calculates additional attributes for HETUS persons which can then
be used for categorization.
"""

import logging
import pandas as pd

from activityassure import utils
import activityassure.hetus_data_processing.hetus_column_names as col
import activityassure.hetus_data_processing.hetus_column_values as val
from activityassure.categorization_attributes import (
    WorkStatus,
    Sex,
    Country,
)


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

MAP_SEX = {
    val.Sex.male: Sex.male,
    val.Sex.female: Sex.female,
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
    if work_status.is_determined() and not labour_status.is_determined():
        return work_status
    if labour_status.is_determined() and not work_status.is_determined():
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
        return MAP_FULLORPARTTIME.get(
            row[col.Person.FULL_OR_PART_TIME], WorkStatus.work_full_or_part
        )
    if status == WorkStatus.unemployed_or_retired:
        # try to determine if retired or unemployed
        # This only occurs for a single person in the whole HETUS 2010 data set
        return WorkStatus.unemployed_or_retired
    return status


@utils.timing
def determine_work_statuses(persondata: pd.DataFrame) -> pd.Series:
    results = persondata.apply(determine_work_status, axis=1)
    results.name = WorkStatus.title()
    counts = results.value_counts()
    determined = counts[
        counts.index.to_series().apply(lambda x: x.is_determined())
    ].sum()
    logging.info(
        f"Determined working status for {determined} out of "
        f"{len(persondata)} persons ({100 * determined / len(persondata):.1f} %)"
    )
    return results


def determine_sex(persondata: pd.DataFrame) -> pd.Series:
    # translate column title and values
    results = persondata[col.Person.SEX].replace(MAP_SEX)
    results.rename(Sex.title(), inplace=True)
    return results


def determine_country(persondata: pd.DataFrame) -> pd.Series:
    # simply gets the COUNTRY index level
    country = persondata.index.get_level_values(col.Country.ID)
    return country.to_series(persondata.index, name=Country.title())
