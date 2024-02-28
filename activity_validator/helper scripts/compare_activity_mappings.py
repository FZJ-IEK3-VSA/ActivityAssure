"""
Helper script for comparing activity mappings and checking which
common activities they contain.
"""

import collections
import json

# file that contains all mappings
path = r"activity_validator\activity_types\mappings.json"

with open(path, "r") as f:
    content: dict[str, dict] = json.load(f)

all_activities: list[str] = []
for d in content.values():
    for v in d.values():
        if isinstance(v, str):
            all_activities.append(v)
        else:
            all_activities.extend(v)

# all_tuples = dict(itertools.chain.from_iterable(content.values()))
# all_activities = [v for k, v in all_tuples]
print(f"{len(all_activities)} activities")
unique = list(set(all_activities))
print(f"{len(unique)} unique activities")

used_by = {
    a: list(
        sorted(author[:2] for author, vals in content.items() if a in vals.values())
    )
    for a in unique
}

duplicates = {
    item: count
    for item, count in collections.Counter(all_activities).most_common()
    if count > 1
}
print(f"\n{len(duplicates)} Duplicates:")
print(
    "\n".join(
        f"{item:<15} {count:>2}   {used_by[item]}" for item, count in duplicates.items()
    )
)

print("\nOnly once:")
print(",".join(a for a in unique if a not in duplicates))
