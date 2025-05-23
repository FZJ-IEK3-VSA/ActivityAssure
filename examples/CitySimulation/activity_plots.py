from activityassure.profile_category import ProfileCategory
from activityassure.ui import data_utils, datapaths, plots
# TODO: Probleme mit import von ui.plots, wenn die Pfade in der config nicht existieren


from pathlib import Path


def create_selected_activity_assure_plots():
    citysim_path = Path("data/city/validation/scenario_city-julich_25_merged")
    citysim_national = Path(f"{citysim_path}_national")
    # validation_national = Path(
    #     "data/validation_data_sets/activity_validation_data_set_national"
    # )

    # input_statistics = ValidationSet.load(citysim_path)

    plot_dir = Path("data/diss_validation_plots")

    profile_type = ProfileCategory("DE")
    filepath = data_utils.get_file_path(
        citysim_national / datapaths.prob_dir, profile_type
    )
    fig = plots.stacked_prob_curves(filepath)
    assert fig
    data_utils.save_plot(
        fig,
        "probability profiles",
        name="De",
        profile_type=profile_type,
        base_path=plot_dir,
    )