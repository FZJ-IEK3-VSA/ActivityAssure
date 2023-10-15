"""
Functions for categorizing all persons or households in HETUS data sets using
different criteria
"""

import logging
import pandas as pd
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
    # create separate index without country for a better overview
    cat_index = key.copy()
    cat_index.remove(col.Country.ID)
    category_sizes = (
        categories.size()
        .reset_index()
        .pivot(index=cat_index, columns=col.Country.ID, values=0)
    )
    logging.info(
        f"Sorted {len(data)} entries into {category_sizes.count().sum()} categories."
    )
    print(category_sizes)
    utils.save_df(category_sizes, "categories", "cat", key)
    return [
        ExpandedActivityProfiles(
            categories.get_group(g),
            ProfileType.from_iterable(g),  # type: ignore
            hetus_constants.PROFILE_OFFSET,
        )
        for g in categories.groups
    ]
