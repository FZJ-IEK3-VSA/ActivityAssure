import logging
import load_data
import household_extraction
import filter

import hetus_columns as col


def main():
    pass


if __name__ == "__main__":
    main()
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = load_data.load_all_hetus_files()
    # data = load_data.load_hetus_files(["AT", "LU"])
    # data = load_data.load_hetus_file("IT")
    data.set_index(col.Diary.KEY, inplace=True)
    
    hhdata = household_extraction.get_usable_household_data(data)
    print(f"Number of diary entries: {len(data)}")
    print(f"Number of households: {len(hhdata)}")
    pass

    #TODO: remove inconsistent households also from full data set

    # compare_hh_size_and_participants(data)

    filters = {
        col.Diary.WEEKDAY: [1],
        col.Diary.MONTH: [6, 7, 8],
        col.HH.SIZE: [1,2,3,4],
    }
    d = filter.filter_combined(data, filters)
    print(len(d))


    pass


    #TODO: check which percentage of the data has missing values in the relevant fields (filter fields and diaries)