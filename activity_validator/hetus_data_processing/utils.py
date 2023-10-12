import logging
from functools import wraps
import pathlib
import time
from typing import Iterable

import pandas as pd
from tabulate import tabulate

#: path for result data # TODO: move to config file
VALIDATION_DATA_PATH = pathlib.Path() / "data" / "validation"


def save_df(
    data: pd.DataFrame,
    subdir: str,
    name: str,
    category: Iterable,
    ext: str = "csv",
) -> None:
    """
    Saves a result data frame to a csv file within the
    main data directory.

    :param data: data to save
    :type data: pd.DataFrame
    :param subdir: subdirectory to save the file at
    :type subdir: str
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
    directory = VALIDATION_DATA_PATH / subdir
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / filename
    data.to_csv(path)
    logging.debug(f"Created DataFrame file {path}")


def load_df(path: str | pathlib.Path) -> tuple[tuple, pd.DataFrame]:
    if isinstance(path, str):
        path = pathlib.Path(path)
    components = tuple(path.stem.split("_"))
    basename = components[0]
    profile_type = components[1:]
    data = pd.read_csv(path, index_col=0)
    logging.debug(f"Loaded DataFrame from {path}")
    return profile_type, data


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
