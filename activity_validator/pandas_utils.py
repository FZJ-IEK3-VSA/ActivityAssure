"""
Helper functions for working with pandas DataFrames
"""

import logging
from pathlib import Path
import pandas as pd

from activity_validator.profile_category import ProfileCategory


def create_result_path(
    path: Path,
    name: str,
    profile_type: ProfileCategory | None = None,
    ext: str = "csv",
) -> Path:
    """
    Creates a full result path for saving a file within
    the main result data directory.

    :param path: base directory for the file
    :param name: base name of the file
    :param profile_type: the category of the profile data,
                         if applicable; is appended to the
                         filename; defaults to None
    :param ext: file extension, defaults to "csv"
    """
    if profile_type is not None:
        # add profile type to filename
        name = profile_type.construct_filename(name)
    if ext and not name.endswith(f".{ext}"):
        # add the file extension
        name += f".{ext}"
    path.mkdir(parents=True, exist_ok=True)
    path = path / name
    return path


def save_df(
    data: pd.DataFrame | pd.Series,
    path: Path,
    name: str,
    profile_type: ProfileCategory | None = None,
    ext: str = "csv",
) -> None:
    """
    Saves a result data frame to a csv file within the
    main data directory.

    :param data: data to save
    :param base_path: directory to save the file in
    :param name: base name of the file
    :param profile_type: the category of the profile data,
                         if applicable; is appended to the
                         filename; defaults to None
    :param ext: file extension, defaults to "csv"
    """
    path = create_result_path(path, name, profile_type, ext)
    data.to_csv(path)
    logging.debug(f"Created DataFrame file {path}")


def load_df(path: Path, timedelta_index: bool = False) -> pd.DataFrame:
    """
    Loads a DataFrame from a csv file.

    :param path: path to the csv file
    :param as_timedelta: whether the index of the DataFrame consists of timedeltas,
                         defaults to False
    :return: the loaded DataFrame
    """
    # load the data
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
