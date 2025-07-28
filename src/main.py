import sys
import mne
import numpy as np
from mne.datasets import eegbci

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                             QVBoxLayout, QHBoxLayout, QPushButton) # Import new widgets
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class EDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EDF Viewer v0.5 - Navigation Controls")
        self.setGeometry(100, 100, 1200, 800)

        # --- Application State Variables ---
        self.raw = None
        self.current_start_time = 0.0
        self.window_duration = 5.0 # Changed to 5s to match your project goal
        self.max_channels_to_display = 20

        # --- Main GUI Layout (Vertical) ---
        main_layout = QVBoxLayout()

        # --- Control Buttons Layout (Horizontal) ---
        # This horizontal layout will hold our buttons
        control_layout = QHBoxLayout()

        # Create the buttons
        self.prev_button = QPushButton("⏮️ Previous 5s")
        self.next_button = QPushButton("Next 5s ⏭️")
        
        # Add buttons to the horizontal layout
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.next_button)
        
        # Connect button clicks to functions
        self.prev_button.clicked.connect(self.prev_window)
        self.next_button.clicked.connect(self.next_window)

        # --- Matplotlib Canvas Setup ---
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # --- Assemble Main Layout ---
        # Add the horizontal button layout to the main vertical layout
        main_layout.addLayout(control_layout)
        # Then add the Matplotlib toolbar and canvas
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        # Set the central widget and its layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # --- Load Data and Initial Plot ---
        self.load_sample_data()
        self.plot_eeg_data()

    def load_sample_data(self):
        """Loads the MNE sample dataset into self.raw."""
        print("Loading MNE sample data...")
        files = eegbci.load_data(subject=1, runs=[6], update_path=True)
        self.raw = mne.io.read_raw_edf(files[0], preload=True)
        self.raw.pick_types(eeg=True)

    def plot_eeg_data(self):
        """Plots the data for the currently selected time window."""
        if self.raw is None:
            return

        sfreq = self.raw.info['sfreq']
        start_sample = int(self.current_start_time * sfreq)
        stop_sample = int((self.current_start_time + self.window_duration) * sfreq)

        ch_names_to_plot = self.raw.ch_names[:self.max_channels_to_display]
        data, times = self.raw.get_data(
            picks=ch_names_to_plot,
            start=start_sample,
            stop=stop_sample,
            return_times=True
        )

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        offset = np.std(data) * 3
        tick_locs = []
        
        for i, ch_name in enumerate(ch_names_to_plot):
            ax.plot(times, data[i] - (i * offset), lw=0.5, color='black')
            tick_locs.append(-(i * offset))

        ax.set_yticks(tick_locs)
        ax.set_yticklabels(ch_names_to_plot)
        ax.tick_params(axis='y', length=0)
        ax.set_xlabel("Time (s)")
        ax.set_title(f"EEG Signals ({self.current_start_time:.2f}s - {self.current_start_time + self.window_duration:.2f}s)")
        ax.grid(True, which='both', axis='y', linestyle=':')
        ax.set_ylim(-(offset * len(ch_names_to_plot)), offset)

        self.canvas.draw()
        print(f"Plot updated to show window: {self.current_start_time}s to {self.current_start_time + self.window_duration}s")
        
        # We should update button states after plotting
        self.update_button_states()

    # --- NEW NAVIGATION METHODS ---
    def next_window(self):
        """Shifts the time window forward."""
        if self.raw is None:
            return
        # Increase start time by the window duration
        self.current_start_time += self.window_duration
        # Re-plot the data for the new time window
        self.plot_eeg_data()

    def prev_window(self):
        """Shifts the time window backward."""
        if self.raw is None:
            return
        # Decrease start time, but don't go below zero
        self.current_start_time = max(0.0, self.current_start_time - self.window_duration)
        self.plot_eeg_data()

    def update_button_states(self):
        """Enable or disable navigation buttons based on position."""
        if self.raw is None:
            return
        # Disable "Previous" button if we are at the beginning
        self.prev_button.setEnabled(self.current_start_time > 0)
        # Disable "Next" button if we are at the end of the file
        max_time = self.raw.n_times / self.raw.info['sfreq']
        self.next_button.setEnabled(self.current_start_time + self.window_duration < max_time)


# --- Main Application Execution ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = EDFViewer()
    main_window.show()
    sys.exit(app.exec())