"""
Functions for loading HETUS data files.
"""

import os
import time
from typing import Dict, Iterable
import pandas as pd
import logging


# TODO: move or remove default path
HETUS_PATH = r"D:\Daten\HETUS Data\HETUS 2010 full set\DATA"
HETUS_FILENAME_PREFIX = "TUS_SUF_A_"
HETUS_FILENAME_SUFFIX = "_2010.csv"


def column_names_to_capitals(data: pd.DataFrame) -> None:
    """
    Changes all column headers to capitals only. Works inplace.

    :param data: dataframe with headers in changing cases
    :type data: pd.DataFrame
    """
    column_translations = {c: c.upper() for c in data.columns}
    data.rename(columns=column_translations, inplace=True)


def get_country(path: str) -> str:
    """
    Given an HETUS file path or name, returns the respective country code

    :param path: name or path of an HETUS file
    :type path: str
    :return: country code of the file
    :rtype: str
    """
    name = os.path.basename(path)
    return name.removeprefix(HETUS_FILENAME_PREFIX).removesuffix(HETUS_FILENAME_SUFFIX)


def get_hetus_file_names(path: str = HETUS_PATH) -> Dict[str, str]:
    """
    Returns a dict containing all available HETUS countries and the respective
    file paths.

    :param path: path to the HETUS directory, defaults to HETUS_PATH
    :type path: str, optional
    :return: dict containing contry codes and file paths
    :rtype: Dict[str, str]
    """
    filenames = os.listdir(path)
    filenames_by_country = {}
    for name in filenames:
        assert name.startswith(HETUS_FILENAME_PREFIX) and name.endswith(
            HETUS_FILENAME_SUFFIX
        ), f"Invalid file name: {name}"
        country = get_country(name)
        filenames_by_country[country] = os.path.join(path, name)
    return filenames_by_country


def build_dtype_dict() -> Dict[str, type]:
    """
    Generates a dictionary of dtypes for pandas.
    Sets all diary columns to str so that leading zeros in the diary
    codes are not lost

    :return: dtype dictionary for parsing with pandas
    :rtype: Dict[str, type]
    """
    columns = [
        "Mact",
        "Pact",
        "Sactn",
        "Sact",
        "Wherep",
        "Alone",
        "Wpartner",
        "Wparent",
        "Wchild",
        "Wotherh",
        "Wotherp",
        "Mcom",
        "Scom",
    ]
    return {c + str(i): str for c in columns for i in range(1, 145)}


#: dictionary specifying the correct data types for some columns
DTYPE_DICT = build_dtype_dict()


def load_hetus_file_from_path(path: str) -> pd.DataFrame:
    """
    Loads a single HETUS file

    :param path: the path of the file
    :type path: str
    :return: HETUS data from the file
    :rtype: pd.DataFrame
    """
    assert os.path.isfile(path), f"File not found: {path}"
    logging.debug(f"Loading HETUS file for {get_country(path)}")
    start = time.time()
    data = pd.read_csv(path, dtype=DTYPE_DICT)
    logging.info(
        f"Loaded HETUS file for {get_country(path)} with {len(data)} entries and {len(data.columns)} columns in {time.time() - start:.1f} s"
    )
    column_names_to_capitals(data)
    # assert len(data.columns) == NUM_COLUMNS, f"Unexpected number of columns: found {len(data.columns)} instead of 1939 columns"
    return data


def load_hetus_file(country: str) -> pd.DataFrame:
    """
    Loads HETUS data of a sinlge country

    :param country: the country code (e.g., "DE" for germany)
    :type country: str
    :raises RuntimeError: invalid country code
    :return: HETUS data for the country
    :rtype: pd.DataFrame
    """
    filenames = get_hetus_file_names()
    if country.upper() not in filenames.keys():
        raise RuntimeError(f"No HETUS file for country '{country}' found")
    return load_hetus_file_from_path(filenames[country])


def load_hetus_files(countries: Iterable[str]) -> pd.DataFrame:
    """
    Loads HETUS data of multiple countries.

    :param countries: a list of country codes (e.g., "DE" for germany)
    :type countries: Iterable[str]
    :return: HETUS data for the countries
    :rtype: pd.DataFrame
    """
    data = pd.concat(load_hetus_file(country) for country in countries)
    return data


def load_all_hetus_files(path: str = HETUS_PATH) -> pd.DataFrame:
    """
    Loads all available HETUS files.

    :param path: the HETUS data folder, defaults to HETUS_PATH
    :type path: str, optional
    :return: HETUS data for all available countries
    :rtype: pd.DataFrame
    """
    start = time.time()
    filenames = get_hetus_file_names(path)
    data = pd.concat(
        load_hetus_file_from_path(filename) for filename in filenames.values()
    )
    logging.info(
        f"Loaded all HETUS files with {len(data)} entries in {time.time() - start:.1f} s"
    )
    return data


def load_all_hetus_files_except_AT(path: str = HETUS_PATH) -> pd.DataFrame:
    """
    Loads all available HETUS files, except for the Austrian file.
    Austria uses 15 minute time slots instead of the usual 10 minute time slots,
    which can cause problems.

    :param path: the HETUS data folder, defaults to HETUS_PATH
    :type path: str, optional
    :return: HETUS data for all available countries except for Austria
    :rtype: pd.DataFrame
    """
    start = time.time()
    filenames = get_hetus_file_names(path)
    del filenames["AT"]
    data = pd.concat(
        load_hetus_file_from_path(filename) for filename in filenames.values()
    )
    logging.info(
        f"Loaded all HETUS files except for AT with {len(data)} entries in {time.time() - start:.1f} s"
    )
    return data
