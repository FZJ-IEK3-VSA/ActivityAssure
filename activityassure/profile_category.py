"""
Contains a class for specifying a category of activity profiles,
including all associated attribute values.
"""

from pathlib import Path
from typing import Any, Collection, Sequence
from dataclasses import dataclass
from dataclasses_json import dataclass_json

from activityassure import categorization_attributes

@dataclass_json
@dataclass(frozen=True)
class BaseProfileCategory:
    """As the ProfileCategory but it does not contain
    country information.
    """
    
    sex: categorization_attributes.Sex | None = None
    work_status: categorization_attributes.WorkStatus | None = None
    day_type: categorization_attributes.DayType | None = None


@dataclass_json
@dataclass(frozen=True)
class ProfileCategory:
    """
    A set of characteristics that defines the category of a
    single-day activity profile and identifies matching
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
        title_val_dict = self.to_title_dict(True)
        return list(title_val_dict.keys())

    def to_title_dict(self, only_used_attributes: bool = False) -> dict[str, Any]:
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

    def to_list(self) -> list[str]:
        """
        Returns a list representation of this profile type. Only returns
        attributes that are not None or empty.

        :return: a list containing the characteristics of this
                 profile category
        """
        values = [
            self.country,
            self.sex,
            self.work_status,
            self.day_type,
        ]
        return [str(v) for v in values if v]

    def __str__(self) -> str:
        """
        Returns a string representation of this profile type

        :return: a str containing the characteristics of this
                 profile category
        """
        return "_".join(str(c) for c in self.to_list())

    def construct_filename(self, name: str = "") -> str:
        return f"{name}_{self}"

    def to_personal_category(self, person: str) -> "PersonProfileCategory":
        """
        Given a person name, creates a PersonalProfileCategory object out of
        this ProfileCategory object.

        :param person: the person name for the new category object
        :return: the new category object including the person name
        """
        return PersonProfileCategory(
            self.country, self.sex, self.work_status, self.day_type, person
        )
    
    def to_base_category(self) -> "BaseProfileCategory":
        """
        Creates a BaseProfileCategory object without country information out of
        this ProfileCategory object.

        :return: the new category object including the person name
        """
        return BaseProfileCategory(
            self.sex, self.work_status, self.day_type
        )

    @staticmethod
    def from_filename(filepath: Path) -> "ProfileCategory":
        components = filepath.stem.split("_")
        assert (
            len(components) > 1
        ), f"Could not parse profile type from path '{filepath}'"
        # basename = components[0] # not needed
        profile_type = ProfileCategory.from_iterable(components[1:])
        return profile_type

    @staticmethod
    def from_iterable(values: Sequence[str | None]) -> "ProfileCategory":
        """
        Creates a ProfileType object from an iterable containing
        the characteristics as strings.

        :param values: the characteristics as strs
        :return: the corresponding ProfileType object
        """
        length = len(values)
        assert 4 <= length <= 5, f"Invalid number of characteristics: {values}"
        if length == 5:
            person = values[-1] or ""
            values = values[:4]
        # extract characteristics
        country, sex_str, work_status_str, day_type_str = values
        try:
            # convert the strings to enum values and create the ProfileType
            sex = categorization_attributes.Sex(sex_str) if sex_str else None
            work_status = (
                categorization_attributes.WorkStatus(work_status_str)
                if work_status_str
                else None
            )
            day_type = (
                categorization_attributes.DayType(day_type_str)
                if day_type_str
                else None
            )
        except KeyError as e:
            assert False, f"Invalid enum key: {e}"
        if length == 5 and person:
            return PersonProfileCategory(country, sex, work_status, day_type, person)
        return ProfileCategory(country, sex, work_status, day_type)

    @staticmethod
    def from_index_tuple(
        names: Collection[str], values: Collection[str] | str
    ) -> "ProfileCategory":
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
        assert len(names) == len(values), "Number of names must match number of values"
        value_dict = dict(zip(names, values))
        # extract used category attributes by their names
        country = value_dict.get(categorization_attributes.Country.title())
        sex = value_dict.get(categorization_attributes.Sex.title())
        work_status = value_dict.get(categorization_attributes.WorkStatus.title())
        day_type = value_dict.get(categorization_attributes.DayType.title())
        person = value_dict.get(categorization_attributes.Person.title())
        return ProfileCategory.from_iterable(
            [country, sex, work_status, day_type, person]
        )


@dataclass(frozen=True)
class PersonProfileCategory(ProfileCategory):
    """
    A more specialized profile category that also includes
    the name of the person, so that each person gets their own
    set categories (usually two, working day and rest day).
    """

    person: str = ""

    def to_title_dict(self, only_used_attributes: bool = False) -> dict[str, Any]:
        d = super().to_title_dict(only_used_attributes)
        d[categorization_attributes.Person.title()] = self.person
        return d

    def to_list(self) -> list[str]:
        t = super().to_list()
        t.append(self.person)
        return t

    def get_category_without_person(self) -> ProfileCategory:
        """
        Returns a more general profile category object without a person name

        :return: the category object without person name
        """
        return ProfileCategory(self.country, self.sex, self.work_status, self.day_type)
