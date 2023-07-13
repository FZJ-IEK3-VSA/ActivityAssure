import json
import logging
from typing import Dict

import pandas as pd
from tabulate import tabulate

import data_checks
import filter
import hetus_columns as col
import level_extraction
import load_data
from attributes import diary_attributes, hh_attributes, person_attributes
from categorize import (categorize, get_diary_categorization_data,
                        get_hh_categorization_data,
                        get_person_categorization_data)
from hetus_values import DayType, EmployedStudent
import category_statistics


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


def check_entries_per_hh(data):
    # TODO: check, of often entries for the same household are from different days
    # To consider: number of days per household, number of persons, number of entries per person,
    # incomplete hh, ...
    pass


if __name__ == "__main__":
    main()
    data = None
    # data = load_data.load_all_hetus_files()
    if data is None:
        data = load_data.load_hetus_files(["DE", "AT"])
    assert data is not None
    data.set_index(col.Diary.KEY, inplace=True)
    stats(data)

    # extract households and persons
    data_valid_persons, persondata = level_extraction.get_usable_person_data(data)
    stats(data_valid_persons, persondata)
    # data_valid_hhs, hhdata = level_extraction.get_usable_household_data(data)
    # stats(data, data_valid_persons, data_valid_hhs)

    # cat_persondata = get_person_categorization_data(persondata)
    key = [col.Country.ID, col.Person.SEX, diary_attributes.Categories.work_status]
    # categorize(cat_persondata, key)

    cat_data = get_diary_categorization_data(data, persondata)
    key += [diary_attributes.Categories.day_type]
    categories = categorize(cat_data, key)
    # cat_hhdata = get_hh_categorization_data(hhdata, persondata)

    category_statistics.calc_probability_profiles(categories)

    # check_entries_per_hh(data)



    # data_checks.all_data_checks(data, persondata, hhdata)

    pass
