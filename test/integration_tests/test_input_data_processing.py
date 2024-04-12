from datetime import timedelta
from pathlib import Path
from activity_validator import activity_mapping, categorization_attributes
from activity_validator.hetus_data_processing import load_data
from activity_validator.hetus_data_processing import validation_data_set_creation
from activity_validator.input_data_processing import process_model_data
from activity_validator.profile_category import ProfileCategory
from test_statistics import (
    check_validation_statistics_size,
)


def test_lpg_example():
    # load and process an artifical time use survey data set in HETUS format
    lpg_input_dir = Path("examples/LoadProfileGenerator/data")
    input_data_path = lpg_input_dir / "preprocessed"
    mapping_file = lpg_input_dir / "activity_mapping.json"
    person_trait_file = lpg_input_dir / "person_characteristics.json"
    merging_file = lpg_input_dir / "activity_merging.json"
    profile_resolution = timedelta(minutes=1)

    HETUS_PATH = "test/test_data/time use survey data"
    data = load_data.load_hetus_files(["TEST"], HETUS_PATH)
    validation_statistics = validation_data_set_creation.process_hetus_2010_data(
        data, hetus_data_protection=False
    )
    # merge activities for LPG example
    mapping, _ = activity_mapping.load_mapping_and_activities(merging_file)
    validation_statistics.map_statistics_activities(mapping)

    # process the LPG data
    input_statistics = process_model_data.process_model_data(
        input_data_path,
        mapping_file,
        person_trait_file,
        profile_resolution,
        categories_per_person=False,
    )
    assert len(input_statistics.statistics) == 4, "Unexpected statistics count"
    assert set(input_statistics.activities) == set(
        validation_statistics.activities
    ), "Different activities"

    # check one of the statistics objects
    category = ProfileCategory(
        "DE",
        categorization_attributes.Sex.female,
        categorization_attributes.WorkStatus.full_time,
        categorization_attributes.DayType.work,
    )
    assert category in input_statistics.statistics, "A profile category is missing"
    statistics = input_statistics.statistics[category]
    check_validation_statistics_size(statistics, input_statistics.activities)

    # validate the statistics
    # indicator_dict_variants = validation.validate_per_category(
    #     input_statistics, validation_statistics, input_path
    # )
