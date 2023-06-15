import logging
import time
from hetus_data_processing.data_analysis import compare_hh_size_and_participants
import load_data
import household_extraction
import filter

import hetus_columns as col
from utils import HetusDayType


def main():
    pass


if __name__ == "__main__":
    main()
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # data = load_data.load_all_hetus_files()
    data = load_data.load_hetus_file("DE")
    #TODO: remove inconsistent households also from full data set
    hhdata = household_extraction.get_household_data(data)
    print(f"Number of diary entries: {len(data)}")
    print(f"Number of households: {len(hhdata)}")

    compare_hh_size_and_participants(data)

    filters = {
        col.Diary.WEEKDAY: [1],
        col.Diary.MONTH: [6, 7, 8],
        col.Country.ID: ["DE", "AT"],
        col.HH.SIZE: [1,2,3,4],
    }
    d = filter.filter_combined(data, filters)
    print(len(d))


    pass


    #TODO: check which percentage of the data has missing values in the relevant fields (filter fields and diaries)