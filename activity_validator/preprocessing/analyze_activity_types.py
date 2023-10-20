import collections
import itertools
import json

import difflib

# Kategorien von Jannik: Personal Area,Employment,Education,Housekeeping,Voluntary Work,Social/Entertainment,Hobbies/Sport,Media Usage,Travel Times,Cooking/Eating,TV Usage
path = r"activity_validator\activity_types\mappings.json"

with open(path, "r") as f:
    content: dict[str, dict] = json.load(f)

all_activities: list[str] = []
for d in content.values():
    all_activities.extend(d.values())
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
        f"{item:<30} {count}   {used_by[item]}" for item, count in duplicates.items()
    )
)

# difflib is not really helpful here
print("\nSimilar:")
# for i, activity in enumerate(unique):
# similar = difflib.get_close_matches(activity, unique, n=10, cutoff=0.5)
# the word itself is always contained in similar
# if len(similar) > 1:
#     similar.remove(activity)
#     print(f"{activity:<30} {similar}")
# overlapping = []
# for other in unique[i + 1 :]:
#     sm = difflib.SequenceMatcher(None, activity, other)
#     pos_a, pos_b, size = sm.find_longest_match(0, len(activity), 0, len(other))
#     if size > 3:
#         overlapping.append(other)
# if overlapping:
#     print(f"{activity:<30} {overlapping}")

print("\nOnly once:")
print(",".join(a for a in unique if a not in duplicates))


# TODO: für jeden Autor ein Mapping erstellen --> so sehe ich, wie gut es funktioniert und habe direkt gute Beispiele
