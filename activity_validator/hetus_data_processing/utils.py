import errno
import logging
import os
from functools import wraps
import time
from typing import Any, Iterable, List

import pandas as pd

#: path for result data # TODO: move to config file
VALIDATION_DATA_PATH = "./data/validation"


def save_file(
    data: pd.DataFrame,
    subdir: str | List[str],
    name: str,
    category: Iterable,
    ext: str = "csv",
) -> None:
    """
    Saves a result file within the main data directory

    :param data: data to save
    :type data: pd.DataFrame
    :param subdir: subdirectory to save the file at
    :type subdir: str | List[str]
    :param name: name of the file
    :type name: str
    :param category: data category, if applicable
    :type category: Any
    :param ext: file extension, defaults to "csv"
    :type ext: str, optional
    """
    if category is not None:
        # add category to filename
        filename = f"{name}_{'_'.join(str(c) for c in category)}"
    filename += f".{ext}"
    # turn subdir into a list if it is not already one
    subdir = subdir if isinstance(subdir, List) else [subdir]
    directory = os.path.join(VALIDATION_DATA_PATH, *subdir)
    os.makedirs(directory, exist_ok=True)

    path = os.path.join(directory, filename)
    data.to_csv(path)
    logging.debug(f"Created file {path}")


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
