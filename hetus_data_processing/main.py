import logging
import load_data
import level_extraction
import filter

from tabulate import tabulate

import hetus_columns as col
from hetus_values import DayType, EmployedStudent


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def stats(data, persondata=None, hhdata=None):
    """Print some basic statistics on HETUS data"""
    print(
        tabulate(
            [
                ["Number of diaries", len(data)],
                ["Number of persons", len(persondata)]
                if persondata is not None
                else [],
                ["Number of households", len(hhdata)] if hhdata is not None else [],
            ]
        )
    )


def check_data_availabilty(data, persondata, hhdata):
    d = filter.filter_stats(
        filter.filter_combined, "sick", data, {col.Diary.DAYTYPE: [DayType.sick]}
    )
    d = filter.filter_stats(
        filter.filter_no_data, "No day type specified", data, col.Diary.DAYTYPE
    )
    d = filter.filter_stats(
        filter.filter_no_data,
        "EmployedStudent no data",
        data,
        col.Diary.EMPLOYED_STUDENT,
    )
    d = filter.filter_stats(filter.filter_no_data, "", data, col.Person.WEEKLY_WORKING_HOURS)


if __name__ == "__main__":
    main()

    # data = load_data.load_all_hetus_files()
    data = load_data.load_hetus_files(["LU", "AT"])
    data.set_index(col.Diary.KEY, inplace=True)
    stats(data)

    data, persondata = level_extraction.get_usable_person_data(data)
    stats(data, persondata)

    data, hhdata = level_extraction.get_usable_household_data(data)
    stats(data, persondata, hhdata)

    check_data_availabilty(data, persondata, hhdata)

    pass

    # TODO: check which percentage of the data has missing values in the relevant fields (filter fields and diaries)
