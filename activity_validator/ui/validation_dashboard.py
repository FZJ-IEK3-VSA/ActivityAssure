import dataclasses
from datetime import datetime, timedelta
import glob
from pathlib import Path
from dash import Dash, html, dcc, callback, Output, Input
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.hetus_data_processing.attributes.diary_attributes import DayType
from activity_validator.hetus_data_processing.attributes.person_attributes import (
    Sex,
    WorkStatus,
)
from activity_validator.ui.overview import chunks, create_rows, draw_figure

from activity_validator.ui.probability_curves import (
    AIOSelectableProbabilityCurves,
    get_profile_types,
)

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# default data paths
# validation_path = Path("data/validation_data")
validation_path = Path("data/validation_data EU mapped")
input_data_path = Path("data/lpg/results")

# data subdirectories
prob_dir = "probability_profiles"
freq_dir = "activity_frequencies"
duration_dir = "activity_durations"
comp_dir = "comparison"
metrics_dir = "metrics"
diff_dir = "differences"


def load_data_by_type(path, profile_type):
    filter = str(path) + "/*" + profile_type.construct_filename() + ".csv"

    # find the correct file
    files = glob.glob(filter)
    if len(files) == 0:
        raise RuntimeError(f"Could not find a matching file: {filter}")
    if len(files) > 1:
        raise RuntimeError(f"Found multiple files for the same profile type: {files}")
    # load the correct file
    _, data = activity_profile.load_df(files[0])
    return data


def draw_activity_figure(subdir: str, profile_type: ProfileType):
    # profile_type = ProfileType.from_iterable(value.split(" - "))
    dv = load_data_by_type(validation_path / subdir, profile_type)
    di = load_data_by_type(input_data_path / subdir, profile_type)
    di.rename(columns={c: c + " - LPG" for c in di.columns}, inplace=True)

    data_sets = []
    for col in dv.columns:
        c2 = col + " - LPG"
        if not c2 in di.columns:
            continue
        d = pd.concat([dv[col], di[c2]], axis=1)
        data_sets.append(d)
    return [dcc.Graph(figure=px.ecdf(d)) for d in data_sets]


# get available validation profile types
profile_types = get_profile_types(validation_path / prob_dir)
countries = list({p.country for p in profile_types})
global_profile_types = {dataclasses.replace(p, country="") for p in profile_types}
global_type_str = [" - ".join(pt.to_tuple()[1:]) for pt in profile_types]

# TODO just for testing
test_profile_type = ProfileType("DE", Sex.female, WorkStatus.full_time, DayType.no_work)

tab1_content = html.Div(
    [
        html.Div(
            [
                html.H2("Validation Data", style={"textAlign": "center"}),
                AIOSelectableProbabilityCurves(validation_path / prob_dir),
            ]
        ),
        html.Div(
            [
                html.H2("LoadProfileGenerator Data", style={"textAlign": "center"}),
                AIOSelectableProbabilityCurves(input_data_path / prob_dir),
            ]
        ),
        html.Div(
            [
                html.H2("Difference", style={"textAlign": "center"}),
                AIOSelectableProbabilityCurves(input_data_path / comp_dir / diff_dir),
            ]
        ),
        html.Div(
            [
                html.H2("Activity Frequencies", style={"textAlign": "center"}),
                html.Div(draw_activity_figure(freq_dir, test_profile_type)),
            ]
        ),
    ]
)

horizontal_limit = 4
tab2_content = html.Div(
    dbc.Card(
        dbc.CardBody(
            [
                country_selector := dcc.Dropdown(
                    countries,
                    countries[0],
                ),
                single_country_div := html.Div(),
            ]
        )
    )
)

tab3_content = html.Div(
    dbc.Card(
        dbc.CardBody(
            [
                category_selector := dcc.Dropdown(
                    global_type_str,
                    global_type_str[0],
                ),
                cross_country_div := html.Div(),
            ]
        )
    )
)

app.layout = html.Div(
    [
        html.H1(children="Activity Profile Validator", style={"textAlign": "center"}),
        tabs := dcc.Tabs(
            [
                dcc.Tab(tab1_content, label="Validation"),
                dcc.Tab(tab2_content, label="Single Country Overview"),
                dcc.Tab(tab3_content, label="Cross-country Overview"),
            ],
        ),
    ]
)


@callback(Output(single_country_div, "children"), Input(country_selector, "value"))
def country_overview(country: str):
    path = validation_path / prob_dir
    profiles_of_country = [p for p in profile_types if p.country == country]
    return create_rows(path, profiles_of_country)


@callback(Output(cross_country_div, "children"), Input(category_selector, "value"))
def cross_country_overview(profile_type: str):
    sex, work_status, day_type = profile_type.split(" - ")
    path = validation_path / prob_dir
    filtered_profile_types = [
        p
        for p in profile_types
        if p.sex == sex and p.work_status == work_status and p.day_type == day_type
    ]
    return create_rows(path, filtered_profile_types)


if __name__ == "__main__":
    app.run(debug=True)
