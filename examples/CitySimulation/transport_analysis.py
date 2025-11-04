"""Create plots for travel distances"""

import logging
from pathlib import Path
import pickle

from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns

from paths import SubDirs

import poi_validation


def prepare_df(df):
    # remove travels to custom POIs
    start_custom = df["start_site"].str.contains("Custom")
    dest_custom = df["dest_site"].str.contains("Custom")
    df = df[~start_custom & ~dest_custom].dropna()

    # add start/dest POI type as columns
    df.insert(
        0, "start_type", df["start_site"].apply(poi_validation.poi_type_from_filename)
    )
    df.insert(
        0, "dest_type", df["dest_site"].apply(poi_validation.poi_type_from_filename)
    )

    # Determine trip type
    df.insert(
        0,
        "trip_type",
        df.apply(
            lambda r: r["dest_type"] if r["dest_site"] != "Home" else r["start_type"],
            axis=1,
        ),
    )

    df.insert(0, "distance_km", df["distance_in_m"] / 1000)
    return df


def plot_general_hist(df, output_dir: Path):
    fig, ax = plt.subplots()

    sns.histplot(
        df["distance_km"],  # convert to km for readability
        bins=20,
        kde=True,
        ax=ax,
    )

    # ax.set_xscale("log")  # apply logarithmic scaling
    ax.set_xlabel("Distanz in km")
    ax.set_ylabel("Anzahl Reisen")
    # ax.grid(True, linestyle="--", alpha=0.5)

    fig.tight_layout()
    filepath = output_dir / "travel_dist_hist.svg"
    fig.savefig(filepath)


def plot_trip_count_hist(df, output_dir: Path):
    fig, ax = plt.subplots()
    order = df["trip_type"].value_counts().index
    sns.countplot(data=df, x="trip_type", order=order)
    # sns.histplot(df["trip_type"], ax=ax)

    ax.set_xlabel("Ziel der Reise")
    ax.set_ylabel("Anzahl Reisen")
    plt.xticks(rotation=90)

    fig.tight_layout()
    filepath = output_dir / "trip_type_hist.svg"
    fig.savefig(filepath)


def distance_per_type_violins(df, output_dir: Path):
    # Plot distribution per trip type
    fig, ax = plt.subplots()
    sns.violinplot(
        data=df,
        x="trip_type",
        y="distance_km",
        ax=ax,
        inner="quartile",
        density_norm="width",
        cut=0,
    )

    ax.set_xlabel("Ziel der Reise")
    ax.set_ylabel("Distanz in km")
    # ax.grid(True, linestyle="--", alpha=0.5, which="both")
    plt.xticks(rotation=90)

    fig.tight_layout()
    filepath = output_dir / "travel_dist_per_type_violins.svg"
    fig.savefig(filepath)


def main(city_result_dir: Path, output_dir: Path):
    # load the travels file containing all travels from the simulation
    filepath = (
        city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.TRANSPORT / "travels.csv"
    )
    pkl_path = filepath.parent / "travels.pkl"
    if filepath.is_file():
        df = pd.read_csv(filepath, index_col=0)
    elif pkl_path.is_file():
        with open(pkl_path, "rb") as f:
            df = pickle.load(f)
    else:
        assert False, f"No travels file found: {filepath}"

    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme()

    df = prepare_df(df)

    distance_per_type_violins(df, output_dir)
    plot_general_hist(df, output_dir)
    plot_trip_count_hist(df, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    city_res_dir = Path("R:/phd_dir/results/scenario_juelich_04_del3")
    # city_res_dir = Path("C:/LPG/Results/plottest")
    output_dir = (
        city_res_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.PLOTS / SubDirs.TRANSPORT
    )
    main(city_res_dir, output_dir)
