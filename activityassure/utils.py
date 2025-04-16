import logging
from functools import wraps
from pathlib import Path
import sys
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


def configure_log_handler(handler):
    """
    Configures a log handler with the default settings

    :param handler: the handler to configure
    """
    handler.setLevel(logging.DEBUG)
    # formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s")
    formatter = logging.Formatter("%(message)s")
    formatter.datefmt = "%Y-%m-%d %H:%M:%S"
    handler.setFormatter(formatter)


def init_logging_stdout_and_file(logfile: Path) -> logging.Logger:
    """
    Sets up logging with two handlers: one for the console and one for a log file.

    :param logfile: path for the log file
    :return: the configured logger object
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # remove the default handler
    logger.handlers.clear()

    # add a handler writing to the console
    console_handler = logging.StreamHandler(sys.stdout)
    configure_log_handler(console_handler)
    logger.addHandler(console_handler)

    # add a handler writing to a log file in the specified directory
    logfile.parent.mkdir(parents=True, exist_ok=True)
    logfile_handler = logging.FileHandler(logfile, "w", "utf-8")
    configure_log_handler(logfile_handler)
    logger.addHandler(logfile_handler)
    return logger
