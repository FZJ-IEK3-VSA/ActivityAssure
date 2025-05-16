"""Aggregates result load profiles produced by the city simulation to get
sum profiles for the whole city"""

from pathlib import Path

import pandas as pd
from tqdm import tqdm


def aggregate_load_sum_profiles(city_result_dir: Path, output_dir: Path):
    dateformat_de = "%d.%m.%Y %H:%M"
    dateformat_en = "%-m/%-d/%Y %-I:%M %p"
    dateformat = dateformat_en

    # relative path of the LPG result file to aggregate
    filename = Path("Results/Overall.SumProfiles.Electricity.csv")

    houses_subdir = city_result_dir / "Houses"
    house_dirs = list(houses_subdir.iterdir())

    all_profiles = []

    # parse the sum profiles from all houses
    for house_dir in tqdm(house_dirs):
        profile_path = house_dir / filename
        profile = pd.read_csv(
            profile_path,
            sep=";",
            index_col=0,
            parse_dates=["Time"],
            date_format=dateformat,
        )
        profile.rename(columns={"Sum [kWh]": house_dir.name}, inplace=True)
        all_profiles.append(profile)

    data = pd.concat(all_profiles, axis="columns")

    output_dir.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_dir / "City.SumProfiles.Electricity.csv")


if __name__ == "__main__":
    city_result_dir = Path("R:/city_simulation_results/scenario_city-julich_25")
    # city_result_dir = Path("D:/LPG/Results/scenario_julich-grosse-rurstr_fullroutes")
    output_dir = Path(f"data/city/postprocessed/{city_result_dir.name}")
    aggregate_load_sum_profiles(city_result_dir, output_dir)
