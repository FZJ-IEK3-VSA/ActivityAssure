import dataclasses
from dash import Dash, html, dcc, callback, Output, Input  # type:ignore
import dash_bootstrap_components as dbc  # type:ignore
from activityassure.ui import data_utils, datapaths, overview

from activityassure.ui import plots
from activityassure.ui.main_validation_view import MainValidationView


# check if the specified data paths exist
datapaths.check_paths()

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "ETHOS.ActivityAssure"
app._favicon = "stacked.ico"


# get available validation profile types
prob_paths = data_utils.get_profile_type_paths(
    datapaths.validation_path / datapaths.prob_dir
)
countries = list({str(p.country) for p in prob_paths.keys()})
global_profile_types = {dataclasses.replace(p, country="") for p in prob_paths.keys()}
global_type_str = [" - ".join(pt.to_list()[1:]) for pt in prob_paths.keys()]


tab1_content = html.Div([MainValidationView()])

horizontal_limit = 4
tab2_content = html.Div(
    dbc.Card(
        dbc.CardBody(
            [
                country_selector := dcc.Dropdown(
                    countries,
                    countries[0],
                    className="mb-3",
                ),
                single_country_share_div := html.Div(
                    className="mb-3",
                ),
                single_country_prob_div := html.Div(),
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
                    className="mb-3",
                ),
                cross_country_div := html.Div(),
            ]
        )
    )
)

app.layout = html.Div(
    [
        html.H1(children="ActivityAssure", style={"textAlign": "center"}),
        tabs := dcc.Tabs(
            children=[
                tab1 := dcc.Tab(tab1_content, label="Validation"),
                tab2 := dcc.Tab(tab2_content, label="Single Country Overview"),
                tab3 := dcc.Tab(tab3_content, label="Cross-country Overview"),
            ],
        ),
    ]
)


@callback(
    Output(single_country_share_div, "children"), Input(country_selector, "value")
)
def country_overview_shares(country: str):
    # filter all profile types of the selected country
    filtered_paths = {
        data_utils.ptype_to_label(profile_type): path
        for profile_type, path in prob_paths.items()
        if profile_type.country == country
    }
    figure = plots.stacked_bar_activity_share(filtered_paths)
    return plots.single_plot_card(figure, "Activity Shares per Profile Type")


@callback(Output(single_country_prob_div, "children"), Input(country_selector, "value"))
def country_overview_probs(country: str):
    # filter all profile types of the selected country
    filtered_paths = {
        data_utils.ptype_to_label(profile_type): path
        for profile_type, path in prob_paths.items()
        if profile_type.country == country
    }
    prob_curves = overview.create_stacked_prob_curves(filtered_paths)
    prob_curve_rows = overview.rows_of_cards(prob_curves)
    return prob_curve_rows


@callback(Output(cross_country_div, "children"), Input(category_selector, "value"))
def cross_country_overview(profile_type_str: str):
    profile_type_parts = profile_type_str.split(" - ")
    if len(profile_type_parts) != 3:
        return plots.replacement_text(
            "Unsuitable profile category for cross-country analysis"
        )
    sex, work_status, day_type = profile_type_parts
    # filter all profile types with the selected characteristics
    filtered_paths = {
        p_type.country or "No Country": path
        for p_type, path in prob_paths.items()
        if p_type.sex == sex
        and p_type.work_status == work_status
        and p_type.day_type == day_type
    }
    figures = overview.create_stacked_prob_curves(filtered_paths)
    prob_curve_rows = overview.rows_of_cards(figures)
    return prob_curve_rows


if __name__ == "__main__":
    app.run(debug=True, dev_tools_hot_reload=False)
