"""
Module that loads all configuration settings for the Dash web app from
the config file.
"""

from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Config:
    """
    Defines all configuration settings for the Dash web app
    """

    #: path of the validation statistics
    validation_path: str
    #: path of the statistics of the model data to validate
    input_path: str
    #: name of the model to validate
    model_name: str
    #: name of the validation data set
    validation_name: str = "Validation"
    #: if False, disables the repetitive and space-consuming legend for per-activity plots
    show_legend_per_activity: bool = True
    #: language for the UI
    language: str = "EN"
    #: if True, mirrors validation data probabiltiy curves on the x axis
    mirrored_plots: bool = False


# parse the content file
config_file = "activityassure/ui/config.json"
with open(config_file, "r", encoding="utf8") as f:
    content = f.read()
config: Config = Config.from_json(content)  # type: ignore
