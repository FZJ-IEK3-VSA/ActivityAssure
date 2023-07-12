import logging
from enum import EnumType  # type: ignore
from functools import wraps
from time import time
from typing import Dict, Optional, Union

import pandas as pd


def translate_column(
    data: pd.DataFrame,
    column: str,
    column_new: Optional[str] = None,
    value_translation: Union[EnumType, Dict] = None,
) -> None:
    """
    Renames a column and changes all values according to a specified enum or dict.
    Can handle normal and multiindex columns.

    :param data: the data to translate
    :type data: pd.DataFrame
    :param column: old name of the column to change
    :type column: str
    :param column_new: optional new name of the column, defaults to None
    :type column_new: Optional[str], optional
    :param value_translation: translation for the column values; can be an enum type or a dict, defaults to None
    :type value_translation: Union[EnumType, Dict], optional
    """
    if isinstance(value_translation, EnumType):
        # create a dict that maps all enum int values to names
        value_map = {e.value: e.name for e in value_translation}  # type:ignore
    else:
        value_map = value_translation
    if column in data.index.names:
        # column is part of the (multi-)index
        i = data.index.names.index(column)
        new_index_level = data.index.levels[i].map(value_map)
        new_index = data.index.set_levels(new_index_level, level=i)
        if column_new:
            # change name of the index level
            new_index.rename({column: column_new}, inplace=True)
        data.index = new_index
    else:
        assert False, "Not implemented"
        if column_new:
            data.rename({column: column_new}, inplace=True)


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
