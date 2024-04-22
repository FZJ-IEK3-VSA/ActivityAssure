"""
Main module for processing HETUS data.
Loads HETUS data, categorizes and processes it and generates a
validation data set out of it.
"""

import logging
from pathlib import Path

import pandas as pd
from activityassure.activity_profile import (
    ExpandedActivityProfiles,
)

import activityassure.hetus_data_processing.hetus_column_names as col
from activityassure.hetus_data_processing import (
    data_protection,
    hetus_translations,
    level_extraction,
)
from activityassure.hetus_data_processing import load_data
from activityassure import pandas_utils, utils
from activityassure import (
    categorization_attributes,
)
from activityassure.hetus_data_processing.categorize import (
    categorize,
    get_diary_data_for_categorization,
)
from activityassure.hetus_data_processing import category_statistics
from activityassure import validation_statistics


@utils.timing
def prepare_hetus_data(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Prepares and cleans raw HETUS data before categorizing and
    calculating statistics.
    Sets the appropriate index, maps activities and removes
    inconsistent entries.

    :param data: raw HETUS data
    :return: cleaned HETUS data on diary and person level, and the list of
             possible activities
    """
    # extract only the columns that are actually needed to improve performance
    relevant_columns = (
        col.Diary.KEY
        + [
            col.Person.WORK_STATUS,
            col.Person.SELF_DECL_LABOUR_STATUS,
            col.Person.FULL_OR_PART_TIME,
            col.Person.SEX,
            col.Diary.DAYTYPE,
            col.Diary.EMPLOYED_STUDENT,
            col.Diary.DAY_AND_PERSON_WEIGHT,
        ]
        + [c for c in data.columns if c.startswith(col.Diary.MAIN_ACTIVITIES_PATTERN)]
    )
    data = data[relevant_columns]
    data.set_index(col.Diary.KEY, inplace=True)
    activities = hetus_translations.translate_activity_codes(data)

    # extract households and persons
    data_valid_persons, persondata = level_extraction.get_usable_person_data(data)
    # data_valid_hhs, hhdata = level_extraction.get_usable_household_data(data)
    return data, persondata, activities


@utils.timing
def process_hetus_2010_data(
    data: pd.DataFrame,
    cat_attributes=None,
    result_path: Path | None = None,
    hetus_data_protection: bool = True,
) -> validation_statistics.ValidationSet:
    """
    Produces a validation data set out of the passed HETUS data.
    Prepares and categorizes the data set and calculates statistics
    for each category.

    :param data: the data to process
    :param cat_attributes: the attributes to use for categorization
    :param result_path: the path to save the data set to; if None, the
                        data is not saved to as files
    """
    data, persondata, activities = prepare_hetus_data(data)

    # calculate additional columns for categorizing and drop rows
    # where important data is missing
    cat_data = get_diary_data_for_categorization(data, persondata)
    # categorize the data
    if cat_attributes is None:
        cat_attributes = (
            categorization_attributes.get_default_categorization_attributes()
        )
    categories = categorize(cat_data, cat_attributes)

    validation_set = category_statistics.calc_statistics_per_category(
        categories, activities
    )

    if hetus_data_protection:
        # ensure Eurostat data protection requirements
        data_protection.apply_eurostat_requirements(validation_set)

    if result_path is not None:
        # save the validation data set
        validation_set.save(result_path)
    return validation_set


def cross_validation_split(
    data: pd.DataFrame,
    result_path: Path,
):
    """
    Splits each category of the data set in half, and stores
    both halves in separate directory structures to allow
    cross-validation.

    :param data: the HETUS data to use
    """
    data, persondata, activities = prepare_hetus_data(data)
    cat_data = get_diary_data_for_categorization(data, persondata)
    cat_attributes = categorization_attributes.get_default_categorization_attributes()
    categories = categorize(cat_data, cat_attributes)

    # split data of each category
    categories1, categories2 = [], []
    for category in categories:
        data1, data2 = pandas_utils.split_data(category.data)
        profile1 = ExpandedActivityProfiles(
            data1, category.profile_type, category.offset, category.resolution
        )
        profile2 = ExpandedActivityProfiles(
            data2, category.profile_type, category.offset, category.resolution
        )
        categories1.append(profile1)
        categories2.append(profile2)

    # create statistics for the split parts separately
    split1 = category_statistics.calc_statistics_per_category(categories1, activities)
    data_protection.apply_eurostat_requirements(split1)
    split1.save(result_path / "validation split 1")

    split2 = category_statistics.calc_statistics_per_category(categories2, activities)
    data_protection.apply_eurostat_requirements(split2)
    split2.save(result_path / "validation split 2")


@utils.timing
def process_all_hetus_countries_AT_separately(
    hetus_path: str,
    result_path: Path,
    hetus_key: str | None = None,
    cat_attributes=None,
    title: str = "",
):
    """
    Generates a full HETUS validation data set for all countries. Processes
    data for Austria separately due to the different structure, and merges
    the results.

    :param hetus_path: HETUS data path
    :param key: key to decrypt HETUS data, defaults to None
    :param cat_attributes: categorization attributes to use, defaults to a
                           full categorization
    :param title: title of the validation data set
    """
    if not cat_attributes:
        cat_attributes = (
            categorization_attributes.get_default_categorization_attributes()
        )
    # process AT data separately (different resolution)
    logging.info("--- Processing HETUS data for AT ---")
    data_at = load_data.load_hetus_files(["AT"], hetus_path, hetus_key)
    result_at = process_hetus_2010_data(data_at, cat_attributes, None)

    # process remaining countries
    logging.info("--- Processing HETUS data for all countries except AT ---")
    data = load_data.load_all_hetus_files_except_AT(hetus_path, hetus_key)
    result_eu = process_hetus_2010_data(data, cat_attributes, None)

    assert (
        result_at.statistics.keys() & result_eu.statistics.keys() == set()
    ), "Overlap in profile types. Cannot merge data from AT and EU."
    combined_statistics = result_at.statistics | result_eu.statistics
    combined = validation_statistics.ValidationSet(
        combined_statistics, result_eu.activities
    )

    if not title:
        # determine title automatically
        title = "_".join(s.lower() for s in cat_attributes)
    # rename result directory
    combined.save(result_path / title)
    logging.info(f"Finished creating the validation data set '{title}'")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    HETUS_PATH = "data/HETUS data/HETUS 2010 full set/DATA"
    key = load_data.read_key_as_arg()

    RESULT_PATH = Path("data/validation_data_sets")

    title = "activity_validation_data_set"
    process_all_hetus_countries_AT_separately(HETUS_PATH, RESULT_PATH, key, None, title)
