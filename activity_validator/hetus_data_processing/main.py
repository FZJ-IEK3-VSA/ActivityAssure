import logging
from pathlib import Path

import pandas as pd
from activity_validator.activity_profile import (
    ExpandedActivityProfiles,
)

import activity_validator.hetus_data_processing.hetus_column_names as col
from activity_validator.hetus_data_processing import (
    data_protection,
    hetus_translations,
    level_extraction,
)
from activity_validator.hetus_data_processing import load_data
from activity_validator import pandas_utils, utils
from activity_validator import (
    categorization_attributes,
)
from activity_validator.hetus_data_processing.categorize import (
    categorize,
    get_diary_data_for_categorization,
)
from activity_validator.hetus_data_processing import category_statistics
from activity_validator import validation_statistics


BASE_RESULT_PATH = Path("data/validation_data_sets")


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
        ]
        + [c for c in data.columns if c.startswith(col.Diary.MAIN_ACTIVITIES_PATTERN)]
    )
    data = data[relevant_columns]

    data.set_index(col.Diary.KEY, inplace=True)
    utils.stats(data)

    activities = hetus_translations.translate_activity_codes(data)

    # extract households and persons
    data_valid_persons, persondata = level_extraction.get_usable_person_data(data)
    utils.stats(data_valid_persons, persondata)
    # data_valid_hhs, hhdata = level_extraction.get_usable_household_data(data)
    return data, persondata, activities


@utils.timing
def process_hetus_2010_data(
    data: pd.DataFrame, cat_attributes=None, save: bool = True, title: str = "latest"
):
    """
    Produces a validation data set out of the passed HETUS data.
    Prepares and categorizes the data set and calculates statistics
    for each category.

    :param data: the data to process
    :param cat_attributes: the attributes to use for categorization
    :param save: whether the data set should be saved to files or not
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

    # ensure Eurostat data protection requirements
    data_protection.apply_eurostat_requirements(validation_set)

    if save:
        # save the validation data set
        validation_set.save(BASE_RESULT_PATH / title)
    return validation_set


def cross_validation_split(data: pd.DataFrame):
    """
    Splits each category of the data set in half, and stores
    both halves in separate directory structures to allow
    cross-validation.

    :param data: the HETUS data to use
    """
    data, persondata, activities = prepare_hetus_data(data)
    cat_data = get_diary_data_for_categorization(data, persondata)
    categorization_attributes = (
        categorization_attributes.get_default_categorization_attributes()
    )
    categories = categorize(cat_data, categorization_attributes)

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
    split1.save(BASE_RESULT_PATH / "Validation Split 1")

    split2 = category_statistics.calc_statistics_per_category(categories2, activities)
    data_protection.apply_eurostat_requirements(split2)
    split2.save(BASE_RESULT_PATH / "Validation Split 2")


def process_all_hetus_countries_AT_separately(
    hetus_path: str,
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
    result_at = process_hetus_2010_data(data_at, cat_attributes, False)

    # process remaining countries
    logging.info("--- Processing HETUS data for all countries except AT ---")
    data = load_data.load_all_hetus_files_except_AT(hetus_path, hetus_key)
    result_eu = process_hetus_2010_data(data, cat_attributes, False)

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
    combined.save(BASE_RESULT_PATH / title)
    logging.info(f"Finished creating the validation data set '{title}'")


def generate_all_dataset_variants(hetus_path: str, key: str | None = None):
    """
    Generates all relevant variants of the validation data set, each with a
    different set of categorization attributes.
    """
    country = categorization_attributes.Country.title()
    sex = categorization_attributes.Sex.title()
    work_status = categorization_attributes.WorkStatus.title()
    day_type = categorization_attributes.DayType.title()
    # default variant with full categorization
    process_all_hetus_countries_AT_separately(
        hetus_path, key, [country, sex, work_status, day_type]
    )
    # variants with only three categorization attributes
    process_all_hetus_countries_AT_separately(
        hetus_path, key, [country, sex, work_status]
    )
    process_all_hetus_countries_AT_separately(hetus_path, key, [country, sex, day_type])
    process_all_hetus_countries_AT_separately(
        hetus_path, key, [country, work_status, day_type]
    )
    # special case: variant without country is special (has to leave out AT data)
    data = load_data.load_all_hetus_files_except_AT(hetus_path, key)
    result = process_hetus_2010_data(data, [sex, work_status, day_type], save=False)
    result.save(BASE_RESULT_PATH / "sex_work status_day type")

    # some other relevant variants
    process_all_hetus_countries_AT_separately(hetus_path, key, [country])
    process_all_hetus_countries_AT_separately(hetus_path, key, [country, sex])
    process_all_hetus_countries_AT_separately(hetus_path, key, [country, day_type])
    process_all_hetus_countries_AT_separately(hetus_path, key, [country, work_status])


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    HETUS_PATH = "D:/Daten/HETUS Data/HETUS 2010 full set/DATA"
    key = load_data.read_key_as_arg()

    # process_all_hetus_countries_AT_separately(HETUS_PATH, key)
    # generate_all_dataset_variants(HETUS_PATH, key)

    # tests on smaller data sets
    data = load_data.load_hetus_files(["DE"], HETUS_PATH, key)
    process_hetus_2010_data(data)
    # cross_validation_split(data)
