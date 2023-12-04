import logging
from functools import wraps
import time

from tabulate import tabulate


def stats(data, persondata=None, hhdata=None):
    """Print some basic statistics on HETUS data"""
    print(
        tabulate(
            [
                ["Number of diaries", len(data)],
                ["Number of persons", len(persondata)]
                if persondata is not None
                else [],
                ["Number of households", len(hhdata)] if hhdata is not None else [],
            ]
        )
    )


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
