"""
Example that demonstrates usage of ETHOS.ActivityAssure for comparing
validation datasets of different countries.
"""

import logging
from pathlib import Path

from activityassure import utils, pandas_utils, validation
from activityassure import comparison_indicators
from activityassure import categorization_attributes
from activityassure.categorization_attributes import WorkStatus
from activityassure.hetus_data_processing import hetus_column_values, hetus_constants
from activityassure.input_data_processing import process_model_data
from activityassure.profile_category import ProfileCategory
from activityassure.visualizations import (
    indicator_heatmaps,
    metric_comparison,
    time_statistics,
)
from activityassure.validation_statistics import ValidationSet
import pandas as pd


@utils.timing
def validate(
    country1: ValidationSet,
    country2: ValidationSet,
) -> dict[str, float]:
    # determine the resolution of the datasets
    resolution1 = len(next(iter(country1.statistics.values())).probability_profiles)
    resolution2 = len(next(iter(country2.statistics.values())).probability_profiles)
    # Prepare validation data, convert resolution
    if resolution1 != resolution2:
        for _, v in (country1.statistics | country2.statistics).items():
            # durations
            v.activity_durations.index = v.activity_durations.index.ceil("30min")  # type: ignore
            v.activity_durations = v.activity_durations.resample("30min").sum()

            # interpolate probability profiles to 10 minute resolution
            if len(v.probability_profiles.columns) != 144:
                v.probability_profiles = comparison_indicators.resample_columns(
                    v.probability_profiles, 144
                )

    # compare input and validation data statistics per profile category
    indicator_dict_variants = validation.validate_per_category(
        country1,
        country2,
        output_path,
        ignore_country=True,
    )

    # save indicators and heatmaps for each indicator variant
    indices = {}
    for variant_name, indicator_set in indicator_dict_variants.items():
        index = validation.get_similarity_index(
            country1,
            indicator_set,
            True,
        )
        indices[variant_name] = index
    return indices


def merge_unemployed_categories(data_path: Path, result_path: Path):
    """Merge categories for work days and non-working days of unemployed people"""
    # load the statistics
    set = ValidationSet.load(data_path)
    # combine all 'unemployed' and 'retired' categories which only differ in day type
    WORK_TYPES_TO_MERGE = [WorkStatus.unemployed, WorkStatus.retired]
    mapping = {
        p: ProfileCategory(
            p.country,
            p.sex,
            p.work_status,
            categorization_attributes.DayType.undetermined,
        )
        for p in set.statistics.keys()
        if p.work_status in WORK_TYPES_TO_MERGE
    }
    set.merge_profile_categories(mapping)
    # save the aggregated statistics
    set.save(result_path)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Validation statistics paths. If missing, run example_validation_data_comparison.py
    # first to create the merged dataset.
    validation_path_merged = Path(
        "data/validation_data_sets/activity_validation_data_set_merged_daytypes"
    )
    output_path = Path("data/country_comparison")

    countries = list(hetus_column_values.HETUS2010_COUNTRIES)
    # preload all country datasets
    country_datasets = {
        country: ValidationSet.load(validation_path_merged, country=country)
        for country in countries
    }
    dfs = {
        k: pd.DataFrame(index=countries, columns=countries)
        for k in ["default", "scaled", "normed"]
    }
    for country1 in countries:
        for country2 in countries:
            # validate the input data using the statistics
            indices = validate(country_datasets[country1], country_datasets[country2])
            for variant, index in indices.items():
                df = dfs[variant]
                df.loc[country1, country2] = indices[variant]
    for variant, df in dfs.items():
        pandas_utils.save_df(df, output_path, f"similarity_indices_{variant}")
