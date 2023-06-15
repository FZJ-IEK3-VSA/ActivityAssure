import pandas as pd
from utils import HetusColumns


def compare_hh_size_and_participants(data: pd.DataFrame):
    """
    Compares the household size fields with the number of HETUS particpants (different PIDs)
    to find out how many household members did not participate
    """
    grouped = data.set_index(HetusColumns.HH.KEY).groupby(level=HetusColumns.HH.KEY)  # type: ignore
    hhdata = grouped.first()
    participants_per_hh = grouped.nunique()["PID"]
    merged = pd.concat([hhdata["HHC1"], hhdata["HHC3"], participants_per_hh], axis=1)

    print("--- Comparing the HH size column (HHC1) to the number of respondents per household")
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
    print(f"Rate of incomplete households (without children): {round(incomplete_hh_without_child / len(hhdata), 2)}")

    merged_lt_0 = merged[merged["Diff"] < 0]
    # HHC1 is topped at 5
    assert (
        merged_lt_0["HHC1"] == 5
    ).all(), "There are households with a higher number of survey participants than the HH size in HHC1"
    print(
        "There are never more participants from a HH than indicated in HHC1 (HH size)"
    )


def analyze_inconsistent_households(data: pd.DataFrame):
    """
    Some more or less unstructured code to analyze inconsistent households in the
    italian HETUS data.
    """
    hhdata = data[HetusColumns.HH.COLUMNS]
    num_values_per_hh = hhdata.groupby(HetusColumns.HH.KEY).nunique()
    inconsistent_columns_per_hh = (num_values_per_hh != 1).sum(axis=1)  # type: ignore
    errors_per_hh = inconsistent_columns_per_hh[inconsistent_columns_per_hh > 0]
    hhdata.set_index(HetusColumns.HH.KEY, inplace=True)
    inconsistent_hh = hhdata.loc[(errors_per_hh.index)]
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
