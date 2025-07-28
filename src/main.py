import mne
from mne.datasets import eegbci

# --- Using a sample MNE dataset ---

# 1. Define which subject and run from the BCI dataset we want.
# We'll use subject 1, run 6 which corresponds to an eyes open/closed task.
subject = 1
runs = [6]

# 2. Download the data. MNE will handle caching it for future use.
# This function returns a list of file paths for the downloaded data.
print("Fetching dataset from MNE...")
files = eegbci.load_data(subject, runs, update_path=True)
print(f"Dataset downloaded to: {files[0]}")

# 3. Load the downloaded EDF file into MNE's 'raw' object.
# We use the first file from the list returned.
# preload=True loads all the data into memory at once.
raw = mne.io.read_raw_edf(files[0], preload=True)

# 4. Print some basic information about the file to the console.
print("\nFile loaded successfully!")
print(raw.info)

# 5. Generate and display the interactive plot of the raw data.
# This will open a new window showing the signals.
print("\nShowing plot...")
raw.plot(block=True)
print("Plot window closed. Program finished.")