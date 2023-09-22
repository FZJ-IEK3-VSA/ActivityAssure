"""
Functions for categorizing all persons or households in HETUS data sets using
different criteria
"""

import logging
from enum import StrEnum  # type: ignore
from typing import Any, Dict, List
import pandas as pd

import hetus_columns as col
import hetus_translations
import hetus_values as val
import utils
from attributes import diary_attributes, person_attributes


class CategoryColumn(StrEnum):
    household = "Household Category"
    person = "Person Category"
    diary = "Diary Category"


def get_person_categorization_data(persondata: pd.DataFrame) -> pd.DataFrame:
    # calculate additionaly attributes and combine them with the data
    work = person_attributes.determine_work_statuses(persondata)
    pdata = pd.concat([persondata, work], axis=1)
    # remove persons where key attributes are missing
    pdata = pdata[pdata[diary_attributes.Categories.work_status] >= 0]
    # select the key attributes to use for categorization
    return pdata


def get_diary_categorization_data(data: pd.DataFrame, persondata: pd.DataFrame) -> pd.DataFrame:
    persondata = get_person_categorization_data(persondata)
    data = data.join(persondata.loc[:, diary_attributes.Categories.work_status])
    # drop diaries of persons with missing key attributes
    data = data[data[diary_attributes.Categories.work_status].notna()]
    # calculate additional attributes
    daytype = diary_attributes.determine_day_types(data)
    data = pd.concat([data, daytype], axis=1)
    data = data[data[diary_attributes.Categories.day_type] >= 0]
    return data


def get_hh_categorization_data(hhdata: pd.DataFrame, persondata: pd.DataFrame) -> pd.DataFrame:
    persondata = get_person_categorization_data(persondata)
    persondata.loc[:,[col.Person.SEX, diary_attributes.Categories.work_status]].groupby(col.HH.KEY).apply(list)

    # TODO: how do I treat diaries from one household, but from different days?
    # --> ignore at first and check if there are weird statistics later
    return None


@utils.timing
def categorize(data: pd.DataFrame, key: List[str]) -> Dict[Any, pd.DataFrame]:
    categories = data.groupby(key)
    # create separate index without country for a better overview
    cat_index = key.copy()
    cat_index.remove(col.Country.ID)
    category_sizes = categories.size().reset_index().pivot(index=cat_index, columns=col.Country.ID, values=0)
    logging.info(f"Sorted {len(data)} entries into {category_sizes.count().sum()} categories.")
    print(category_sizes)
    hetus_translations.translate_column(category_sizes, col.Person.SEX, "Sex", val.Sex)
    hetus_translations.translate_column(category_sizes, diary_attributes.Categories.work_status, "Work Status", person_attributes.WorkStatus)
    # store category sizes as a file
    utils.save_file(category_sizes, "categories", "cat", key)
    return {g: categories.get_group(g) for g in categories.groups}
