"""
Example that demonstrates usage of ETHOS.ActivityAssure for comparing
validation datasets of different countries.
"""

from collections import defaultdict
import logging
from pathlib import Path

from activityassure import utils, pandas_utils, validation
from activityassure import comparison_indicators
from activityassure.hetus_data_processing import hetus_column_values
from activityassure.validation_statistics import ValidationSet
import pandas as pd


@utils.timing
def get_similiarity_indices(
    country1: ValidationSet,
    country2: ValidationSet,
) -> dict[str, dict[str, float]]:
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
    all_indices = {}
    for variant_name, indicator_set in indicator_dict_variants.items():
        indices = validation.get_similarity_index(
            country1,
            indicator_set,
            True,
        )
        all_indices[variant_name] = indices
    return all_indices


def create_similarity_matrices(
    validation_path_merged: Path, output_path: Path, countries: list[str]
) -> None:
    # preload all country datasets
    country_datasets = {
        country: ValidationSet.load(validation_path_merged, country=country)
        for country in countries
    }
    dfs: dict[str, dict[str, pd.DataFrame]] = defaultdict(
        lambda: defaultdict(lambda: pd.DataFrame(index=countries, columns=countries))
    )
    for country1 in countries:
        for country2 in countries:
            # validate the input data using the statistics
            index_variants = get_similiarity_indices(
                country_datasets[country1], country_datasets[country2]
            )
            for variant, indices in index_variants.items():
                for indicator, index in indices.items():
                    df = dfs[variant][indicator]
                    df.loc[country1, country2] = index
    for variant, dfdict in dfs.items():
        subdir = output_path / variant
        subdir.mkdir(parents=True, exist_ok=True)
        for indicator, df in dfdict.items():
            pandas_utils.save_df(df, subdir, f"similarity_{indicator}")


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
    output_path = Path("data/country_comparison/similarity_matrices")

    countries = list(hetus_column_values.HETUS2010_COUNTRIES)
    create_similarity_matrices(validation_path_merged, output_path, countries)
