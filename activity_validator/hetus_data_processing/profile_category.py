"""
Contains a class for specifying a category of activity profiles,
including all associated attribute values.
"""

from pathlib import Path
from typing import Any, Collection
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from activity_validator.hetus_data_processing.attributes import (
    categorization_attributes,
)


@dataclass_json
@dataclass(frozen=True)
class ProfileType:  # TODO: move to dedicated profile type module
    """
    A set of characteristics that defines the type of a
    sinlge-day activity profile and identifies matching
    validation data.
    """

    country: str | None = None
    sex: categorization_attributes.Sex | None = None
    work_status: categorization_attributes.WorkStatus | None = None
    day_type: categorization_attributes.DayType | None = None

    def get_attribute_names(self) -> list[str]:
        """
        Returns the names of the currently used attributes

        :return: list of attribute names
        """
        title_val_dict = self.to_dict(True)
        return list(title_val_dict.keys())

    def to_dict(self, only_used_attributes: bool = False) -> dict[str, Any]:
        """
        Returns the profile type as a dict, mapping the attribute
        titles to the corresponding values.

        :param only_used_attributes: if True, only includes attributes that are
                                     in use, i.e. that are not None
        :return: the dict representing this ProfileType
        """
        value_dict = {
            categorization_attributes.Country.title(): self.country,
            categorization_attributes.Sex.title(): self.sex,
            categorization_attributes.WorkStatus.title(): self.work_status,
            categorization_attributes.DayType.title(): self.day_type,
        }
        if only_used_attributes:
            # exclude unused attributes
            value_dict = {k: v for k, v in value_dict.items() if v is not None}
        return value_dict

    def to_tuple(self) -> tuple[str, str, str, str]:
        """
        Returns a tuple representation of this profile type.

        :return: a tuple containing the characteristics of this
                 profile type
        """
        return (
            str(self.country),
            str(self.sex),
            str(self.work_status),
            str(self.day_type),
        )

    def __str__(self) -> str:
        """
        Returns a string representation of this profile type

        :return: a str containing the characteristics of this
                 profile type
        """
        return "_".join(str(c) for c in self.to_tuple())

    def construct_filename(self, name: str = "") -> str:
        return f"{name}_{self}"

    @staticmethod
    def from_filename(filepath: Path) -> "ProfileType":
        components = filepath.stem.split("_")
        assert (
            len(components) > 1
        ), f"Could not parse profile type from path '{filepath}'"
        # basename = components[0] # not needed
        profile_type = ProfileType.from_iterable(components[1:])
        return profile_type

    @staticmethod
    def from_iterable(values: Collection[str | None]) -> "ProfileType":
        """
        Creates a ProfileType object from an iterable containing
        the characteristics as strings.

        :param values: the characteristics as strs
        :return: the corresponding ProfileType object
        """
        assert len(values) == 4, f"Invalid number of characteristics: {values}"
        # extract characteristics
        country, sex, work_status, day_type = values
        try:
            # convert the strings to enum values and create the ProfileType
            profile_type = ProfileType(
                country,
                categorization_attributes.Sex(sex) if sex else None,
                (
                    categorization_attributes.WorkStatus(work_status)
                    if work_status
                    else None
                ),
                categorization_attributes.DayType(day_type) if day_type else None,
            )
        except KeyError as e:
            assert False, f"Invalid enum key: {e}"
        return profile_type

    @staticmethod
    def from_index_tuple(
        names: Collection[str], values: Collection[str] | str
    ) -> "ProfileType":
        """
        Creates a ProfileType object from a list of attribute names and a list
        with their respective values. The lists names and values must match.
        This can be useful when not all attributes are set, e.g., when only the
        country is specified.

        :param names: index level names corresponding to the ProfileType attributes
        :param values: the values of the ProfileType attributes
        :return: the ProfileType object
        """
        if isinstance(values, str):
            # pandas does not put single index values in a list
            values = [values]
        assert len(names) == len(values), f"Number of names must match number of values"
        value_dict = dict(zip(names, values))
        # extract used category attributes by their names
        country = value_dict.get(categorization_attributes.Country.title())
        sex = value_dict.get(categorization_attributes.Sex.title())
        work_status = value_dict.get(categorization_attributes.WorkStatus.title())
        day_type = value_dict.get(categorization_attributes.DayType.title())
        return ProfileType.from_iterable([country, sex, work_status, day_type])
