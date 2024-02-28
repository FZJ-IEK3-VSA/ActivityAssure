"""
Contains column value definitions of the HETUS 2010 data set.
For the column enums, the docstrings indicate the name of the 
corresponding HETUS column.
"""

from enum import IntEnum

#: the country codes used by Eurostat
EUROSTAT_COUNTRY_CODES = {
    "BE": "Belgium ",
    "EL": "Greece ",
    "LT": "Lithuania ",
    "PT": "Portugal ",
    "BG": "Bulgaria ",
    "ES": "Spain ",
    "LU": "Luxembourg ",
    "RO": "Romania ",
    "CZ": "Czechia ",
    "FR": "France ",
    "HU": "Hungary ",
    "SI": "Slovenia ",
    "DK": "Denmark ",
    "HR": "Croatia ",
    "MT": "Malta ",
    "SK": "Slovakia ",
    "DE": "Germany ",
    "IT": "Italy ",
    "NL": "Netherlands ",
    "FI": "Finland ",
    "EE": "Estonia ",
    "CY": "Cyprus ",
    "AT": "Austria ",
    "SE": "Sweden ",
    "IE": "Ireland ",
    "LV": "Latvia ",
    "PL": "Poland ",
}


class NoData(IntEnum):
    """
    Enum defining the values used when no data is present for
    different reasons. These codes are the same for all columns.
    """

    not_applicable = -1
    not_asked = -6
    refusal = -7
    dont_know = -8
    not_available = -9


class DayType(IntEnum):
    """DDV7"""

    work = 1
    school = 2
    day_off = 3
    sick = 4
    vacation = 5
    on_leave = 6


class EmployedStudent(IntEnum):
    """DDV6"""

    yes = 1
    no = 2
    not_asked = -6
    refusal = -7


class Sex(IntEnum):
    """INC1"""

    male = 1
    female = 2


class WorkStatus(IntEnum):
    """INC4_1"""

    work_full = 1
    work_part = 2
    on_leave = 3
    unemployed = 4
    student = 5


class SelfDeclLaborStatus(IntEnum):
    """IND17_1"""

    employed = 10
    unemployed = 20
    student = 31
    retirement = 32
    military_or_community_service = 34
    domestic_tasks = 35
    other_inactive = 36


class WorkLastWeek(IntEnum):
    """IND1"""

    yes = 1
    temporarily_absent = 2
    not_working = 3


class FullOrPartTime(IntEnum):
    """IND7"""

    full_time = 1
    part_time = 2
