"""
Functions for categorizing all persons or households in HETUS data sets using
different criteria
"""

import logging
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import (
    ExpandedActivityProfiles,
    ProfileType,
)

import activity_validator.hetus_data_processing.hetus_columns as col
from activity_validator.hetus_data_processing import hetus_constants, utils
from activity_validator.hetus_data_processing.attributes import (
    diary_attributes,
    person_attributes,
)


@utils.timing
def get_person_categorization_data(persondata: pd.DataFrame) -> pd.DataFrame:
    # calculate additionaly attributes and combine them with the data
    country = person_attributes.determine_country(persondata)
    work = person_attributes.determine_work_statuses(persondata)
    sex = person_attributes.determine_sex(persondata)
    pdata = pd.concat([persondata, country, work, sex], axis=1)
    # remove persons where key attributes are missing
    pdata = pdata[
        pdata[person_attributes.WorkStatus.title()].apply(lambda x: x.is_determined())
    ]
    # select the key attributes to use for categorization
    return pdata


@utils.timing
def get_diary_categorization_data(
    data: pd.DataFrame, persondata: pd.DataFrame
) -> pd.DataFrame:
    persondata = get_person_categorization_data(persondata)
    columns = [
        person_attributes.Country.title(),
        person_attributes.WorkStatus.title(),
        person_attributes.Sex.title(),
    ]
    data = data.join(persondata.loc[:, columns])
    # drop diaries of persons with missing key attributes
    data = data[data[person_attributes.WorkStatus.title()].notna()]
    # calculate additional attributes
    daytype = diary_attributes.determine_day_types(data)
    data = pd.concat([data, daytype], axis=1)
    daytype_col = diary_attributes.DayType.title()
    data = data[data[daytype_col] != diary_attributes.DayType.undetermined]
    return data


def get_hh_categorization_data(
    hhdata: pd.DataFrame, persondata: pd.DataFrame
) -> pd.DataFrame:
    persondata = get_person_categorization_data(persondata)
    persondata.loc[:, [col.Person.SEX, person_attributes.WorkStatus.title()]].groupby(
        col.HH.KEY
    ).apply(list)

    # TODO: how do I treat diaries from one household, but from different days?
    # --> ignore at first and check if there are weird statistics later
    return None


def apply_hetus_size_limits(category_sizes: pd.DataFrame) -> None:
    """
    Applies the HETUS cell size limits from Eurostat. Works inplace.
    Eurostat specifies two size limits. Below these limits, only
    the range of the cell size may be specified, not the exact size.

    :param category_sizes: the category size dataframe to adapt
    """
    # For sizes below the limits, overwrites the actual size with the
    # respective limit
    # the between mask cannot be created for the whole dataframe at once
    for col in category_sizes.columns:
        upper_limit = category_sizes[col].between(
            hetus_constants.MIN_CELL_SIZE,
            hetus_constants.MIN_CELL_SIZE_FOR_SIZE,
            inclusive="left",
        )
        category_sizes.loc[upper_limit, col] = hetus_constants.MIN_CELL_SIZE_FOR_SIZE
    # the values below the lower limit can be overwritten at once
    category_sizes[category_sizes < hetus_constants.MIN_CELL_SIZE] = (
        hetus_constants.MIN_CELL_SIZE
    )


@utils.timing
def categorize(data: pd.DataFrame, key: list[str]) -> list[ExpandedActivityProfiles]:
    """
    Groups all entries into categories, depending on the categorization
    keys. Each value combination of the specified key columns results in a
    separate category.

    :param data: the data to categorize
    :param key: the column names to use for categorization
    :return: the separated data sets for all categories
    """
    categories = data.groupby(key)
    logging.info(f"Sorted {len(data)} entries into {categories.ngroups} categories.")
    return [
        ExpandedActivityProfiles(
            categories.get_group(g),
            (p := ProfileType.from_index_tuple(key, g)),  # type: ignore
            hetus_constants.PROFILE_OFFSET,
            hetus_constants.get_resolution(p.country),
        )
        for g in categories.groups
    ]


@utils.timing
def filter_categories(
    categories: list[ExpandedActivityProfiles],
) -> list[ExpandedActivityProfiles]:
    """
    Removes all categories that are too small and don't
    fullfill the requirements by EUROSTAT to permit publication

    :param categories: the categories to filter
    :return: the categories that can be published
    """
    total_entries = sum(len(c.data) for c in categories)
    filtered = [c for c in categories if len(c.data) >= hetus_constants.MIN_CELL_SIZE]
    kept_entries = sum(len(c.data) for c in filtered)
    keep_ratio = round(100 * kept_entries / total_entries, 1)
    logging.info(
        f"{len(filtered)} out of {len(categories)} categories can be published. "
        f"These contain {kept_entries} of {total_entries} entries ({keep_ratio} %)."
    )
    return filtered
