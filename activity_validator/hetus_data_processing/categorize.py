"""
Functions for calculating additional attributes categorizing
the diary entries.
"""

import logging
import pandas as pd
from activity_validator.hetus_data_processing.activity_profile import (
    ExpandedActivityProfiles,
    ProfileType,
)

from activity_validator.hetus_data_processing import hetus_constants, utils
from activity_validator.hetus_data_processing.attributes import (
    categorization_attributes,
    person_attributes,
    diary_attributes,
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
        pdata[categorization_attributes.WorkStatus.title()].apply(
            lambda x: x.is_determined()
        )
    ]
    # select the key attributes to use for categorization
    return pdata


@utils.timing
def get_diary_categorization_data(
    data: pd.DataFrame, persondata: pd.DataFrame
) -> pd.DataFrame:
    persondata = get_person_categorization_data(persondata)
    columns = [
        categorization_attributes.Country.title(),
        categorization_attributes.WorkStatus.title(),
        categorization_attributes.Sex.title(),
    ]
    data = data.join(persondata.loc[:, columns])
    # drop diaries of persons with missing key attributes
    data = data[data[categorization_attributes.WorkStatus.title()].notna()]
    # calculate additional attributes
    daytype = diary_attributes.determine_day_types(data)
    data = pd.concat([data, daytype], axis=1)
    daytype_col = categorization_attributes.DayType.title()
    data = data[data[daytype_col] != categorization_attributes.DayType.undetermined]
    return data


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
