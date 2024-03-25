from activity_validator import categorization_attributes
from activity_validator.hetus_data_processing import load_data
from activity_validator.hetus_data_processing import main
from activity_validator.profile_category import ProfileCategory
from test_statistics import check_validation_statistics_size


def test_validation_data_set_ceation():
    """
    Tests creation of the valdiation data set out of HETUS data.
    """
    # load and process an artifical time use survey data set in HETUS format
    HETUS_PATH = "test/test_data/time use survey data"
    data = load_data.load_hetus_files(["TEST"], HETUS_PATH)
    result = main.process_hetus_2010_data(data, hetus_data_protection=False)

    assert len(result.activities) == 15, "Incorrect activity list"
    assert len(result.statistics) == 20, "Missing profile categories"

    # check one of the statistics objects
    category = ProfileCategory(
        "DE",
        categorization_attributes.Sex.female,
        categorization_attributes.WorkStatus.full_time,
        categorization_attributes.DayType.work,
    )
    assert category in result.statistics, "A profile category is missing"
    statistics = result.statistics[category]
    check_validation_statistics_size(statistics, result.activities)

    # check the category sizes dataframe
    category_sizes = result.get_category_info_dataframe(
        "Sizes", lambda stat: stat.category_size
    )
    assert category_sizes.to_numpy().sum() == 21, "Incorrect category sizes"

    # check category filtering
    result.filter_categories(2)
    assert len(result.statistics) == 1, "Filtering did not work as expected"
