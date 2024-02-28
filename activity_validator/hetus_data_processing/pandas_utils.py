"""
Helper functions for working with pandas DataFrames
"""

import logging
from pathlib import Path
import pandas as pd

from activity_validator.profile_category import ProfileType

#: path for result data # TODO: move to config file
VALIDATION_DATA_PATH = Path("data/validation data sets/latest")


def create_result_path(
    subdir: str,
    name: str,
    profile_type: ProfileType | None = None,
    base_path: Path | None = None,
    ext: str = "csv",
) -> Path:
    """
    Creates a full result path for saving a file within
    the main result data directory.

    :param subdir: subdirectory to save the file at
    :param name: base name of the file
    :param profile_type: the category of the profile data,
                         if applicable; is appended to the
                         filename; defaults to None
    :param base_path: base directory for the file,
                      defaults to VALIDATION_DATA_PATH
    :param ext: file extension, defaults to "csv"
    """
    if not base_path:
        base_path = VALIDATION_DATA_PATH
    if profile_type is not None:
        # add profile type to filename
        name = profile_type.construct_filename(name)
    if ext and not name.endswith(f".{ext}"):
        name += f".{ext}"
    if subdir:
        base_path /= subdir
    base_path.mkdir(parents=True, exist_ok=True)
    path = base_path / name
    return path


def convert_to_timedelta(data: pd.DataFrame) -> None:
    for col in data.columns:
        data[col] = pd.to_timedelta(data[col])


def save_df(
    data: pd.DataFrame | pd.Series,
    subdir: str,
    name: str,
    profile_type: ProfileType | None = None,
    base_path: Path = VALIDATION_DATA_PATH,
    ext: str = "csv",
) -> None:
    """
    Saves a result data frame to a csv file within the
    main data directory.

    :param data: data to save
    :param subdir: subdirectory to save the file at
    :param name: base name of the file
    :param profile_type: the category of the profile data,
                         if applicable; is appended to the
                         filename; defaults to None
    :param base_path: base directory for the file,
                      defaults to VALIDATION_DATA_PATH
    :param ext: file extension, defaults to "csv"
    """
    path = create_result_path(subdir, name, profile_type, base_path, ext)
    data.to_csv(path)
    logging.debug(f"Created DataFrame file {path}")


def load_df(
    path: str | Path, timedelta_index: bool = False
) -> pd.DataFrame:  # TODO: make obsolete?
    """
    Loads a data frame from a csv file.

    :param path: path to the csv file
    :param as_timedelta: whether the DataFrame contains a timedelta
                         index, defaults to False
    :return: the loaded DataFrame
    """
    if isinstance(path, str):
        path = Path(path)
    # load the data
    # TODO: for duration data sometimes DtypeWarning: Columns (1,3,5,6,8,9,10,11,12,13,14,15) have mixed types. Specify dtype option on import or set low_memory=False.
    data = pd.read_csv(path, index_col=0)
    if timedelta_index:
        # convert the index to timedeltas
        data.index = pd.to_timedelta(data.index)
    logging.debug(f"Loaded DataFrame from {path}")
    return data


def split_data(data: pd.DataFrame) -> list[pd.DataFrame]:
    """
    Randomly split a dataframe into half.

    :param data: the dataframe to split
    :return: a list containing the dataframe halves
    """
    part1 = data.sample(frac=0.5)
    part2 = data.drop(part1.index)
    return [part1, part2]
