"""Load and analyze desire values from Desire csv files"""

import json
import logging
from pathlib import Path
import pickle
from matplotlib import pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from tqdm import tqdm
from cmcrameri import cm

from paths import SubDirs
import load_profile_processing


def load_desire_values(filepath: Path):
    with open(filepath, encoding="utf-8") as f:
        file_content = [line.rstrip(";\n") + "\n" for line in f]

    df = pd.read_csv(
        pd.io.common.StringIO("".join(file_content)),  # type: ignore
        sep=";",
        usecols=["Time", "Special / Pharmacy Visit"],
        index_col="Time",
        parse_dates=["Time"],
        date_format=load_profile_processing.DATEFORMAT_EN,
    )
    return df


def collect_desire_profiles(city_result_dir: Path):
    visits_file = (
        city_result_dir
        / "Postprocessed/raw_activity_statistics/visit-pharmacy/frequency_by_person.json"
    )

    with open(visits_file) as f:
        visits_per_person = json.load(f)

    # pattern of the LPG result files to aggregate
    file_prefix = "Desires."
    filepattern = f"{file_prefix}*.csv"

    # collect all household load profiles
    houses_subdir = city_result_dir / "Houses"
    files = list(houses_subdir.rglob(filepattern))

    dfs = {}
    not_in_visits_file = 0
    for file in tqdm(files):
        house = file.parent.parent.name
        parts = file.stem.removeprefix(file_prefix).split(".")
        assert len(parts) == 2, f"Unexpected filename: {file.stem}"
        hh, person = parts
        person_name = person.split(" (")[0]
        person_id = f"{person_name}_{house}_{hh}"
        if person_id not in visits_per_person:
            not_in_visits_file += 1
            continue
        if visits_per_person[person_id] > 0:
            df = load_desire_values(file)
            df.rename({"Special / Pharmacy Visit": person_id}, inplace=True)
            dfs[person_id] = df

    logging.info(f"Loaded {len(dfs)} desire files of pharmacy visitors")
    logging.info(f"Person IDs missing in the visits file: {not_in_visits_file}")

    # save the merged desires file
    merged = pd.concat(dfs.values(), axis="columns")
    with open(city_result_dir / "Postprocessed/merged_desires.pkl", "wb") as f:
        pickle.dump(merged, f)
    merged.to_csv(city_result_dir / "Postprocessed/merged_desires.csv")

    mean = merged.mean(axis="columns")
    mean.to_csv(city_result_dir / "Postprocessed/desires_mean.csv")


def plot_desire_profiles(city_result_dir: Path):
    filepath = city_result_dir / SubDirs.POSTPROCESSED_DIR / "merged_desires_pharma.csv"
    full_df = pd.read_csv(filepath, index_col="Time", parse_dates=["Time"])

    df = full_df.mean(axis="columns").to_frame("mean")

    # Reshape data to hours × days
    assert isinstance(df.index, pd.DatetimeIndex), "Datetimes not parsed correctly"
    # df["day"] = df.index.dayofyear
    # df["time"] = df.index.time  # or use hour/minute if finer
    # df["hour"] = df.index.hour + df.index.minute / 60
    # # Pivot: rows = time, columns = day, values = load
    # reshaped = df.pivot_table(index="hour", columns="day", values="mean")

    TIME_COL = "Time"
    df["date"] = df.index.date  # extract day
    df[TIME_COL] = df.index.time
    reshaped = df.pivot(index=TIME_COL, columns="date", values="mean")

    fig, ax = plt.subplots()
    im = ax.imshow(
        reshaped,
        aspect="auto",
        origin="upper",
        cmap=cm.batlow,  # type: ignore
        interpolation="none",
    )

    # Add colorbar
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Desire Pharmacy Visit")

    # Set the x-axis to the correct dates

    # Optionally, highlight Mondays
    mondays = [i for i, col in enumerate(reshaped.columns) if col.weekday() == 0]  # type: ignore
    ax.set_xticks(mondays)
    xlabels = [reshaped.columns[i].strftime("%a, %d.%m.") for i in mondays]  # type: ignore
    ax.set_xticklabels(xlabels, rotation=90)

    # define y-ticks (time)
    vals_per_day = len(reshaped.index)
    start_hour = reshaped.index.min().hour
    hour_range = reshaped.index.max().hour - start_hour + 1

    def hour_formatter(x, pos):
        x = x * hour_range / vals_per_day + start_hour
        h = int(x)
        m = int((x - h) * 60)
        return f"{h % 24:02d}:{m:02d}"

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(hour_formatter))
    ax.set_yticks(np.linspace(0, vals_per_day, num=7))

    fig.tight_layout()
    plt.show()


def main(city_result_dir: Path):
    # collect_desire_profiles(city_result_dir, visits_file)
    plot_desire_profiles(city_result_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    city_result_dir = Path(
        "/fast/home/d-neuroth/phd_dir/results/scenario_juelich_04_eplpo_fair_100_1"
    )
    # city_result_dir = Path("R:/phd_dir/results/scenario_juelich_04_eplpo_fair_100_1")

    main(city_result_dir)
