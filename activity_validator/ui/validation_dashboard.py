import dataclasses
from datetime import datetime, timedelta
import glob
from pathlib import Path
from dash import Dash, html, dcc, callback, Output, Input  # type:ignore
import dash_bootstrap_components as dbc  # type:ignore
import plotly.express as px  # type:ignore
import pandas as pd
from activity_validator.hetus_data_processing import activity_profile
from activity_validator.hetus_data_processing.activity_profile import ProfileType
from activity_validator.hetus_data_processing.attributes.diary_attributes import DayType
from activity_validator.hetus_data_processing.attributes.person_attributes import (
    Sex,
    WorkStatus,
)
from activity_validator.ui import data_utils
from activity_validator.ui import datapaths
from activity_validator.ui.overview import chunks, create_rows, draw_figure

from activity_validator.ui.main_validation_view import MainValidationView


app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])


# get available validation profile types
profile_types = data_utils.get_profile_types(
    datapaths.validation_path / datapaths.prob_dir
).keys()
countries = list({p.country for p in profile_types})
global_profile_types = {dataclasses.replace(p, country="") for p in profile_types}
global_type_str = [" - ".join(pt.to_tuple()[1:]) for pt in profile_types]

# TODO just for testing
test_profile_type = ProfileType("DE", Sex.female, WorkStatus.full_time, DayType.no_work)

tab1_content = html.Div([MainValidationView()])

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
    path = datapaths.validation_path / datapaths.prob_dir
    profiles_of_country = [p for p in profile_types if p.country == country]
    return create_rows(path, profiles_of_country)


@callback(Output(cross_country_div, "children"), Input(category_selector, "value"))
def cross_country_overview(profile_type: str):
    sex, work_status, day_type = profile_type.split(" - ")
    path = datapaths.validation_path / datapaths.prob_dir
    filtered_profile_types = [
        p
        for p in profile_types
        if p.sex == sex and p.work_status == work_status and p.day_type == day_type
    ]
    return create_rows(path, filtered_profile_types)


if __name__ == "__main__":
    app.run(debug=True)
