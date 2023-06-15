"""
Contains column names of HETUS data, ordered by level
"""

# class Key:
#     """
#     General column names that together function as identifier
#     """
#     YEAR = "YEAR"
#     COUNTRY = "COUNTRY"
#     HID = "HID"
#     PID = "PID"
#     DIARY = "DIARY"

class Year:
    ID = "YEAR"
    KEY = [ID]

class Country:
    ID = "COUNTRY"
    KEY = Year.KEY + [ID]

class HH:
    """
    Column names on household level.
    This encompasses all columns that describe features of the
    household rather than of a person or a sinlge diary entry,
    and that should therefore be the same for all entries
    belonging to the same household (which is not the case in
    the actual data).
    """

    #: ID of the household
    ID = "HID"
    #: unique key for a household: COUNTRY + HID
    KEY = Country.KEY + [ID]

    #: number of persons in the household
    SIZE = "HHC1"

    #: all columns on household level besides the key columns
    CONTENT = [
        "HHC1",
        "HHC3",
        "HHC4",
        "HHC5",
        "HHQ3_1",
        "HHQ4",
        "HHQ5",
        "HHQ6C",
        "HHQ6D",
        "HHQ6E",
        "HHQ6F",
        "HHQ6G",
        "HHQ6H",
        "HHQ6K",
        "HHQ6L_1",
        "HHQ6M",
        "HHQ6N",
        "HHQ6O",
        "HHQ6R",
        "HHQ6P",
        "HHQ9_1",
        "HHQ10A",
        "HHQ10F",
    ]
    #: all columns on household level
    ALL = KEY + CONTENT


class Person:
    """
    Column names on personal level.
    This encompasses all columns with information on the respondent,
    e.g., sex or age
    """

    ID = "PID"
    KEY = HH.KEY + [ID]

    SEX = "INC1"
    AGE_GROUP = "INC2"
    LIFECYCLE = "INC3"
    STATUS = "INC4"


class Diary:
    """
    Metadata columns on the diary level (mostly date info)
    """

    ID = "DIARY"
    KEY = Person.KEY + [ID]

    WEEKDAY = "DDV1"
    MONTH = "DDV3"
    DAYTYPE = "DDV7"
