import json
import logging
from typing import Dict
import pandas as pd

from tabulate import tabulate

import load_data
import level_extraction
import filter
import hetus_columns as col
import data_checks
from hetus_values import DayType, EmployedStudent
from attributes import person_attributes, diary_attributes, hh_attributes


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


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


if __name__ == "__main__":
    main()
    data = None
    # data = load_data.load_all_hetus_files()
    if data is None:
        data = load_data.load_hetus_files(["DE", "AT"])
    data.set_index(col.Diary.KEY, inplace=True)
    stats(data)

    # extract households and persons
    data_valid_persons, persondata = level_extraction.get_usable_person_data(data)
    stats(data_valid_persons, persondata)
    data_valid_hhs, hhdata = level_extraction.get_usable_household_data(data)
    stats(data, data_valid_persons, data_valid_hhs)

    person_attributes.determine_work_statuses(persondata)
    diary_attributes.calc_day_type(data)

    data_checks.all_data_checks(data, persondata, hhdata)

    pass
