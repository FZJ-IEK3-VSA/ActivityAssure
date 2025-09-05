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
    return dict(sorted(d.items(), key=lambda x: x[1], reverse=True))


def get_activity_statistics(
    profile_dir: Path, output_dir: Path, resolution=timedelta(minutes=1)
):
    total_occurrences = Counter()
    total_durations = defaultdict(int)
    user_counts = defaultdict(int)
    files = list(profile_dir.iterdir())
    for csv_file in tqdm(files):
        assert csv_file.is_file(), f"Unexpected directory: {csv_file}"
        # load the activity profile from csv
        activity_profile = SparseActivityProfile.load_from_csv(
            csv_file, None, resolution  # type: ignore
        )
        # add occurrences, durations and
        names = [a.name for a in activity_profile.activities]
        total_occurrences.update(names)
        for activity in set(names):
            user_counts[activity] += 1
        for activity in activity_profile.activities:
            total_durations[activity.name] += activity.duration

    # get user shares relative to total person count
    person_count = len(files)
    user_shares = {k: v / person_count for k, v in user_counts.items()}

    # convert durations to timedelta strings
    total_durations = sort_by_val(total_durations)
    total_dur_strs = {k: str(v * resolution) for k, v in total_durations.items()}

    # collect general statistics
    stats = {
        "persons": person_count,
        "total profile duration": str(
            resolution * sum(v for v in total_durations.values())
        ),
    }

    # save statistics
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Calculated general activity statistics from {len(files)} profiles")
    with open(output_dir / "general_info.json", "w", encoding="utf8") as f:
        json.dump(stats, f, indent=4)
    with open(output_dir / "total_occurrences.json", "w", encoding="utf8") as f:
        json.dump(dict(total_occurrences.most_common()), f, indent=4)
    with open(output_dir / "user_shares.json", "w", encoding="utf8") as f:
        json.dump(sort_by_val(user_shares), f, indent=4)
    with open(output_dir / "total_durations.json", "w", encoding="utf8") as f:
        json.dump(total_dur_strs, f, indent=4)


if __name__ == "__main__":
    path = Path(sys.argv[1])
    assert path.is_dir(), f"Invalid input path: {sys.argv[1]}"
    get_activity_statistics(path, Path("affordance_statistics"))
