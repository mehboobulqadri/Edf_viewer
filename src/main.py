import sys
import mne
import numpy as np
import pandas as pd
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QDoubleValidator, QFont, QKeySequence, QAction, QColor
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMenu,
    QPushButton, QFileDialog, QLineEdit, QLabel, QScrollBar, QStatusBar,
    QComboBox, QMessageBox, QDialog, QListWidget, QListWidgetItem,
    QInputDialog, QSlider, QColorDialog
)
import time
import logging
from pathlib import Path
from typing import List, Tuple

# Optimize Matplotlib for performance
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 1.0
mpl.rcParams['agg.path.chunksize'] = 10000
mpl.rcParams['font.size'] = 8
mpl.rcParams['figure.autolayout'] = True

# Logging setup
logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='edf_viewer_errors.log')

class HighlightSectionDialog(QDialog):
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
        self.duration_input.setValidator(QDoubleValidator(0.0, self.max_time, 2))
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
            if start < 0 or start + duration > self.max_time or duration < 0:
                QMessageBox.warning(self, "Invalid Input", "Start time or duration is out of bounds.")
                return None
            return (self.channel_combo.currentText(), start, duration, self.selected_color)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values.")
            return None

class AnnotationManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Annotations and Highlights")
        self.resize(600, 400)
        main_layout = QVBoxLayout(self)

        self.annotation_list = QListWidget()
        self.annotation_list.setSelectionMode(QListWidget.ExtendedSelection)
        main_layout.addWidget(QLabel("General Annotations:"))
        main_layout.addWidget(self.annotation_list)

        self.highlight_list = QListWidget()
        self.highlight_list.setSelectionMode(QListWidget.ExtendedSelection)
        main_layout.addWidget(QLabel("Channel-Specific Highlights:"))
        main_layout.addWidget(self.highlight_list)

        button_layout = QHBoxLayout()
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.clicked.connect(self.remove_selected)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        main_layout.addLayout(button_layout)

        self.load_annotations()

    def load_annotations(self):
        self.annotation_list.clear()
        for i, (onset, duration, description) in enumerate(zip(self.parent().annotations.onset, self.parent().annotations.duration, self.parent().annotations.description)):
            item = QListWidgetItem(f"Annotation {i}: onset={onset:.2f}s, duration={duration:.2f}s, description={description}")
            item.setData(Qt.ItemDataRole.UserRole, ('annotation', i))
            self.annotation_list.addItem(item)

        self.highlight_list.clear()
        for i, (ch_name, onset, duration, color) in enumerate(self.parent().section_highlights):
            item = QListWidgetItem(f"Highlight {i}: channel={ch_name}, onset={onset:.2f}s, duration={duration:.2f}s")
            item.setData(Qt.ItemDataRole.UserRole, ('highlight', i))
            self.highlight_list.addItem(item)

    def remove_selected(self):
        selected_annotations = [item.data(Qt.ItemDataRole.UserRole) for item in self.annotation_list.selectedItems()]
        selected_highlights = [item.data(Qt.ItemDataRole.UserRole) for item in self.highlight_list.selectedItems()]

        if selected_annotations:
            indices = [idx for _, idx in selected_annotations]
            mask = np.ones(len(self.parent().annotations), dtype=bool)
            mask[indices] = False
            self.parent().annotations = mne.Annotations(
                onset=self.parent().annotations.onset[mask],
                duration=self.parent().annotations.duration[mask],
                description=[self.parent().annotations.description[i] for i in range(len(mask)) if mask[i]]
            )

        if selected_highlights:
            indices = [idx for _, idx in selected_highlights]
            self.parent().section_highlights = [h for i, h in enumerate(self.parent().section_highlights) if i not in indices]

        self.load_annotations()

class EDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clinical EDF Viewer")
        self.setGeometry(100, 100, 1400, 900)

        self.raw = None
        self.view_start_time = 0.0
        self.view_duration = 10.0
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
        self.sensitivity = 50e-6
        self.annotations = mne.Annotations(onset=[], duration=[], description=[])
        self.section_highlights: List[Tuple[str, float, float, QColor]] = []
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self._validate_and_plot)

        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_status_bar()
        self.update_button_states()

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        control_layout = self.create_control_panel()
        focus_layout = self.create_focus_panel()
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
        main_layout.addWidget(plot_container, 1)
        main_layout.addWidget(self.hscroll)
        self.setCentralWidget(main_widget)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def setup_menus(self):
        self.file_menu = self.menuBar().addMenu("File")
        save_ann_action = QAction("Save Annotations", self)
        save_ann_action.triggered.connect(self.save_annotations)
        self.file_menu.addAction(save_ann_action)
        load_ann_action = QAction("Load Annotations", self)
        load_ann_action.triggered.connect(self.load_annotations)
        self.file_menu.addAction(load_ann_action)
        load_csv_action = QAction("Load CSV Annotations", self)
        load_csv_action.triggered.connect(self.load_csv_annotations)
        self.file_menu.addAction(load_csv_action)
        save_csv_action = QAction("Export Annotations to CSV", self)
        save_csv_action.triggered.connect(self.export_annotations_csv)
        self.file_menu.addAction(save_csv_action)
        clear_highlights_action = QAction("Clear Highlights", self)
        clear_highlights_action.triggered.connect(self.clear_highlights)
        self.file_menu.addAction(clear_highlights_action)
        manage_ann_action = QAction("Manage Annotations", self)
        manage_ann_action.triggered.connect(self.open_annotation_manager)
        self.file_menu.addAction(manage_ann_action)

        self.tools_menu = self.menuBar().addMenu("Tools")
        self.popup_action = QAction("Enable Confirmation Popups", self, checkable=True)
        self.popup_action.setChecked(self.popup_enabled)
        self.popup_action.triggered.connect(self.toggle_popup_action)
        self.tools_menu.addAction(self.popup_action)

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
        self.sensitivity_slider.setRange(10, 200)
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

    def setup_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
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
        self.fps_label = QLabel("FPS: --")
        self.status_bar.addPermanentWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.fps_label)

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

    def open_annotation_manager(self):
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        dialog = AnnotationManagerDialog(self)
        if dialog.exec():
            self._validate_and_plot()

    def load_edf_file(self, file_path):
        try:
            self.status_label.setText("Loading file...")
            QApplication.processEvents()
            if self.raw is not None:
                self.raw.close()
            file_size = Path(file_path).stat().st_size
            preload = file_size < 500 * 1024 * 1024
            self.raw = mne.io.read_raw_edf(file_path, preload=preload, verbose=False)
            if len(self.raw.ch_names) == 0:
                raise ValueError("No channels in file.")
            self.total_channels = len(self.raw.ch_names)
            self.channel_indices = list(range(self.total_channels))
            self.channel_colors = {ch: self.channel_colors.get(ch, QColor('black')) for ch in self.raw.ch_names}
            self.section_highlights = []
            self.annotations = mne.Annotations(onset=[], duration=[], description=[])
            self.reset_view()
            self.status_label.setText(f"Loaded: {Path(file_path).name}")
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
        self.debounce_timer.start(50)
        if self.raw is None or not self.channel_indices:
            self.figure.clear()
            self.canvas.draw()
            self.update_button_states()
            self.update_scrollbars()
            return
        try:
            start_time = time.time()
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.view_duration = np.clip(self.view_duration, 0.1, max_time)
            self.view_start_time = np.clip(self.view_start_time, 0, max_time - self.view_duration)
            self.focus_duration = np.clip(self.focus_duration, 0.1, self.view_duration)
            self.focus_start_time = np.clip(self.focus_start_time, 0, max_time - self.focus_duration)
            self.channel_offset = np.clip(self.channel_offset, 0, max(0, self.total_channels - self.visible_channels))
            self.plot_eeg_data()
            self.update_scrollbars()
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
            n_points = stop_samp - start_samp
            decim = max(1, n_points // 10000)
            data, times = self.raw.get_data(picks=ch_to_plot_indices, start=start_samp, stop=stop_samp, return_times=True)
            if decim > 1:
                data = data[:, ::decim]
                times = times[::decim]
            data = np.where(np.isnan(data), 0, data) * (1e6 / self.sensitivity)
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
                y_min, y_max = ax.get_ylim()
                for onset, duration, description in zip(self.annotations.onset, self.annotations.duration, self.annotations.description):
                    if onset < view_end and onset + duration > view_start:
                        if duration == 0:
                            ax.axvline(onset, color='green', linestyle='--', alpha=0.6)
                        else:
                            ax.axvspan(onset, onset + duration, color='green', alpha=0.3)
                for ch_name, onset, duration, color in self.section_highlights:
                    if onset < view_end and onset + duration > view_start and ch_name in ch_names:
                        ch_idx = ch_names.index(ch_name)
                        y_center = -ch_idx * offset
                        delta = offset / 2
                        ymin_data = y_center - delta
                        ymax_data = y_center + delta
                        ymin = (ymin_data - y_min) / (y_max - y_min)
                        ymax = (ymax_data - y_min) / (y_max - y_min)
                        if duration == 0:
                            ax.axvline(onset, ymin=ymin, ymax=ymax, color=color.name(), linestyle='--', alpha=0.6)
                        else:
                            ax.axvspan(onset, onset + duration, ymin=ymin, ymax=ymax, color=color.name(), alpha=0.4)
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

    def on_scroll(self, event):
        if self.raw is None or event.inaxes is None:
            return
        new_duration = self.view_duration / self.zoom_factor if event.button == 'up' else self.view_duration * self.zoom_factor
        self.view_duration = new_duration
        self._validate_and_plot()

    def on_click(self, event):
        if self.raw is None or event.xdata is None:
            return
        self.focus_start_time = event.xdata - (self.focus_duration / 2.0)
        self._validate_and_plot()

    def next_focus(self):
        if self.raw is None or not self.channel_indices:
            return
        if self.popup_enabled and not self.show_annotation_popup():
            return
        max_time = self.raw.n_times / self.raw.info['sfreq']
        self.focus_start_time = min(max_time - self.focus_duration, self.focus_start_time + self.focus_step_time)
        if self.focus_start_time > self.view_start_time + self.view_duration * 0.75:
            self.view_start_time = self.focus_start_time - self.view_duration * 0.75
        self._validate_and_plot()
        self.status_label.setText(f"Labelled section at {self.focus_start_time:.1f}s")

    def prev_focus(self):
        if self.raw is None or not self.channel_indices:
            return
        if self.popup_enabled and not self.show_annotation_popup():
            return
        self.focus_start_time = max(0, self.focus_start_time - self.focus_step_time)
        if self.focus_start_time < self.view_start_time + self.view_duration * 0.25:
            self.view_start_time = self.focus_start_time - self.view_duration * 0.25
        self._validate_and_plot()
        self.status_label.setText(f"Returned to section at {self.focus_start_time:.1f}s")

    def toggle_auto_move(self):
        if self.raw is None:
            return
        if self.is_auto_moving:
            self.stop_auto_move()
        else:
            self.start_auto_move()

    def start_auto_move(self):
        self.is_auto_moving = True
        self.auto_move_timer.start(int(self.focus_step_time * 1000))
        self.status_label.setText("Auto-moving focus window...")

    def stop_auto_move(self):
        self.is_auto_moving = False
        self.auto_move_timer.stop()
        self.status_label.setText("Auto-move stopped")

    def auto_move_focus(self):
        if not self.is_auto_moving or self.raw is None or not self.channel_indices:
            self.stop_auto_move()
            return
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
            self._validate_and_plot()

    def show_annotation_popup(self):
        if not self.popup_enabled:
            return True
        label, ok = QInputDialog.getText(self, "Label Section", "Enter label for this section:")
        if ok:
            if self.validate_annotations(self.focus_start_time, self.focus_duration, label):
                self.annotations += mne.Annotations(onset=[self.focus_start_time], duration=[self.focus_duration], description=[label])
                return True
            return False
        return False

    def validate_annotations(self, onset, duration, description):
        for existing_onset, existing_duration in zip(self.annotations.onset, self.annotations.duration):
            if (onset < existing_onset + existing_duration and onset + duration > existing_onset):
                QMessageBox.warning(self, "Annotation Overlap", "Cannot add annotation: overlaps with existing annotation.")
                return False
        return True

    def toggle_popup_action(self, checked):
        self.popup_enabled = checked
        self.popup_action.setChecked(checked)
        self.status_label.setText(f"Popup confirmations {'enabled' if checked else 'disabled'}")

    def save_annotations(self):
        if not self.annotations:
            QMessageBox.information(self, "No Annotations", "No annotations to save.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Annotations", "", "Text Files (*.txt)")
        if file_path:
            self.annotations.save(file_path)
            self.status_label.setText(f"Annotations saved to {file_path}")

    def load_annotations(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Annotations", "", "Text Files (*.txt)")
        if file_path:
            self.annotations = mne.read_annotations(file_path)
            self.status_label.setText(f"Annotations loaded from {file_path}")
            self._validate_and_plot()

    def export_annotations_csv(self):
        if not self.annotations and not self.section_highlights:
            QMessageBox.information(self, "No Annotations", "No annotations or highlights to export.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Annotations to CSV", "", "CSV Files (*.csv)")
        if file_path:
            annotation_data = {
                'onset': self.annotations.onset,
                'duration': self.annotations.duration,
                'description': self.annotations.description,
                'channel': [''] * len(self.annotations.onset)
            }
            highlight_data = {
                'onset': [h[1] for h in self.section_highlights],
                'duration': [h[2] for h in self.section_highlights],
                'description': ['Highlight'] * len(self.section_highlights),
                'channel': [h[0] for h in self.section_highlights]
            }
            df = pd.concat([pd.DataFrame(annotation_data), pd.DataFrame(highlight_data)], ignore_index=True)
            df.to_csv(file_path, index=False)
            self.status_label.setText(f"Annotations exported to {file_path}")

    def load_csv_annotations(self):
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Load CSV Annotations", "", "CSV Files (*.csv)")
        if file_path:
            df = pd.read_csv(file_path)
            df = df.dropna(subset=['onset', 'description'])
            max_time = self.raw.n_times / self.raw.info['sfreq']
            onsets = pd.to_numeric(df['onset'], errors='coerce').dropna()
            durations = pd.to_numeric(df.get('duration', 0), errors='coerce').fillna(0)
            descriptions = df['description'].astype(str)
            channels = df.get('channel', pd.Series(None, index=onsets.index))
            valid_mask = (onsets >= 0) & (onsets + durations <= max_time) & (durations >= 0)
            onsets, durations, descriptions, channels = [s[valid_mask] for s in [onsets, durations, descriptions, channels]]
            general_mask = channels.isna()
            self.annotations += mne.Annotations(
                onset=onsets[general_mask].values,
                duration=durations[general_mask].values,
                description=descriptions[general_mask].values
            )
            channel_highlights = [
                (ch, onset, duration, QColor('blue'))
                for ch, onset, duration in zip(channels.dropna(), onsets[~general_mask], durations[~general_mask])
                if ch in self.raw.ch_names
            ]
            self.section_highlights.extend(channel_highlights)
            self.status_label.setText(f"Loaded {len(onsets)} annotations from {Path(file_path).name}")
            self._validate_and_plot()

    def on_channel_scroll(self, value):
        self.channel_offset = value
        self._validate_and_plot()

    def on_time_scroll(self, value):
        self.view_start_time = value / 100.0
        self._validate_and_plot()

    def on_channel_selection_changed(self, text):
        if self.raw is None:
            return
        self.visible_channels = self.total_channels if text == "All" else int(text)
        self._validate_and_plot()

    def update_sensitivity(self, value):
        self.sensitivity = value * 1e-6
        self.sensitivity_label.setText(f"{value} µV")
        self._validate_and_plot()

    def update_focus_duration(self):
        if self.raw is None:
            return
        duration = float(self.duration_input.text())
        max_time = self.raw.n_times / self.raw.info['sfreq']
        if duration <= 0 or duration > max_time:
            QMessageBox.warning(self, "Invalid Input", "Focus duration must be positive and within file duration.")
            return
        self.focus_duration = duration
        self._validate_and_plot()

    def update_focus_step(self):
        if self.raw is None:
            return
        step = float(self.step_input.text())
        if step <= 0:
            QMessageBox.warning(self, "Invalid Input", "Step time must be positive.")
            return
        self.focus_step_time = step
        if self.is_auto_moving:
            self.auto_move_timer.start(int(self.focus_step_time * 1000))

    def zoom_in(self):
        self.on_scroll(type('event', (), {'button': 'up', 'inaxes': True})())

    def zoom_out(self):
        self.on_scroll(type('event', (), {'button': 'down', 'inaxes': True})())

    def reset_view(self):
        if self.raw is None:
            return
        self.view_start_time = 0.0
        self.view_duration = 10.0
        self.focus_start_time = 0.0
        self.focus_duration = 1.0
        self.channel_offset = 0
        self.sensitivity = 50e-6
        self.sensitivity_slider.setValue(int(self.sensitivity * 1e6))
        self._validate_and_plot()

    def update_button_states(self):
        is_loaded = self.raw is not None and bool(self.channel_indices)
        for widget in [self.channel_combo, self.channel_button, self.color_button, self.sensitivity_slider,
                       self.duration_input, self.update_duration_button, self.step_input, self.update_step_button,
                       self.vscroll, self.hscroll]:
            if widget:
                widget.setEnabled(is_loaded)

    def update_scrollbars(self):
        if self.raw is None or not self.channel_indices:
            self.hscroll.setEnabled(False)
            self.vscroll.setEnabled(False)
            return
        h_max = int((self.raw.n_times / self.raw.info['sfreq'] - self.view_duration) * 100)
        self.hscroll.setRange(0, max(0, h_max))
        self.hscroll.setPageStep(int(self.view_duration * 100))
        self.hscroll.setValue(int(self.view_start_time * 100))
        self.hscroll.setEnabled(h_max > 0)
        max_offset = max(0, self.total_channels - self.visible_channels)
        self.vscroll.setRange(0, max_offset)
        self.vscroll.setPageStep(self.visible_channels)
        self.vscroll.setValue(self.channel_offset)
        self.vscroll.setEnabled(max_offset > 0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = EDFViewer()
    viewer.show()
    sys.exit(app.exec())