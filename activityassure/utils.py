import json
import logging
from functools import wraps
from pathlib import Path
import re
import sys
import time
from typing import Any
import unicodedata


class ActValidatorException(Exception):
    """Generic error in ActivityAssure"""


def create_json_file(filepath: Path, data: Any) -> None:
    """Saves data, e.g. a dict, to a json file.

    :param filepath: path for the json file
    :param data: the data to save
    """
    if not filepath.suffix == ".json":
        filepath = Path(f"{filepath}.json")
    with open(filepath, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4)


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


def replace_umlauts(s: str) -> str:
    """Replaces any German umlauts in the passed str
    with their common replacements.

    :param s: the str to adapt
    :return: the adapted str without umlauts
    """
    umlaut_map = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
    for k, v in umlaut_map.items():
        s = s.replace(k, v)
    return s


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        # custom addition for umlauts
        value = replace_umlauts(value)

        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")
