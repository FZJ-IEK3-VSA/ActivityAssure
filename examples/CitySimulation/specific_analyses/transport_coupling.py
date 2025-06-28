"""
Simple script for checking the influence of the transport model on activities by comparing
results of simulation runs with default routes and with routes from MODE.Regional
"""

from pathlib import Path
from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns
import logging

from activityassure import validation

from activityassure.comparison_indicators import ValidationIndicators

MEAN_IDX = ValidationIndicators.mean_column


def compare_two_city_results():
    """Validate two city simulation result sets against each other"""
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.DEBUG,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    base_dir = Path("C:/LPG/Results/scenario_julich-grosse-rurstr/Postprocessed")
    base_dir = Path("C:/Users/d.neuroth/Downloads/comparison")
    # validation_subdir = "Postprocessed/activityassure_statistics"
    scenario1 = base_dir / "fullroutes"
    scenario2 = base_dir / "testroutes"

    validation.default_validation(scenario1, scenario2)


def load_validation_results(result_dir: Path) -> pd.DataFrame:
    # path template for the indicator file for different indicator variants
    base_path = (
        result_dir
        / "Postprocessed/activityassure_statistics_merged/validation_results/{}/indicators_per_category.csv"
    )
    # load the indicators
    indicators_default = pd.read_csv(str(base_path).format("default"))
    # indicators_scaled = pd.read_csv(str(base_path).format("scaled"))
    # add the scaled indicators to the default dataframe
    # indicators_scaled = indicators_scaled.loc[
    #     :, ["mae", "rmse", "bias", "wasserstein"]
    # ].add_prefix("scaled_")
    # indicators = pd.concat([indicators_default, indicators_scaled], axis=1)
    df = indicators_default
    colnames = {"Unnamed: 0": "profile type", "Unnamed: 1": "activity"}
    df.rename(columns=colnames, inplace=True)
    df = df.set_index(list(colnames.values()))
    return df


def filter_activities(df: pd.DataFrame, activity: list[str]) -> pd.DataFrame:
    # only select the mean indicators, exclude per-activity indicators
    return df[df.index.get_level_values(1).isin(activity)]


if __name__ == "__main__":
    # input: directory of one city simulation with test routes and one with full
    # routes from MODE.Regional
    base_result_dir = Path("R:/city_simulation_results/grosse-rurstr")
    path_test = base_result_dir / "scenario_julich-grosse-rurstr_1_testroutes"
    path_full = base_result_dir / "scenario_julich-grosse-rurstr_2"

    results_test = load_validation_results(path_test)
    results_full = load_validation_results(path_full)

    means_test = filter_activities(results_test, [MEAN_IDX])
    means_full = filter_activities(results_full, [MEAN_IDX])
    mean_diff = (means_full - means_test).sum()

    combined = pd.concat(
        [means_test.sum().to_frame().T, means_full.sum().to_frame().T], axis="index", keys=["default", "MODE.Regional"], names=["Routes"]
    )
    pearson = combined[["pearson_corr"]]
    combined.drop(columns=["bias", "pearson_corr"], inplace=True)
    melted = combined.melt(var_name="Indicator", value_name="Value", ignore_index=False)

    # bar chart showing some indicators for test and full, showing that full fits better
    ax = sns.barplot(
        x="Indicator",
        y="Value",
        hue="Routes",
        data=melted,
        ci=None,
        # dodge=True,
    )
    # ax = sns.barplot(pearson, y="pearson_corr", hue="variant", ci=None)

    for i, container in enumerate(ax.containers):
        ax.bar_label(container, fmt="%.3f", label_type="center")
    plt.savefig("transport_influence_on_activity.svg")
    plt.show()


    # TODO: compare for the most relevant activities (not at home, pc)



    # TODO: especially look at full time working day categories
    # filter by category
    # data = data[(data.iloc[:, 0].str.contains("unemployed_rest"))]

