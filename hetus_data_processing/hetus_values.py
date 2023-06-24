from enum import IntEnum
from typing import List


class DayType(IntEnum):
    """
    Mapped to field

    :param IntEnum: _description_
    :type IntEnum: _type_
    """

    work = 1
    school = 2
    day_off = 3
    sick = 4
    vacation = 5
    on_leave = 6

    not_applicable = -1
    not_asked = -6
    refusal = -7
    dont_know = -8
    not_available = -9

    @staticmethod
    def no_data() -> List["DayType"]:
        """
        Returns a list of all values that indicate missing data

        :return: list of DayType values for missing data
        :rtype: DayType
        """
        return [
            DayType.not_applicable,
            DayType.not_asked,
            DayType.refusal,
            DayType.dont_know,
            DayType.not_available,
        ]
    

class EmployedStudent(IntEnum):
    """
    Values vor variable DDV6
    """
    yes = 1
    no = 2
    not_asked = -6
    refusal = -7


class HHFamilyStatus(IntEnum):
    single = 0
    single_parent = 1
    couple = 2
    family = 3
    flatsharing = 4


class WorkStatus(IntEnum):
    work_full = 1
    work_part = 2
    on_leave = 3
    unemployed = 4
    student = 5
    not_applicable = -1
    not_asked = -6
    refusal = -7
    dont_know = -8
    not_available = -9