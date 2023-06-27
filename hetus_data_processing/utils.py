from functools import wraps
import logging
from time import time


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
        logging.debug("Timing: %r took: %2.4f sec" % (f.__name__, te - ts))
        return result

    return wrap
