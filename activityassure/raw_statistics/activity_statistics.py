"""Calculates statistics on occurrences of the original activities, without
mappings or aggregations."""

# load and preprocess all input data
import sys
from collections import Counter, defaultdict
from datetime import timedelta
import json
from pathlib import Path

from tqdm import tqdm
from activityassure.activity_profile import SparseActivityProfile


def sort_by_val(d: dict) -> dict:
    """Sorts a dict by value in descending order.

    :param d: the dict to sort
    :return: a new, sorted dict
    """
    return dict(sorted(d.items(), key=lambda x: x[1], reverse=True))


def save_dict(filepath: Path, data: dict) -> None:
    """Saves a dict to a json file

    :param filepath: target file path
    :param data: the dict to save
    """
    with open(filepath, "w", encoding="utf8") as f:
        json.dump(data, f, indent=4)


def dur_dict_to_strs(d: dict[str, int], resolution: timedelta) -> dict[str, str]:
    """Converts a duration dict with int values to a dict containing
    timedelta strings.

    :param d: the dict with duration values in timesteps
    :param resolution: the resolution to apply
    :return: the resulting dict with timedelta strings
    """
    return {k: str(v * resolution) for k, v in d.items()}


def get_activity_statistics(
    profile_dir: Path, output_dir: Path, resolution=timedelta(minutes=1)
):
    occurrences = Counter()
    durations = defaultdict(int)
    user_counts = defaultdict(int)
    files = list(profile_dir.iterdir())
    for csv_file in tqdm(files):
        assert csv_file.is_file(), f"Unexpected directory: {csv_file}"
        # load the activity profile from csv
        activity_profile = SparseActivityProfile.load_from_csv(
            csv_file, None, resolution  # type: ignore
        )
        # add occurrences, durations and user counts
        names = [a.name for a in activity_profile.activities]
        occurrences.update(names)
        for activity in set(names):
            user_counts[activity] += 1
        for activity in activity_profile.activities:
            durations[activity.name] += activity.duration

    # get user shares relative to total person count
    person_count = len(files)
    user_shares = {k: v / person_count for k, v in user_counts.items()}

    # convert durations to timedelta strings
    durations = sort_by_val(durations)
    total_dur_strs = dur_dict_to_strs(durations, resolution)

    # get the average total duration per person that carries out the activity
    dur_per_user = {k: v / person_count / user_shares[k] for k, v in durations.items()}
    dur_per_user = sort_by_val(dur_per_user)
    dur_per_user_strs = dur_dict_to_strs(dur_per_user, resolution)

    # get the average number of occurences per person that carries out the activity
    occ_per_user = sort_by_val(
        {k: v / person_count / user_shares[k] for k, v in occurrences.items()}
    )

    # collect general statistics
    stats = {
        "persons": person_count,
        "total profile duration": str(resolution * sum(v for v in durations.values())),
    }

    # save all statistics in json files
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Calculated general activity statistics from {len(files)} profiles")
    save_dict(output_dir / "general_info.json", stats)
    save_dict(output_dir / "total_occurrences.json", dict(occurrences.most_common()))
    save_dict(output_dir / "user_shares.json", sort_by_val(user_shares))
    save_dict(output_dir / "total_durations.json", total_dur_strs)
    save_dict(output_dir / "duration_per_user.json", dur_per_user_strs)
    save_dict(output_dir / "occurrences_per_user.json", occ_per_user)


if __name__ == "__main__":
    path = Path(sys.argv[1])
    assert path.is_dir(), f"Invalid input path: {sys.argv[1]}"
    get_activity_statistics(path, Path("affordance_statistics"))
