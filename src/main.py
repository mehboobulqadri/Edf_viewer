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

        self.setWindowTitle("EDF Viewer v0.3 - Manual Plot")
        self.setGeometry(100, 100, 1200, 800)

        # This setup is correct and remains the same
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

        # --- Load the data when the app starts ---
        # In the future, a "Load File" button will do this.
        self.load_and_plot_data()

    def load_and_plot_data(self):
        """Loads data and calls the plotting function."""
        print("Loading MNE sample data...")
        files = eegbci.load_data(subject=1, runs=[6], update_path=True)
        self.raw = mne.io.read_raw_edf(files[0], preload=True)
        
        # We only want to see the EEG channels for this example
        self.raw.pick_types(eeg=True)
        
        # Now, plot the data we just loaded
        self.plot_eeg_data()

    def plot_eeg_data(self):
        """
        Extracts data from the raw object and plots it on the canvas.
        This is the manual plotting method.
        """
        print("Manually plotting EEG data...")
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Get the EEG data and times
        data, times = self.raw.get_data(return_times=True)
        
        # --- Plotting Logic ---
        # To prevent signals from overlapping, we'll stack them vertically.
        # We calculate an offset based on the average peak-to-peak amplitude.
        ch_names = self.raw.ch_names
        n_channels = len(ch_names)
        
        # Calculate a reasonable offset
        offset = np.std(data) * 3 # An offset of 3 standard deviations
        tick_locs = [] # To store y-axis tick locations
        
        for i, ch_name in enumerate(ch_names):
            y = data[i]
            y_offset = i * offset
            ax.plot(times, y - y_offset, lw=0.5, color='black')
            tick_locs.append(-y_offset)

        # --- Formatting the Plot ---
        ax.set_yticks(tick_locs)
        ax.set_yticklabels(ch_names)
        ax.tick_params(axis='y', length=0) # Hide y-axis ticks
        ax.set_xlabel("Time (s)")
        ax.set_title("EEG Signals")
        ax.set_ylim(-offset * n_channels, offset) # Adjust y-limits for visibility
        ax.grid(True, which='both', axis='y', linestyle=':')

        self.canvas.draw()
        print("Plotting complete.")

# --- Main Application Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = EDFViewer()
    main_window.show()
    sys.exit(app.exec())