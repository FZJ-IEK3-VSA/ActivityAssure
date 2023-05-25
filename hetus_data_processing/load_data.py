import os
import time
from typing import Dict, List
import pandas as pd
from dataclasses import dataclass
import logging

DATAPATH = r"D:\Daten\HETUS Data\HETUS 2010 full set\DATA"
HETUS_FILENAME_PREFIX = "TUS_SUF_A_"
HETUS_FILENAME_SUFFIX = "_2010.csv"

# @dataclass
# class HetusHousehold:
#     pass

# @dataclass
# class HetusPerson:
#     pass


# @dataclass
# class HetusRecord:
#     pass    


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


def get_hetus_file_names(path: str = DATAPATH) -> Dict[str, str]:
    filenames = os.listdir(path)
    filenames_by_country = {}
    for name in filenames:
        assert name.startswith(HETUS_FILENAME_PREFIX) and name.endswith(
            HETUS_FILENAME_SUFFIX
        ), f"Invalid file name: {name}"
        country = get_country(name)
        filenames_by_country[country] = os.path.join(path, name)
    return filenames_by_country


def load_hetus_file(path: str) -> pd.DataFrame:
    logging.debug(f"Loading HETUS file for {get_country(path)}")
    start = time.time()
    data = pd.read_csv(path)
    logging.info(f"Loaded HETUS file for {get_country(path)} with {len(data)} entries in {time.time() - start:.1f} s")
    return data


def load_hetus_file_for_country(country: str) -> pd.DataFrame:
    filenames = get_hetus_file_names()
    if country.upper() not in filenames.keys():
        raise RuntimeError(f"No HETUS file for country '{country}' found")
    return load_hetus_file(filenames[country])


def load_all_hetus_files(path: str = DATAPATH) -> pd.DataFrame:
    start = time.time()
    filenames = get_hetus_file_names(path)
    data = pd.concat(load_hetus_file(filename) for filename in filenames.values())
    logging.info(f"Loaded all HETUS files with {len(data)} entries in {time.time() - start:.1f} s")
    return data


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    filenames = get_hetus_file_names()

    filename_germany = filenames["DE"]
    data = load_hetus_file(filename_germany)
    data.head()

    d = load_all_hetus_files()
    d.head()
    print(len(d))



if __name__ == "__main__":
    main()
