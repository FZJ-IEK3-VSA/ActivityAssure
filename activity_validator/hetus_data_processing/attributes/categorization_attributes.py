"""
Defines the attributes that are used for categorizing activity
profiles.
"""

from enum import StrEnum


class Country(str):
    """
    Specifies the home country of a person:
    """

    @staticmethod
    def title() -> str:
        return "country"


class WorkStatus(StrEnum):
    """
    Specifies the working status of a person
    """

    full_time = "full time"
    part_time = "part time"
    unemployed = "unemployed"
    retired = "retired"
    student = "student"

    undetermined = "undetermined"
    work_full_or_part = "full or part time"
    unemployed_or_retired = "unemployed or retired"

    @staticmethod
    def title() -> str:
        return "work status"

    def is_determined(self) -> bool:
        return not (
            self == WorkStatus.undetermined
            or self == WorkStatus.work_full_or_part
            or self == WorkStatus.unemployed_or_retired
        )


class Sex(StrEnum):
    """
    Specifies the sex of a person
    """

    male = "male"
    female = "female"

    @staticmethod
    def title() -> str:
        return "sex"


class DayType(StrEnum):
    """
    Specifies the day type of a diary entry
    """

    work = "working day"
    no_work = "rest day"

    undetermined = "undetermined"

    @staticmethod
    def title() -> str:
        return "day type"
