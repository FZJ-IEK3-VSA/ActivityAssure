"""
Functions for calculating additional attributes categorizing
the diary entries.
"""

import logging
import pandas as pd
from activity_validator import categorization_attributes, utils
from activity_validator.activity_profile import (
    ExpandedActivityProfiles,
    ProfileCategory,
)

import activity_validator.hetus_data_processing.hetus_column_names as col
from activity_validator.hetus_data_processing import hetus_constants
from activity_validator.hetus_data_processing.attributes import (
    person_attributes,
    diary_attributes,
)


@utils.timing
def get_person_data_for_categorization(persondata: pd.DataFrame) -> pd.DataFrame:
    """
    Calcluates attributes needed to categorize the persons. Removes
    all persons for which theses attributes could not be determined.

    :param persondata: HETUS person data
    :return: HETUS person data for categorization
    """
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
def get_diary_data_for_categorization(
    data: pd.DataFrame, persondata: pd.DataFrame
) -> pd.DataFrame:
    """
    Adds all attributes necessary to categorize the diaries. Removes
    all diaries where these attributes could not be determined.

    :param data: HETUS data
    :param persondata: HETUS person data
    :return: HETUS data ready for categorization
    """
    persondata = get_person_data_for_categorization(persondata)
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
def categorize(
    data: pd.DataFrame, cat_attributes: list[str], include_weights: bool = False
) -> list[ExpandedActivityProfiles]:
    """
    Groups all entries into categories, depending on the categorization
    keys. Each value combination of the specified key columns results in a
    separate category.

    :param data: the data to categorize
    :param cat_attributes: the column names to use for categorization
    :param include_weights: if HETUS weights should be included
    :return: the separated data sets for all categories
    """
    # check if wheights are available if they shall be included
    weights_ok = col.Diary.DAY_AND_PERSON_WEIGHT in data.columns or not include_weights
    assert weights_ok, f"Weight column '{col.Diary.DAY_AND_PERSON_WEIGHT}' is missing"
    categories = data.groupby(cat_attributes)
    logging.info(f"Sorted {len(data)} entries into {categories.ngroups} categories.")
    groups = {
        ProfileCategory.from_index_tuple(
            cat_attributes,
            group_key,  # type: ignore[arg-type]
        ): categories.get_group(group_key)
        for group_key in categories.groups
    }
    return [
        ExpandedActivityProfiles(
            col.get_activity_data(group),
            profile_type,
            hetus_constants.PROFILE_OFFSET,
            hetus_constants.get_resolution(profile_type.country),
            group[col.Diary.DAY_AND_PERSON_WEIGHT] if include_weights else None,
        )
        for profile_type, group in groups.items()
    ]
