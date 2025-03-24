"""
Functions for checking availability of data in some columns and share of certain
special cases.
"""

import logging
import activityassure.hetus_data_processing.hetus_column_names as col
from activityassure.hetus_data_processing import filter, load_data
from activityassure.hetus_data_processing.hetus_column_values import DayType


def special_entries(data, persondata):
    print("--- Irregular patterns (maybe should be removed) ---")
    d = filter.filter_stats(
        filter.filter_combined, "sick days", data, {col.Diary.DAYTYPE: [DayType.sick]}
    )
    d = filter.filter_stats(
        filter.filter_combined,
        "second job",
        persondata,
        {col.Person.MULTIPLE_JOBS: [1]},
    )


def check_daytype_data(data):
    print("--- Data availability on day type ---")
    d = filter.filter_stats(filter.filter_no_data, "Day type", data, col.Diary.DAYTYPE)
    d = filter.filter_stats(
        filter.filter_no_data,
        "EmployedStudent",
        data,
        col.Diary.EMPLOYED_STUDENT,
    )
    d = filter.filter_stats(
        filter.filter_no_data,
        "Weekday",
        data,
        col.Diary.WEEKDAY,
    )


def check_seasonal_data(data):
    print("--- Data availability on season ---")
    d = filter.filter_stats(
        filter.filter_no_data,
        "Month",
        data,
        col.Diary.MONTH,
    )
    # Not sure if year is relevant for seasonality
    d = filter.filter_stats(
        filter.filter_no_data,
        "Year",
        data,
        col.Diary.YEAR,
    )


def check_employment_data(persondata):
    print("--- Data availability on employment status ---")
    d = filter.filter_stats(
        filter.filter_no_data,
        "Work status",
        persondata,
        col.Person.WORK_STATUS,
    )
    d = filter.filter_stats(
        filter.filter_no_data,
        "Labour status",
        persondata,
        col.Person.SELF_DECL_LABOUR_STATUS,
    )
    d = filter.filter_stats(
        filter.filter_no_data,
        "Work last week",
        persondata,
        col.Person.WORK_LAST_WEEK,
    )
    d = filter.filter_stats(
        filter.filter_no_data,
        "Full or part time",
        persondata,
        col.Person.FULL_OR_PART_TIME,
    )
    d = filter.filter_stats(
        filter.filter_no_data,
        "Weekly work hours",
        persondata,
        col.Person.WEEKLY_WORKING_HOURS,
    )


def check_personal_data(persondata):
    print("--- Data availability on person level ---")
    d = filter.filter_stats(
        filter.filter_no_data,
        "Sex",
        persondata,
        col.Person.SEX,
    )
    d = filter.filter_stats(
        filter.filter_no_data,
        "Age group",
        persondata,
        col.Person.AGE_GROUP,
    )


def check_activity_data(data):
    print("--- Data availability on activity level ---")
    a3 = col.get_activity_data(data)
    non_na_share = a3.count().sum() / (len(a3) * len(a3.columns))
    print(
        f"Share of missing 10 min activity entries in total: {(1 - non_na_share) * 100:.1f} %"
    )
    non_na_per_row = a3.count(axis=1)
    rows_with_na = len(non_na_per_row[non_na_per_row < 144]) / len(a3)
    print(f"Share of incomplete diary entries: {rows_with_na * 100:.1f} %")


def check_countries(data):
    countries = data.index.get_level_values(col.Country.ID)
    countries = set(countries)
    if len(countries) != 17:
        all = load_data.get_hetus_file_names().keys()
        missing = [c for c in all if c not in countries]
        logging.warninging(f"Missing countries: {missing}")
    else:
        logging.info("All countries covered")


def all_data_checks(data, persondata, hhdata):
    check_employment_data(persondata)
    check_personal_data(persondata)
    check_daytype_data(data)
    check_seasonal_data(data)
    special_entries(data, persondata)
    check_activity_data(data)
