import logging
from pathlib import Path

import pandas as pd
from activity_validator.hetus_data_processing.activity_profile import (
    VALIDATION_DATA_PATH,
)

import activity_validator.hetus_data_processing.hetus_columns as col
from activity_validator.hetus_data_processing import (
    hetus_translations,
    level_extraction,
)
from activity_validator.hetus_data_processing import load_data
from activity_validator.hetus_data_processing import utils
from activity_validator.hetus_data_processing.attributes import (
    diary_attributes,
    person_attributes,
)
from activity_validator.hetus_data_processing.categorize import (
    categorize,
    filter_categories,
    get_diary_categorization_data,
)
from activity_validator.hetus_data_processing import category_statistics


@utils.timing
def process_hetus_2010_data(data: pd.DataFrame):
    data.set_index(col.Diary.KEY, inplace=True)
    utils.stats(data)

    hetus_translations.translate_activity_codes(data)
    activity_types = hetus_translations.get_activity_type_list()

    # extract households and persons
    data_valid_persons, persondata = level_extraction.get_usable_person_data(data)
    utils.stats(data_valid_persons, persondata)
    # data_valid_hhs, hhdata = level_extraction.get_usable_household_data(data)
    # utils.stats(data, data_valid_persons, data_valid_hhs)

    # calculate additional columns for categorizing and drop rows
    # where important data is missing
    cat_data = get_diary_categorization_data(data, persondata)
    key = [
        col.Country.ID,
        person_attributes.Sex.title(),
        person_attributes.WorkStatus.title(),
        diary_attributes.DayType.title(),
    ]
    categories = categorize(cat_data, key)
    categories = filter_categories(categories)

    # cat_hhdata = get_hh_categorization_data(hhdata, persondata)

    category_statistics.calc_statistics_per_category(categories, activity_types)

    # data_checks.all_data_checks(data, persondata, hhdata)


def merge_categories_files(path1: Path, path2: Path):
    data1 = pd.read_csv(path1)
    data2 = pd.read_csv(path2)
    assert len(data1) == len(data2), "Cannot merge without specifying the index columns"
    merged = pd.concat([data1, data2], axis=1)
    merged = merged.loc[:, ~merged.columns.duplicated()].copy()  # type: ignore
    merged.to_csv(path1.parent / "categories.csv", index=False)


def process_all_hetus_countries_AT_separately():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # process AT data separately (different resolution)
    logging.info("--- Processing HETUS data for AT ---")
    data_at = load_data.load_hetus_files(["AT"])
    process_hetus_2010_data(data_at)

    # rename categories file
    categories_path = VALIDATION_DATA_PATH / "categories" / "categories.csv"
    categories_at = categories_path.rename(categories_path.parent / "categories_AT.csv")

    # process remaining countries
    logging.info("--- Processing HETUS data for all countries except AT ---")
    data = load_data.load_all_hetus_files_except_AT()
    process_hetus_2010_data(data)
    categories_eu = categories_path.rename(categories_path.parent / "categories_EU.csv")

    # merge categories files
    merge_categories_files(categories_at, categories_eu)


if __name__ == "__main__":
    process_all_hetus_countries_AT_separately()

    # data = load_data.load_all_hetus_files_except_AT()
    # process_hetus_2010_data(data)
