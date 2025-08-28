import sys
import mne
import numpy as np
import pandas as pd
import pyqtgraph as pg
import psutil
import time
import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from collections import deque
from dataclasses import dataclass, asdict

# Optional performance dependencies
try:
    import numba
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QPointF
from PyQt6.QtGui import QAction, QColor, QKeySequence, QDoubleValidator, QFont, QCursor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QFileDialog, QLineEdit, QLabel, QScrollBar, QStatusBar,
    QComboBox, QMessageBox, QDialog, QListWidget, QListWidgetItem,
    QToolBar, QGroupBox, QTextEdit, QDoubleSpinBox, QButtonGroup, QRadioButton,
    QColorDialog, QMenuBar, QSplitter, QCheckBox,
    QMenu, QInputDialog, QGridLayout, QGraphicsRectItem
)

# Enhanced PyQtGraph configuration for maximum performance
pg.setConfigOptions(
    useOpenGL=True,
    enableExperimental=True,
    antialias=True,
    background='#181c20',
    foreground='#e0e6ed',
    imageAxisOrder='row-major',
    crashWarning=False,
    useNumba=NUMBA_AVAILABLE,
    leftButtonPan=False,
    segmentedLineMode='on'
)

# High-performance settings
PERF_CONFIG = {
    'max_points_per_curve': 10000,
    'downsample_threshold': 50000,
    'cache_size_mb': 256,
    'render_threads': min(4, psutil.cpu_count()),
    'chunk_size': 1000000,
    'prefetch_chunks': 3,
    'gpu_memory_limit': 512,  # MB
    'target_fps': 60
}

@dataclass
class Annotation:
    start_time: float
    duration: float
    description: str
    color: str
    timestamp: str
    channel: Optional[str] = None
    notes: str = ""

@dataclass
class SessionState:
    file_path: str
    view_start_time: float
    view_duration: float
    focus_start_time: float
    focus_duration: float
    channel_indices: List[int]
    channel_colors: Dict[str, str]
    channel_offset: int
    visible_channels: int
    sensitivity: float
    annotations: List[Dict[str, Any]]
    timestamp: str

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='edf_viewer_errors.log'
)

class DataLoaderThread(QThread):
    data_loaded = pyqtSignal(object)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.progress_updated.emit(25)
            raw = mne.io.read_raw_edf(self.file_path, preload=True, verbose=False)
            self.progress_updated.emit(75)
            raw.filter(l_freq=0.1, h_freq=None, verbose=False)
            self.progress_updated.emit(100)
            self.data_loaded.emit(raw)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ChannelSelectionDialog(QDialog):
    def __init__(self, raw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Selection")
        self.resize(600, 800)
        self.raw = raw
        self.selected_channels = parent.channel_indices if hasattr(parent, 'channel_indices') else list(range(len(raw.ch_names)))
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Vertical)
        available_group = QGroupBox("Available Channels")
        available_layout = QVBoxLayout()
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        available_layout.addWidget(self.available_list)
        available_group.setLayout(available_layout)
        selected_group = QGroupBox("Selected Channels (Drag to reorder)")
        selected_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.selected_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
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
        self.add_all_button = QPushButton("Add All")
        self.add_button = QPushButton("→ Add")
        self.remove_button = QPushButton("← Remove")
        self.remove_all_button = QPushButton("Remove All")
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self.add_all_button)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.remove_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        self.add_all_button.clicked.connect(self.add_all_channels)
        self.add_button.clicked.connect(self.add_channels)
        self.remove_button.clicked.connect(self.remove_channels)
        self.remove_all_button.clicked.connect(self.remove_all_channels)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        main_layout.addWidget(splitter)
        main_layout.addLayout(button_layout)
    
    def add_all_channels(self):
        while self.available_list.count() > 0:
            self.selected_list.addItem(self.available_list.takeItem(0))
    
    def add_channels(self):
        for item in self.available_list.selectedItems():
            self.selected_list.addItem(self.available_list.takeItem(self.available_list.row(item)))
    
    def remove_channels(self):
        for item in self.selected_list.selectedItems():
            self.available_list.addItem(self.selected_list.takeItem(self.selected_list.row(item)))
    
    def remove_all_channels(self):
        while self.selected_list.count() > 0:
            self.available_list.addItem(self.selected_list.takeItem(0))
    
    def get_selected_channels(self):
        return [self.selected_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.selected_list.count())]
    
    def accept(self):
        if self.selected_list.count() == 0:
            QMessageBox.warning(self, "Invalid Selection", "You must select at least one channel.")
            return
        super().accept()

class ChannelColorDialog(QDialog):
    def __init__(self, raw, channel_colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Channel Colors")
        self.resize(400, 600)
        self.raw = raw
        self.channel_colors = channel_colors.copy()
        layout = QVBoxLayout(self)
        self.color_list = QListWidget()
        self.color_list.setAlternatingRowColors(True)
        for ch_name in self.raw.ch_names:
            color = self.channel_colors.get(ch_name, '#e0e6ed')
            item = QListWidgetItem(ch_name)
            item.setForeground(QColor(color))
            self.color_list.addItem(item)
        self.color_list.itemDoubleClicked.connect(self.change_color)
        layout.addWidget(QLabel("Double-click a channel to change its color."))
        layout.addWidget(self.color_list)
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
    
    def change_color(self, item):
        ch_name = item.text()
        current_color = self.channel_colors.get(ch_name, '#e0e6ed')
        color = QColorDialog.getColor(QColor(current_color), self, f"Select Color for {ch_name}")
        if color.isValid():
            self.channel_colors[ch_name] = color.name()
            item.setForeground(color)
    
    def get_channel_colors(self):
        return self.channel_colors

class ScreenshotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Screenshot Options")
        self.resize(450, 600)
        
        main_layout = QVBoxLayout(self)
        
        # File settings
        file_group = QGroupBox("File Settings")
        file_layout = QVBoxLayout()
        
        file_layout.addWidget(QLabel("Filename:"))
        self.filename_input = QLineEdit("eeg_screenshot")
        file_layout.addWidget(self.filename_input)
        
        file_layout.addWidget(QLabel("Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "PDF", "SVG"])
        file_layout.addWidget(self.format_combo)
        
        file_layout.addWidget(QLabel("Quality (for JPEG):"))
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(95)
        self.quality_label = QLabel("95%")
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        file_layout.addLayout(quality_layout)
        self.quality_slider.valueChanged.connect(lambda v: self.quality_label.setText(f"{v}%"))
        
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Size and resolution
        size_group = QGroupBox("Size & Resolution")
        size_layout = QVBoxLayout()
        
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "Current View", "1920x1080 (HD)", "2560x1440 (QHD)", 
            "3840x2160 (4K)", "Custom"
        ])
        size_layout.addWidget(QLabel("Size:"))
        size_layout.addWidget(self.size_combo)
        
        custom_size_layout = QHBoxLayout()
        custom_size_layout.addWidget(QLabel("Width:"))
        self.width_input = QLineEdit("1920")
        self.width_input.setValidator(QDoubleValidator(100, 10000, 0))
        custom_size_layout.addWidget(self.width_input)
        custom_size_layout.addWidget(QLabel("Height:"))
        self.height_input = QLineEdit("1080")
        self.height_input.setValidator(QDoubleValidator(100, 10000, 0))
        custom_size_layout.addWidget(self.height_input)
        size_layout.addLayout(custom_size_layout)
        
        size_layout.addWidget(QLabel("DPI:"))
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["72", "150", "300", "600"])
        self.dpi_combo.setCurrentText("150")
        size_layout.addWidget(self.dpi_combo)
        
        size_group.setLayout(size_layout)
        main_layout.addWidget(size_group)
        
        # Grid and appearance
        appearance_group = QGroupBox("Grid & Appearance")
        appearance_layout = QVBoxLayout()
        
        self.show_grid = QCheckBox("Show Grid")
        self.show_grid.setChecked(True)
        appearance_layout.addWidget(self.show_grid)
        
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("Grid Style:"), 0, 0)
        self.grid_style = QComboBox()
        self.grid_style.addItems(["Solid", "Dashed", "Dotted"])
        grid_layout.addWidget(self.grid_style, 0, 1)
        
        grid_layout.addWidget(QLabel("Grid Color:"), 1, 0)
        self.grid_color_button = QPushButton("Choose Color")
        self.grid_color = QColor(128, 128, 128, 100)
        self.grid_color_button.setStyleSheet(f"background-color: {self.grid_color.name()}")
        self.grid_color_button.clicked.connect(self.choose_grid_color)
        grid_layout.addWidget(self.grid_color_button, 1, 1)
        
        grid_layout.addWidget(QLabel("Time Grid (s):"), 2, 0)
        self.time_grid_input = QLineEdit("1.0")
        self.time_grid_input.setValidator(QDoubleValidator(0.1, 60.0, 1))
        grid_layout.addWidget(self.time_grid_input, 2, 1)
        
        grid_layout.addWidget(QLabel("Amplitude Grid (µV):"), 3, 0)
        self.amp_grid_input = QLineEdit("50")
        self.amp_grid_input.setValidator(QDoubleValidator(1.0, 1000.0, 1))
        grid_layout.addWidget(self.amp_grid_input, 3, 1)
        
        appearance_layout.addLayout(grid_layout)
        
        self.show_labels = QCheckBox("Show Channel Labels")
        self.show_labels.setChecked(True)
        appearance_layout.addWidget(self.show_labels)
        
        self.show_time_axis = QCheckBox("Show Time Axis")
        self.show_time_axis.setChecked(True)
        appearance_layout.addWidget(self.show_time_axis)
        
        self.show_annotations = QCheckBox("Include Annotations")
        self.show_annotations.setChecked(True)
        appearance_layout.addWidget(self.show_annotations)
        
        appearance_group.setLayout(appearance_layout)
        main_layout.addWidget(appearance_group)
        
        # Transform options
        transform_group = QGroupBox("Transforms")
        transform_layout = QVBoxLayout()
        
        self.invert_colors = QCheckBox("Invert Colors (White Background)")
        transform_layout.addWidget(self.invert_colors)
        
        self.enhance_contrast = QCheckBox("Enhance Contrast")
        transform_layout.addWidget(self.enhance_contrast)
        
        transform_layout.addWidget(QLabel("Brightness:"))
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-50, 50)
        self.brightness_slider.setValue(0)
        self.brightness_label = QLabel("0%")
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(self.brightness_slider)
        brightness_layout.addWidget(self.brightness_label)
        transform_layout.addLayout(brightness_layout)
        self.brightness_slider.valueChanged.connect(lambda v: self.brightness_label.setText(f"{v}%"))
        
        transform_group.setLayout(transform_layout)
        main_layout.addWidget(transform_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.preview_button = QPushButton("Preview")
        self.save_button = QPushButton("Save Screenshot")
        self.cancel_button = QPushButton("Cancel")
        
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.preview_button.clicked.connect(self.preview_screenshot)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.size_combo.currentTextChanged.connect(self.on_size_changed)
        
        self.on_size_changed("Current View")
    
    def choose_grid_color(self):
        color = QColorDialog.getColor(self.grid_color, self, "Select Grid Color")
        if color.isValid():
            self.grid_color = color
            self.grid_color_button.setStyleSheet(f"background-color: {color.name()}")
    
    def on_size_changed(self, size_text):
        custom_enabled = size_text == "Custom"
        self.width_input.setEnabled(custom_enabled)
        self.height_input.setEnabled(custom_enabled)
        
        if not custom_enabled:
            if size_text == "1920x1080 (HD)":
                self.width_input.setText("1920")
                self.height_input.setText("1080")
            elif size_text == "2560x1440 (QHD)":
                self.width_input.setText("2560")
                self.height_input.setText("1440")
            elif size_text == "3840x2160 (4K)":
                self.width_input.setText("3840")
                self.height_input.setText("2160")
    
    def preview_screenshot(self):
        # This will be implemented to show a preview
        QMessageBox.information(self, "Preview", "Preview functionality will show the screenshot before saving.")
    
    def get_screenshot_settings(self):
        return {
            'filename': self.filename_input.text(),
            'format': self.format_combo.currentText(),
            'quality': self.quality_slider.value(),
            'size': self.size_combo.currentText(),
            'width': int(float(self.width_input.text())) if self.width_input.text() else 1920,
            'height': int(float(self.height_input.text())) if self.height_input.text() else 1080,
            'dpi': int(self.dpi_combo.currentText()),
            'show_grid': self.show_grid.isChecked(),
            'grid_style': self.grid_style.currentText(),
            'grid_color': self.grid_color,
            'time_grid': float(self.time_grid_input.text()) if self.time_grid_input.text() else 1.0,
            'amp_grid': float(self.amp_grid_input.text()) if self.amp_grid_input.text() else 50.0,
            'show_labels': self.show_labels.isChecked(),
            'show_time_axis': self.show_time_axis.isChecked(),
            'show_annotations': self.show_annotations.isChecked(),
            'invert_colors': self.invert_colors.isChecked(),
            'enhance_contrast': self.enhance_contrast.isChecked(),
            'brightness': self.brightness_slider.value()
        }

class HighlightSectionDialog(QDialog):
    def __init__(self, raw, channel_names, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Highlight Section")
        self.resize(400, 350)
        self.raw = raw
        self.max_time = raw.n_times / raw.info['sfreq'] if raw else 0
        self.channel_names = channel_names

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

        main_layout.addWidget(QLabel("Description (optional):"))
        self.description_input = QLineEdit("Highlight")
        main_layout.addWidget(self.description_input)

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
            description = self.description_input.text().strip() or "Highlight"
            if start < 0 or start + duration > self.max_time or duration < 0:
                QMessageBox.warning(self, "Invalid Input", "Start time or duration is out of bounds.")
                return None
            return (self.channel_combo.currentText(), start, duration, self.selected_color.name(), description)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values.")
            return None

class AnnotationManager:
    def __init__(self, raw=None):
        self.raw = raw
        # initialize as empty mne.Annotations
        self.annotations = mne.Annotations([], [], [])
        self.annotation_colors = []  # Store colors for annotations
        self.section_highlights = []

    def add_annotation(self, start_time, duration, description, color='green'):
        try:
            # Create new Annotations and append
            new_ann = mne.Annotations([start_time], [duration], [description])
            # Combine by constructing a new Annotations concatenating lists (safer)
            onsets = list(self.annotations.onset) + list(new_ann.onset)
            durations = list(self.annotations.duration) + list(new_ann.duration)
            descriptions = list(self.annotations.description) + list(new_ann.description)
            self.annotations = mne.Annotations(onset=onsets, duration=durations, description=descriptions)
            # Store color information separately since MNE doesn't support it
            if not hasattr(self, 'annotation_colors'):
                self.annotation_colors = []
            self.annotation_colors.append(color)
        except Exception:
            # fallback simple approach
            self.annotations += mne.Annotations([start_time], [duration], [description])
            if not hasattr(self, 'annotation_colors'):
                self.annotation_colors = []
            self.annotation_colors.append(color)

    def add_highlight(self, channel, start_time, duration, color, description="Highlight"):
        self.section_highlights.append((channel, start_time, duration, color, description))

    def export_to_csv(self, file_path, viewer_state=None):
        now = datetime.now()
        # Ensure we have colors for all annotations
        if not hasattr(self, 'annotation_colors'):
            self.annotation_colors = ['green'] * len(self.annotations.onset)
        elif len(self.annotation_colors) < len(self.annotations.onset):
            # Pad with default color
            self.annotation_colors.extend(['green'] * (len(self.annotations.onset) - len(self.annotation_colors)))
        
        # System metadata (if viewer_state provided)
        system_data = {}
        if viewer_state:
            system_data = {
                'system_timestamp': now.isoformat(),
                'total_channels': viewer_state.get('total_channels', ''),
                'visible_channels': viewer_state.get('visible_channels', ''),
                'sensitivity': viewer_state.get('sensitivity', ''),
                'view_duration': viewer_state.get('view_duration', ''),
                'view_start_time': viewer_state.get('view_start_time', ''),
                'focus_duration': viewer_state.get('focus_duration', ''),
                'channel_offset': viewer_state.get('channel_offset', ''),
                'file_path': viewer_state.get('file_path', ''),
            }
        
        annotation_data = {
            'type': ['annotation'] * len(self.annotations.onset),
            'onset': list(self.annotations.onset),
            'duration': list(self.annotations.duration),
            'description': list(self.annotations.description),
            'channel': [''] * len(self.annotations.onset),
            'color': self.annotation_colors[:len(self.annotations.onset)],
            'exported_at': [now.isoformat()] * len(self.annotations.onset)
        }
        
        highlight_data = {
            'type': ['highlight'] * len(self.section_highlights),
            'onset': [h[1] for h in self.section_highlights],
            'duration': [h[2] for h in self.section_highlights],
            'description': [h[4] if len(h) > 4 else 'Highlight' for h in self.section_highlights],
            'channel': [h[0] for h in self.section_highlights],
            'color': [h[3] for h in self.section_highlights],
            'exported_at': [now.isoformat()] * len(self.section_highlights)
        }
        
        # Add system metadata to each row
        for key, value in system_data.items():
            annotation_data[key] = [value] * len(self.annotations.onset) if len(self.annotations.onset) > 0 else []
            highlight_data[key] = [value] * len(self.section_highlights) if len(self.section_highlights) > 0 else []
        
        df = pd.concat([pd.DataFrame(annotation_data), pd.DataFrame(highlight_data)], ignore_index=True)
        
        # Sort by onset time for better organization
        if not df.empty:
            df = df.sort_values('onset')
        
        df.to_csv(file_path, index=False, float_format='%.6f')

    def remove_annotation_at(self, idx):
        onsets = list(self.annotations.onset)
        durations = list(self.annotations.duration)
        descriptions = list(self.annotations.description)
        if 0 <= idx < len(onsets):
            del onsets[idx]
            del durations[idx]
            del descriptions[idx]
            self.annotations = mne.Annotations(onset=onsets, duration=durations, description=descriptions)
            # Also remove the corresponding color
            if hasattr(self, 'annotation_colors') and 0 <= idx < len(self.annotation_colors):
                del self.annotation_colors[idx]

    def remove_highlight_at(self, idx):
        if 0 <= idx < len(self.section_highlights):
            del self.section_highlights[idx]

    def edit_annotation_at(self, idx, new_description):
        onsets = list(self.annotations.onset)
        durations = list(self.annotations.duration)
        descriptions = list(self.annotations.description)
        if 0 <= idx < len(descriptions):
            descriptions[idx] = new_description
            self.annotations = mne.Annotations(onset=onsets, duration=durations, description=descriptions)

class AnnotationDialog(QDialog):
    def __init__(self, raw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Annotation")
        self.resize(400, 300)
        self.raw = raw
        self.max_time = raw.n_times / raw.info['sfreq'] if raw else 0

        main_layout = QVBoxLayout(self)
        
        main_layout.addWidget(QLabel("Start Time (s):"))
        self.start_input = QLineEdit("0.0")
        self.start_input.setValidator(QDoubleValidator(0.0, self.max_time, 2))
        main_layout.addWidget(self.start_input)

        main_layout.addWidget(QLabel("Duration (s):"))
        self.duration_input = QLineEdit("1.0")
        self.duration_input.setValidator(QDoubleValidator(0.0, self.max_time, 2))
        main_layout.addWidget(self.duration_input)

        main_layout.addWidget(QLabel("Description:"))
        self.description_input = QLineEdit("Annotation")
        main_layout.addWidget(self.description_input)

        main_layout.addWidget(QLabel("Color:"))
        self.color_button = QPushButton("Choose Color")
        self.selected_color = QColor('green')
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
        color = QColorDialog.getColor(self.selected_color, self, "Select Annotation Color")
        if color.isValid():
            self.selected_color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()}")

    def get_annotation_info(self):
        try:
            start = float(self.start_input.text())
            duration = float(self.duration_input.text())
            description = self.description_input.text().strip() or "Annotation"
            if start < 0 or start + duration > self.max_time or duration < 0:
                QMessageBox.warning(self, "Invalid Input", "Start time or duration is out of bounds.")
                return None
            return (start, duration, description, self.selected_color.name())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values.")
            return None

class AnnotationManagerDialog(QDialog):
    def __init__(self, annotation_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Annotations and Highlights")
        self.resize(600, 400)
        self.annotation_manager = annotation_manager
        main_layout = QVBoxLayout(self)

        self.annotation_list = QListWidget()
        self.annotation_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        main_layout.addWidget(QLabel("General Annotations:"))
        main_layout.addWidget(self.annotation_list)

        self.highlight_list = QListWidget()
        self.highlight_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
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
        self.highlight_list.clear()
        for i, ann in enumerate(zip(self.annotation_manager.annotations.onset,
                                    self.annotation_manager.annotations.duration,
                                    self.annotation_manager.annotations.description)):
            onset, duration, description = ann
            item = QListWidgetItem(f"Annotation {i}: onset={onset:.2f}s, duration={duration:.2f}s, description={description}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.annotation_list.addItem(item)

        for i, highlight in enumerate(self.annotation_manager.section_highlights):
            if len(highlight) > 4:
                ch_name, onset, duration, color, description = highlight
                item = QListWidgetItem(f"Highlight {i}: {description} - channel={ch_name}, onset={onset:.2f}s, duration={duration:.2f}s")
            else:
                ch_name, onset, duration, color = highlight
                item = QListWidgetItem(f"Highlight {i}: channel={ch_name}, onset={onset:.2f}s, duration={duration:.2f}s")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.highlight_list.addItem(item)

    def remove_selected(self):
        selected_annotations = sorted([item.data(Qt.ItemDataRole.UserRole) for item in self.annotation_list.selectedItems()], reverse=True)
        selected_highlights = sorted([item.data(Qt.ItemDataRole.UserRole) for item in self.highlight_list.selectedItems()], reverse=True)

        for idx in selected_annotations:
            self.annotation_manager.remove_annotation_at(idx)

        for idx in selected_highlights:
            self.annotation_manager.remove_highlight_at(idx)

        self.load_annotations()
        if self.parent() and hasattr(self.parent(), 'perf_manager'):
            self.parent().perf_manager.request_update()

class CustomViewBox(pg.ViewBox):
    dragStart = pyqtSignal(QPointF)
    dragFinish = pyqtSignal(QPointF)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseMode(self.RectMode)

    def mouseDragEvent(self, ev, axis=None):
        if ev.button() != Qt.MouseButton.LeftButton:
            return super().mouseDragEvent(ev, axis)

        pos = self.mapSceneToView(ev.scenePos())

        # FIX: Get view range for boundary checks
        view_range = self.viewRange()[0]
        view_width = view_range[1] - view_range[0]

        # Check if in reordering area (near left edge) or Shift for annotation
        is_reorder_area = pos.x() < view_range[0] + view_width * 0.1
        is_annotation = ev.modifiers() & Qt.KeyboardModifier.ShiftModifier

        if is_reorder_area or is_annotation:
            # Perform custom drag for reordering or annotation
            if ev.isStart():
                self.dragStart.emit(pos)
            elif ev.isFinish():
                self.dragFinish.emit(pos)
            ev.accept()
        else:
            # Allow standard rectangular zoom
            super().mouseDragEvent(ev, axis)

class HighPerformanceDataCache:
    def __init__(self, max_size_mb=PERF_CONFIG['cache_size_mb']):
        self.cache = {}
        self.size_mb = 0
        self.max_size_mb = max_size_mb
        self.access_order = deque()
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key):
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            self.hit_count += 1
            return self.cache[key]
        self.miss_count += 1
        return None
    
    def put(self, key, value):
        value_size_mb = self._estimate_size(value)
        while (self.size_mb + value_size_mb > self.max_size_mb and len(self.cache) > 0):
            oldest = self.access_order.popleft()
            old_value = self.cache.pop(oldest)
            self.size_mb -= self._estimate_size(old_value)
        self.cache[key] = value
        self.size_mb += value_size_mb
        self.access_order.append(key)
    
    def _estimate_size(self, value):
        if isinstance(value, tuple) and len(value) == 2:
            data, times = value
            if hasattr(data, 'nbytes') and hasattr(times, 'nbytes'):
                return (data.nbytes + times.nbytes) / (1024 * 1024)
        return 0.1
    
    def get_hit_rate(self):
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def clear(self):
        self.cache.clear()
        self.access_order.clear()
        self.size_mb = 0
        self.hit_count = 0
        self.miss_count = 0

class HighPerformanceSignalProcessor:
    @staticmethod
    def intelligent_downsample(data, target_points=PERF_CONFIG['max_points_per_curve']):
        if data.size == 0:
            return data, np.array([])
        
        n_points = data.shape[1] if data.ndim > 1 else len(data)
        if n_points <= target_points:
            # indices: simple range
            if data.ndim == 2:
                indices = np.tile(np.arange(n_points), (data.shape[0], 1))
            else:
                indices = np.arange(n_points)
            return data, indices
        
        downsample_factor = max(1, n_points // target_points)
        
        if data.ndim == 2:
            n_channels, n_samples = data.shape
            new_samples = (n_samples + downsample_factor - 1) // downsample_factor
            result = np.zeros((n_channels, new_samples), dtype=data.dtype)
            indices = np.zeros((n_channels, new_samples), dtype=int)
            for j in range(new_samples):
                start_idx = j * downsample_factor
                end_idx = min(start_idx + downsample_factor, n_samples)
                chunk = data[:, start_idx:end_idx]
                # relative index of max abs per channel
                rel_idx = np.argmax(np.abs(chunk), axis=1)
                abs_idx = rel_idx + start_idx
                result[:, j] = chunk[np.arange(n_channels), rel_idx]
                indices[:, j] = abs_idx
            return result, indices
        else:
            ds_indices = np.arange(0, n_points, downsample_factor)
            return data[ds_indices], ds_indices
    
    @staticmethod
    def adaptive_scaling(data, target_range=(-2, 2), percentile=98):
        if data.size == 0:
            return data, 1.0
        try:
            # FIX: Per-channel scaling to handle varying amplitudes
            if data.ndim == 2:
                data_abs = np.abs(data)
                scale_factors = np.percentile(data_abs, percentile, axis=1)
                scale_factors[scale_factors == 0] = 1.0  # Prevent division by zero
                scaled_data = data / scale_factors[:, np.newaxis]
                max_vals = np.percentile(np.abs(scaled_data), 99, axis=1)
                for i in range(data.shape[0]):
                    if max_vals[i] > target_range[1]:
                        scaled_data[i] *= (target_range[1] / max_vals[i])
                return scaled_data, scale_factors
            else:
                data_abs = np.abs(data)
                scale_factor = np.percentile(data_abs, percentile)
                if scale_factor == 0:
                    scale_factor = 1.0
                scaled_data = data / scale_factor
                max_val = np.percentile(np.abs(scaled_data), 99)
                if max_val > target_range[1]:
                    scaled_data *= (target_range[1] / max_val)
                return scaled_data, scale_factor
        except Exception as e:
            logging.error(f"Adaptive scaling error: {e}")
            return data, 1.0

class PerformanceManager:
    def __init__(self, viewer):
        self.viewer = viewer
        self.fps = 0.0
        self.memory_mb = 0.0
        self.render_time_ms = 0.0
        self.cache_hit_rate = 0.0
        self.last_time = time.perf_counter()  # Use perf_counter for consistency
        self.frame_count = 0
        self.render_quality = 1.0
        self.target_fps = PERF_CONFIG['target_fps']
        self.min_frame_time = 1.0 / self.target_fps
        self.last_update = 0
        self.pending_update = False
        self.frame_times = deque(maxlen=60)
        self.last_render_start = 0
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(500)  # Update display every 500ms for more responsive UI
    
    def start_render_timing(self):
        self.last_render_start = time.time()
    
    def end_render_timing(self):
        if self.last_render_start > 0:
            render_time = (time.time() - self.last_render_start) * 1000
            self.render_time_ms = render_time
            self.frame_times.append(render_time)
            self.last_render_start = 0
    
    def request_update(self, priority='normal'):
        current_time = time.perf_counter()
        
        # Always count actual render requests for accurate FPS
        self.frame_count += 1
        
        # Only render if enough time has passed (frame rate limiting)
        if current_time - self.last_update >= self.min_frame_time:
            self.start_render_timing()
            self.viewer.plot_eeg_data()
            self.end_render_timing()
            self.last_update = current_time
            
            # Update FPS calculation based on actual renders
            if current_time - self.last_time >= 1.0:  # Update every 1 second for stable FPS
                time_diff = current_time - self.last_time
                if time_diff > 0:
                    self.fps = self.frame_count / time_diff
                    self.frame_count = 0
                    self.last_time = current_time
                    # Adjust render quality based on FPS
                    if self.fps < 30:
                        self.render_quality = max(0.5, self.render_quality - 0.1)
                    elif self.fps > 50:
                        self.render_quality = min(1.0, self.render_quality + 0.05)
        elif not self.pending_update:
            self.pending_update = True
            QTimer.singleShot(int((self.last_update + self.min_frame_time - current_time) * 1000),
                             self._perform_delayed_update)
    
    def _perform_delayed_update(self):
        self.start_render_timing()
        self.viewer.plot_eeg_data()
        self.end_render_timing()
        self.last_update = time.perf_counter()
        self.frame_count += 1
        self.pending_update = False
    
    def update_display(self):
        try:
            process = psutil.Process()
            self.memory_mb = process.memory_info().rss / 1024 / 1024
        except:
            pass
        if hasattr(self.viewer, 'data_cache'):
            self.cache_hit_rate = self.viewer.data_cache.get_hit_rate()
        
        # Update sidebar performance labels
        if hasattr(self.viewer, 'fps_label'):
            color = "green" if self.fps > 45 else "orange" if self.fps > 25 else "red"
            self.viewer.fps_label.setText(f"<span style='color: {color}'>FPS: {self.fps:.1f}</span>")
        if hasattr(self.viewer, 'memory_label'):
            self.viewer.memory_label.setText(f"Memory: {self.memory_mb:.1f} MB")
        if hasattr(self.viewer, 'cache_label'):
            cache_color = "green" if self.cache_hit_rate > 0.8 else "orange" if self.cache_hit_rate > 0.5 else "red"
            self.viewer.cache_label.setText(f"<span style='color: {cache_color}'>Cache: {self.cache_hit_rate:.1%}</span>")
        
        # Update status bar performance labels
        if hasattr(self.viewer, 'status_fps_label'):
            color = "green" if self.fps > 45 else "orange" if self.fps > 25 else "red"
            self.viewer.status_fps_label.setText(f"<span style='color: {color}'>FPS: {self.fps:.1f}</span>")
        if hasattr(self.viewer, 'status_memory_label'):
            self.viewer.status_memory_label.setText(f"Memory: {self.memory_mb:.1f} MB")
        if hasattr(self.viewer, 'status_cache_label'):
            cache_color = "green" if self.cache_hit_rate > 0.8 else "orange" if self.cache_hit_rate > 0.5 else "red"
            self.viewer.status_cache_label.setText(f"<span style='color: {cache_color}'>Cache: {self.cache_hit_rate:.1%}</span>")

class EDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clinical EEG Viewer")
        self.setGeometry(100, 100, 1200, 800)
        self.raw = None
        self.channel_indices = []
        self.channel_colors = {}
        self.view_start_time = 0.0
        self.view_duration = 10.0
        self.focus_start_time = 0.0
        self.focus_duration = 1.0
        self.focus_step_time = 0.5
        self.channel_offset = 0
        self.total_channels = 0
        self.visible_channels = 10
        self.sensitivity = 50
        self.auto_sensitivity = True
        self.auto_move_active = False
        self._updating_scrollbar = False  # Flag to prevent recursive updates
        self.annotation_manager = AnnotationManager()
        self.plot_items = {}
        self.separator_lines = []
        self.annotation_items = []
        self.data_cache = HighPerformanceDataCache()
        self.perf_manager = PerformanceManager(self)
        self.signal_processor = HighPerformanceSignalProcessor()
        self._data_buffer = None
        self._times_buffer = None
        self._channel_offset_buffer = None
        self.drag_start_time = None
        self.drag_channel = None
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_status_bar()
        self.connect_signals()
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(300000)

        # FIX: Connect to X-range changes to sync state (prevents reset after panning)
        self.view_box.sigXRangeChanged.connect(self.on_xrange_changed)

    def on_xrange_changed(self, vb, xr):
        new_start, new_end = xr
        new_duration = new_end - new_start
        # Update only if significantly different to prevent feedback loops
        if abs(new_start - self.view_start_time) > 1e-4 or abs(new_duration - self.view_duration) > 1e-4:
            self.view_start_time = new_start
            self.view_duration = new_duration
            self.update_time_combo_display()
            self.update_scrollbars()

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)
        title = QLabel("Clinical EEG Viewer")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #64b5f6; margin-bottom: 10px;")
        sidebar.addWidget(title)
        display_group = QGroupBox("Display Settings")
        display_layout = QVBoxLayout()
        sens_layout = QHBoxLayout()
        sens_layout.addWidget(QLabel("Sensitivity:"))
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(10, 500)
        self.sensitivity_slider.setValue(50)
        sens_layout.addWidget(self.sensitivity_slider)
        self.sens_label = QLabel("50 µV")
        sens_layout.addWidget(self.sens_label)
        display_layout.addLayout(sens_layout)
        self.auto_sens_check = QCheckBox("Auto Sensitivity")
        self.auto_sens_check.setChecked(True)
        display_layout.addWidget(self.auto_sens_check)
        display_layout.addWidget(QLabel("Visible Channels:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["5", "10", "15", "20", "30", "40", "50", "All"])
        self.channel_combo.setCurrentText("10")
        display_layout.addWidget(self.channel_combo)
        display_layout.addWidget(QLabel("Time Scale:"))
        self.time_combo = QComboBox()
        self.time_combo.addItems(["5s", "10s", "15s", "20s", "30s", "1m", "2m", "5m"])
        self.time_combo.setCurrentText("10s")
        display_layout.addWidget(self.time_combo)
        display_layout.addWidget(QLabel("Focus Duration (s):"))
        self.duration_input = QLineEdit("1.0")
        self.duration_input.setValidator(QDoubleValidator(0.1, 60.0, 2))
        display_layout.addWidget(self.duration_input)
        display_group.setLayout(display_layout)
        sidebar.addWidget(display_group)
        ann_group = QGroupBox("Annotations")
        ann_layout = QVBoxLayout()
        ann_btn = QPushButton("Add Annotation")
        ann_btn.clicked.connect(self.add_annotation_popup)
        ann_layout.addWidget(ann_btn)
        highlight_btn = QPushButton("Add Highlight")
        highlight_btn.clicked.connect(self.open_highlight_dialog)
        ann_layout.addWidget(highlight_btn)
        manage_btn = QPushButton("Manage")
        manage_btn.clicked.connect(self.open_annotation_manager)
        ann_layout.addWidget(manage_btn)
        ann_group.setLayout(ann_layout)
        sidebar.addWidget(ann_group)
        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout()
        self.fps_label = QLabel("FPS: --")
        self.memory_label = QLabel("Memory: -- MB")
        self.cache_label = QLabel("Cache: --")
        perf_layout.addWidget(self.fps_label)
        perf_layout.addWidget(self.memory_label)
        perf_layout.addWidget(self.cache_label)
        perf_group.setLayout(perf_layout)
        sidebar.addWidget(perf_group)
        sidebar.addStretch()
        main_layout.addLayout(sidebar, 1)
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.view_box = CustomViewBox()
        self.plot_widget = pg.PlotWidget(viewBox=self.view_box)
        self.plot_widget.setBackground('#181c20')
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Channels')
        self.plot_widget.setLabel('bottom', 'Time', 's')
        try:
            self.plot_widget.getAxis('left').setTextPen('#e0e6ed')
            self.plot_widget.getAxis('bottom').setTextPen('#e0e6ed')
        except Exception:
            pass
        self.vscroll = QScrollBar(Qt.Orientation.Vertical)
        self.hscroll = QScrollBar(Qt.Orientation.Horizontal)
        plot_container = QHBoxLayout()
        plot_container.addWidget(self.plot_widget, 1)
        plot_container.addWidget(self.vscroll)
        plot_layout.addLayout(plot_container, 1)
        plot_layout.addWidget(self.hscroll)
        main_layout.addWidget(plot_widget, 4)
        self.setCentralWidget(main_widget)

    def setup_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')
        open_action = QAction('Open EDF', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        save_action = QAction('Save Session', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_session)
        file_menu.addAction(save_action)
        load_action = QAction('Load Session', self)
        load_action.setShortcut('Ctrl+L')
        load_action.triggered.connect(self.load_session)
        file_menu.addAction(load_action)
        file_menu.addSeparator()
        import_action = QAction('Import Annotations CSV', self)
        import_action.triggered.connect(self.import_csv)
        file_menu.addAction(import_action)
        export_action = QAction('Export Annotations CSV', self)
        export_action.triggered.connect(self.export_csv)
        file_menu.addAction(export_action)
        tools_menu = menubar.addMenu('Tools')
        channel_select_action = QAction('Select Channels', self)
        channel_select_action.setShortcut('Ctrl+C')
        channel_select_action.triggered.connect(self.open_channel_selection)
        tools_menu.addAction(channel_select_action)
        color_select_action = QAction('Set Channel Colors', self)
        color_select_action.triggered.connect(self.open_color_selection)
        tools_menu.addAction(color_select_action)
        help_menu = menubar.addMenu('Help')
        shortcuts_action = QAction('Keyboard Shortcuts', self)
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)

    def show_shortcuts(self):
        shortcuts = (
            "Left/Right Arrow: Scroll time horizontally\n"
            "Up/Down Arrow: Scroll channels vertically\n"
            "Ctrl++ / Ctrl+-: Zoom in/out\n"
            "Space: Toggle auto-move mode\n"
            "G/H: Previous/Next focus section\n"
            "Mouse click: Set focus window position\n"
            "Mouse drag: Create annotation region\n"
            "Ctrl+Click: Set focus duration\n"
            "Mouse wheel: Scroll channels\n"
            "Ctrl+Wheel: Zoom time scale\n"
            "Alt+Wheel: Scroll time\n"
            "Drag plot: Pan time\n"
            "C (with Ctrl): Open channel selection"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts)

    def setup_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        load_action = QAction('📁 Load', self)
        load_action.setToolTip('Load EDF/BDF file')
        load_action.triggered.connect(self.open_file)
        toolbar.addAction(load_action)
        toolbar.addSeparator()
        prev_action = QAction('⬅ Previous', self)
        prev_action.setToolTip('Scroll to previous time section')
        prev_action.triggered.connect(self.previous_section)
        toolbar.addAction(prev_action)
        next_action = QAction('➡ Next', self)
        next_action.setToolTip('Scroll to next time section')
        next_action.triggered.connect(self.next_section)
        toolbar.addAction(next_action)
        self.auto_action = QAction('Start Auto', self)
        self.auto_action.setCheckable(True)
        self.auto_action.setToolTip('Toggle auto-scrolling through the recording')
        self.auto_action.triggered.connect(self.toggle_auto_move)
        toolbar.addAction(self.auto_action)
        toolbar.addSeparator()
        channel_action = QAction('⚙️ Channels', self)
        channel_action.setToolTip('Select and reorder channels')
        channel_action.triggered.connect(self.open_channel_selection)
        toolbar.addAction(channel_action)
        color_action = QAction('🎨 Colors', self)
        color_action.setToolTip('Set channel colors')
        color_action.triggered.connect(self.open_color_selection)
        toolbar.addAction(color_action)
        toolbar.addSeparator()
        screenshot_action = QAction('📷 Screenshot', self)
        screenshot_action.setToolTip('Take screenshot with options')
        screenshot_action.triggered.connect(self.open_screenshot_dialog)
        toolbar.addAction(screenshot_action)

    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready - Load an EDF file to begin")
        # Create separate status bar labels (different from sidebar labels)
        self.status_fps_label = QLabel("FPS: --")
        self.status_memory_label = QLabel("Memory: -- MB")
        self.status_cache_label = QLabel("Cache: --")
        self.status_bar.addPermanentWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.status_fps_label)
        self.status_bar.addPermanentWidget(self.status_memory_label)
        self.status_bar.addPermanentWidget(self.status_cache_label)

    def connect_signals(self):
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity)
        self.channel_combo.currentTextChanged.connect(self.update_channels)
        self.time_combo.currentTextChanged.connect(self.update_time_scale)
        self.duration_input.editingFinished.connect(self.update_focus_duration)
        self.auto_sens_check.toggled.connect(self.toggle_auto_sensitivity)
        self.vscroll.valueChanged.connect(self.update_channel_offset)
        self.hscroll.valueChanged.connect(self.update_time_offset)
        self.plot_widget.scene().sigMouseClicked.connect(self.on_plot_clicked)
        self.plot_widget.scene().sigMouseMoved.connect(self.on_mouse_move)
        self.view_box.dragStart.connect(self.on_drag_start)
        self.view_box.dragFinish.connect(self.on_drag_finish)
        
        # Enable channel reordering by dragging on Y-axis
        self.dragging_channel = False
        self.drag_start_channel = None
        self.drag_current_y = None

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open EDF File",
            "",
            "EDF Files (*.edf *.bdf);;All Files (*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        self.loader_thread = DataLoaderThread(file_path)
        self.loader_thread.data_loaded.connect(self.on_data_loaded)
        self.loader_thread.error_occurred.connect(self.on_load_error)
        self.loader_thread.start()
        self.status_label.setText(f"Loading {Path(file_path).name}...")

    def on_data_loaded(self, raw):
        self.raw = raw
        self.annotation_manager.raw = raw
        self.channel_indices = list(range(len(raw.ch_names)))
        self.channel_colors = {ch: '#e0e6ed' for ch in raw.ch_names}
        self.total_channels = len(self.channel_indices)
        self.view_start_time = 0.0
        self.focus_start_time = 0.0
        self.channel_offset = 0
        self.create_plot_items()
        self.update_scrollbars()
        self.update_time_combo_display()  # Ensure combo box shows current zoom level
        self.perf_manager.request_update()
        self.status_label.setText(f"Loaded: {len(raw.ch_names)} channels from {Path(self.raw.filenames[0]).name}")

    def on_load_error(self, error):
        QMessageBox.critical(self, "Error", f"Failed to load file:\n{error}")
        self.status_label.setText(f"Error loading file: {error}")

    def create_plot_items(self):
        if not self.raw:
            return
        self.plot_widget.clear()
        self.plot_items = {}
        self.separator_lines = []
        for i in self.channel_indices:
            ch_name = self.raw.ch_names[i]
            color = self.channel_colors.get(ch_name, '#e0e6ed')
            plot_item = pg.PlotDataItem(
                pen=pg.mkPen(color, width=1.2),
                clipToView=True,
                autoDownsample=True,
                antialias=True
            )
            self.plot_items[ch_name] = plot_item
            self.plot_widget.addItem(plot_item)

    def plot_eeg_data(self):
        if not self.raw or not self.channel_indices:
            return
        try:
            # FIX: If auto_sensitivity enabled, compute optimal sensitivity from current view data
            start_sample = int(self.view_start_time * self.raw.info['sfreq'])
            end_sample = int((self.view_start_time + self.view_duration) * self.raw.info['sfreq'])
            end_sample = min(end_sample, self.raw.n_times)  # Clamp to data length
            max_time = self.raw.n_times / self.raw.info['sfreq']
            effective_end_time = min(self.view_start_time + self.view_duration, max_time)

            if start_sample >= end_sample:
                return
            start_ch = self.channel_offset
            end_ch = min(self.channel_offset + self.visible_channels, self.total_channels)
            visible_indices = self.channel_indices[start_ch:end_ch]
            visible_ch_names = [self.raw.ch_names[i] for i in visible_indices]
            self.visible_ch_names = visible_ch_names
            if not visible_ch_names:
                return
            cache_key = (start_sample, end_sample, tuple(visible_indices), self.sensitivity)
            cached_data = self.data_cache.get(cache_key)
            if cached_data is None:
                data, times = self.raw.get_data(picks=visible_indices, start=start_sample, stop=end_sample, return_times=True)
                cached_data = (data, times)
                self.data_cache.put(cache_key, cached_data)
            data, times = cached_data

            if self.auto_sensitivity:
                # Compute per-channel max amplitude in current view
                data_abs = np.abs(data)
                max_amps = np.percentile(data_abs, 98, axis=1)
                overall_max = np.max(max_amps) if len(max_amps) > 0 else 1.0
                if overall_max > 0:
                    # Set sensitivity to fit signals within ~80% of channel height (assuming spacing=2.5, target ±1)
                    self.sensitivity = 50.0 * (1.0 / overall_max) * 50.0  # Adjust empirically
                    self.sensitivity = max(10, min(500, self.sensitivity))
                    self.sensitivity_slider.setValue(int(self.sensitivity))
                    self.sens_label.setText(f"{self.sensitivity} µV (auto)")

            # Intelligent downsample
            data_ds, indices_ds = self.signal_processor.intelligent_downsample(data)

            # Build times_ds robustly so shapes align with data_ds
            if data_ds.ndim == 2:
                # data_ds shape: (n_channels, n_samples_ds)
                if np.ndim(indices_ds) == 2:
                    # indices_ds is per-channel indices
                    times_ds = times[indices_ds]
                else:
                    # indices_ds is 1D; replicate for each channel
                    t1d = times[indices_ds]
                    times_ds = np.tile(t1d, (data_ds.shape[0], 1))
            else:
                # single channel
                times_ds = times[indices_ds]

            # Scaling
            data_ds, _ = self.signal_processor.adaptive_scaling(data_ds)
            data_ds = data_ds * (self.sensitivity / 50.0)

            # Pre-allocate buffers
            if self._data_buffer is None or self._data_buffer.shape != data_ds.shape:
                self._data_buffer = np.empty(data_ds.shape, dtype=data_ds.dtype)
            if self._times_buffer is None or self._times_buffer.shape != times_ds.shape:
                self._times_buffer = np.empty(times_ds.shape, dtype=times_ds.dtype)
            if self._channel_offset_buffer is None or self._channel_offset_buffer.shape != (data_ds.shape[0],):
                self._channel_offset_buffer = np.empty(data_ds.shape[0], dtype=np.float32)

            np.copyto(self._data_buffer, data_ds)
            np.copyto(self._times_buffer, times_ds)

            spacing = 2.5
            num_visible = len(visible_indices)
            np.multiply(np.arange(num_visible, dtype=np.float32)[::-1], spacing, out=self._channel_offset_buffer)
            # add channel offsets (broadcast across time dimension)
            self._data_buffer += self._channel_offset_buffer[:, np.newaxis]

            # Update plot items
            for i, ch_name in enumerate(visible_ch_names):
                if ch_name not in self.plot_items:
                    continue
                    
                # Extract data for this channel
                if self._times_buffer.ndim > 1:
                    x = self._times_buffer[i]
                else:
                    x = self._times_buffer
                    
                if self._data_buffer.ndim > 1:
                    y = self._data_buffer[i]
                else:
                    y = self._data_buffer
                
                # Ensure both x and y are 1D arrays and have the same length
                x = np.asarray(x).flatten()
                y = np.asarray(y).flatten()
                
                # Skip if arrays are empty or have different lengths
                if len(x) == 0 or len(y) == 0 or len(x) != len(y):
                    continue
                    
                # Update the plot item
                try:
                    self.plot_items[ch_name].setData(x, y, skipFiniteCheck=True)
                except Exception as e:
                    logging.error(f"Error updating plot for channel {ch_name}: {e}")
                    continue

            # Set visibility
            for ch_name in self.plot_items:
                self.plot_items[ch_name].setVisible(ch_name in visible_ch_names)

            # Update channel labels
            y_ticks = [(float(self._channel_offset_buffer[i]), visible_ch_names[i]) for i in range(num_visible)]
            self.plot_widget.getAxis('left').setTicks([y_ticks])

            # Set view ranges
            self.plot_widget.setXRange(self.view_start_time, effective_end_time, padding=0)
            self.plot_widget.setYRange(-spacing / 2, (num_visible - 1) * spacing + spacing / 2, padding=0)

            # Channel separators
            for line in self.separator_lines:
                self.plot_widget.removeItem(line)
            self.separator_lines = []
            for i in range(1, num_visible):
                sep = pg.InfiniteLine(
                    pos=self._channel_offset_buffer[i-1] - spacing / 2,
                    angle=0,
                    pen=pg.mkPen('#2a2e36', width=1)
                )
                self.plot_widget.addItem(sep)
                self.separator_lines.append(sep)

            # Annotations and focus
            self.update_annotations()

        except Exception as e:
            logging.error(f"Plot update error: {e}")
            self.status_label.setText(f"Error rendering: {str(e)}")

    def update_annotations(self):
        for item in self.annotation_items:
            try:
                self.plot_widget.removeItem(item)
            except Exception:
                pass
        self.annotation_items = []
        if self.focus_duration > 0:
            focus_region = pg.LinearRegionItem(
                [self.focus_start_time, self.focus_start_time + self.focus_duration],
                brush=pg.mkBrush(255, 255, 0, 50),
                pen=pg.mkPen(255, 255, 0, 100),
                movable=True
            )
            # FIX: Check if method exists before connecting to avoid AttributeError
            if hasattr(self, 'on_focus_moved'):
                focus_region.sigRegionChanged.connect(self.on_focus_moved)
            else:
                logging.warning("on_focus_moved not available; skipping connection")
            self.plot_widget.addItem(focus_region)
            self.annotation_items.append(focus_region)

        spacing = 2.5
        y_min = -spacing / 2
        y_max = (len(self.visible_ch_names) - 1) * spacing + spacing / 2 if hasattr(self, 'visible_ch_names') else 0

        # Ensure we have colors for all annotations
        if not hasattr(self.annotation_manager, 'annotation_colors'):
            self.annotation_manager.annotation_colors = ['green'] * len(self.annotation_manager.annotations.onset)
        elif len(self.annotation_manager.annotation_colors) < len(self.annotation_manager.annotations.onset):
            self.annotation_manager.annotation_colors.extend(['green'] * (len(self.annotation_manager.annotations.onset) - len(self.annotation_manager.annotation_colors)))

        for i, (onset, duration, description) in enumerate(zip(self.annotation_manager.annotations.onset,
                                                               self.annotation_manager.annotations.duration,
                                                               self.annotation_manager.annotations.description)):
            if onset + duration < self.view_start_time or onset > self.view_start_time + self.view_duration:
                continue
            color_name = self.annotation_manager.annotation_colors[i] if i < len(self.annotation_manager.annotation_colors) else 'green'
            color = QColor(color_name)
            pen = pg.mkPen(color.darker(150), width=2)
            brush = pg.mkBrush(color.red(), color.green(), color.blue(), 80)
            if duration > 0:
                # Create rectangle using LinearRegionItem for better visibility
                region = pg.LinearRegionItem(
                    [onset, onset + duration],
                    brush=brush,
                    pen=pen,
                    movable=False
                )
                self.plot_widget.addItem(region)
                self.annotation_items.append(region)
                
                # Add border lines for clarity
                left_line = pg.PlotDataItem([onset, onset], [y_min, y_max], pen=pen)
                right_line = pg.PlotDataItem([onset + duration, onset + duration], [y_min, y_max], pen=pen)
                self.plot_widget.addItem(left_line)
                self.plot_widget.addItem(right_line)
                self.annotation_items.extend([left_line, right_line])
            else:
                line = pg.PlotDataItem([onset, onset], [y_min, y_max], pen=pen)
                self.plot_widget.addItem(line)
                self.annotation_items.append(line)

            mid_y = (y_min + y_max) / 2
            text = pg.TextItem(text=description, color=color.darker(150), anchor=(0.5, 0.5))
            text.setPos(onset + duration / 2, mid_y)
            self.plot_widget.addItem(text)
            self.annotation_items.append(text)

        for highlight in self.annotation_manager.section_highlights:
            if len(highlight) > 4:
                ch_name, onset, duration, color_str, description = highlight
            else:
                ch_name, onset, duration, color_str = highlight
                description = "Highlight"
            if onset + duration < self.view_start_time or onset > self.view_start_time + self.view_duration:
                continue
            if not hasattr(self, 'visible_ch_names') or ch_name not in self.visible_ch_names:
                continue
            color = QColor(color_str)
            pen = pg.mkPen(color.darker(150), width=2)
            brush = pg.mkBrush(color.red(), color.green(), color.blue(), 100)
            local_idx = self.visible_ch_names.index(ch_name)
            
            # Calculate y_center safely - use manual calculation if buffer not available
            if hasattr(self, '_channel_offset_buffer') and self._channel_offset_buffer is not None and local_idx < len(self._channel_offset_buffer):
                y_center = float(self._channel_offset_buffer[local_idx])
            else:
                # Fallback calculation - channels are spaced from top to bottom
                num_visible = len(self.visible_ch_names)
                y_center = (num_visible - 1 - local_idx) * spacing
            
            y_min_ch = y_center - spacing / 2
            y_max_ch = y_center + spacing / 2

            if duration > 0:
                # Create proper rectangle for channel highlight using QGraphicsRectItem
                from PyQt6.QtWidgets import QGraphicsRectItem
                from PyQt6.QtCore import QRectF
                
                rect_item = QGraphicsRectItem(QRectF(onset, y_min_ch, duration, spacing))
                rect_item.setPen(pen)
                rect_item.setBrush(brush)
                self.plot_widget.addItem(rect_item)
                self.annotation_items.append(rect_item)
                
                # Add border lines for clarity
                left_line = pg.PlotDataItem([onset, onset], [y_min_ch, y_max_ch], pen=pen)
                right_line = pg.PlotDataItem([onset + duration, onset + duration], [y_min_ch, y_max_ch], pen=pen)
                self.plot_widget.addItem(left_line)
                self.plot_widget.addItem(right_line)
                self.annotation_items.extend([left_line, right_line])
            else:
                line = pg.PlotDataItem([onset, onset], [y_min_ch, y_max_ch], pen=pen)
                self.plot_widget.addItem(line)
                self.annotation_items.append(line)

            # Use description for highlight text label
            text = pg.TextItem(text=description, color=color.darker(150), anchor=(0.5, 0.5))
            text.setPos(onset + duration / 2, y_center)
            self.plot_widget.addItem(text)
            self.annotation_items.append(text)

    def update_scrollbars(self):
        if not self.raw or not self.channel_indices:
            self.vscroll.setEnabled(False)
            self.hscroll.setEnabled(False)
            return
        
        # Set flag to prevent recursive updates
        self._updating_scrollbar = True
        
        max_offset = max(0, self.total_channels - self.visible_channels)
        self.vscroll.setRange(0, max_offset)
        self.vscroll.setValue(self.channel_offset)
        self.vscroll.setPageStep(max(1, self.visible_channels // 2))
        self.vscroll.setEnabled(bool(max_offset > 0))  # FIX: Cast to bool to avoid np.bool deprecation
        max_time = self.raw.n_times / self.raw.info['sfreq']
        max_time_offset = max(0, max_time - self.view_duration)
        self.hscroll.setRange(0, int(max_time_offset * 100))
        self.hscroll.setValue(int(self.view_start_time * 100))
        self.hscroll.setPageStep(int(self.view_duration * 50))
        self.hscroll.setEnabled(bool(max_time_offset > 0))  # FIX: Cast to bool to avoid np.bool deprecation
        
        # Clear flag
        self._updating_scrollbar = False

    def update_sensitivity(self, value):
        self.sensitivity = value
        self.sens_label.setText(f"{value} µV")
        self.auto_sensitivity = False
        self.auto_sens_check.setChecked(False)
        self.perf_manager.request_update()
        self.auto_export_csv()  # Auto-export when sensitivity changes

    def toggle_auto_sensitivity(self, checked):
        self.auto_sensitivity = checked
        if checked:
            self.perf_manager.request_update()  # Trigger recompute in plot_eeg_data

    def update_channels(self, value):
        if value == "All":
            self.visible_channels = self.total_channels
        else:
            try:
                self.visible_channels = int(value)
            except ValueError:
                self.visible_channels = 10
        self.create_plot_items()
        self.update_scrollbars()
        self.perf_manager.request_update()
        self.auto_export_csv()  # Auto-export when visible channels change

    def update_time_scale(self, value):
        """Update time scale from combo box selection"""
        try:
            time_val = float(value.replace('s', '')) if 's' in value else float(value.replace('m', '')) * 60
            
            # Only update if the value is significantly different to avoid unnecessary resets
            if abs(self.view_duration - time_val) > 0.1:
                self.view_duration = time_val
                self.update_scrollbars()
                self.perf_manager.request_update()
                self.auto_export_csv()  # Auto-export when time scale changes
        except (ValueError, AttributeError):
            # Handle invalid values gracefully
            pass

    def update_time_combo_display(self):
        """Update the time combo box to show current zoom level without triggering signals"""
        if not hasattr(self, 'time_combo'):
            return
            
        # Temporarily disconnect the signal to prevent recursive updates
        self.time_combo.currentTextChanged.disconnect(self.update_time_scale)
        
        # Find the closest predefined value or add a custom one
        current_duration = self.view_duration
        predefined_values = ["5s", "10s", "15s", "20s", "30s", "1m", "2m", "5m"]
        predefined_seconds = [5, 10, 15, 20, 30, 60, 120, 300]
        
        # Check if current duration matches any predefined value (within 0.1s tolerance)
        closest_match = None
        for i, seconds in enumerate(predefined_seconds):
            if abs(current_duration - seconds) < 0.1:
                closest_match = predefined_values[i]
                break
        
        if closest_match:
            # Set to the closest predefined value
            self.time_combo.setCurrentText(closest_match)
        else:
            # Add custom value if it doesn't exist
            if current_duration < 60:
                custom_text = f"{current_duration:.1f}s"
            else:
                custom_text = f"{current_duration/60:.1f}m"
            
            # Check if this custom value already exists
            if self.time_combo.findText(custom_text) == -1:
                # Remove any previous custom values (they start with numbers not in predefined list)
                for i in range(self.time_combo.count() - 1, -1, -1):
                    text = self.time_combo.itemText(i)
                    if text not in predefined_values:
                        self.time_combo.removeItem(i)
                
                # Add the new custom value
                self.time_combo.addItem(custom_text)
            
            self.time_combo.setCurrentText(custom_text)
        
        # Reconnect the signal
        self.time_combo.currentTextChanged.connect(self.update_time_scale)
    
    def _navigate_preserving_zoom(self, direction):
        """Navigate while absolutely preserving zoom level"""
        # Store current zoom
        preserved_zoom = self.view_duration
        
        # Temporarily disconnect signals that might affect zoom
        self.time_combo.currentTextChanged.disconnect(self.update_time_scale)
        self.hscroll.valueChanged.disconnect(self.update_time_offset)
        
        try:
            # Perform navigation
            if direction == 'left':
                self.view_start_time = max(0, self.view_start_time - self.view_duration * 0.1)
            elif direction == 'right':
                max_time = self.raw.n_times / self.raw.info['sfreq'] if self.raw else 100
                self.view_start_time = min(max_time - self.view_duration, 
                                         self.view_start_time + self.view_duration * 0.1)
            
            # Force zoom back to preserved value
            self.view_duration = preserved_zoom
            
            # Update scrollbars manually
            self._updating_scrollbar = True
            if self.raw:
                max_time = self.raw.n_times / self.raw.info['sfreq']
                max_time_offset = max(0, max_time - self.view_duration)
                self.hscroll.setRange(0, int(max_time_offset * 100))
                self.hscroll.setValue(int(self.view_start_time * 100))
                self.hscroll.setPageStep(int(self.view_duration * 50))
            self._updating_scrollbar = False
            
            # Update display
            self.perf_manager.request_update()
            
        finally:
            # Always reconnect signals
            self.time_combo.currentTextChanged.connect(self.update_time_scale)
            self.hscroll.valueChanged.connect(self.update_time_offset)
            
            # Final check - force zoom if it somehow changed
            if abs(self.view_duration - preserved_zoom) > 0.001:
                print(f"ZOOM CORRUPTION DETECTED! Forcing back to {preserved_zoom}")
                self.view_duration = preserved_zoom
    
    def _previous_section_preserving_zoom(self):
        """Previous section while preserving zoom"""
        if not self.raw:
            return
        preserved_zoom = self.view_duration
        
        self.focus_start_time = max(0, self.focus_start_time - self.focus_duration)
        if self.focus_start_time < self.view_start_time:
            self.view_start_time = max(0, self.focus_start_time - self.view_duration * 0.1)
            self.update_scrollbars()
        
        # Force zoom preservation
        self.view_duration = preserved_zoom
        self.perf_manager.request_update()
    
    def _next_section_preserving_zoom(self):
        """Next section while preserving zoom"""
        if not self.raw:
            return
        preserved_zoom = self.view_duration
        
        max_time = self.raw.n_times / self.raw.info['sfreq']
        self.focus_start_time = min(max_time - self.focus_duration, self.focus_start_time + self.focus_duration)
        if self.focus_start_time + self.focus_duration > self.view_start_time + self.view_duration:
            self.view_start_time = min(max_time - self.view_duration, self.focus_start_time - self.view_duration * 0.1)
            self.update_scrollbars()
        
        # Force zoom preservation
        self.view_duration = preserved_zoom
        self.perf_manager.request_update()

    def update_focus_duration(self):
        try:
            duration = float(self.duration_input.text())
            if duration > 0:
                self.focus_duration = duration
                self.perf_manager.request_update()
        except ValueError:
            pass

    def update_channel_offset(self, value):
        self.channel_offset = value
        self.create_plot_items()
        self.perf_manager.request_update()

    def update_time_offset(self, value):
        # Skip if we're updating scrollbars programmatically to prevent recursive updates
        if self._updating_scrollbar:
            return
            
        # Convert scrollbar value back to time, ensuring proper direction
        self.view_start_time = value / 100.0
        # Clamp to valid range
        if self.raw:
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.view_start_time = max(0, min(self.view_start_time, max_time - self.view_duration))
        self.perf_manager.request_update()

    def on_plot_clicked(self, event):
        if not self.raw or event.isAccepted():
            return
        pos = event.scenePos()
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.view_box.mapSceneToView(pos)
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.focus_duration = 1.0
                self.duration_input.setText(str(self.focus_duration))
                self.focus_start_time = mouse_point.x() - self.focus_duration / 2
            else:
                clicked_annotation = self._get_annotation_at_position(mouse_point.x(), mouse_point.y())
                if clicked_annotation:
                    self.show_annotation_context_menu(event, clicked_annotation)
                else:
                    self.focus_start_time = max(0, mouse_point.x() - self.focus_duration / 2)
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.focus_start_time = min(self.focus_start_time, max_time - self.focus_duration)
            self.perf_manager.request_update()
            event.accept()

    def on_mouse_move(self, pos):
        if not self.raw or not hasattr(self, 'visible_ch_names'):
            return
        view_pos = self.view_box.mapSceneToView(pos)
        if 0 <= view_pos.x() <= self.raw.n_times / self.raw.info['sfreq']:
            y_range = self.view_box.viewRange()[1]
            if y_range[1] - y_range[0] != 0:
                channel_idx = int((y_range[1] - view_pos.y()) /
                                ((y_range[1] - y_range[0]) / max(1, self.visible_channels)))
            else:
                channel_idx = -1
            if 0 <= channel_idx < len(self.visible_ch_names):
                channel_name = self.visible_ch_names[channel_idx]
                self.status_label.setText(f"Time: {view_pos.x():.2f}s | Channel: {channel_name}")
            else:
                self.status_label.setText(f"Time: {view_pos.x():.2f}s")

    def on_drag_start(self, pos):
        # Check if this is a channel reordering drag (near the Y-axis labels)
        view_range = self.view_box.viewRange()
        x_range = view_range[0]
        
        # If drag starts near the left edge (within 10% of view width), it's channel reordering
        view_width = x_range[1] - x_range[0]
        if pos.x() < x_range[0] + (view_width * 0.1):
            self.start_channel_reorder_drag(pos)
        else:
            self.start_annotation_drag(pos)
    
    def start_channel_reorder_drag(self, pos):
        """Start channel reordering drag"""
        y_range = self.view_box.viewRange()[1]
        spacing = (y_range[1] - y_range[0]) / max(1, self.visible_channels)
        ch_idx_from_top = int((pos.y() - y_range[0]) / spacing) if spacing != 0 else 0
        ch_idx = self.visible_channels - 1 - ch_idx_from_top
        
        if 0 <= ch_idx < self.visible_channels and hasattr(self, 'visible_ch_names'):
            self.dragging_channel = True
            self.drag_start_channel = ch_idx
            self.drag_current_y = pos.y()
            self.status_label.setText(f"Dragging channel: {self.visible_ch_names[ch_idx]}")
        else:
            self.dragging_channel = False
    
    def start_annotation_drag(self, pos):
        """Start annotation drag"""
        self.drag_start_time = pos.x()
        y_range = self.view_box.viewRange()[1]
        spacing = (y_range[1] - y_range[0]) / max(1, self.visible_channels)
        ch_idx_from_top = int((pos.y() - y_range[0]) / spacing) if spacing != 0 else 0
        ch_idx = self.visible_channels - 1 - ch_idx_from_top
        if 0 <= ch_idx < self.visible_channels and hasattr(self, 'visible_ch_names'):
            try:
                self.drag_channel = self.visible_ch_names[ch_idx]
            except Exception:
                self.drag_channel = None
        else:
            self.drag_channel = None

    def on_drag_finish(self, pos):
        if self.dragging_channel and self.drag_start_channel is not None:
            self.finish_channel_reorder_drag(pos)
        elif self.drag_start_time is not None:
            self.finish_annotation_drag(pos)
    
    def finish_channel_reorder_drag(self, pos):
        """Finish channel reordering drag"""
        y_range = self.view_box.viewRange()[1]
        spacing = (y_range[1] - y_range[0]) / max(1, self.visible_channels)
        ch_idx_from_top = int((pos.y() - y_range[0]) / spacing) if spacing != 0 else 0
        target_idx = self.visible_channels - 1 - ch_idx_from_top
        
        if 0 <= target_idx < self.visible_channels and target_idx != self.drag_start_channel:
            self.reorder_channels(self.drag_start_channel, target_idx)
        
        # Reset drag state
        self.dragging_channel = False
        self.drag_start_channel = None
        self.drag_current_y = None
    
    def finish_annotation_drag(self, pos):
        """Finish annotation drag"""
        end_time = pos.x()
        start = min(self.drag_start_time, end_time)
        duration = abs(self.drag_start_time - end_time)
        if duration > 0.1:
            if self.drag_channel:
                self.show_highlight_creation_dialog(start, duration, self.drag_channel)
            else:
                self.add_annotation_popup(start, duration)
        self.drag_start_time = None
        self.drag_channel = None
    
    def reorder_channels(self, from_index, to_index):
        """Reorder channels by moving from_index to to_index"""
        if not hasattr(self, 'visible_ch_names') or from_index == to_index:
            return
            
        # Get the current channel order from channel_indices
        current_visible_indices = [self.channel_indices[self.channel_offset + i] 
                                 for i in range(min(len(self.visible_ch_names), 
                                                   len(self.channel_indices) - self.channel_offset))]
        
        if from_index >= len(current_visible_indices) or to_index >= len(current_visible_indices):
            return
            
        # Move the channel
        moved_index = current_visible_indices.pop(from_index)
        current_visible_indices.insert(to_index, moved_index)
        
        # Update the main channel_indices array
        for i, idx in enumerate(current_visible_indices):
            if self.channel_offset + i < len(self.channel_indices):
                self.channel_indices[self.channel_offset + i] = idx
        
        # Refresh the display
        self.create_plot_items()
        self.perf_manager.request_update()
        self.auto_export_csv()  # Auto-export when channel order changes
        
        # Show feedback
        from_ch = self.visible_ch_names[from_index] if from_index < len(self.visible_ch_names) else "Unknown"
        to_ch = self.visible_ch_names[to_index] if to_index < len(self.visible_ch_names) else "Unknown"
        self.status_label.setText(f"Moved channel {from_ch} to position of {to_ch}")

    def add_annotation_popup(self, start_time=None, duration=None):
        if start_time is None:
            start_time = self.focus_start_time
            duration = self.focus_duration
        
        dialog = AnnotationDialog(self.raw, self)
        dialog.start_input.setText(str(start_time))
        dialog.duration_input.setText(str(duration))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            annotation_info = dialog.get_annotation_info()
            if annotation_info:
                start, dur, description, color = annotation_info
                self.annotation_manager.add_annotation(start, dur, description, color)
                self.perf_manager.request_update()
                self.auto_export_csv()  # Auto-export when annotations change

    def show_highlight_creation_dialog(self, start_time, duration, channel=None):
        dialog = HighlightSectionDialog(self.raw, self.visible_ch_names, self)
        dialog.start_input.setText(str(start_time))
        dialog.duration_input.setText(str(duration))
        if channel:
            dialog.channel_combo.setCurrentText(channel)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            highlight_info = dialog.get_highlight_info()
            if highlight_info:
                ch_name, start, dur, color, description = highlight_info
                self.annotation_manager.add_highlight(ch_name, start, dur, color, description)
                # Force immediate update for highlights
                self.update_annotations()  # Update annotations display immediately
                self.perf_manager.request_update()
                self.auto_export_csv()  # Auto-export when annotations change

    def show_annotation_context_menu(self, event, annotation):
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        action = menu.exec(QCursor.pos())
        if action == edit_action:
            self.edit_annotation(annotation)
        elif action == delete_action:
            self.delete_annotation(annotation)

    def _get_annotation_at_position(self, x, y):
        spacing = 2.5
        for idx, (onset, duration) in enumerate(zip(self.annotation_manager.annotations.onset, self.annotation_manager.annotations.duration)):
            if x < onset or x > onset + duration:
                continue
            return ('annotation', idx)
        for idx, highlight in enumerate(self.annotation_manager.section_highlights):
            ch_name = highlight[0]
            onset = highlight[1]
            duration = highlight[2]
            if x < onset or x > onset + duration:
                continue
            if ch_name not in getattr(self, 'visible_ch_names', []):
                continue
            local_idx = self.visible_ch_names.index(ch_name)
            
            # Calculate y_center safely - use manual calculation if buffer not available
            if hasattr(self, '_channel_offset_buffer') and self._channel_offset_buffer is not None and local_idx < len(self._channel_offset_buffer):
                y_center = float(self._channel_offset_buffer[local_idx])
            else:
                # Fallback calculation - channels are spaced from top to bottom
                num_visible = len(self.visible_ch_names)
                y_center = (num_visible - 1 - local_idx) * spacing
            
            y_min = y_center - spacing / 2
            y_max = y_center + spacing / 2
            if y_min <= y <= y_max:
                return ('highlight', idx)
        return None

    def edit_annotation(self, ann_info):
        ann_type, idx = ann_info
        if ann_type == 'annotation':
            description = self.annotation_manager.annotations.description[idx]
            label, ok = QInputDialog.getText(self, "Edit Annotation", "Enter label:", text=description)
            if ok and label:
                self.annotation_manager.edit_annotation_at(idx, label)
                self.perf_manager.request_update()
        else:
            highlight = self.annotation_manager.section_highlights[idx]
            if len(highlight) > 4:
                ch_name, onset, duration, color_str, description = highlight
            else:
                ch_name, onset, duration, color_str = highlight
                description = "Highlight"
            dialog = HighlightSectionDialog(self.raw, self.visible_ch_names, self)
            dialog.start_input.setText(str(onset))
            dialog.duration_input.setText(str(duration))
            dialog.description_input.setText(description)
            dialog.channel_combo.setCurrentText(ch_name)
            dialog.selected_color = QColor(color_str)
            dialog.color_button.setStyleSheet(f"background-color: {color_str}")
            if dialog.exec() == QDialog.DialogCode.Accepted:
                highlight_info = dialog.get_highlight_info()
                if highlight_info:
                    new_ch_name, new_start, new_dur, new_color, new_description = highlight_info
                    self.annotation_manager.section_highlights[idx] = (new_ch_name, new_start, new_dur, new_color, new_description)
                    self.perf_manager.request_update()

    def delete_annotation(self, ann_info):
        ann_type, idx = ann_info
        if ann_type == 'annotation':
            self.annotation_manager.remove_annotation_at(idx)
        else:
            self.annotation_manager.remove_highlight_at(idx)
        self.perf_manager.request_update()

    def open_highlight_dialog(self):
        if not self.raw:
            return
        dialog = HighlightSectionDialog(self.raw, self.visible_ch_names, self)
        dialog.start_input.setText(str(self.focus_start_time))
        dialog.duration_input.setText(str(self.focus_duration))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            highlight_info = dialog.get_highlight_info()
            if highlight_info:
                ch_name, start, dur, color, description = highlight_info
                self.annotation_manager.add_highlight(ch_name, start, dur, color, description)
                # Force immediate update for highlights
                self.update_annotations()  # Update annotations display immediately
                self.perf_manager.request_update()
                self.auto_export_csv()  # Auto-export when annotations change

    def open_annotation_manager(self):
        if not self.raw:
            return
        dialog = AnnotationManagerDialog(self.annotation_manager, self)
        dialog.exec()
        self.perf_manager.request_update()

    def open_channel_selection(self):
        if not self.raw:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        dialog = ChannelSelectionDialog(self.raw, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.channel_indices = dialog.get_selected_channels()
            self.total_channels = len(self.channel_indices)
            self.channel_offset = 0
            self.create_plot_items()
            self.update_scrollbars()
            self.perf_manager.request_update()
            self.auto_export_csv()  # Auto-export when channel selection changes

    def open_color_selection(self):
        if not self.raw:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        dialog = ChannelColorDialog(self.raw, self.channel_colors, self)
        if dialog.exec():
            self.channel_colors = dialog.get_channel_colors()
            self.create_plot_items()
            self.perf_manager.request_update()
    
    def open_screenshot_dialog(self):
        if not self.raw:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        dialog = ScreenshotDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_screenshot_settings()
            self.take_screenshot(settings)
    
    def take_screenshot(self, settings):
        """Take a screenshot with the specified settings"""
        try:
            from datetime import datetime
            import os
            from PyQt6.QtGui import QPainter, QPixmap
            from PyQt6.QtCore import QSize
            
            # Create screenshots directory if it doesn't exist
            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{settings['filename']}_{timestamp}.{settings['format'].lower()}"
            filepath = screenshot_dir / filename
            
            # Determine size
            if settings['size'] == "Current View":
                size = self.plot_widget.size()
            else:
                size = QSize(settings['width'], settings['height'])
            
            # Create pixmap
            pixmap = QPixmap(size)
            pixmap.fill(QColor('#181c20') if not settings['invert_colors'] else QColor('white'))
            
            # Create painter
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Apply transforms
            if settings['invert_colors']:
                # Invert the plot widget colors temporarily
                original_bg = self.plot_widget.backgroundBrush()
                original_fg = pg.getConfigOption('foreground')
                pg.setConfigOptions(background='white', foreground='black')
                self.plot_widget.setBackground('white')
            
            # Render the plot
            self.plot_widget.render(painter)
            
            # Add grid if requested
            if settings['show_grid']:
                self.draw_grid_on_screenshot(painter, size, settings)
            
            # Add custom elements
            if settings['show_time_axis']:
                self.draw_time_axis_on_screenshot(painter, size, settings)
            
            if settings['show_labels']:
                self.draw_channel_labels_on_screenshot(painter, size, settings)
            
            # Apply brightness and contrast
            if settings['brightness'] != 0 or settings['enhance_contrast']:
                self.apply_image_transforms(pixmap, settings)
            
            painter.end()
            
            # Restore original colors if inverted
            if settings['invert_colors']:
                pg.setConfigOptions(background='#181c20', foreground='#e0e6ed')
                self.plot_widget.setBackground('#181c20')
            
            # Save the screenshot
            success = pixmap.save(str(filepath), settings['format'], settings['quality'])
            
            if success:
                self.status_label.setText(f"Screenshot saved: {filename}")
                QMessageBox.information(self, "Screenshot Saved", 
                                      f"Screenshot saved successfully:\n{filepath}")
            else:
                QMessageBox.critical(self, "Error", "Failed to save screenshot.")
                
        except Exception as e:
            QMessageBox.critical(self, "Screenshot Error", f"Failed to take screenshot:\n{str(e)}")
    
    def draw_grid_on_screenshot(self, painter, size, settings):
        """Draw grid lines on the screenshot"""
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPen
        
        pen = QPen(settings['grid_color'])
        if settings['grid_style'] == "Dashed":
            pen.setStyle(Qt.PenStyle.DashLine)
        elif settings['grid_style'] == "Dotted":
            pen.setStyle(Qt.PenStyle.DotLine)
        painter.setPen(pen)
        
        # Draw vertical time grid lines
        time_step = settings['time_grid']
        pixels_per_second = size.width() / self.view_duration
        for t in range(0, int(self.view_duration) + 1, int(time_step)):
            x = t * pixels_per_second
            painter.drawLine(int(x), 0, int(x), size.height())
        
        # Draw horizontal amplitude grid lines
        if hasattr(self, 'visible_ch_names'):
            spacing = size.height() / len(self.visible_ch_names)
            for i in range(len(self.visible_ch_names) + 1):
                y = i * spacing
                painter.drawLine(0, int(y), size.width(), int(y))
    
    def draw_time_axis_on_screenshot(self, painter, size, settings):
        """Draw time axis labels on the screenshot"""
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import Qt
        
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QColor('white') if not settings['invert_colors'] else QColor('black'))
        
        # Draw time labels
        pixels_per_second = size.width() / self.view_duration
        for t in range(0, int(self.view_duration) + 1):
            x = t * pixels_per_second
            time_label = f"{self.view_start_time + t:.1f}s"
            painter.drawText(int(x) + 5, size.height() - 10, time_label)
    
    def draw_channel_labels_on_screenshot(self, painter, size, settings):
        """Draw channel labels on the screenshot"""
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import Qt
        
        if not hasattr(self, 'visible_ch_names'):
            return
            
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.setPen(QColor('white') if not settings['invert_colors'] else QColor('black'))
        
        spacing = size.height() / len(self.visible_ch_names)
        for i, ch_name in enumerate(self.visible_ch_names):
            y = (i + 0.5) * spacing
            painter.drawText(10, int(y), ch_name)
    
    def apply_image_transforms(self, pixmap, settings):
        """Apply brightness and contrast transforms to the pixmap"""
        # FIX: Stub - implement image processing if needed (e.g., using Pillow or Qt filters)
        pass

    def previous_section(self):
        self._previous_section_preserving_zoom()

    def next_section(self):
        self._next_section_preserving_zoom()

    def toggle_auto_move(self, checked):
        self.auto_move_active = checked
        self.auto_action.setText("Stop Auto" if checked else "Start Auto")
        if checked:
            self.auto_move_timer = QTimer()
            self.auto_move_timer.timeout.connect(self.next_section)
            self.auto_move_timer.start(2000)
        else:
            if hasattr(self, 'auto_move_timer'):
                self.auto_move_timer.stop()

    def save_session(self):
        if not self.raw:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        if file_path:
            try:
                session_data = {
                    'file_path': self.raw.filenames[0],
                    'view_start_time': self.view_start_time,
                    'view_duration': self.view_duration,
                    'focus_start_time': self.focus_start_time,
                    'focus_duration': self.focus_duration,
                    'channel_indices': self.channel_indices,
                    'channel_colors': self.channel_colors,
                    'channel_offset': self.channel_offset,
                    'visible_channels': self.visible_channels,
                    'sensitivity': self.sensitivity,
                    'annotations_onset': list(self.annotation_manager.annotations.onset),
                    'annotations_duration': list(self.annotation_manager.annotations.duration),
                    'annotations_description': list(self.annotation_manager.annotations.description),
                    'annotations_colors': getattr(self.annotation_manager, 'annotation_colors', []),
                    'section_highlights': [list(highlight) for highlight in self.annotation_manager.section_highlights],
                    'timestamp': datetime.now().isoformat()
                }
                with open(file_path, 'w') as f:
                    json.dump(session_data, f, indent=2)
                self.status_label.setText(f"Session saved: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save:\n{str(e)}")

    def load_session(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    session_data = json.load(f)
                if session_data.get('file_path') and Path(session_data['file_path']).exists():
                    if not self.raw or self.raw.filenames[0] != session_data['file_path']:
                        self.load_file(session_data['file_path'])
                        return
                self.view_start_time = session_data.get('view_start_time', 0.0)
                self.view_duration = session_data.get('view_duration', 10.0)
                self.focus_start_time = session_data.get('focus_start_time', 0.0)
                self.focus_duration = session_data.get('focus_duration', 1.0)
                self.channel_indices = session_data.get('channel_indices', list(range(len(self.raw.ch_names))))
                self.channel_colors = session_data.get('channel_colors', {ch: '#e0e6ed' for ch in self.raw.ch_names})
                self.channel_offset = session_data.get('channel_offset', 0)
                self.visible_channels = session_data.get('visible_channels', 10)
                self.sensitivity = session_data.get('sensitivity', 50)
                self.annotation_manager.annotations = mne.Annotations(
                    onset=session_data.get('annotations_onset', []),
                    duration=session_data.get('annotations_duration', []),
                    description=session_data.get('annotations_description', [])
                )
                self.annotation_manager.annotation_colors = session_data.get('annotations_colors', [])
                # Handle both old and new highlight formats
                highlights = session_data.get('section_highlights', [])
                self.annotation_manager.section_highlights = []
                for highlight in highlights:
                    if len(highlight) < 5:
                        # Old format (ch_name, onset, duration, color) - add default description
                        highlight = list(highlight) + ['Highlight']
                    self.annotation_manager.section_highlights.append(tuple(highlight))
                self.sensitivity_slider.setValue(int(self.sensitivity))
                self.channel_combo.setCurrentText(str(self.visible_channels) if self.visible_channels < self.total_channels else "All")
                self.duration_input.setText(str(self.focus_duration))
                self.create_plot_items()
                self.update_scrollbars()
                self.perf_manager.request_update()
                self.status_label.setText(f"Session loaded: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load:\n{str(e)}")

    def auto_save(self):
        if not self.raw:
            return
        try:
            autosave_dir = Path("sessions/autosave")
            autosave_dir.mkdir(parents=True, exist_ok=True)
            session_data = {
                'file_path': self.raw.filenames[0],
                'view_start_time': self.view_start_time,
                'view_duration': self.view_duration,
                'focus_start_time': self.focus_start_time,
                'focus_duration': self.focus_duration,
                'channel_indices': self.channel_indices,
                'channel_colors': self.channel_colors,
                'channel_offset': self.channel_offset,
                'visible_channels': self.visible_channels,
                'sensitivity': self.sensitivity,
                'annotations_onset': list(self.annotation_manager.annotations.onset),
                'annotations_duration': list(self.annotation_manager.annotations.duration),
                'annotations_description': list(self.annotation_manager.annotations.description),
                'annotations_colors': getattr(self.annotation_manager, 'annotation_colors', []),
                'section_highlights': [list(highlight) for highlight in self.annotation_manager.section_highlights],
                'timestamp': datetime.now().isoformat()
            }
            autosave_file = autosave_dir / f"autosave_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(autosave_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            autosave_files = sorted(autosave_dir.glob("autosave_*.json"))
            for old_file in autosave_files[:-3]:
                old_file.unlink()
        except Exception as e:
            logging.error(f"Auto-save failed: {e}")

    def auto_export_csv(self):
        """Automatically export annotations to CSV when they change"""
        if not self.raw:
            return
        try:
            # Create auto-export directory
            auto_export_dir = Path("exports/auto")
            auto_export_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = auto_export_dir / f"auto_annotations_{timestamp}.csv"
            
            # Gather comprehensive viewer state including all requested information
            viewer_state = {
                'total_channels': self.total_channels,
                'visible_channels': self.visible_channels,
                'sensitivity': self.sensitivity,
                'view_duration': self.view_duration,
                'view_start_time': self.view_start_time,
                'focus_duration': self.focus_duration,
                'focus_start_time': self.focus_start_time,
                'channel_offset': self.channel_offset,
                'file_path': self.raw.filenames[0] if self.raw else '',
                'auto_sensitivity': self.auto_sensitivity,
                'sampling_frequency': self.raw.info['sfreq'] if self.raw else 0,
                'total_recording_duration': (self.raw.n_times / self.raw.info['sfreq']) if self.raw else 0,
                'selected_channel_names': [self.raw.ch_names[i] for i in self.channel_indices] if self.raw else [],
                'zoom_level': f"1:{self.view_duration}s",
                'current_time_window': f"{self.view_start_time:.2f}s - {self.view_start_time + self.view_duration:.2f}s",
                'focus_window': f"{self.focus_start_time:.2f}s - {self.focus_start_time + self.focus_duration:.2f}s",
                'performance_fps': getattr(self.perf_manager, 'fps', 0),
                'memory_usage_mb': getattr(self.perf_manager, 'memory_mb', 0),
                'cache_hit_rate': getattr(self.perf_manager, 'cache_hit_rate', 0),
            }
            
            # Export with current state
            self.annotation_manager.export_to_csv(str(file_path), viewer_state)
            
            # Keep only the last 10 auto-export files to prevent disk bloat
            auto_files = sorted(auto_export_dir.glob("auto_annotations_*.csv"))
            for old_file in auto_files[:-10]:
                try:
                    old_file.unlink()
                except Exception:
                    pass
                    
        except Exception as e:
            logging.error(f"Auto-export CSV failed: {e}")

    def export_csv(self):
        if (not self.annotation_manager.annotations or len(self.annotation_manager.annotations.onset) == 0) and not self.annotation_manager.section_highlights:
            QMessageBox.warning(self, "No Data", "No annotations to export.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Annotations", f"annotations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV Files (*.csv)")
        if file_path:
            try:
                # Gather current viewer state
                viewer_state = {
                    'total_channels': self.total_channels,
                    'visible_channels': self.visible_channels,
                    'sensitivity': self.sensitivity,
                    'view_duration': self.view_duration,
                    'view_start_time': self.view_start_time,
                    'focus_duration': self.focus_duration,
                    'channel_offset': self.channel_offset,
                    'file_path': self.raw.filenames[0] if self.raw else '',
                }
                self.annotation_manager.export_to_csv(file_path, viewer_state)
                self.status_label.setText(f"Exported: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export:\n{str(e)}")

    def import_csv(self):
        if not self.raw:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Annotations", "", "CSV Files (*.csv)")
        if file_path:
            try:
                df = pd.read_csv(file_path)
                for _, row in df.iterrows():
                    channel = row.get('channel')
                    if channel and pd.notna(channel):
                        # This is a channel highlight
                        description = row.get('description', 'Highlight')
                        color = row.get('color', 'red')
                        self.annotation_manager.add_highlight(row['channel'], row['onset'], row['duration'], color, description)
                    else:
                        # This is a general annotation
                        description = row.get('description', 'Annotation')
                        color = row.get('color', 'green')
                        self.annotation_manager.add_annotation(row['onset'], row['duration'], description, color)
                self.perf_manager.request_update()
                self.status_label.setText(f"Imported annotations from: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import:\n{str(e)}")

    def keyPressEvent(self, event):
        key = event.key()
        if not self.raw:
            super().keyPressEvent(event)
            return
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Plus:
                zoom_factor = 0.9
                self.view_duration = max(0.1, min(3600, self.view_duration * zoom_factor))
                self.update_time_combo_display()  # Update combo box to show current zoom
                self.update_scrollbars()
                self.perf_manager.request_update()
                self.auto_export_csv()  # Auto-export when zoom changes
            elif key == Qt.Key.Key_Minus:
                zoom_factor = 1.1
                self.view_duration = max(0.1, min(3600, self.view_duration * zoom_factor))
                self.update_time_combo_display()  # Update combo box to show current zoom
                self.update_scrollbars()
                self.perf_manager.request_update()
                self.auto_export_csv()  # Auto-export when zoom changes
            else:
                super().keyPressEvent(event)
            return
        if key == Qt.Key.Key_Left:
            # Move time axis to the left (earlier time), EEG should move left too
            self._navigate_preserving_zoom('left')
        elif key == Qt.Key.Key_Right:
            # Move time axis to the right (later time), EEG should move right too
            self._navigate_preserving_zoom('right')
        elif key == Qt.Key.Key_Up:
            self.channel_offset = max(0, self.channel_offset - 1)
            self.vscroll.setValue(self.channel_offset)
            self.create_plot_items()
            self.perf_manager.request_update()
        elif key == Qt.Key.Key_Down:
            max_offset = max(0, self.total_channels - self.visible_channels)
            self.channel_offset = min(max_offset, self.channel_offset + 1)
            self.vscroll.setValue(self.channel_offset)
            self.create_plot_items()
            self.perf_manager.request_update()
        elif key == Qt.Key.Key_Space:
            self.auto_move_active = not self.auto_move_active
            self.toggle_auto_move(self.auto_move_active)
        elif key == Qt.Key.Key_G:
            self._previous_section_preserving_zoom()
        elif key == Qt.Key.Key_H:
            self._next_section_preserving_zoom()
        else:
            super().keyPressEvent(event)

    def on_focus_moved(self, region):
        start, end = region.getRegion()
        self.focus_start_time = start
        self.focus_duration = end - start
        self.duration_input.setText(f"{self.focus_duration:.1f}")

    def wheelEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if not self.raw or event.isAccepted():
            return
        delta = event.angleDelta().y()
        if modifiers == Qt.KeyboardModifier.NoModifier:
            if delta > 0:
                self.channel_offset = max(0, self.channel_offset - 1)
            else:
                self.channel_offset = min(self.total_channels - self.visible_channels, self.channel_offset + 1)
            self.vscroll.setValue(self.channel_offset)
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier:
            # FIX: Center zoom on mouse position
            mouse_point = self.view_box.mapSceneToView(event.scenePos())
            old_start = self.view_start_time
            old_duration = self.view_duration
            zoom_factor = 0.9 if delta > 0 else 1.1
            new_duration = max(0.1, min(3600, old_duration * zoom_factor))
            rel_pos = (mouse_point.x() - old_start) / old_duration if old_duration > 0 else 0.5
            new_start = mouse_point.x() - rel_pos * new_duration
            max_time = self.raw.n_times / self.raw.info['sfreq'] if self.raw else 0
            new_start = max(0, min(new_start, max_time - new_duration))
            self.view_start_time = new_start
            self.view_duration = new_duration
            self.update_time_combo_display()
            self.update_scrollbars()
            self.perf_manager.request_update()
            self.auto_export_csv()  # Auto-export when zoom changes
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier:
            time_shift = (self.view_duration * 0.1) * (-1 if delta > 0 else 1)
            self.view_start_time = max(0, self.view_start_time + time_shift)
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.view_start_time = min(max_time - self.view_duration, self.view_start_time)
            self.update_scrollbars()
            self.perf_manager.request_update()
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Clinical EEG Viewer")
    viewer = EDFViewer()
    viewer.show()
    sys.exit(app.exec())