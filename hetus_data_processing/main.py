import logging
from hetus_data_processing.utils import DayType
import load_data
import level_extraction
import filter

from tabulate import tabulate

import hetus_columns as col


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


if __name__ == "__main__":
    main()

    # data = load_data.load_all_hetus_files()
    data = load_data.load_hetus_files(["DE"])
    data.set_index(col.Diary.KEY, inplace=True)
    stats(data)

    data, persondata = level_extraction.get_usable_person_data(data)
    stats(data, persondata)

    data, hhdata = level_extraction.get_usable_household_data(data)
    stats(data, persondata, hhdata)

    filters = {col.Diary.DAYTYPE: [DayType.sick]}

    sick = filter.filter_stats(data, {col.Diary.DAYTYPE: [DayType.sick]})
    no_day_type = filter.filter_stats(data, {col.Diary.DAYTYPE: DayType.no_data()}, "No day type specified")

    pass

    # TODO: check which percentage of the data has missing values in the relevant fields (filter fields and diaries)
