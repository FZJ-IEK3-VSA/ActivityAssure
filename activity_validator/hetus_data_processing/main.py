import logging
from pathlib import Path

import pandas as pd
from activity_validator.hetus_data_processing.activity_profile import (
    VALIDATION_DATA_PATH,
    ExpandedActivityProfiles,
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
def prepare_data(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Prepares and cleans raw HETUS data before categorizing and
    calculating statistics.
    Sets the appropriate index, maps activities and removes
    inconsistent entries.

    :param data: raw HETUS data
    :return: cleaned HETUS data and the list of possible activities
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

    hetus_translations.translate_activity_codes(data)
    activity_types = hetus_translations.get_activity_type_list()

    # extract households and persons
    data_valid_persons, persondata = level_extraction.get_usable_person_data(data)
    utils.stats(data_valid_persons, persondata)
    # data_valid_hhs, hhdata = level_extraction.get_usable_household_data(data)
    return data, persondata, activity_types


@utils.timing
def process_hetus_2010_data(data: pd.DataFrame, categorization_attributes=None):
    """
    Prepare and categorize the data set and calculate
    statistics for each category.

    :param data: the data to process
    """
    data, persondata, activity_types = prepare_data(data)

    # calculate additional columns for categorizing and drop rows
    # where important data is missing
    cat_data = get_diary_categorization_data(data, persondata)
    # categorize the data
    if categorization_attributes is None:
        categorization_attributes = [
            col.Country.ID,
            person_attributes.Sex.title(),
            person_attributes.WorkStatus.title(),
            diary_attributes.DayType.title(),
        ]
    categories = categorize(cat_data, categorization_attributes)
    categories = filter_categories(categories)

    # cat_hhdata = get_hh_categorization_data(hhdata, persondata)

    category_statistics.calc_statistics_per_category(categories, activity_types)


def split_data(data: pd.DataFrame) -> list[pd.DataFrame]:
    """
    Randomly split a dataframe into half.

    :param data: the dataframe to split
    :return: a list containing the dataframe halves
    """
    part1 = data.sample(frac=0.5)
    part2 = data.drop(part1.index)
    return [part1, part2]


def cross_validation_split(data: pd.DataFrame):
    """
    Splits each category of the data set in half, and stores
    both halves in separate directory structures to allow
    cross-validation.

    :param data: the HETUS data to use
    """
    data, persondata, activity_types = prepare_data(data)
    cat_data = get_diary_categorization_data(data, persondata)
    key = [
        col.Country.ID,
        person_attributes.Sex.title(),
        person_attributes.WorkStatus.title(),
        diary_attributes.DayType.title(),
    ]
    categories = categorize(cat_data, key)
    categories = filter_categories(categories)
    # split data of each category
    categories1, categories2 = [], []
    for category in categories:
        data1, data2 = split_data(category.data)
        profile1 = ExpandedActivityProfiles(
            data1, category.profile_type, category.offset, category.resolution
        )
        profile2 = ExpandedActivityProfiles(
            data2, category.profile_type, category.offset, category.resolution
        )
        categories1.append(profile1)
        categories2.append(profile2)

    # create statistics for the split parts separately
    category_statistics.calc_statistics_per_category(categories1, activity_types)
    VALIDATION_DATA_PATH.rename(VALIDATION_DATA_PATH.parent / "Validation Split 1")
    category_statistics.calc_statistics_per_category(categories2, activity_types)
    VALIDATION_DATA_PATH.rename(VALIDATION_DATA_PATH.parent / "Validation Split 2")


def merge_category_sizes_files(path1: Path, path2: Path):
    """
    Merges two different category size files. The files must
    contain the same row indices, but different column
    indices.
    Saves the resulting file next to the first input file.
    Deletes the two original files.

    :param path1: path to the first file
    :param path2: path to the second file
    """
    data1 = pd.read_csv(path1)
    data2 = pd.read_csv(path2)
    if len(data1.columns) == len(data2.columns) == 2 and all(
        data1.columns == data2.columns
    ):
        # only a single categorization attribute
        axis = 0
    else:
        assert len(data1) == len(
            data2
        ), "Cannot merge without specifying the index columns"
        axis = 1
    merged = pd.concat([data1, data2], axis=axis)  # type: ignore
    # remove the duplicated index
    merged = merged.loc[:, ~merged.columns.duplicated()].copy()  # type: ignore
    merged.to_csv(path1.parent / "category_sizes.csv", index=False)
    # delete the original files
    path1.unlink()
    path2.unlink()


def process_all_hetus_countries_AT_separately(
    hetus_path: str,
    key: str | None = None,
    categorization_attributes=None,
    title: str = "",
):
    # process AT data separately (different resolution)
    logging.info("--- Processing HETUS data for AT ---")
    data_at = load_data.load_hetus_files(["AT"], hetus_path, key)
    process_hetus_2010_data(data_at, categorization_attributes)

    # rename categories file
    categories_path = VALIDATION_DATA_PATH / "categories" / "category_sizes.csv"
    categories_at = categories_path.rename(
        categories_path.parent / "category_sizes_AT.csv"
    )

    # process remaining countries
    logging.info("--- Processing HETUS data for all countries except AT ---")
    data = load_data.load_all_hetus_files_except_AT(hetus_path, key)
    process_hetus_2010_data(data, categorization_attributes)
    categories_eu = categories_path.rename(
        categories_path.parent / "category_sizes_EU.csv"
    )

    # merge categories files
    merge_category_sizes_files(categories_at, categories_eu)

    if not title:
        # determine title automatically
        if categorization_attributes:
            title = "_".join(s.lower() for s in categorization_attributes)
        else:
            title = "full_categorization"
    # rename result directory
    Path(VALIDATION_DATA_PATH).rename(VALIDATION_DATA_PATH.parent / title)
    logging.info(f"Finished creating the validation data set '{title}'")


def generate_all_dataset_variants(hetus_path: str, key: str | None = None):
    """
    Generates all relevant variants of the validation data set
    with a different set of categorization attributes.
    """
    country = col.Country.ID
    sex = person_attributes.Sex.title()
    work_status = person_attributes.WorkStatus.title()
    day_type = diary_attributes.DayType.title()
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
    process_hetus_2010_data(data)
    Path(VALIDATION_DATA_PATH).rename(
        VALIDATION_DATA_PATH.parent / "sex_work status_day type"
    )
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

    HETUS_PATH = (
        "/storage_cluster/projects/2022-d-neuroth-phd/data/hetus_2010_encrypted/"
    )
    key = load_data.read_key_as_arg()
    generate_all_dataset_variants(HETUS_PATH, key)

    # process_all_hetus_countries_AT_separately(HETUS_PATH, key)

    # data = load_data.load_all_hetus_files_except_AT()
    # data = load_data.load_hetus_files(["FI"], HETUS_PATH, key=key)
    # process_hetus_2010_data(data)
    # cross_validation_split(data)
