import sys
import mne
import numpy as np
from mne.datasets import eegbci

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class EDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EDF Viewer v0.4 - Time Window Plot")
        self.setGeometry(100, 100, 1200, 800)

        # --- Application State Variables ---
        # These will control what part of the data we are looking at.
        self.raw = None
        self.current_start_time = 0.0  # Start at the beginning of the file
        self.window_duration = 10.0    # Show 10 seconds of data at a time
        self.max_channels_to_display = 20 # Limit channels to avoid clutter

        # --- GUI Setup ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        self.load_sample_data()
        # Initial plot after loading
        self.plot_eeg_data()

    def load_sample_data(self):
        """Loads the MNE sample dataset into self.raw."""
        print("Loading MNE sample data...")
        files = eegbci.load_data(subject=1, runs=[6], update_path=True)
        self.raw = mne.io.read_raw_edf(files[0], preload=True)
        self.raw.pick_types(eeg=True) # We only want EEG channels

    def plot_eeg_data(self):
        """Plots the data for the currently selected time window."""
        if self.raw is None:
            return # Don't plot if no data is loaded

        # --- Calculate Time and Data Slice ---
        sfreq = self.raw.info['sfreq']
        start_sample = int(self.current_start_time * sfreq)
        stop_sample = int((self.current_start_time + self.window_duration) * sfreq)

        # Get the slice of data for the window
        # We also limit the number of channels here using pick
        ch_names_to_plot = self.raw.ch_names[:self.max_channels_to_display]
        data, times = self.raw.get_data(
            picks=ch_names_to_plot,
            start=start_sample,
            stop=stop_sample,
            return_times=True
        )

        # --- Plotting ---
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        offset = np.std(data) * 3
        tick_locs = []
        
        for i, ch_name in enumerate(ch_names_to_plot):
            y = data[i]
            ax.plot(times, y - (i * offset), lw=0.5, color='black')
            tick_locs.append(-(i * offset))

        # --- Formatting the Plot ---
        ax.set_yticks(tick_locs)
        ax.set_yticklabels(ch_names_to_plot)
        ax.tick_params(axis='y', length=0)
        ax.set_xlabel("Time (s)")
        ax.set_title(f"EEG Signals ({self.current_start_time:.2f}s - {self.current_start_time + self.window_duration:.2f}s)")
        ax.grid(True, which='both', axis='y', linestyle=':')
        
        # Adjust y-limits for visibility, leaving a little space
        ax.set_ylim(-(offset * len(ch_names_to_plot)), offset)

        self.canvas.draw()
        print(f"Plot updated to show window: {self.current_start_time}s to {self.current_start_time + self.window_duration}s")


# --- Main Application Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = EDFViewer()
    main_window.show()
    sys.exit(app.exec())