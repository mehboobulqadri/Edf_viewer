import sys
import mne
import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QDoubleValidator, QFont, QKeySequence, QAction, QColor
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenu
    QPushButton, QFileDialog, QLineEdit, QLabel, QScrollBar, QStatusBar,
    QComboBox, QGroupBox, QMessageBox, QCheckBox, QFrame,
    QToolBar, QDialog, QListWidget, QListWidgetItem,
    QSplitter, QAbstractItemView, QInputDialog, QSlider, QColorDialog
)
import time
import logging
from pathlib import Path

# Configure Matplotlib for optimal EEG visualization performance
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 1.0
mpl.rcParams['agg.path.chunksize'] = 10000
mpl.rcParams['font.size'] = 8
mpl.rcParams['figure.autolayout'] = True

# Set up logging for critical errors
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='edf_viewer_errors.log')

class ChannelSelectionDialog(QDialog):
    """Dialog for selecting and ordering EEG channels."""
    def __init__(self, raw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Selection")
        self.resize(600, 800)
        self.raw = raw
        self.selected_channels = parent.channel_indices if hasattr(parent, 'channel_indices') and parent.channel_indices else list(range(len(raw.ch_names)))

        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Vertical)

        available_group = QGroupBox("Available Channels")
        available_layout = QVBoxLayout()
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        available_layout.addWidget(self.available_list)
        available_group.setLayout(available_layout)

        selected_group = QGroupBox("Selected Channels (Drag to reorder)")
        selected_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.selected_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        selected_layout.addWidget(self.selected_list)
        selected_group.setLayout(selected_layout)

        selected_set = set(self.selected_channels)
        for i, ch_name in enumerate(raw.ch_names):
            item = QListWidgetItem(ch_name)
            item.setData(Qt.ItemDataRole.UserRole, i)
            if i in selected_set:
                self.selected_list.addItem(item)
            else:
                self.available_list.addItem(item)

        splitter.addWidget(available_group)
        splitter.addWidget(selected_group)
        splitter.setSizes([300, 500])

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("→ Add")
        self.remove_button = QPushButton("← Remove")
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        self.add_button.clicked.connect(self.add_channels)
        self.remove_button.clicked.connect(self.remove_channels)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        main_layout.addWidget(splitter)
        main_layout.addLayout(button_layout)

    def add_channels(self):
        for item in self.available_list.selectedItems():
            self.selected_list.addItem(self.available_list.takeItem(self.available_list.row(item)))

    def remove_channels(self):
        for item in self.selected_list.selectedItems():
            self.available_list.addItem(self.selected_list.takeItem(self.selected_list.row(item)))

    def get_selected_channels(self):
        return [self.selected_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.selected_list.count())]

    def accept(self):
        if self.selected_list.count() == 0:
            QMessageBox.warning(self, "Invalid Selection", "You must select at least one channel to continue.")
            return
        super().accept()

class ChannelColorDialog(QDialog):
    """Dialog for assigning colors to individual EEG channels."""
    def __init__(self, raw, channel_colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Color Selection")
        self.resize(400, 600)
        self.raw = raw
        self.channel_colors = channel_colors.copy()

        main_layout = QVBoxLayout(self)
        self.color_list = QListWidget()
        self.color_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for ch_name in raw.ch_names:
            item = QListWidgetItem(ch_name)
            color = self.channel_colors.get(ch_name, QColor('black'))
            item.setBackground(color)
            item.setData(Qt.ItemDataRole.UserRole, ch_name)
            self.color_list.addItem(item)
        main_layout.addWidget(self.color_list)

        button_layout = QHBoxLayout()
        self.set_color_button = QPushButton("Set Color")
        self.reset_color_button = QPushButton("Reset to Default")
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.set_color_button)
        button_layout.addWidget(self.reset_color_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        self.set_color_button.clicked.connect(self.set_channel_color)
        self.reset_color_button.clicked.connect(self.reset_channel_color)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        main_layout.addLayout(button_layout)

    def set_channel_color(self):
        selected = self.color_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a channel to set its color.")
            return
        ch_name = selected[0].data(Qt.ItemDataRole.UserRole)
        color = QColorDialog.getColor(self.channel_colors.get(ch_name, QColor('black')), self, f"Select Color for {ch_name}")
        if color.isValid():
            self.channel_colors[ch_name] = color
            selected[0].setBackground(color)

    def reset_channel_color(self):
        selected = self.color_list.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Please select a channel to reset its color.")
            return
        ch_name = selected[0].data(Qt.ItemDataRole.UserRole)
        self.channel_colors[ch_name] = QColor('black')
        selected[0].setBackground(QColor('black'))

    def get_channel_colors(self):
        return self.channel_colors

class HighlightSectionDialog(QDialog):
    """Dialog for highlighting a specific section of a channel."""
    def __init__(self, raw, channel_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Highlight Section")
        self.resize(400, 300)
        self.raw = raw
        self.max_time = raw.n_times / raw.info['sfreq'] if raw else 0

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(QLabel("Select Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(channel_names)
        main_layout.addWidget(self.channel_combo)

        main_layout.addWidget(QLabel("Start Time (s):"))
        self.start_input = QLineEdit("0.0")
        self.start_input.setValidator(QDoubleValidator(0.0, self.max_time, 2))
        main_layout.addWidget(self.start_input)

        main_layout.addWidget(QLabel("Duration (s):"))
        self.duration_input = QLineEdit("1.0")
        self.duration_input.setValidator(QDoubleValidator(0.1, self.max_time, 2))
        main_layout.addWidget(self.duration_input)

        main_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton("Choose Color")
        self.selected_color = QColor('red')
        self.color_button.setStyleSheet(f"background-color: {self.selected_color.name()}")
        self.color_button.clicked.connect(self.choose_color)
        main_layout.addWidget(self.color_button)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def choose_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Select Highlight Color")
        if color.isValid():
            self.selected_color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()}")

    def get_highlight_info(self):
        try:
            start = float(self.start_input.text())
            duration = float(self.duration_input.text())
            if start + duration > self.max_time or start < 0 or duration <= 0:
                QMessageBox.warning(self, "Invalid Input", "Start time or duration is out of bounds.")
                return None
            return (self.channel_combo.currentText(), start, duration, self.selected_color)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for start time and duration.")
            return None

class EDFViewer(QMainWindow):
    """Advanced EDF Viewer for clinical EEG review with annotation and color coding."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clinical EDF Viewer")
        self.setGeometry(100, 100, 1400, 900)

        self.raw = None
        self.view_start_time = 0.0
        self.view_duration = 10.0
        self.min_duration = 0.1
        self.max_duration = 30.0
        self.focus_start_time = 0.0
        self.focus_duration = 1.0
        self.focus_step_time = 0.5
        self.is_auto_moving = False
        self.auto_move_timer = QTimer(self)
        self.auto_move_timer.timeout.connect(self.auto_move_focus)
        self.channel_indices = []
        self.channel_colors = {}
        self.channel_offset = 0
        self.total_channels = 0
        self.visible_channels = 20
        self.popup_enabled = True
        self.zoom_factor = 1.3
        self.plot_fps = 0
        self.sensitivity = 50e-6  # µV scaling
        self.annotations = mne.Annotations(onset=[], duration=[], description=[])
        self.section_highlights = []  # List of (ch_name, onset, duration, color) tuples
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._validate_and_plot)

        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_status_bar()
        self.update_button_states()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        control_layout = self.create_control_panel()
        focus_layout = self.create_focus_panel()
        navigation_layout = self.create_navigation_panel()
        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        plot_container = QWidget()
        plot_layout = QHBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self.canvas, 1)
        self.vscroll = QScrollBar(Qt.Orientation.Vertical)
        self.vscroll.valueChanged.connect(self.on_channel_scroll)
        plot_layout.addWidget(self.vscroll)
        self.hscroll = QScrollBar(Qt.Orientation.Horizontal)
        self.hscroll.valueChanged.connect(self.on_time_scroll)
        main_layout.addLayout(control_layout)
        main_layout.addLayout(focus_layout)
        main_layout.addLayout(navigation_layout)
        main_layout.addWidget(plot_container, 1)
        main_layout.addWidget(self.hscroll)
        self.setCentralWidget(main_widget)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.show_context_menu)

    def setup_menus(self):
        self.file_menu = self.menuBar().addMenu("File")
        save_ann_action = QAction("Save Annotations", self)
        save_ann_action.triggered.connect(self.save_annotations)
        self.file_menu.addAction(save_ann_action)
        load_ann_action = QAction("Load Annotations", self)
        load_ann_action.triggered.connect(self.load_annotations)
        self.file_menu.addAction(load_ann_action)
        save_csv_action = QAction("Export Annotations to CSV", self)
        save_csv_action.triggered.connect(self.export_annotations_csv)
        self.file_menu.addAction(save_csv_action)
        clear_highlights_action = QAction("Clear Highlights", self)
        clear_highlights_action.triggered.connect(self.clear_highlights)
        self.file_menu.addAction(clear_highlights_action)

    def create_control_panel(self):
        layout = QHBoxLayout()
        self.load_button = QPushButton("Load EDF File")
        self.load_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.load_button)
        layout.addWidget(QLabel("Visible Channels:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["20", "30", "40", "50", "All"])
        self.channel_combo.setCurrentText(str(self.visible_channels))
        self.channel_combo.currentTextChanged.connect(self.on_channel_selection_changed)
        layout.addWidget(self.channel_combo)
        self.channel_button = QPushButton("Manage Channels...")
        self.channel_button.clicked.connect(self.open_channel_selection)
        layout.addWidget(self.channel_button)
        self.color_button = QPushButton("Set Channel Colors...")
        self.color_button.clicked.connect(self.open_color_selection)
        layout.addWidget(self.color_button)
        layout.addWidget(QLabel("Sensitivity (µV):"))
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(10, 200)  # 10µV to 200µV
        self.sensitivity_slider.setValue(int(self.sensitivity * 1e6))
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity)
        layout.addWidget(self.sensitivity_slider)
        self.sensitivity_label = QLabel(f"{self.sensitivity * 1e6:.0f} µV")
        layout.addWidget(self.sensitivity_label)
        layout.addStretch()
        return layout

    def create_focus_panel(self):
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Focus Duration (s):"))
        self.duration_input = QLineEdit(str(self.focus_duration))
        self.duration_input.setFixedWidth(60)
        self.duration_input.setValidator(QDoubleValidator(0.1, 10.0, 2))
        self.update_duration_button = QPushButton("Update")
        self.update_duration_button.clicked.connect(self.update_focus_duration)
        layout.addWidget(self.duration_input)
        layout.addWidget(self.update_duration_button)
        layout.addWidget(QLabel("Step (s):"))
        self.step_input = QLineEdit(str(self.focus_step_time))
        self.step_input.setFixedWidth(60)
        self.step_input.setValidator(QDoubleValidator(0.1, 10.0, 2))
        self.update_step_button = QPushButton("Set Step")
        self.update_step_button.clicked.connect(self.update_focus_step)
        layout.addWidget(self.step_input)
        layout.addWidget(self.update_step_button)
        layout.addStretch()
        return layout

    def create_navigation_panel(self):
        layout = QHBoxLayout()
        self.prev_focus_button = QPushButton("⏮️ Prev (G)")
        self.next_focus_button = QPushButton("Next (H) ⏭️")
        self.auto_button = QPushButton("▶ Auto (Space)")
        self.prev_focus_button.clicked.connect(self.prev_focus)
        self.next_focus_button.clicked.connect(self.next_focus)
        self.auto_button.clicked.connect(self.toggle_auto_move)
        layout.addWidget(self.prev_focus_button)
        layout.addWidget(self.next_focus_button)
        layout.addWidget(self.auto_button)
        layout.addStretch()
        self.popup_checkbox = QCheckBox("Enable Confirmation Popups")
        self.popup_checkbox.setChecked(self.popup_enabled)
        self.popup_checkbox.stateChanged.connect(self.toggle_popup)
        layout.addWidget(self.popup_checkbox)
        self.fps_label = QLabel("FPS: --")
        layout.addWidget(self.fps_label)
        return layout

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        load_action = QAction("Load EDF", self, triggered=self.open_file_dialog)
        toolbar.addAction(load_action)
        channel_action = QAction("Manage Channels", self, triggered=self.open_channel_selection)
        toolbar.addAction(channel_action)
        color_action = QAction("Set Colors", self, triggered=self.open_color_selection)
        toolbar.addAction(color_action)
        highlight_action = QAction("Highlight Section", self, triggered=self.open_highlight_dialog)
        toolbar.addAction(highlight_action)
        clear_highlights_action = QAction("Clear Highlights", self, triggered=self.clear_highlights)
        toolbar.addAction(clear_highlights_action)
        toolbar.addSeparator()
        zoom_in_action = QAction("Zoom In", self, shortcut="Ctrl++", triggered=self.zoom_in)
        toolbar.addAction(zoom_in_action)
        zoom_out_action = QAction("Zoom Out", self, shortcut="Ctrl+-", triggered=self.zoom_out)
        toolbar.addAction(zoom_out_action)
        reset_action = QAction("Reset View", self, shortcut="Ctrl+0", triggered=self.reset_view)
        toolbar.addAction(reset_action)
        toolbar.addSeparator()
        prev_action = QAction("Previous Section", self, shortcut="G", triggered=self.prev_focus)
        toolbar.addAction(prev_action)
        next_action = QAction("Next Section", self, shortcut="H", triggered=self.next_focus)
        toolbar.addAction(next_action)
        auto_action = QAction("Toggle Auto", self, shortcut="Space", triggered=self.toggle_auto_move)
        toolbar.addAction(auto_action)

    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready - Load an EDF file.")
        self.status_bar.addPermanentWidget(self.status_label)

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EDF File", "", "EDF Files (*.edf *.bdf)")
        if file_path:
            self.load_edf_file(file_path)

    def open_channel_selection(self):
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        dialog = ChannelSelectionDialog(self.raw, self)
        if dialog.exec():
            self.channel_indices = dialog.get_selected_channels()
            self.total_channels = len(self.channel_indices)
            self.channel_offset = 0
            self.channel_colors = {self.raw.ch_names[i]: self.channel_colors.get(self.raw.ch_names[i], QColor('black')) for i in self.channel_indices}
            self.section_highlights = [h for h in self.section_highlights if h[0] in [self.raw.ch_names[i] for i in self.channel_indices]]
            self._validate_and_plot()

    def open_color_selection(self):
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        dialog = ChannelColorDialog(self.raw, self.channel_colors, self)
        if dialog.exec():
            self.channel_colors = dialog.get_channel_colors()
            self._validate_and_plot()

    def open_highlight_dialog(self):
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        dialog = HighlightSectionDialog(self.raw, [self.raw.ch_names[i] for i in self.channel_indices], self)
        if dialog.exec():
            highlight_info = dialog.get_highlight_info()
            if highlight_info:
                self.section_highlights.append(highlight_info)
                self._validate_and_plot()

    def clear_highlights(self):
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        self.section_highlights = []
        self._validate_and_plot()
        self.status_label.setText("All highlights cleared")

    def show_context_menu(self, position):
        if self.raw is None:
            return
        menu = QMenu()
        highlight_action = QAction("Highlight Section", self)
        highlight_action.triggered.connect(self.open_highlight_dialog)
        menu.addAction(highlight_action)
        clear_highlights_action = QAction("Clear Highlights", self)
        clear_highlights_action.triggered.connect(self.clear_highlights)
        menu.addAction(clear_highlights_action)
        menu.exec(self.canvas.mapToGlobal(position))

    def load_edf_file(self, file_path):
        try:
            self.status_label.setText("Loading file...")
            QApplication.processEvents()
            if self.raw is not None:
                self.raw.close()  # Close previous file to free memory
            file_size = Path(file_path).stat().st_size
            preload = file_size < 500 * 1024 * 1024  # Preload if <500MB
            self.raw = mne.io.read_raw_edf(file_path, preload=preload, verbose=False)
            if len(self.raw.ch_names) == 0:
                raise ValueError("The selected file contains no channels.")
            self.total_channels = len(self.raw.ch_names)
            self.channel_indices = list(range(self.total_channels))
            self.channel_colors = {ch: self.channel_colors.get(ch, QColor('black')) for ch in self.raw.ch_names}
            self.section_highlights = []
            self.annotations = mne.Annotations(onset=[], duration=[], description=[])
            self.reset_view()
            self.status_label.setText(f"Loaded: {Path(file_path).name} | Duration: {self.raw.n_times / self.raw.info['sfreq']:.1f}s | Size: {file_size / 1024 / 1024:.1f}MB | Preload: {'Yes' if preload else 'No'}")
        except Exception as e:
            logging.error(f"Error loading file {file_path}: {e}")
            QMessageBox.critical(self, "File Error", f"Failed to load EDF file:\n{e}")
            self.raw = None
            self.channel_indices = []
            self.channel_colors = {}
            self.section_highlights = []
            self.annotations = mne.Annotations(onset=[], duration=[], description=[])
            self._validate_and_plot()
        finally:
            self.update_button_states()

    def _validate_and_plot(self):
        if self.debounce_timer.isActive():
            return
        self.debounce_timer.start(50)  # 50ms debounce
        if self.raw is None or not self.channel_indices:
            self.figure.clear()
            self.canvas.draw()
            self.update_button_states()
            self.update_scrollbars()
            return
        try:
            start_time = time.time()
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.view_duration = np.clip(self.view_duration, self.min_duration, max_time)
            self.view_start_time = np.clip(self.view_start_time, 0, max_time - self.view_duration)
            self.focus_duration = np.clip(self.focus_duration, 0.1, self.view_duration)
            self.focus_start_time = np.clip(self.focus_start_time, 0, max_time - self.focus_duration)
            self.channel_offset = np.clip(self.channel_offset, 0, max(0, self.total_channels - self.visible_channels))
            self.plot_eeg_data()
            self.update_scrollbars()
            self.update_status_bar()
            elapsed = time.time() - start_time
            if elapsed > 0:
                self.plot_fps = int(1.0 / elapsed)
                self.fps_label.setText(f"FPS: {self.plot_fps}")
        except Exception as e:
            logging.error(f"Error in _validate_and_plot: {e}")
            QMessageBox.critical(self, "Plot Error", f"Failed to update plot:\n{e}")

    def plot_eeg_data(self):
        if self.raw is None or not self.channel_indices:
            return
        try:
            view_start = self.view_start_time
            view_end = view_start + self.view_duration
            start_samp = int(view_start * self.raw.info['sfreq'])
            stop_samp = int(view_end * self.raw.info['sfreq'])
            start_samp = max(0, start_samp)
            stop_samp = min(self.raw.n_times, stop_samp)
            if start_samp >= stop_samp:
                return
            end_ch = min(self.channel_offset + self.visible_channels, len(self.channel_indices))
            ch_to_plot_indices = self.channel_indices[self.channel_offset:end_ch]
            ch_names = [self.raw.ch_names[i] for i in ch_to_plot_indices]
            if not ch_to_plot_indices:
                return
            # Dynamic decimation based on maximum points
            n_points = stop_samp - start_samp
            max_points = 10000  # Target maximum points for smooth rendering
            decim = max(1, n_points // max_points)
            data, times = self.raw.get_data(picks=ch_to_plot_indices, start=start_samp, stop=stop_samp, return_times=True)
            if decim > 1:
                data = data[:, ::decim]
                times = times[::decim]
            data = np.where(np.isnan(data), 0, data)  # Handle NaN values
            data *= 1e6 / self.sensitivity  # Scale to µV and apply sensitivity
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            if data.size > 0:
                offset = (np.std(data) or 1) * 15
                tick_locs = [-i * offset for i in range(len(ch_to_plot_indices))]
                for i, (ch_idx, channel_data) in enumerate(zip(ch_to_plot_indices, data)):
                    ch_name = self.raw.ch_names[ch_idx]
                    color = self.channel_colors.get(ch_name, QColor('black')).name()
                    ax.plot(times, channel_data - (i * offset), lw=0.8, color=color)
                ax.set_yticks(tick_locs)
                ax.set_yticklabels(ch_names)
                # Plot general annotations
                for onset, duration, description in zip(self.annotations.onset, self.annotations.duration, self.annotations.description):
                    if onset < view_end and onset + duration > view_start:
                        ax.axvspan(onset, onset + duration, color='green', alpha=0.3)
                        ax.text(onset, ax.get_ylim()[1], description, fontsize=8, verticalalignment='top')
                # Plot channel-specific highlights
                for ch_name, onset, duration, color in self.section_highlights:
                    if onset < view_end and onset + duration > view_start and ch_name in ch_names:
                        ch_idx = ch_names.index(ch_name)
                        y_pos = -ch_idx * offset
                        ax.axvspan(onset, onset + duration, ymin=(y_pos - offset/2)/(tick_locs[0] - offset/2), 
                                   ymax=(y_pos + offset/2)/(tick_locs[0] - offset/2), color=color.name(), alpha=0.4)
                ax.axvspan(self.focus_start_time, self.focus_start_time + self.focus_duration, color='yellow', alpha=0.4, zorder=0)
            ax.set_xlim(view_start, view_end)
            ax.set_xlabel("Time (s)")
            ax.grid(True, which='major', axis='x', linestyle='--', alpha=0.5)
            self.canvas.draw()
        except Exception as e:
            logging.error(f"Error plotting EEG data: {e}")
            QMessageBox.critical(self, "Plot Error", f"Failed to plot EEG data:\n{e}")

    def keyPressEvent(self, event):
        if self.raw is None or self.duration_input.hasFocus() or self.step_input.hasFocus():
            super().keyPressEvent(event)
            return
        try:
            pan_amount = self.view_duration * 0.1
            if event.key() == Qt.Key.Key_Right:
                self.view_start_time += pan_amount
            elif event.key() == Qt.Key.Key_Left:
                self.view_start_time -= pan_amount
            elif event.key() == Qt.Key.Key_Up:
                self.channel_offset = max(0, self.channel_offset - 1)
            elif event.key() == Qt.Key.Key_Down:
                self.channel_offset = min(max(0, self.total_channels - self.visible_channels), self.channel_offset + 1)
            else:
                super().keyPressEvent(event)
                return
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in keyPressEvent: {e}")
            QMessageBox.critical(self, "Navigation Error", f"Failed to navigate:\n{e}")

    def on_scroll(self, event):
        if self.raw is None or event.inaxes is None:
            return
        try:
            new_duration = self.view_duration / self.zoom_factor if event.button == 'up' else self.view_duration * self.zoom_factor
            self.view_duration = new_duration
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in on_scroll: {e}")
            QMessageBox.critical(self, "Zoom Error", f"Failed to zoom:\n{e}")

    def on_click(self, event):
        if self.raw is None or event.xdata is None:
            return
        try:
            self.focus_start_time = event.xdata - (self.focus_duration / 2.0)
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in on_click: {e}")
            QMessageBox.critical(self, "Click Error", f"Failed to set focus:\n{e}")

    def next_focus(self):
        if self.raw is None or not self.channel_indices:
            return
        try:
            if self.popup_enabled and not self.show_annotation_popup():
                return
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.focus_start_time = min(max_time - self.focus_duration, self.focus_start_time + self.focus_step_time)
            if self.focus_start_time > self.view_start_time + self.view_duration * 0.75:
                self.view_start_time = self.focus_start_time - self.view_duration * 0.75
                self.view_start_time = max(0, min(self.view_start_time, max_time - self.view_duration))
            self._validate_and_plot()
            self.status_label.setText(f"Labelled section at {self.focus_start_time:.1f}s")
        except Exception as e:
            logging.error(f"Error in next_focus: {e}")
            QMessageBox.critical(self, "Navigation Error", f"Failed to move to next section:\n{e}")

    def prev_focus(self):
        if self.raw is None or not self.channel_indices:
            return
        try:
            if self.popup_enabled and not self.show_annotation_popup():
                return
            self.focus_start_time = max(0, self.focus_start_time - self.focus_step_time)
            if self.focus_start_time < self.view_start_time + self.view_duration * 0.25:
                self.view_start_time = self.focus_start_time - self.view_duration * 0.25
                self.view_start_time = max(0, min(self.view_start_time, self.raw.n_times / self.raw.info['sfreq'] - self.view_duration))
            self._validate_and_plot()
            self.status_label.setText(f"Returned to section at {self.focus_start_time:.1f}s")
        except Exception as e:
            logging.error(f"Error in prev_focus: {e}")
            QMessageBox.critical(self, "Navigation Error", f"Failed to move to previous section:\n{e}")

    def toggle_auto_move(self):
        if self.raw is None:
            return
        try:
            if self.is_auto_moving:
                self.stop_auto_move()
            else:
                self.start_auto_move()
        except Exception as e:
            logging.error(f"Error in toggle_auto_move: {e}")
            QMessageBox.critical(self, "Auto Move Error", f"Failed to toggle auto-move:\n{e}")

    def start_auto_move(self):
        try:
            self.is_auto_moving = True
            self.auto_move_timer.start(int(self.focus_step_time * 1000))
            self.auto_button.setText("⏹ Stop Auto")
            self.status_label.setText("Auto-moving focus window...")
        except Exception as e:
            logging.error(f"Error in start_auto_move: {e}")
            QMessageBox.critical(self, "Auto Move Error", f"Failed to start auto-move:\n{e}")

    def stop_auto_move(self):
        try:
            self.is_auto_moving = False
            self.auto_move_timer.stop()
            self.auto_button.setText("▶ Auto (Space)")
            self.status_label.setText("Auto-move stopped")
        except Exception as e:
            logging.error(f"Error in stop_auto_move: {e}")
            QMessageBox.critical(self, "Auto Move Error", f"Failed to stop auto-move:\n{e}")

    def auto_move_focus(self):
        if not self.is_auto_moving or self.raw is None or not self.channel_indices:
            self.stop_auto_move()
            return
        try:
            max_time = self.raw.n_times / self.raw.info['sfreq']
            new_position = self.focus_start_time + self.focus_step_time
            if new_position > max_time - self.focus_duration:
                self.stop_auto_move()
                self.status_label.setText("Reached end of recording")
            else:
                if self.popup_enabled and not self.show_annotation_popup():
                    self.stop_auto_move()
                    return
                self.focus_start_time = new_position
                if self.focus_start_time > self.view_start_time + self.view_duration * 0.75:
                    self.view_start_time = self.focus_start_time - self.view_duration * 0.75
                    self.view_start_time = max(0, min(self.view_start_time, max_time - self.view_duration))
                self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in auto_move_focus: {e}")
            QMessageBox.critical(self, "Auto Move Error", f"Failed to auto-move focus:\n{e}")

    def show_annotation_popup(self):
        if not self.popup_enabled:
            return True
        try:
            label, ok = QInputDialog.getText(self, "Label Section", "Enter label for this section:")
            if ok:
                self.validate_annotations(self.focus_start_time, self.focus_duration, label)
                self.annotations += mne.Annotations(onset=[self.focus_start_time], duration=[self.focus_duration], description=[label])
                return True
            return False
        except Exception as e:
            logging.error(f"Error in show_annotation_popup: {e}")
            QMessageBox.critical(self, "Annotation Error", f"Failed to add annotation:\n{e}")
            return False

    def validate_annotations(self, onset, duration, description):
        """Validate annotations to prevent overlaps and ensure ML compatibility."""
        try:
            for existing_onset, existing_duration in zip(self.annotations.onset, self.annotations.duration):
                if (onset < existing_onset + existing_duration and onset + duration > existing_onset):
                    logging.warning(f"Annotation overlap detected at onset {onset}s")
                    QMessageBox.warning(self, "Annotation Warning", "New annotation overlaps with existing one. Consider adjusting the time range.")
        except Exception as e:
            logging.error(f"Error in validate_annotations: {e}")
            QMessageBox.critical(self, "Annotation Error", f"Failed to validate annotation:\n{e}")

    def set_popup_enabled(self, enabled):
        try:
            self.popup_enabled = enabled
            self.popup_checkbox.blockSignals(True)
            self.popup_checkbox.setChecked(enabled)
            self.popup_checkbox.blockSignals(False)
            self.status_label.setText(f"Popup confirmations {'enabled' if enabled else 'disabled'}")
        except Exception as e:
            logging.error(f"Error in set_popup_enabled: {e}")
            QMessageBox.critical(self, "Popup Error", f"Failed to toggle popup setting:\n{e}")

    def toggle_popup(self, state):
        try:
            self.set_popup_enabled(state == Qt.CheckState.Checked.value)
        except Exception as e:
            logging.error(f"Error in toggle_popup: {e}")
            QMessageBox.critical(self, "Popup Error", f"Failed to toggle popup:\n{e}")

    def save_annotations(self):
        if not self.annotations:
            QMessageBox.information(self, "No Annotations", "There are no annotations to save.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Annotations", "", "Text Files (*.txt)")
        if file_path:
            try:
                self.annotations.save(file_path)
                self.status_label.setText(f"Annotations saved to {file_path}")
            except Exception as e:
                logging.error(f"Error saving annotations: {e}")
                QMessageBox.critical(self, "Save Error", f"Failed to save annotations:\n{e}")

    def load_annotations(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Annotations", "", "Text Files (*.txt)")
        if file_path:
            try:
                self.annotations = mne.read_annotations(file_path)
                self.status_label.setText(f"Annotations loaded from {file_path}")
            except Exception as e:
                logging.error(f"Error loading annotations: {e}")
                QMessageBox.critical(self, "Load Error", f"Failed to load annotations:\n{e}")
                self.annotations = mne.Annotations(onset=[], duration=[], description=[])
            self._validate_and_plot()

    def export_annotations_csv(self):
        if not self.annotations and not self.section_highlights:
            QMessageBox.information(self, "No Annotations", "There are no annotations or highlights to export.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Annotations to CSV", "", "CSV Files (*.csv)")
        if file_path:
            try:
                import pandas as pd
                annotation_data = {
                    'onset': self.annotations.onset,
                    'duration': self.annotations.duration,
                    'description': self.annotations.description
                }
                highlight_data = {
                    'channel': [h[0] for h in self.section_highlights],
                    'onset': [h[1] for h in self.section_highlights],
                    'duration': [h[2] for h in self.section_highlights],
                    'color': [h[3].name() for h in self.section_highlights]
                }
                df_annotations = pd.DataFrame(annotation_data)
                df_highlights = pd.DataFrame(highlight_data)
                df = pd.concat([df_annotations, df_highlights], axis=1, ignore_index=True)
                df.to_csv(file_path, index=False)
                self.status_label.setText(f"Annotations and highlights exported to {file_path}")
            except Exception as e:
                logging.error(f"Error exporting annotations: {e}")
                QMessageBox.critical(self, "Export Error", f"Failed to export annotations:\n{e}")

    def predict_artifacts(self):
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        try:
            # Placeholder for ML-based artifact detection
            # Example: model = load_pytorch_model()
            # data = self.raw.get_data()
            # predictions = model.predict(data)
            # for onset, duration, label in predictions:
            #     self.validate_annotations(onset, duration, label)
            #     self.annotations += mne.Annotations(onset=[onset], duration=[duration], description=[label])
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in predict_artifacts: {e}")
            QMessageBox.critical(self, "ML Error", f"Failed to predict artifacts:\n{e}")

    def on_channel_scroll(self, value):
        try:
            self.channel_offset = value
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in on_channel_scroll: {e}")
            QMessageBox.critical(self, "Scroll Error", f"Failed to scroll channels:\n{e}")

    def on_time_scroll(self, value):
        try:
            self.view_start_time = value / 100.0
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in on_time_scroll: {e}")
            QMessageBox.critical(self, "Scroll Error", f"Failed to scroll time:\n{e}")

    def on_channel_selection_changed(self, text):
        if self.raw is None:
            return
        try:
            self.visible_channels = self.total_channels if text == "All" else int(text)
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in on_channel_selection_changed: {e}")
            QMessageBox.critical(self, "Channel Selection Error", f"Failed to update channel selection:\n{e}")

    def update_sensitivity(self, value):
        try:
            self.sensitivity = value * 1e-6
            self.sensitivity_label.setText(f"{value} µV")
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in update_sensitivity: {e}")
            QMessageBox.critical(self, "Sensitivity Error", f"Failed to update sensitivity:\n{e}")

    def update_focus_duration(self):
        if self.raw is None:
            return
        try:
            duration = float(self.duration_input.text())
            max_time = self.raw.n_times / self.raw.info['sfreq']
            if duration <= 0 or duration > max_time:
                QMessageBox.warning(self, "Invalid Input", "Focus duration must be positive and within file duration.")
                return
            self.focus_duration = duration
            self._validate_and_plot()
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric value for focus duration.")
        except Exception as e:
            logging.error(f"Error in update_focus_duration: {e}")
            QMessageBox.critical(self, "Focus Error", f"Failed to update focus duration:\n{e}")

    def update_focus_step(self):
        if self.raw is None:
            return
        try:
            step = float(self.step_input.text())
            if step <= 0:
                QMessageBox.warning(self, "Invalid Input", "Step time must be positive.")
                return
            self.focus_step_time = step
            if self.is_auto_moving:
                self.auto_move_timer.start(int(self.focus_step_time * 1000))
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid numeric value for step time.")
        except Exception as e:
            logging.error(f"Error in update_focus_step: {e}")
            QMessageBox.critical(self, "Step Error", f"Failed to update step time:\n{e}")

    def zoom_in(self):
        self.on_scroll(type('event', (), {'button': 'up', 'inaxes': True})())

    def zoom_out(self):
        self.on_scroll(type('event', (), {'button': 'down', 'inaxes': True})())

    def reset_view(self):
        if self.raw is None:
            return
        try:
            self.view_start_time = 0.0
            self.view_duration = 10.0
            self.focus_start_time = 0.0
            self.focus_duration = 1.0
            self.channel_offset = 0
            self.sensitivity = 50e-6
            self.sensitivity_slider.setValue(int(self.sensitivity * 1e6))
            self._validate_and_plot()
        except Exception as e:
            logging.error(f"Error in reset_view: {e}")
            QMessageBox.critical(self, "Reset Error", f"Failed to reset view:\n{e}")

    def update_button_states(self):
        is_loaded = self.raw is not None and bool(self.channel_indices)
        widgets = [
            self.channel_combo, self.channel_button, self.color_button, self.sensitivity_slider,
            self.duration_input, self.update_duration_button, self.step_input, self.update_step_button,
            self.prev_focus_button, self.next_focus_button, self.auto_button, self.vscroll, self.hscroll
        ]
        for widget in widgets:
            if widget:
                widget.setEnabled(bool(is_loaded))

    def update_scrollbars(self):
        if self.raw is None or not self.channel_indices:
            self.hscroll.setEnabled(False)
            self.vscroll.setEnabled(False)
            return
        try:
            self.hscroll.blockSignals(True)
            h_max = int((self.raw.n_times / self.raw.info['sfreq'] - self.view_duration) * 100)
            self.hscroll.setRange(0, max(0, h_max))
            self.hscroll.setPageStep(int(self.view_duration * 100))
            self.hscroll.setValue(int(self.view_start_time * 100))
            self.hscroll.setEnabled(bool(self.raw.n_times / self.raw.info['sfreq'] > self.view_duration))
            self.hscroll.blockSignals(False)
            self.vscroll.blockSignals(True)
            max_offset = max(0, self.total_channels - self.visible_channels)
            self.vscroll.setRange(0, max_offset)
            self.vscroll.setPageStep(self.visible_channels)
            self.vscroll.setValue(self.channel_offset)
            self.vscroll.setEnabled(bool(max_offset > 0))
            self.vscroll.blockSignals(False)
        except Exception as e:
            logging.error(f"Error in update_scrollbars: {e}")
            QMessageBox.critical(self, "Scrollbar Error", f"Failed to update scrollbars:\n{e}")

    def update_status_bar(self):
        if self.raw is None:
            self.status_label.setText("Ready - Load an EDF file.")
        else:
            try:
                file_size = Path(self.raw.filenames[0]).stat().st_size / 1024 / 1024
                preload = hasattr(self.raw, '_data')
                status = (f"File: {Path(self.raw.filenames[0]).name} | "
                          f"Duration: {self.raw.n_times / self.raw.info['sfreq']:.1f}s | "
                          f"View: {self.view_start_time:.1f}s - {self.view_start_time + self.view_duration:.1f}s | "
                          f"Channels: {self.total_channels} | "
                          f"Sensitivity: {self.sensitivity * 1e6:.0f} µV | "
                          f"Size: {file_size:.1f}MB | Preload: {'Yes' if preload else 'No'}")
                self.status_label.setText(status)
            except Exception as e:
                logging.error(f"Error in update_status_bar: {e}")
                QMessageBox.critical(self, "Status Error", f"Failed to update status bar:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = EDFViewer()
    viewer.show()
    sys.exit(app.exec())