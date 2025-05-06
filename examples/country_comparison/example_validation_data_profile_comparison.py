#%%
from pathlib import Path
from matplotlib import gridspec
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from activityassure.hetus_data_processing import hetus_constants
from activityassure.profile_category import ProfileCategory
from activityassure.validation_statistics import ValidationSet
import os

validation_data_path = Path("data/validation_data_sets/activity_validation_data_set")

country1 = 'AT'
country2 = 'DE'
mode = "frequencies"
profile = ['female', 'student', 'working day']
activities = ["iron"]


validation_dataset_country1 = ValidationSet.load(validation_data_path, country=country1)
validation_dataset_country2 = ValidationSet.load(validation_data_path, country=country2)

# Resample
if hetus_constants.get_resolution(country1) != hetus_constants.get_resolution(country2):
    for _, v in (validation_dataset_country1.statistics | validation_dataset_country2.statistics).items():
        v.activity_durations.index = v.activity_durations.index.ceil('30min')
        v.activity_durations = v.activity_durations.resample('30min').sum()

        current_resolution = 10 if len(v.probability_profiles.columns) == 144 else 15
        v.probability_profiles.columns = [i * current_resolution for i in range(0, len(v.probability_profiles.columns))]
        v.probability_profiles = v.probability_profiles.T.groupby(lambda x: x // 30 * 30).mean().T
        v.probability_profiles.columns = [f"MACT{i}" for i in range(1, len(v.probability_profiles.columns)+1)]


#%% Plot
activities = activities if len(activities) > 0 else list(set(validation_dataset_country1.activity_durations.columns) | set(validation_dataset_country2.activity_durations.columns))
width = 8
ncols = 2
nrows = len(activities)
fig = plt.figure(figsize=(width,1.5*nrows*2))
gs = gridspec.GridSpec(nrows*2, 2, width_ratios=[2, 1])
axs = []
for i in range(len(activities)):
    axs.append([fig.add_subplot(gs[i*2, 0]), fig.add_subplot(gs[i*2, 1]), fig.add_subplot(gs[(i*2)+1,:])])
plt.subplots_adjust(left=0.1, hspace=0.7, top=0.9, wspace=0.25) 

for i, activity in enumerate(activities):
    ###### Read and merge 
    # Durations
    merged_df_durations = pd.merge(
        left=validation_dataset_country1.statistics[ProfileCategory.from_iterable([country1, profile[0], profile[1], profile[2]])].activity_durations[activity], 
        right=validation_dataset_country2.statistics[ProfileCategory.from_iterable([country2, profile[0], profile[1], profile[2]])].activity_durations[activity], 
        left_index=True, right_index=True, how="outer", suffixes=[f"_{country1}", f"_{country2}"]
    )
    merged_df_durations["id"] = merged_df_durations.index.map(lambda x: f"{x.components.hours:02}:{x.components.minutes:02}")
    
    # Frequencies
    merged_df_frequencies = pd.merge(
        left=validation_dataset_country1.statistics[ProfileCategory.from_iterable([country1, profile[0], profile[1], profile[2]])].activity_frequencies[activity], 
        right=validation_dataset_country2.statistics[ProfileCategory.from_iterable([country2, profile[0], profile[1], profile[2]])].activity_frequencies[activity], 
        left_index=True, right_index=True, how="outer", suffixes=[f"_{country1}", f"_{country2}"])

    merged_df_frequencies["id"] = merged_df_frequencies.index

    # Prepare dataframes
    for df in [merged_df_durations, merged_df_frequencies]:
        df.replace(0, None, inplace=True)
        df.dropna(subset=[f"{activity}_{country1}", f"{activity}_{country2}"], how='all', inplace=True)
        df.fillna(0, inplace=True)
        df.rename(columns={f"{activity}_{country1}": country1, f"{activity}_{country2}": country2}, inplace=True)

    melted_df_durations = merged_df_durations.melt(id_vars="id", var_name="Category", value_name="Value")
    melted_df_frequencies = merged_df_frequencies.melt(id_vars="id", var_name="Category", value_name="Value")

    # Probability profiles
    profile_country1 = validation_dataset_country1.statistics[ProfileCategory.from_iterable([country1, profile[0], profile[1], profile[2]])].probability_profiles.loc[activity,:]
    profile_country2 = validation_dataset_country2.statistics[ProfileCategory.from_iterable([country2, profile[0], profile[1], profile[2]])].probability_profiles.loc[activity,:]
            
    merged_df_profile = pd.merge(
        left=profile_country1, 
        right=profile_country2, 
        left_index=True, right_index=True, how="outer", suffixes=[f"_{country1}", f"_{country2}"])

    merged_df_profile["id"] = merged_df_profile.index.str.replace("MACT", "")
    melted_df_profile = merged_df_profile.melt(id_vars="id", var_name="Category", value_name="Value")
    melted_df_profile["id"] = melted_df_profile["id"].astype(int)
    ######### Plot 
    # Durations
    sns.barplot(x="id", y="Value", hue="Category", data=melted_df_durations, dodge=True, ax=axs[i][0], legend=False)
    xticklabels = axs[i][0].get_xticklabels()
    axs[i][0].set_xticklabels([v if i % 2 == 0 else "" for i, v in enumerate(xticklabels)] if len(xticklabels) > 20 else xticklabels, rotation=90, ha='right')
    axs[i][0].set_ylabel("probability")
    axs[i][0].set_xlabel("duration")
    
    # Frequencies
    sns.barplot(x="id", y="Value", hue="Category", data=melted_df_frequencies, dodge=True, ax=axs[i][1], legend=True)
    axs[i][1].set_ylabel("probability")
    axs[i][1].set_xlabel("frequencies")

    # Probability profiles
    sns.barplot(x="id", y="Value", hue="Category", data=melted_df_profile, dodge=True, ax=axs[i][2], legend=False)
    axs[i][2].set_ylabel("probability")
    axs[i][2].set_xlabel("Time")
    axs[i][2].set_xticklabels(axs[i][2].get_xticklabels(), rotation=90, ha='right')

    pos = axs[i][0].get_position()
    y_pos = pos.y0  # Center text in row
    fig.text(0, y_pos, activity, 
                fontsize=12, fontweight='bold', va="center", ha="center", rotation=90)

fig.suptitle(str(profile))
target_file=Path(f"../../data/country_comparison/{country1}-{country2}/{"_".join(profile)}__{'_'.join(activities)}.png")
os.makedirs(target_file.parent, exist_ok=True)
fig.savefig(target_file)