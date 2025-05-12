"""
Example that demonstrates usage of ETHOS.ActivityAssure by validating
the city simulation of the LoadProfileGenerator.
"""

from datetime import timedelta
import logging
from pathlib import Path

from activityassure.input_data_processing import process_model_data
import example_lpg_validation as lpgexample

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)
    # preprocessed input data paths
    lpg_example_data_dir = Path("examples/LoadProfileGenerator/data")
    city_data_path = Path("data/city/preprocessed/scenario_city-julich_mini")
    merging_file = lpg_example_data_dir / "activity_merging_city.json"
    mapping_file = lpg_example_data_dir / "activity_mapping_city.json"
    person_trait_file = lpg_example_data_dir / "person_characteristics.json"
    # validation statistics paths
    validation_stats_path = Path(
        "data/validation_data_sets/activity_validation_data_set"
    )
    validation_stats_path_merged = Path(f"{validation_stats_path}_merged")
    # input statistics path
    # here the statistics of the input data and the validation results will be stored
    city_stats_path = Path("data/city/validation") / city_data_path.name
    city_stats_path_merged = Path(f"{city_stats_path}_merged")

    # the LoadProfileGenerator simulates cooking and eating as one activity, therefore these
    # two activities must be merged in the validation statistics
    process_model_data.merge_activities(
        validation_stats_path, merging_file, validation_stats_path_merged
    )

    # calculate statistics for the input model data
    input_statistics = process_model_data.process_model_data(
        city_data_path,
        mapping_file,
        person_trait_file,
        profile_resolution,
        categories_per_person=False,
    )
    # save the created statistics
    input_statistics.save(city_stats_path)

    # apply the activity merging to the city simulation results as well
    process_model_data.merge_activities(
        city_stats_path, merging_file, city_stats_path_merged
    )

    # validate the input data using the statistics
    lpgexample.validate(city_stats_path_merged, validation_stats_path_merged)

    # additionally, aggregate both statistics to national level and validate with that
    validation_national = Path(f"{validation_stats_path_merged}_national")
    process_model_data.aggregate_to_national_level(
        validation_stats_path_merged, validation_national
    )
    citysim_national = Path(f"{city_stats_path_merged}_national")
    process_model_data.aggregate_to_national_level(
        city_stats_path_merged, citysim_national
    )

    lpgexample.validate(citysim_national, validation_national)
