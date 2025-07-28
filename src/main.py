import sys
import mne
import numpy as np
# We will no longer need the sample dataset by default
# from mne.datasets import eegbci

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog) # Import QFileDialog

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class EDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EDF Viewer v0.6 - File Loading")
        self.setGeometry(100, 100, 1200, 800)

        # --- Application State Variables ---
        self.raw = None
        self.current_start_time = 0.0
        self.window_duration = 5.0
        self.max_channels_to_display = 20

        # --- Main GUI Layout (Vertical) ---
        main_layout = QVBoxLayout()

        # --- Control Buttons Layout (Horizontal) ---
        control_layout = QHBoxLayout()

        self.load_button = QPushButton("Load EDF File")
        self.prev_button = QPushButton("⏮️ Previous 5s")
        self.next_button = QPushButton("Next 5s ⏭️")

        control_layout.addWidget(self.load_button)
        control_layout.addWidget(self.prev_button)
        control_layout.addWidget(self.next_button)

        self.load_button.clicked.connect(self.open_file_dialog)
        self.prev_button.clicked.connect(self.prev_window)
        self.next_button.clicked.connect(self.next_window)

        # --- Matplotlib Canvas Setup ---
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        # --- Assemble Main Layout ---
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.canvas)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # --- Initial State ---
        # Plot is initially empty, buttons are disabled
        self.update_button_states()

    def open_file_dialog(self):
        """Opens a dialog to select an EDF file."""
        # The first element of the tuple is the file path
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open EDF File",
            "", # Start directory
            "EDF Files (*.edf);;All Files (*)"
        )
        if file_path: # If the user selected a file
            self.load_edf_file(file_path)

    def load_edf_file(self, file_path):
        """Loads data from an EDF file and plots it."""
        try:
            print(f"Loading file: {file_path}")
            self.raw = mne.io.read_raw_edf(file_path, preload=True)
            # Reset view to the beginning of the new file
            self.current_start_time = 0.0
            self.plot_eeg_data()
            print("File loaded successfully.")
        except Exception as e:
            # In a real app, show a popup error message
            print(f"Error loading file: {e}")

    def plot_eeg_data(self):
        if self.raw is None:
            # Clear the canvas if no file is loaded
            self.figure.clear()
            self.canvas.draw()
            return

        sfreq = self.raw.info['sfreq']
        start_sample = int(self.current_start_time * sfreq)
        stop_sample = int((self.current_start_time + self.window_duration) * sfreq)

        # Pick EEG channels first, then slice for display
        eeg_channels = self.raw.copy().pick_types(eeg=True).ch_names
        ch_names_to_plot = eeg_channels[:self.max_channels_to_display]
        
        if not ch_names_to_plot:
            print("No EEG channels found in the file.")
            self.figure.clear()
            self.canvas.draw()
            return

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
        self.update_button_states()

    def next_window(self):
        if self.raw is None: return
        self.current_start_time += self.window_duration
        self.plot_eeg_data()

    def prev_window(self):
        if self.raw is None: return
        self.current_start_time = max(0.0, self.current_start_time - self.window_duration)
        self.plot_eeg_data()

    def update_button_states(self):
        """Enable or disable buttons based on whether a file is loaded."""
        if self.raw is None:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
        else:
            self.prev_button.setEnabled(self.current_start_time > 0)
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.next_button.setEnabled(self.current_start_time + self.window_duration < max_time)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = EDFViewer()
    main_window.show()
    sys.exit(app.exec())