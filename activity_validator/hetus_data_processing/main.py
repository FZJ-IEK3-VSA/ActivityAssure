import logging

import activity_validator.hetus_data_processing.hetus_columns as col
from activity_validator.hetus_data_processing import (
    hetus_translations,
    level_extraction,
)
from activity_validator.hetus_data_processing import load_data
from activity_validator.hetus_data_processing import utils
from activity_validator.hetus_data_processing.attributes import (
    diary_attributes,
    person_attributes,
)
from activity_validator.hetus_data_processing.categorize import (
    categorize,
    get_diary_categorization_data,
)
from activity_validator.hetus_data_processing import category_statistics


@utils.timing
def process_hetus_2010_data():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    data = None
    # data = load_data.load_all_hetus_files_except_AT()
    if data is None:
        data = load_data.load_hetus_files(["DE"])
    assert data is not None
    data.set_index(col.Diary.KEY, inplace=True)
    utils.stats(data)

    hetus_translations.translate_activity_codes(data)
    hetus_translations.save_final_activity_types()

    # extract households and persons
    data_valid_persons, persondata = level_extraction.get_usable_person_data(data)
    utils.stats(data_valid_persons, persondata)
    # data_valid_hhs, hhdata = level_extraction.get_usable_household_data(data)
    # utils.stats(data, data_valid_persons, data_valid_hhs)

    # cat_persondata = get_person_categorization_data(persondata)
    key = [
        col.Country.ID,
        person_attributes.Sex.title(),
        person_attributes.WorkStatus.title(),
    ]
    # categorize(cat_persondata, key)

    cat_data = get_diary_categorization_data(data, persondata)
    key += [diary_attributes.DayType.title()]
    categories = categorize(cat_data, key)
    # cat_hhdata = get_hh_categorization_data(hhdata, persondata)

    category_statistics.calc_statistics_per_category(categories)

    # data_checks.all_data_checks(data, persondata, hhdata)

    pass


if __name__ == "__main__":
    process_hetus_2010_data()
