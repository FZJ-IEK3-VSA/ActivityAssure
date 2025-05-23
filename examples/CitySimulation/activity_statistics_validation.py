"""
Example that demonstrates usage of ETHOS.ActivityAssure by validating
the city simulation of the LoadProfileGenerator.
"""

from datetime import timedelta
import logging
from pathlib import Path

from activityassure import validation
from activityassure.input_data_processing import process_model_data


def calc_citysim_statistics_and_validate(preprocessed_data_path: Path):
    # define all input and output paths and other parameters
    profile_resolution = timedelta(minutes=1)

    # additional files with mappings and person information
    example_data_dir = Path("examples/CitySimulation/data")
    merging_file = example_data_dir / "activity_merging_city.json"
    mapping_file = example_data_dir / "activity_mapping_city.json"
    person_trait_file = Path("examples/LoadProfileGenerator/data/person_characteristics.json")
    # validation statistics paths
    validation_stats_path = Path(
        "data/validation_data_sets/activity_validation_data_set"
    )
    validation_stats_path_merged = Path(f"{validation_stats_path}_merged")
    # input statistics path
    # here the statistics of the input data and the validation results will be stored
    city_stats_path = Path("data/city/validation") / preprocessed_data_path.name
    city_stats_path_merged = Path(f"{city_stats_path}_merged")

    # the LoadProfileGenerator simulates cooking and eating as one activity, therefore these
    # two activities must be merged in the validation statistics
    process_model_data.merge_activities(
        validation_stats_path, merging_file, validation_stats_path_merged
    )

    # calculate statistics for the input model data
    input_statistics = process_model_data.process_model_data(
        preprocessed_data_path,
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
    validation.default_validation(city_stats_path_merged, validation_stats_path_merged)

    # additionally, aggregate both statistics to national level and validate with that
    validation_national = Path(f"{validation_stats_path_merged}_national")
    process_model_data.aggregate_to_national_level(
        validation_stats_path_merged, validation_national
    )
    citysim_national = Path(f"{city_stats_path_merged}_national")
    process_model_data.aggregate_to_national_level(
        city_stats_path_merged, citysim_national
    )

    validation.default_validation(citysim_national, validation_national)

    # TODO: futher validation steps:
    # - include POI validation
    # - add travel validation
    # - activity statistics, if that adds anything to this


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # path to a directory with preprocessed activitiy profiles in csv format
    preprocessed_city_data = Path("data/city/preprocessed/scenario_city-julich_mini")
    calc_citysim_statistics_and_validate(preprocessed_city_data)


if __name__ == "__main__":
    main()
