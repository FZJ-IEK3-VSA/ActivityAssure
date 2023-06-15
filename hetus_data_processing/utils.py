from enum import IntEnum
from functools import wraps
from time import time

class HetusDayType(IntEnum):
    """
    Mapped to field 

    :param IntEnum: _description_
    :type IntEnum: _type_
    """
    work=1
    school=2
    day_off=3
    sick=4
    vacation=5
    on_leave=6


class HHFamilyStatus(IntEnum):
    single=0
    single_parent=1
    couple=2
    family=3
    flatsharing=4




class HetusColumns:
    """
    Contains column names of HETUS data sets.
    """
    class General:
        """
        General column names that together function as identifier
        """
        YEAR = "YEAR"
        HID = "HID"
        PID = "PID"
        DIARY = "DIARY"
        COUNTRY = "COUNTRY"

    class Diary:
        """
        Metadata columns on the diary (mostly date info)
        """

        WEEKDAY = "DDV1"
        MONTH = "DDV3"
        DAYTYPE = "DDV7"

    class HH:
        """
        Column names on household level.
        This encompasses all columns that describe features of the
        household rather than of a person or a sinlge diary entry,
        and that should therefore be the same for all entries
        belonging to the same household (which is not the case in
        the actual data).
        """

        #: number of persons in the household
        SIZE = "HHC1"

        #: unique key for a household: COUNTRY + HID
        KEY = ["COUNTRY", "HID"]
        #: all columns on household level besides the key columns
        CONTENT_COLUMNS = [
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
        COLUMNS = KEY + CONTENT_COLUMNS

    class Personal:
        """
        Column names on personal level.
        This encompasses all columns with information on the respondent,
        e.g., sex or age
        """
        SEX = "INC1"
        AGE_GROUP = "INC2"
        LIFECYCLE = "INC3"
        STATUS = "INC4"


def timing(f):
    """
    Timing decorator
    slightly adapted from here:
    https://stackoverflow.com/questions/1622943/timeit-versus-timing-decorator#answer-27737385
    """
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print("func:%r took: %2.4f sec" % (f.__name__, te - ts))
        return result

    return wrap
