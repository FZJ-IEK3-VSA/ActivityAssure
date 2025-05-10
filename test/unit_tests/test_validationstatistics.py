from datetime import timedelta
import numpy as np
import pandas as pd
import pytest

from activityassure.categorization_attributes import DayType, Sex, WorkStatus
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationStatistics


@pytest.fixture
def stats1():
    activities = ["eat", "sleep"]
    durations = [
        timedelta(hours=1),
        timedelta(hours=2),
        timedelta(hours=8),
        timedelta(hours=9),
    ]
    dur = pd.DataFrame(
        [[0.6, 0.4, 0, 0], [0, 0, 0.8, 0.2]], index=activities, columns=durations
    ).T
    frequencies = [0, 1, 2, 4]
    freq = pd.DataFrame(
        [[0, 0.1, 0.5, 0.4], [0.1, 0.9, 0, 0]], index=activities, columns=frequencies
    ).T
    timesteps = [f"Timestep {i}" for i in range(1, 25)]
    prob = pd.DataFrame([[0.6] * 24, [0.4] * 24], columns=timesteps, index=activities)
    cat = ProfileCategory("DE", Sex.female, WorkStatus.student, DayType.no_work)
    return ValidationStatistics(cat, prob, freq, dur, 5, 1)


@pytest.fixture
def stats2():
    activities = ["work", "sleep"]
    durations = [
        timedelta(hours=1),
        timedelta(hours=2),
        timedelta(hours=7),
        timedelta(hours=8),
    ]
    dur = pd.DataFrame(
        [[0.6, 0.4, 0, 0], [0, 0, 1.0, 0]], index=activities, columns=durations
    ).T
    frequencies = [0, 1, 2, 4]
    freq = pd.DataFrame(
        [[0, 0.1, 0.5, 0.4], [0, 1, 0, 0]], index=activities, columns=frequencies
    ).T
    timesteps = [f"Timestep {i}" for i in range(1, 25)]
    prob = pd.DataFrame([[0.3] * 24, [0.7] * 24], columns=timesteps, index=activities)
    cat = ProfileCategory("DE", Sex.female, WorkStatus.student, DayType.work)
    return ValidationStatistics(cat, prob, freq, dur, 5, 1)


def test_validation_statistics_merge(
    stats1: ValidationStatistics, stats2: ValidationStatistics
):
    new_category = ProfileCategory("DE", Sex.female, WorkStatus.student)
    merged = ValidationStatistics.merge_statistics([stats1, stats2], new_category)

    # check if dataframe indices are combined correctly
    assert merged.get_activities() == ["eat", "sleep", "work"]
    assert list(merged.activity_durations.index) == [
        timedelta(hours=1),
        timedelta(hours=2),
        timedelta(hours=7),
        timedelta(hours=8),
        timedelta(hours=9),
    ]
    assert list(merged.activity_frequencies.index) == [0, 1, 2, 4]

    # check if the probabilities are combined correctly
    # durations are averaged, but stay unchanged if missing in one of the stats
    assert merged.activity_durations["eat"].tolist() == [0.6, 0.4, 0, 0, 0]
    assert merged.activity_durations["work"].tolist() == [0.6, 0.4, 0, 0, 0]
    assert merged.activity_durations["sleep"].tolist() == [
        (x + y) / 2 for x, y in zip([0, 0, 0, 0.8, 0.2], [0, 0, 1.0, 0, 0])
    ]

    # check if the frequencies are combined correctly
    # frequencies are averaged, but if missing, they are set to 100% on frequency 0 for this stat object
    assert merged.activity_frequencies["eat"].tolist() == [0.5, 0.05, 0.25, 0.2]
    assert merged.activity_frequencies["work"].tolist() == [0.5, 0.05, 0.25, 0.2]
    assert merged.activity_frequencies["sleep"].tolist() == [
        (x + y) / 2 for x, y in zip([0.1, 0.9, 0, 0], [0, 1, 0, 0])
    ]

    # check if the probabilities are combined correctly
    # probabilities are averaged, but if missing, they are set to 0% for this stat object
    assert merged.probability_profiles.loc["eat"].tolist() == [0.3] * 24  # type: ignore
    assert merged.probability_profiles.loc["work"].tolist() == [0.15] * 24  # type: ignore
    assert merged.probability_profiles.loc["sleep"].tolist() == [  # type: ignore
        (x + y) / 2 for x, y in zip([0.4] * 24, [0.7] * 24)
    ]
