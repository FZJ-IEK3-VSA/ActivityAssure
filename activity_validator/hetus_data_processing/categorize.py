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
    work = person_attributes.determine_work_statuses(persondata)
    sex = person_attributes.determine_sex(persondata)
    pdata = pd.concat([persondata, work, sex], axis=1)
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
    data = data.join(
        persondata.loc[
            :, (person_attributes.WorkStatus.title(), person_attributes.Sex.title())
        ]
    )
    # drop diaries of persons with missing key attributes
    data = data[data[person_attributes.WorkStatus.title()].notna()]
    # calculate additional attributes
    daytype = diary_attributes.determine_day_types(data)
    data = pd.concat([data, daytype], axis=1)
    data = data[
        data[diary_attributes.DayType.title()] != diary_attributes.DayType.undetermined
    ]
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


def get_category_sizes(categories, key: list[str]) -> pd.DataFrame:
    """
    Returns a DataFrame with the size of each category, in a readable format.

    :param categories: the result of calling groupby on HETUS data
    :param key: the key used in groupby
    :return: a DataFrame containing category sizes
    """
    # create separate index without country for a better overview
    sizes = categories.size()
    if len(key) > 1:
        # set country as column header to enhance clarity
        cat_index = key.copy()
        cat_index.remove(key[0])
        sizes = sizes.reset_index().pivot(index=cat_index, columns=key[0], values=0)
    return sizes


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
    category_sizes = get_category_sizes(categories, key)
    logging.info(
        f"Sorted {len(data)} entries into {category_sizes.count().sum()} categories."
    )
    print(category_sizes)
    activity_profile.save_df(category_sizes, "categories", "categories")
    return [
        ExpandedActivityProfiles(
            categories.get_group(g),
            (p := ProfileType.from_iterable(g)),  # type: ignore
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
    filtered = [c for c in categories if len(c.data) >= hetus_constants.MIN_CELL_SIZE]
    logging.info(
        f"{len(filtered)} out of {len(categories)} categories can be published."
    )
    return filtered
