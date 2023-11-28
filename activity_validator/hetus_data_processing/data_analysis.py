"""
Contains rather prototyped functions that can be helpful for further examining
specific aspects of the HETUS data if necessary.
"""

import pandas as pd
from activity_validator.hetus_data_processing import hetus_translations
from activity_validator.hetus_data_processing.activity_profile import (
    ExpandedActivityProfiles,
)
from activity_validator.hetus_data_processing.category_statistics import (
    calc_probability_profiles,
)

import activity_validator.hetus_data_processing.hetus_columns as col
from activity_validator.hetus_data_processing.hetus_translations import (
    load_hetus_activity_codes,
)
from activity_validator.hetus_data_processing import level_extraction


def detect_household_level_columns(data: pd.DataFrame) -> pd.Index:
    """
    Analysis-function for checking which columns are actually on household
    level and thus always have the same value for all entries belonging to
    the same household.
    Can be used to check for which hosehold level columns the data
    is acutally consistent across all entries.

    :param data: hetus data
    :return: index containing all columns on household level
    """
    # count how many different values for each column there are within a single household
    num_values_per_hh = data.groupby(col.HH.KEY).nunique()
    # get the columns that always have the same value within a single household
    hh_data = (num_values_per_hh == 1).all(axis=0)  # type: ignore
    hh_data = hh_data.loc[hh_data == True]
    return hh_data.index


def compare_hh_size_and_participants(data: pd.DataFrame):
    """
    Compares the household size fields with the number of HETUS particpants (different PIDs)
    to find out how many household members did not participate
    """
    data = data.reset_index().set_index(col.HH.KEY)
    grouped = data.groupby(level=col.HH.KEY)  # type: ignore
    hhdata = grouped.first()
    participants_per_hh = grouped.nunique()["PID"]
    merged = pd.concat([hhdata["HHC1"], hhdata["HHC3"], participants_per_hh], axis=1)

    print(
        "--- Comparing the HH size column (HHC1) to the number of respondents per household"
    )
    # this Diff column shows how many household members did not take part in the survey
    merged["Diff"] = merged["HHC1"] - merged["PID"]
    total_hh_members = merged["HHC1"].sum()
    # total number of hh members that did not participate
    hh_with_too_few_members = merged["Diff"][merged["Diff"] > 0]
    missing_members = hh_with_too_few_members.sum()
    incomplete_hh = hh_with_too_few_members.count()
    print(f"Total number of HH members: {total_hh_members}")
    print(
        f"Number of HH members that did not participate in the survey: {missing_members}"
    )
    print(
        f"Participation rate (without children): {round((total_hh_members - missing_members)/total_hh_members, 2)}"
    )
    print(f"Rate of incomplete households: {round(incomplete_hh / len(hhdata), 2)}")

    # same numbers, but considering that children did not participate in general (actually not only children <7, but <10)
    total_without_child = merged["HHC1"].sum() - merged["HHC3"].sum()
    merged["Diff2"] = merged["HHC1"] - merged["PID"] - merged["HHC3"]

    hh_with_too_few_members_no_child = merged["Diff2"][merged["Diff2"] > 0]
    missing_without_child = hh_with_too_few_members_no_child.sum()
    incomplete_hh_without_child = hh_with_too_few_members_no_child.count()
    print(f"Total number of HH members (without children): {total_without_child}")
    print(
        f"Number of HH members that did not participate in the survey (without children): {missing_without_child}"
    )
    print(
        f"Participation rate (without children): {round((total_without_child - missing_without_child)/total_without_child, 2)}"
    )
    print(
        f"Rate of incomplete households (without children): {round(incomplete_hh_without_child / len(hhdata), 2)}"
    )

    merged_lt_0 = merged[merged["Diff"] < 0]
    # HHC1 is topped at 5
    assert (
        merged_lt_0["HHC1"] == 5
    ).all(), "There are households with a higher number of survey participants than the HH size in HHC1"
    print(
        "There are never more participants from a HH than indicated in HHC1 (HH size)"
    )


def show_inconsistent_households(data: pd.DataFrame):
    """
    Analysis-function for showing inconsistencies in the data regarding households,
    i.e. where several entries belonging to the same household contain different
    values for household-level columns.

    :param data: the data to check
    """
    hhdata = data[col.HH.ALL]
    num_values_per_hh = hhdata.groupby(col.HH.KEY).nunique()
    inconsistent_hh_per_column = (num_values_per_hh != 1).sum(axis=0)  # type: ignore
    print(f"Inconsistencies per column: \n{inconsistent_hh_per_column}")
    inconsistent_columns_per_hh = (num_values_per_hh != 1).sum(axis=1)  # type: ignore
    inconsistent_households = inconsistent_columns_per_hh[
        inconsistent_columns_per_hh > 0
    ]
    print(
        f"Households with inconsistencies: {len(inconsistent_households)} of {len(data)}"
        f"\n{inconsistent_households}"
    )
    return inconsistent_hh_per_column, inconsistent_households


def analyze_inconsistent_households(data: pd.DataFrame):
    """
    Some more or less unstructured code to analyze further inconsistencies in the
    italian HETUS data on household level.
    """
    data = level_extraction.limit_to_columns_by_level(data, col.HH)
    num_values_per_hh = data.groupby(col.HH.KEY).nunique()
    inconsistent_columns_per_hh = (num_values_per_hh != 1).sum(axis=1)  # type: ignore
    errors_per_hh = inconsistent_columns_per_hh[inconsistent_columns_per_hh > 0]
    data.set_index(col.HH.KEY, inplace=True)
    inconsistent_hh = data.loc[(errors_per_hh.index)]
    grouped = inconsistent_hh.groupby(level="HID")
    # list all rows where the numbers of household members of different age classes
    # don't add up to the total
    invalid_rows = []
    new_index = []
    for index, df in grouped:
        for i, row in df.iterrows():
            # only these rows are affected
            n1 = row["HHC3"]  # children < 7
            n2 = row["HHC4"]  # person 7-17
            n3 = row["HHC5"]  # person >17
            s = row["HHC1"]  # sum of persons, topped at 5
            # 2 means 2 or more, so we cannot really check these entries
            if n1 in [0, 1] and n2 in [0, 1] and n3 in [0, 1]:
                x = n1 + n2 + n3
                if x != s:
                    print(f"{index:>5}:{i} - expected {s}, but sum is {x}")
                    invalid_rows.append(row)
                    new_index.append(i)
    # This dataframe contains all entries where the member counts don't add up
    invalid = pd.DataFrame(data=invalid_rows, index=new_index)
    # The following line shows that there are also households with multiple invalid entries
    invalid[invalid.index.duplicated(keep=False)]
    # TODO: I could check how many valid entries there are for each invalid household:
    #   - are there households without any valid entry?
    #   - are there households where valid entries are in the minority?
    # Depending on that, I might be able to determine the correct values for all columns


def compare_mact_and_pact(a2: pd.DataFrame, a3: pd.DataFrame):
    """
    The fields Mact (main activity) and Pact (main aggregated activity)
    don't always match. This function analyzes differences.

    Response from Eurostat: Pact uses a different coding. Researchers
    should only use Mact.
    """
    # get the 2-digit codes that correspond to the 3-digit codes
    a2_check = a3.map(lambda x: x[:2] if isinstance(x, str) else x)
    a2_check.columns = a2.columns

    # check if the 2-digit codes in the database (a2) and the 2-digit codes
    # obtained from the 2-digit codes (a2_check) match
    diff = a2 != a2_check
    equal_per_col = diff.sum(axis=0)  # type: ignore
    equal_per_entry = diff.sum(axis=1)  # type: ignore

    combinations = pd.DataFrame(
        {"Combinations": zip(a2.values.flatten(), a2_check.values.flatten())}
    )
    print(combinations.value_counts())


def activity_frequencies(data: pd.DataFrame):
    # extract main activity columns (normal and aggregated)
    # hint: PACT is not the equivalent of 2-digit codes, it is
    # a different, internal format from Eurostat
    pact = data.filter(like=col.Diary.MAIN_ACTIVITIES_AGG_PATTERN)
    a3 = col.get_activity_data(data)

    a2_frequency = pact.stack().value_counts()
    a3_frequency = a3.stack().value_counts()

    a1 = a3.map(lambda x: x[0] if isinstance(x, str) else x)
    a1_frequency = a1.stack().value_counts()

    # convert to average time per diary in minutes
    time_factor = 10 / len(data)
    a1_frequency = a1_frequency * time_factor
    a2_frequency = a2_frequency * time_factor
    a3_frequency = a3_frequency * time_factor

    codes = load_hetus_activity_codes()
    a1_frequency.index = a1_frequency.index.map(lambda x: codes.get(x, x))
    a2_frequency.index = a2_frequency.index.map(lambda x: codes.get(x, x))
    a3_frequency.index = a3_frequency.index.map(lambda x: codes.get(x, x))

    print(a1_frequency)


def calc_overall_activity_shares(data: pd.DataFrame, activity_types=None) -> pd.Series:
    """
    Calculates the overall share of each activity type

    :param data: HETUS diary data
    :param activity_types: optionally pass the available activity types.
                           Is determined automatically if not passed.
    :return: the overall share for each activity type
    """
    if activity_types is None:
        activity_types = hetus_translations.save_final_activity_types()
    hetus_translations.translate_activity_codes(data)
    data = col.get_activity_data(data)
    probabilities = calc_probability_profiles(data, activity_types)
    overall_shares = probabilities.mean(axis=1)
    return overall_shares


def calc_activity_share_per_profile_type(
    categories: list[ExpandedActivityProfiles],
) -> pd.DataFrame:
    """
    Calculates the activity shares in each profile type individually.

    :param categories: list of profiles per type
    :return: activity shares per type
    """
    activity_types = hetus_translations.save_final_activity_types()
    shares_per_group = pd.DataFrame(
        {
            d.profile_type: calc_overall_activity_shares(d.data, activity_types)
            for d in categories
        }
    )
    return shares_per_group
