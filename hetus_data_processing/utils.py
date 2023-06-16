from enum import IntEnum
from functools import wraps
from time import time


class HetusDayType(IntEnum):
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


class HHFamilyStatus(IntEnum):
    single = 0
    single_parent = 1
    couple = 2
    family = 3
    flatsharing = 4


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
