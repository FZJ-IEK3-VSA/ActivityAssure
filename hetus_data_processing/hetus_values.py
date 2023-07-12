from enum import IntEnum


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
