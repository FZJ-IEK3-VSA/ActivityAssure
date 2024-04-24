import logging
from functools import wraps
import time
from typing import Any


class ActValidatorException(Exception):
    """Generic error in ActivityAssure"""


def merge_dicts(dict1: dict[Any, list], dict2: dict[Any, list]) -> dict[Any, list]:
    """
    Merges two dicts of lists. Whenever a key is present is both dicts, the two
    corresponding lists are concatenated.

    :param dict1: the first dict
    :param dict2: the second dict
    :return: the merged dict
    """
    keys = dict1.keys() | dict2.keys()
    return {k: dict1.get(k, []) + dict2.get(k, []) for k in keys}


def timing(f):
    """
    Timing decorator
    slightly adapted from here:
    https://stackoverflow.com/questions/1622943/timeit-versus-timing-decorator#answer-27737385
    """

    @wraps(f)
    def wrap(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()
        logging.debug("Timing: %r took: %2.4f sec" % (f.__name__, te - ts))
        return result

    return wrap
