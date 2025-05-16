"""Aggregates result load profiles produced by the city simulation to get
sum profiles for the whole city"""

from datetime import datetime, timedelta
from pathlib import Path

import psutil
import pandas as pd


def aggregate_load_sum_profiles(city_result_dir: Path, output_dir: Path):
    dateformat_de = "%d.%m.%Y %H:%M"
    dateformat_en = "%-m/%-d/%Y %-I:%M %p"
    dateformat = dateformat_en

    # relative path of the LPG result file to aggregate
    filename = Path("Results/Overall.SumProfiles.Electricity.csv")
    data_col_name = "Sum [kWh]"

    houses_subdir = city_result_dir / "Houses"
    house_dirs = list(houses_subdir.iterdir())
    house_num = len(house_dirs)

    # parse the sum profiles from all houses
    all_profiles = []
    last_update = datetime.now()
    for i, house_dir in enumerate(house_dirs):
        profile_path = house_dir / filename
        profile = pd.read_csv(
            profile_path,
            sep=";",
            index_col=0,
            parse_dates=["Time"],
            date_format=dateformat,
            dtype={0: int, data_col_name: float},
        )
        profile.rename(columns={data_col_name: house_dir.name}, inplace=True)
        all_profiles.append(profile)

        # print progress
        if datetime.now() - last_update > timedelta(seconds=30):
            ram = psutil.Process().memory_info().rss / 1024**2
            print(
                f"Progress: {i}/{house_num} ({100 * i / house_num:.1f}%), RAM usage: {ram:.2f} MiB"
            )

    data = pd.concat(all_profiles, axis="columns")

    output_dir.mkdir(parents=True, exist_ok=True)
    data.to_csv(output_dir / "City.SumProfiles.Electricity.csv")


if __name__ == "__main__":
    city_result_dir = Path(
        "/fast/home/d-neuroth/city_simulation_results/scenario_city-julich_25"
    )
    # city_result_dir = Path("D:/LPG/Results/scenario_julich-grosse-rurstr_fullroutes")
    output_dir = Path(f"data/city/postprocessed/{city_result_dir.name}")
    aggregate_load_sum_profiles(city_result_dir, output_dir)
