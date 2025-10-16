"""Geographic analyses showing various indicators on a map"""

import json
import logging
from pathlib import Path

from matplotlib.colors import LogNorm
import pandas as pd

from paths import SubDirs

import matplotlib.pyplot as plt
import contextily as ctx  # type: ignore

import geopandas as gpd  # type: ignore
from shapely.geometry import Point  # type: ignore


def read_house_coordinates(scenario_dir: Path) -> dict[str, dict[str, float]]:
    with open(scenario_dir / "house_coordinates.json", "r", encoding="utf8") as f:
        return json.load(f)


def get_house_geodf(scenario_dir: Path) -> gpd.GeoDataFrame:
    """Reads the house coordinates and returns a GeoDataFrame with the
    appropriate geometry.

    :scenario_dir: the scenario directory
    :return: a GeoDataFrame for all houses in the scenario
    """
    house_coordinates = read_house_coordinates(scenario_dir)
    house_ids = list(house_coordinates.keys())
    coordinates = [
        Point(c["Longitude"], c["Latitude"]) for c in house_coordinates.values()
    ]
    df: gpd.GeoDataFrame = gpd.GeoDataFrame(geometry=coordinates, index=house_ids)

    # set the coordinate reference system to WGS 84 (EPSG:4326)
    df.set_crs("EPSG:4326", inplace=True)
    return df


def basic_map_plot(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    filename = "total_demand_per_profile.csv"
    filepath = (
        city_result_dir
        / SubDirs.POSTPROCESSED_DIR
        / SubDirs.LOADS_DIR
        / "aggregated_house"
        / filename
    )
    df_loads = pd.read_csv(filepath)
    df_loads.set_index("House", inplace=True)

    geodf = get_house_geodf(scenario_dir)

    df = pd.concat([geodf, df_loads], axis="columns")

    # df = df.iloc[:100,]

    # convert to Web Mercator
    df.to_crs("EPSG:3857", inplace=True)  # type: ignore

    # Plot
    fig, ax = plt.subplots(figsize=(16, 9))
    df.plot(
        ax=ax,
        column="Total demand [kWh]",
        legend=True,
        markersize=2,
        cmap="jet",
        norm=LogNorm(
            vmin=df["Total demand [kWh]"].min(),
            vmax=df["Total demand [kWh]"].max(),
        ),
    )

    # Add basemap
    ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik)  # type: ignore

    # make the plot a bit smaller to make room for the legend
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.7, box.height])  # type: ignore

    # move the legend to the right, outside of the plot
    legend = ax.get_legend()
    # legend.set_bbox_to_anchor((1.1, 1))

    # save and show the plot
    result_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.MAPS
    result_dir.mkdir(parents=True, exist_ok=True)
    plt.show()
    # fig.savefig(result_dir / "demand.png")


def main(scenario_dir: Path, city_result_dir: Path, output_dir: Path):
    """Contains all geographic postprocessing of the city simulation.

    :param city_result_dir: result directory of the city simulation
    :param output_dir: output directory for the postpocessed data
    """
    basic_map_plot(scenario_dir, city_result_dir, output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    scenario_dir = Path("R:/phd_dir/city_scenarios/scenario_julich_02")
    city_result_dir = Path("R:/phd_dir/results/scenario_julich_02")
    # city_result_dir = Path(r"C:\LPG\Results\scenario_julich")
    output_dir = city_result_dir / SubDirs.POSTPROCESSED_DIR / SubDirs.TRANSPORT

    main(scenario_dir, city_result_dir, output_dir)
