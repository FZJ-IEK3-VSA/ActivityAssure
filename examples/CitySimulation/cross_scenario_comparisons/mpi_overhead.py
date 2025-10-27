"""Plots MPI overhead and simulation speed for different numbers of workers"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

csv_path = Path("R:/phd_dir/results/speedtest100/mainsim_speedlog.csv")
df = pd.read_csv(csv_path)

for col in ["Main loop", "MPI communication"]:
    df[col] = pd.to_timedelta(df[col])


# --- Plot average MPI percent per Test ---
plt.figure(figsize=(6, 4))
sns.barplot(
    data=df,
    x="Test",
    hue="Test",
    y="MPI percent",
    estimator="mean",
    errorbar="sd",  # show standard deviation as error bar
    # palette="Blues_d",
    legend=False,
)

# plt.title("Average MPI Percent per Test")
plt.xlabel("Anzahl Worker")
plt.ylabel("Rechenaufwand für Kommunikation [%]")
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.tight_layout()
plt.savefig("bars_mpi_overhead.svg")


# --- Plot average MPI percent per Test ---
plt.figure(figsize=(6, 4))
sns.barplot(
    data=df,
    x="Test",
    hue="Test",
    y="person steps/second",
    estimator="mean",
    errorbar="sd",
    palette="Blues_d",
    legend=False,
)

# plt.title("Average Person Steps per Second per Test")
plt.xlabel("Anzahl Worker")
plt.ylabel("Personen-Zeitschritte pro Sekunde")
plt.grid(axis="y", linestyle="--", alpha=0.6)
plt.tight_layout()
# plt.show()
plt.savefig("bars_person_steps.svg")
