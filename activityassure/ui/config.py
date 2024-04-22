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


# parse the content file
config_file = "activity_validator/ui/config.json"
with open(config_file) as f:
    content = f.read()
config: Config = Config.from_json(content)
