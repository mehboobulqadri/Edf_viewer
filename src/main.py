import sys
import mne
import numpy as np

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                             QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
                             QLineEdit, QLabel)
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

class EDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EDF Viewer v1.3 ")
        self.setGeometry(100, 100, 1200, 800)

        # --- State Variables ---
        self.raw = None
        self.view_start_time = 0.0
        self.view_duration = 10.0
        self.focus_start_time = 0.0
        self.focus_duration = 1.0

        # --- GUI Setup ---
        main_layout = QVBoxLayout()
        control_layout = QHBoxLayout()
        focus_layout = QHBoxLayout()

        focus_layout.addWidget(QLabel("Focus Duration (s):"))
        self.duration_input = QLineEdit(str(self.focus_duration))
        self.duration_input.setFixedWidth(60)
        self.update_duration_button = QPushButton("Update")
        focus_layout.addWidget(self.duration_input)
        focus_layout.addWidget(self.update_duration_button)
        focus_layout.addStretch()
        focus_layout.addWidget(QLabel("Move Focus Window:"))
        self.prev_focus_button = QPushButton("⏮️")
        self.next_focus_button = QPushButton("⏭️")
        focus_layout.addWidget(self.prev_focus_button)
        focus_layout.addWidget(self.next_focus_button)

        self.load_button = QPushButton("Load EDF File")
        control_layout.addWidget(self.load_button)

        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)

        # --- Event Connections ---
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.load_button.clicked.connect(self.open_file_dialog)
        self.update_duration_button.clicked.connect(self.update_focus_duration)
        self.next_focus_button.clicked.connect(self.next_focus)
        self.prev_focus_button.clicked.connect(self.prev_focus)

        main_layout.addLayout(control_layout)
        main_layout.addLayout(focus_layout)
        main_layout.addWidget(self.canvas)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.update_button_states()

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EDF File", "", "EDF Files (*.edf)")
        if file_path:
            self.load_edf_file(file_path)

    def load_edf_file(self, file_path):
        try:
            self.raw = mne.io.read_raw_edf(file_path, preload=True, verbose=False)
            self.raw.pick_types(eeg=True, meg=False, stim=False, exclude=[])

            self.view_start_time = 0.0
            self.view_duration = 10.0
            self.focus_start_time = 0.0
            self.focus_duration = 1.0
            self.duration_input.setText(str(self.focus_duration))

            self._validate_and_plot()
        except Exception as e:
            print(f"Error loading file: {e}")

    def _validate_and_plot(self):
        if self.raw is None:
            return
        max_time = self.raw.times[-1]

        self.view_duration = np.clip(self.view_duration, 0.1, max_time)
        self.view_start_time = np.clip(self.view_start_time, 0, max_time - self.view_duration)
        self.focus_duration = np.clip(self.focus_duration, 0.1, max_time)
        self.focus_start_time = np.clip(self.focus_start_time, 0, max_time - self.focus_duration)

        self.plot_eeg_data()

    def keyPressEvent(self, event):
        if self.raw is None or self.duration_input.hasFocus():
            return

        pan_amount = self.view_duration * 0.1
        max_time = self.raw.times[-1]

        if event.key() == Qt.Key.Key_Right:
            self.view_start_time += pan_amount
        elif event.key() == Qt.Key.Key_Left:
            self.view_start_time -= pan_amount

        # Clamp view_start_time
        self.view_start_time = np.clip(self.view_start_time, 0, max_time - self.view_duration)

        self._validate_and_plot()


    def on_scroll(self, event):
        if self.raw is None or event.inaxes is None:
            return

        x_mouse = event.xdata  # Time under mouse
        old_duration = self.view_duration
        max_time = self.raw.times[-1]

        # Zooming factor
        zoom_factor = 1.3
        if event.button == 'up':  # Zoom in
            new_duration = self.view_duration / zoom_factor
        elif event.button == 'down':  # Zoom out
            new_duration = self.view_duration * zoom_factor
        else:
            return

        # Clamp new_duration
        new_duration = np.clip(new_duration, 0.1, max_time)

        # Calculate new start time so that x_mouse stays in place
        rel_mouse_pos = (x_mouse - self.view_start_time) / old_duration
        new_start = x_mouse - rel_mouse_pos * new_duration

        # Clamp start time to not go out of bounds
        new_start = np.clip(new_start, 0, max_time - new_duration)

        self.view_start_time = new_start
        self.view_duration = new_duration

        self._validate_and_plot()


    def on_click(self, event):
        if self.raw is None or event.inaxes is None:
            return
        self.focus_start_time = event.xdata
        self._validate_and_plot()

    def update_focus_duration(self):
        try:
            duration = float(self.duration_input.text())
            self.focus_duration = duration
            self._validate_and_plot()
        except ValueError:
            print("Invalid duration.")

    def next_focus(self):
        if self.raw is None:
            return
        self.focus_start_time += self.focus_duration
        self._validate_and_plot()

    def prev_focus(self):
        if self.raw is None:
            return
        self.focus_start_time -= self.focus_duration
        self._validate_and_plot()

    def plot_eeg_data(self):
        if self.raw is None:
            return

        view_start = self.view_start_time
        view_end = view_start + self.view_duration

        start_samp = int(view_start * self.raw.info['sfreq'])
        stop_samp = int(view_end * self.raw.info['sfreq'])

        ch_names_to_plot = self.raw.ch_names[:20]
        if not ch_names_to_plot:
            return

        data, times = self.raw.get_data(picks=ch_names_to_plot, start=start_samp, stop=stop_samp, return_times=True)
        times += view_start

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        offset = np.std(data) * 3 if np.std(data) > 0 else 1
        tick_locs = []

        for i, ch_name in enumerate(ch_names_to_plot):
            ax.plot(times, data[i] - (i * offset), lw=0.5, color='black')
            tick_locs.append(-(i * offset))

        ax.axvspan(self.focus_start_time, self.focus_start_time + self.focus_duration,
                   color='yellow', alpha=0.4, zorder=0)

        ax.set_yticks(tick_locs)
        ax.set_yticklabels(ch_names_to_plot)
        ax.set_xlim(view_start, view_end)
        ax.set_xlabel("Time (s)")
        ax.xaxis.set_major_locator(MaxNLocator(nbins=10, prune='both'))
        ax.grid(True, which='both', axis='y', linestyle=':')
        self.canvas.draw()
        self.update_button_states()

    def update_button_states(self):
        is_loaded = self.raw is not None
        for widget in [self.duration_input, self.update_duration_button, self.prev_focus_button, self.next_focus_button]:
            widget.setEnabled(is_loaded)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = EDFViewer()
    main_window.show()
    sys.exit(app.exec())
