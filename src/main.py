"""
EDF Viewer - Main Application Entry Point
High-performance clinical EEG viewer with advanced features and optimizations.
"""

import sys
import os
import gc
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

import mne
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt6.QtGui import QAction, QKeySequence, QFont, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLineEdit, QLabel, QComboBox, QMessageBox,
    QToolBar, QMenuBar, QSplitter, QScrollBar, QStatusBar, QMenu, QInputDialog
)

# Configure PyQtGraph for maximum performance
from config import PERF_CONFIG, NUMBA_AVAILABLE, APP_NAME, APP_VERSION, DEFAULT_VIEW_DURATION
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

# Import our modules
from config import SessionState, Annotation
from utils.validation import setup_logging, ValidationUtils, ErrorHandlingUtils
from utils.performance import MemoryOptimizer, ThreadPoolManager
from core.data_processing import (
    DataLoaderThread, HighPerformanceDataCache, 
    HighPerformanceSignalProcessor, PerformanceManager
)
from ui.components import theme_manager, StatusBar, LoadingOverlay, apply_dark_theme
from ui.dialogs import (
    ChannelSelectionDialog, ChannelColorDialog, ScreenshotDialog,
    AnnotationDialog, HighlightSectionDialog
)

class CustomViewBox(pg.ViewBox):
    """Custom ViewBox with enhanced mouse and keyboard interactions"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.viewer = None  # Will be set by the main viewer
    
    def mousePressEvent(self, event):
        """Handle mouse press events for annotation creation"""
        if event.button() == Qt.MouseButton.RightButton and self.viewer:
            # Right-click to create annotation
            pos = self.mapSceneToView(event.scenePos())
            self.viewer.create_annotation_at_position(pos.x())
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def wheelEvent(self, event):
        """Enhanced wheel event handling for zoom and scroll"""
        if not self.viewer:
            super().wheelEvent(event)
            return
        
        modifiers = QApplication.keyboardModifiers()
        delta = event.angleDelta().y()
        
        # Ctrl + wheel: time zoom
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            zoom_factor = 0.9 if delta > 0 else 1.1
            self.viewer.zoom_time(zoom_factor)
            event.accept()
        # Shift + wheel: amplitude zoom
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            zoom_factor = 1.1 if delta > 0 else 0.9
            self.viewer.zoom_amplitude(zoom_factor)
            event.accept()
        # Alt + wheel: horizontal scroll
        elif modifiers == Qt.KeyboardModifier.AltModifier:
            scroll_factor = 0.1 * (-1 if delta > 0 else 1)
            self.viewer.scroll_time(scroll_factor)
            event.accept()
        else:
            super().wheelEvent(event)

class AnnotationManager:
    """Centralized annotation management"""
    
    def __init__(self):
        self.annotations: List[Annotation] = []
        self._annotation_items = []  # Visual items
    
    def add_annotation(self, annotation: Annotation) -> bool:
        """Add new annotation"""
        try:
            self.annotations.append(annotation)
            logging.info(f"Added annotation: {annotation.description} at {annotation.start_time}s")
            return True
        except Exception as e:
            logging.error(f"Failed to add annotation: {e}")
            return False
    
    def remove_annotation(self, index: int) -> bool:
        """Remove annotation by index"""
        try:
            if 0 <= index < len(self.annotations):
                removed = self.annotations.pop(index)
                logging.info(f"Removed annotation: {removed.description}")
                return True
            return False
        except Exception as e:
            logging.error(f"Failed to remove annotation: {e}")
            return False
    
    def get_annotations_in_range(self, start_time: float, end_time: float) -> List[Annotation]:
        """Get annotations within time range"""
        return [
            ann for ann in self.annotations
            if (ann.start_time < end_time and 
                ann.start_time + ann.duration > start_time)
        ]
    
    def export_annotations(self, file_path: str) -> bool:
        """Export annotations to JSON file"""
        try:
            data = [
                {
                    'start_time': ann.start_time,
                    'duration': ann.duration,
                    'description': ann.description,
                    'color': ann.color,
                    'timestamp': ann.timestamp,
                    'channel': ann.channel,
                    'notes': ann.notes
                }
                for ann in self.annotations
            ]
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"Exported {len(self.annotations)} annotations to {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to export annotations: {e}")
            return False
    
    def import_annotations(self, file_path: str) -> bool:
        """Import annotations from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            imported_count = 0
            for item in data:
                annotation = Annotation(
                    start_time=item['start_time'],
                    duration=item['duration'],
                    description=item['description'],
                    color=item['color'],
                    timestamp=item['timestamp'],
                    channel=item.get('channel'),
                    notes=item.get('notes', '')
                )
                self.annotations.append(annotation)
                imported_count += 1
            
            logging.info(f"Imported {imported_count} annotations from {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to import annotations: {e}")
            return False

class EDFViewer(QMainWindow):
    """Main EDF Viewer application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setGeometry(100, 100, 1400, 900)
        
        # Core data and state
        self.raw = None
        self.channel_indices = []
        self.channel_colors = {}
        self.view_start_time = 0.0
        self.view_duration = DEFAULT_VIEW_DURATION
        self.channel_offset = 0
        self.total_channels = 0
        self.visible_channels = 10
        self.sensitivity = 50
        
        # High-performance components
        self.data_cache = HighPerformanceDataCache()
        self.signal_processor = HighPerformanceSignalProcessor()
        self.perf_manager = PerformanceManager(self)
        self.annotation_manager = AnnotationManager()
        self.thread_pool = ThreadPoolManager()
        
        # UI components
        self.plot_widget = None
        self.plot_items = {}
        self.annotation_items = []
        self.loading_overlay = None
        
        # Timers and threads
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start(300000)  # 5 minutes
        
        # Build UI
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_status_bar()
        self.connect_signals()
        
        # Apply theme
        apply_dark_theme(QApplication.instance())
        
        logging.info(f"{APP_NAME} v{APP_VERSION} initialized successfully")
    
    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Left sidebar for controls
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Main plot area
        plot_area = self.create_plot_area()
        main_layout.addWidget(plot_area, stretch=1)
        
        # Loading overlay
        self.loading_overlay = LoadingOverlay(central_widget)
    
    def create_sidebar(self) -> QWidget:
        """Create the control sidebar"""
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setSpacing(15)
        
        # Title
        title_label = QLabel(APP_NAME)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(title_label)
        
        # File controls
        file_group = self.create_file_controls()
        sidebar_layout.addWidget(file_group)
        
        # View controls
        view_group = self.create_view_controls()
        sidebar_layout.addWidget(view_group)
        
        # Channel controls
        channel_group = self.create_channel_controls()
        sidebar_layout.addWidget(channel_group)
        
        # Annotation controls
        annotation_group = self.create_annotation_controls()
        sidebar_layout.addWidget(annotation_group)
        
        sidebar_layout.addStretch()
        return sidebar_widget
    
    def create_file_controls(self) -> QWidget:
        """Create file operation controls"""
        from ui.components import ModernGroupBox, ModernButton
        
        group = ModernGroupBox("File Operations")
        layout = QVBoxLayout()
        
        self.open_button = ModernButton("Open EDF File")
        self.open_button.clicked.connect(self.open_file)
        layout.addWidget(self.open_button)
        
        self.recent_files_combo = QComboBox()
        self.recent_files_combo.addItem("Recent Files...")
        layout.addWidget(self.recent_files_combo)
        
        self.export_button = ModernButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        self.export_button.setEnabled(False)
        layout.addWidget(self.export_button)
        
        group.setLayout(layout)
        return group
    
    def create_view_controls(self) -> QWidget:
        """Create view control widgets"""
        from ui.components import ModernGroupBox, ModernButton, ModernSlider
        
        group = ModernGroupBox("View Controls")
        layout = QVBoxLayout()
        
        # Time window controls
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Time Window:"))
        self.time_window_combo = QComboBox()
        self.time_window_combo.addItems(["1s", "2s", "5s", "10s", "20s", "30s", "60s"])
        self.time_window_combo.setCurrentText("10s")
        self.time_window_combo.currentTextChanged.connect(self.change_time_window)
        time_layout.addWidget(self.time_window_combo)
        layout.addLayout(time_layout)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_button = ModernButton("◀ Prev")
        self.prev_button.clicked.connect(self.previous_window)
        self.next_button = ModernButton("Next ▶")
        self.next_button.clicked.connect(self.next_window)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        layout.addLayout(nav_layout)
        
        # Sensitivity control
        layout.addWidget(QLabel("Sensitivity (µV):"))
        self.sensitivity_slider = ModernSlider()
        self.sensitivity_slider.setRange(1, 200)
        self.sensitivity_slider.setValue(50)
        self.sensitivity_slider.valueChanged.connect(self.change_sensitivity)
        layout.addWidget(self.sensitivity_slider)
        
        # Auto-scroll
        self.auto_scroll_button = ModernButton("Auto Scroll")
        self.auto_scroll_button.setCheckable(True)
        self.auto_scroll_button.clicked.connect(self.toggle_auto_scroll)
        layout.addWidget(self.auto_scroll_button)
        
        group.setLayout(layout)
        return group
    
    def create_channel_controls(self) -> QWidget:
        """Create channel control widgets"""
        from ui.components import ModernGroupBox, ModernButton
        
        group = ModernGroupBox("Channel Controls")
        layout = QVBoxLayout()
        
        # Channel selection
        self.select_channels_button = ModernButton("Select Channels")
        self.select_channels_button.clicked.connect(self.select_channels)
        self.select_channels_button.setEnabled(False)
        layout.addWidget(self.select_channels_button)
        
        # Channel colors
        self.channel_colors_button = ModernButton("Channel Colors")
        self.channel_colors_button.clicked.connect(self.set_channel_colors)
        self.channel_colors_button.setEnabled(False)
        layout.addWidget(self.channel_colors_button)
        
        # Visible channels info
        self.channels_info_label = QLabel("Channels: 0/0")
        layout.addWidget(self.channels_info_label)
        
        group.setLayout(layout)
        return group
    
    def create_annotation_controls(self) -> QWidget:
        """Create annotation control widgets"""
        from ui.components import ModernGroupBox, ModernButton
        
        group = ModernGroupBox("Annotations")
        layout = QVBoxLayout()
        
        self.add_annotation_button = ModernButton("Add Annotation")
        self.add_annotation_button.clicked.connect(self.add_annotation)
        self.add_annotation_button.setEnabled(False)
        layout.addWidget(self.add_annotation_button)
        
        self.manage_annotations_button = ModernButton("Manage Annotations")
        self.manage_annotations_button.clicked.connect(self.manage_annotations)
        self.manage_annotations_button.setEnabled(False)
        layout.addWidget(self.manage_annotations_button)
        
        group.setLayout(layout)
        return group
    
    def create_plot_area(self) -> QWidget:
        """Create the main plotting area"""
        plot_widget = QWidget()
        layout = QVBoxLayout(plot_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main plot
        self.plot_widget = pg.PlotWidget(viewBox=CustomViewBox())
        self.plot_widget.getViewBox().viewer = self
        self.plot_widget.setLabel('left', 'Channels')
        self.plot_widget.setLabel('bottom', 'Time (s)')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        layout.addWidget(self.plot_widget)
        
        # Horizontal scrollbar
        self.hscroll = QScrollBar(Qt.Orientation.Horizontal)
        self.hscroll.valueChanged.connect(self.scroll_horizontal)
        layout.addWidget(self.hscroll)
        
        # Vertical scrollbar for channels
        vscroll_layout = QHBoxLayout()
        layout.addLayout(vscroll_layout)
        
        vscroll_layout.addStretch()
        self.vscroll = QScrollBar(Qt.Orientation.Vertical)
        self.vscroll.valueChanged.connect(self.scroll_vertical)
        vscroll_layout.addWidget(self.vscroll)
        
        return plot_widget
    
    def setup_menus(self):
        """Setup application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        open_action = QAction('Open EDF File...', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('Export Data...', self)
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        screenshot_action = QAction('Take Screenshot...', self)
        screenshot_action.triggered.connect(self.take_screenshot)
        file_menu.addAction(screenshot_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        theme_menu = view_menu.addMenu('Theme')
        for theme_name in theme_manager.themes.keys():
            action = QAction(theme_name.title(), self)
            action.triggered.connect(lambda checked, name=theme_name: theme_manager.set_theme(name))
            theme_menu.addAction(action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        performance_action = QAction('Performance Monitor', self)
        performance_action.triggered.connect(self.show_performance_monitor)
        tools_menu.addAction(performance_action)
        
        memory_action = QAction('Optimize Memory', self)
        memory_action.triggered.connect(self.optimize_memory)
        tools_menu.addAction(memory_action)
    
    def setup_toolbar(self):
        """Setup application toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add common actions to toolbar
        toolbar.addAction("Open", self.open_file)
        toolbar.addSeparator()
        toolbar.addAction("Previous", self.previous_window)
        toolbar.addAction("Next", self.next_window)
        toolbar.addSeparator()
        toolbar.addAction("Screenshot", self.take_screenshot)
    
    def setup_status_bar(self):
        """Setup status bar with performance indicators"""
        # Use Qt's built-in status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        # Create our custom status widget
        self.status_bar = StatusBar()
        status_bar.addPermanentWidget(self.status_bar)
    
    def connect_signals(self):
        """Connect various signals"""
        # Theme manager subscription
        theme_manager.subscribe(self.apply_theme)
    
    def apply_theme(self, theme: dict):
        """Apply theme to main window"""
        colors = theme['colors']
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {colors['primary_bg']};
                color: {colors['primary_text']};
            }}
        """)
        
        # Update plot widget colors
        if self.plot_widget:
            self.plot_widget.setBackground(colors['primary_bg'])
    
    def open_file(self):
        """Open EDF file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open EDF File", "", 
            "EDF Files (*.edf *.bdf);;All Files (*)"
        )
        
        if file_path:
            self.load_edf_file(file_path)
    
    def load_edf_file(self, file_path: str):
        """Load EDF file asynchronously"""
        self.loading_overlay.show_loading("Loading EDF file...")
        
        # Disable UI during loading
        self.setEnabled(False)
        
        # Start data loading thread
        self.data_loader = DataLoaderThread(file_path)
        self.data_loader.data_loaded.connect(self.on_data_loaded)
        self.data_loader.error_occurred.connect(self.on_data_load_error)
        self.data_loader.progress_updated.connect(self.on_load_progress)
        self.data_loader.start()
    
    def on_data_loaded(self, raw):
        """Handle successful data loading"""
        try:
            self.raw = raw
            self.total_channels = len(raw.ch_names)
            self.channel_indices = list(range(min(self.visible_channels, self.total_channels)))
            
            # Initialize channel colors
            default_color = theme_manager.get_color('primary_text')
            self.channel_colors = {ch: default_color for ch in raw.ch_names}
            
            # Update UI
            self.update_ui_after_load()
            self.update_plot()
            
            # Update status
            file_name = Path(self.data_loader.file_path).name
            self.status_bar.update_file_status(file_name)
            self.status_bar.update_channels(len(self.channel_indices), self.total_channels)
            
            logging.info(f"Successfully loaded EDF file with {self.total_channels} channels")
            
        except Exception as e:
            ErrorHandlingUtils.show_user_error(
                self, "Loading Error", 
                f"Failed to process loaded data: {str(e)}"
            )
            logging.error(f"Data processing error: {e}", exc_info=True)
        finally:
            self.loading_overlay.hide_loading()
            self.setEnabled(True)
    
    def on_data_load_error(self, error_message: str):
        """Handle data loading error"""
        ErrorHandlingUtils.show_user_error(
            self, "Loading Error", error_message
        )
        self.loading_overlay.hide_loading()
        self.setEnabled(True)
    
    def on_load_progress(self, progress: int):
        """Handle loading progress updates"""
        if progress < 100:
            self.loading_overlay.show_loading(f"Loading EDF file... {progress}%")
    
    def update_ui_after_load(self):
        """Update UI elements after successful file load"""
        # Enable controls
        self.export_button.setEnabled(True)
        self.select_channels_button.setEnabled(True)
        self.channel_colors_button.setEnabled(True)
        self.add_annotation_button.setEnabled(True)
        self.manage_annotations_button.setEnabled(True)
        
        # Update scrollbars
        self.update_scrollbars()
        
        # Update channel info
        self.update_channel_info()
    
    def update_scrollbars(self):
        """Update scrollbar ranges and positions"""
        if not self.raw:
            return
        
        # Horizontal scrollbar (time)
        max_time = self.raw.n_times / self.raw.info['sfreq']
        max_scroll = max(0, max_time - self.view_duration)
        
        self.hscroll.setRange(0, int(max_scroll * 100))
        self.hscroll.setValue(int(self.view_start_time * 100))
        
        # Vertical scrollbar (channels)
        max_channel_offset = max(0, self.total_channels - self.visible_channels)
        self.vscroll.setRange(0, max_channel_offset)
        self.vscroll.setValue(self.channel_offset)
    
    def update_channel_info(self):
        """Update channel information display"""
        visible = len(self.channel_indices)
        total = self.total_channels
        self.channels_info_label.setText(f"Channels: {visible}/{total}")
    
    def update_plot(self):
        """Update the main EEG plot"""
        if not self.raw or not self.channel_indices:
            return
        
        start_time = time.time()
        
        try:
            # Clear existing plot items
            self.plot_widget.clear()
            self.plot_items.clear()
            
            # Get data for current view
            data = self.get_plot_data()
            
            if data is None:
                return
            
            # Create plot items for visible channels
            self.create_channel_plots(data)
            
            # Add annotations
            self.update_annotations()
            
            # Update time axis
            self.update_time_axis()
            
            # Record frame time for performance monitoring
            frame_time = time.time() - start_time
            self.perf_manager.record_frame_time(frame_time)
            
            # Update status
            self.status_bar.update_position(self.view_start_time)
            
        except Exception as e:
            logging.error(f"Plot update failed: {e}", exc_info=True)
    
    def get_plot_data(self) -> Optional[np.ndarray]:
        """Get data for current plot view with caching"""
        if not self.raw:
            return None
        
        # Calculate sample range
        sfreq = self.raw.info['sfreq']
        start_sample = int(self.view_start_time * sfreq)
        end_sample = int((self.view_start_time + self.view_duration) * sfreq)
        end_sample = min(end_sample, self.raw.n_times)
        
        if start_sample >= end_sample:
            return None
        
        # Create cache key
        visible_channels = self.channel_indices[self.channel_offset:self.channel_offset + self.visible_channels]
        cache_key = f"data_{start_sample}_{end_sample}_{hash(tuple(visible_channels))}"
        
        # Try to get from cache
        cached_data = self.data_cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            # Get data from raw object
            data = self.raw[visible_channels, start_sample:end_sample][0]
            
            # Apply downsampling for performance
            target_points = self.perf_manager.get_recommended_points(
                PERF_CONFIG.get('max_points_per_curve', 10000)
            )
            
            if data.shape[1] > target_points:
                data = self.signal_processor.downsample_data(data, target_points)
            
            # Cache the data
            self.data_cache.put(cache_key, data)
            
            return data
            
        except Exception as e:
            logging.error(f"Failed to get plot data: {e}")
            return None
    
    def create_channel_plots(self, data: np.ndarray):
        """Create plot items for each visible channel"""
        if data is None:
            return
        
        sfreq = self.raw.info['sfreq']
        time_vector = np.linspace(
            self.view_start_time, 
            self.view_start_time + self.view_duration,
            data.shape[1]
        )
        
        visible_channels = self.channel_indices[self.channel_offset:self.channel_offset + self.visible_channels]
        
        for i, ch_idx in enumerate(visible_channels):
            if i >= data.shape[0]:
                break
            
            ch_name = self.raw.ch_names[ch_idx]
            ch_data = data[i] * (1000 / self.sensitivity) + (self.visible_channels - i - 1) * 10
            
            # Get channel color
            color = self.channel_colors.get(ch_name, theme_manager.get_color('primary_text'))
            
            # Create plot item
            plot_item = self.plot_widget.plot(
                time_vector, ch_data,
                pen=pg.mkPen(color=color, width=1),
                name=ch_name
            )
            
            self.plot_items[ch_name] = plot_item
    
    def update_annotations(self):
        """Update annotation display"""
        # Clear existing annotation items
        for item in self.annotation_items:
            self.plot_widget.removeItem(item)
        self.annotation_items.clear()
        
        # Get annotations in current view
        annotations = self.annotation_manager.get_annotations_in_range(
            self.view_start_time,
            self.view_start_time + self.view_duration
        )
        
        # Create annotation items
        for annotation in annotations:
            self.create_annotation_item(annotation)
    
    def create_annotation_item(self, annotation: Annotation):
        """Create visual item for annotation"""
        try:
            # Create rectangle for annotation
            rect = pg.QtWidgets.QGraphicsRectItem(
                annotation.start_time,
                -1,
                annotation.duration,
                self.visible_channels * 10 + 2
            )
            
            # Set appearance
            color = pg.mkColor(annotation.color)
            color.setAlpha(50)  # Semi-transparent
            rect.setBrush(pg.mkBrush(color))
            rect.setPen(pg.mkPen(annotation.color, width=2))
            
            # Add to plot
            self.plot_widget.addItem(rect)
            self.annotation_items.append(rect)
            
            # Add text label
            text_item = pg.TextItem(
                annotation.description,
                color=annotation.color,
                anchor=(0, 1)
            )
            text_item.setPos(annotation.start_time, self.visible_channels * 10)
            self.plot_widget.addItem(text_item)
            self.annotation_items.append(text_item)
            
        except Exception as e:
            logging.error(f"Failed to create annotation item: {e}")
    
    def update_time_axis(self):
        """Update time axis labels and range"""
        if self.plot_widget:
            self.plot_widget.setXRange(
                self.view_start_time, 
                self.view_start_time + self.view_duration,
                padding=0
            )
            self.plot_widget.setYRange(-2, self.visible_channels * 10 + 2, padding=0)
    
    # Navigation methods
    def change_time_window(self, window_text: str):
        """Change time window duration"""
        try:
            self.view_duration = float(window_text.rstrip('s'))
            self.update_scrollbars()
            self.update_plot()
        except ValueError:
            logging.error(f"Invalid time window: {window_text}")
    
    def previous_window(self):
        """Navigate to previous time window"""
        if self.raw:
            self.view_start_time = max(0, self.view_start_time - self.view_duration)
            self.update_scrollbars()
            self.update_plot()
    
    def next_window(self):
        """Navigate to next time window"""
        if self.raw:
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.view_start_time = min(
                max_time - self.view_duration,
                self.view_start_time + self.view_duration
            )
            self.update_scrollbars()
            self.update_plot()
    
    def scroll_horizontal(self, value: int):
        """Handle horizontal scrollbar movement"""
        self.view_start_time = value / 100.0
        self.update_plot()
    
    def scroll_vertical(self, value: int):
        """Handle vertical scrollbar movement"""
        self.channel_offset = value
        self.update_plot()
    
    def change_sensitivity(self, value: int):
        """Change amplitude sensitivity"""
        self.sensitivity = value
        self.update_plot()
    
    def zoom_time(self, factor: float):
        """Zoom time axis"""
        new_duration = self.view_duration * factor
        new_duration = max(0.1, min(3600, new_duration))  # Limit between 0.1s and 1 hour
        self.view_duration = new_duration
        self.update_scrollbars()
        self.update_plot()
    
    def zoom_amplitude(self, factor: float):
        """Zoom amplitude"""
        new_sensitivity = self.sensitivity * factor
        new_sensitivity = max(1, min(1000, new_sensitivity))
        self.sensitivity = int(new_sensitivity)
        self.sensitivity_slider.setValue(self.sensitivity)
        self.update_plot()
    
    def scroll_time(self, factor: float):
        """Scroll in time"""
        time_shift = self.view_duration * factor
        if self.raw:
            max_time = self.raw.n_times / self.raw.info['sfreq']
            self.view_start_time = max(0, min(
                max_time - self.view_duration,
                self.view_start_time + time_shift
            ))
            self.update_scrollbars()
            self.update_plot()
    
    def toggle_auto_scroll(self, checked: bool):
        """Toggle auto-scroll mode"""
        # Auto-scroll implementation would go here
        logging.info(f"Auto-scroll {'enabled' if checked else 'disabled'}")
    
    # Dialog methods
    def select_channels(self):
        """Open channel selection dialog"""
        if not self.raw:
            return
        
        dialog = ChannelSelectionDialog(self.raw, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.channel_indices = dialog.get_selected_channels()
            self.channel_offset = 0  # Reset offset
            self.update_channel_info()
            self.update_scrollbars()
            self.update_plot()
    
    def set_channel_colors(self):
        """Open channel color dialog"""
        if not self.raw:
            return
        
        dialog = ChannelColorDialog(self.raw, self.channel_colors, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.channel_colors = dialog.get_channel_colors()
            self.update_plot()
    
    def take_screenshot(self):
        """Open screenshot dialog"""
        dialog = ScreenshotDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_screenshot_settings()
            self.save_screenshot(settings)
    
    def save_screenshot(self, settings: Dict[str, Any]):
        """Save screenshot with given settings"""
        try:
            # Get save location
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Screenshot",
                f"{settings['filename']}.{settings['format'].lower()}",
                f"{settings['format']} Files (*.{settings['format'].lower()})"
            )
            
            if file_path:
                # Capture plot widget
                pixmap = self.plot_widget.grab()
                
                # Save with quality settings
                if settings['format'].upper() == 'JPEG':
                    pixmap.save(file_path, settings['format'], settings['quality'])
                else:
                    pixmap.save(file_path, settings['format'])
                
                logging.info(f"Screenshot saved: {file_path}")
                
        except Exception as e:
            ErrorHandlingUtils.show_user_error(
                self, "Screenshot Error",
                f"Failed to save screenshot: {str(e)}"
            )
    
    def add_annotation(self):
        """Add new annotation"""
        dialog = AnnotationDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            annotation = dialog.get_annotation()
            self.annotation_manager.add_annotation(annotation)
            self.update_annotations()
    
    def manage_annotations(self):
        """Open annotation management dialog"""
        # This would open a comprehensive annotation manager
        ErrorHandlingUtils.show_user_error(
            self, "Not Implemented",
            "Annotation management dialog not yet implemented.",
            "information"
        )
    
    def create_annotation_at_position(self, time_pos: float):
        """Create annotation at specific time position"""
        if not self.raw:
            return
        
        # Quick annotation creation
        text, ok = QInputDialog.getText(
            self, "Quick Annotation",
            f"Add annotation at {time_pos:.2f}s:"
        )
        
        if ok and text:
            annotation = Annotation(
                start_time=time_pos,
                duration=1.0,
                description=text,
                color="#ff0000",
                timestamp=datetime.now().isoformat()
            )
            self.annotation_manager.add_annotation(annotation)
            self.update_annotations()
    
    # Utility methods
    def export_data(self):
        """Export current data view"""
        if not self.raw:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "",
            "CSV Files (*.csv);;NumPy Files (*.npy);;All Files (*)"
        )
        
        if file_path:
            try:
                data = self.get_plot_data()
                if data is not None:
                    if file_path.endswith('.csv'):
                        np.savetxt(file_path, data.T, delimiter=',')
                    elif file_path.endswith('.npy'):
                        np.save(file_path, data)
                    
                    logging.info(f"Data exported: {file_path}")
                
            except Exception as e:
                ErrorHandlingUtils.show_user_error(
                    self, "Export Error",
                    f"Failed to export data: {str(e)}"
                )
    
    def show_performance_monitor(self):
        """Show performance monitoring dialog"""
        stats = self.perf_manager.monitor.get_performance_summary()
        cache_stats = self.data_cache.get_stats()
        
        message = f"""Performance Statistics:
        
Average Render Time: {stats['avg_render_time']:.3f}s
Maximum Render Time: {stats['max_render_time']:.3f}s
Frame Count: {stats['frame_count']}

Memory Usage: {stats['avg_memory_usage']:.1f}MB (avg)
Maximum Memory: {stats['max_memory_usage']:.1f}MB

Cache Hit Rate: {cache_stats['hit_rate']:.1%}
Cache Utilization: {cache_stats['utilization']:.1%}
Cache Size: {cache_stats['size_mb']:.1f}MB / {cache_stats['max_size_mb']}MB
"""
        
        ErrorHandlingUtils.show_user_error(
            self, "Performance Monitor", message, "information"
        )
    
    def optimize_memory(self):
        """Optimize memory usage"""
        try:
            # Clear caches
            self.data_cache.clear()
            
            # Force garbage collection
            memory_freed = MemoryOptimizer.optimize_memory_usage()
            
            ErrorHandlingUtils.show_user_error(
                self, "Memory Optimization",
                f"Memory optimization completed.\n"
                f"Approximately {memory_freed:.1f}MB freed.",
                "information"
            )
            
        except Exception as e:
            ErrorHandlingUtils.show_user_error(
                self, "Optimization Error",
                f"Memory optimization failed: {str(e)}"
            )
    
    def auto_save(self):
        """Auto-save session state"""
        if not self.raw:
            return
        
        try:
            # Create session state
            session_state = SessionState(
                file_path=self.data_loader.file_path if hasattr(self, 'data_loader') else "",
                view_start_time=self.view_start_time,
                view_duration=self.view_duration,
                focus_start_time=0.0,  # Not implemented yet
                focus_duration=1.0,    # Not implemented yet
                channel_indices=self.channel_indices,
                channel_colors=self.channel_colors,
                channel_offset=self.channel_offset,
                visible_channels=self.visible_channels,
                sensitivity=self.sensitivity,
                annotations=[],  # Would serialize annotations
                timestamp=datetime.now().isoformat()
            )
            
            # Save to auto-save file
            auto_save_path = Path("auto_save_session.json")
            with open(auto_save_path, 'w') as f:
                json.dump(session_state.__dict__, f, indent=2)
            
            logging.debug("Auto-save completed")
            
        except Exception as e:
            logging.error(f"Auto-save failed: {e}")
    
    def closeEvent(self, event):
        """Handle application close"""
        try:
            # Cleanup resources
            if hasattr(self, 'data_loader') and self.data_loader.isRunning():
                self.data_loader.cancel()
                self.data_loader.wait(5000)  # Wait up to 5 seconds
            
            self.data_cache.cleanup()
            self.perf_manager.cleanup()
            self.thread_pool.shutdown()
            
            # Final memory cleanup
            MemoryOptimizer.optimize_memory_usage()
            
            logging.info("Application shutting down cleanly")
            
        except Exception as e:
            logging.error(f"Cleanup error: {e}")
        
        event.accept()

def main() -> int:
    """Main application entry point"""
    try:
        # Initialize logging first
        setup_logging()
        logging.info("=== EDF Viewer Application Starting ===")
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setApplicationVersion(APP_VERSION)
        
        # Log system information
        memory_info = MemoryOptimizer.get_memory_info()
        logging.info(f"Initial memory usage: {memory_info['rss']:.1f}MB")
        
        # Create and show main window
        viewer = EDFViewer()
        viewer.show()
        
        # Run application event loop
        try:
            result = app.exec()
            logging.info(f"Application exited with code: {result}")
            return result
        except Exception as e:
            logging.error(f"Application event loop error: {e}", exc_info=True)
            return 1
            
    except Exception as e:
        logging.error(f"Critical error in main: {e}", exc_info=True)
        try:
            ErrorHandlingUtils.show_user_error(
                None, "Critical Error", 
                f"Application startup failed:\n{str(e)}",
                "critical"
            )
        except:
            print(f"Critical error: {e}")
        return 1

if __name__ == "__main__":
    try:
        # Initialize logging before anything else
        setup_logging()
        logging.info("=== EDF Viewer Application Starting ===")
        
        # Log system information
        memory_info = MemoryOptimizer.get_memory_info()
        logging.info(f"Initial memory usage: {memory_info['rss']:.1f}MB")
        
        # Run application
        exit_code = main()
        
        # Final cleanup and logging
        final_memory = MemoryOptimizer.get_memory_info()
        logging.info(f"Final memory usage: {final_memory['rss']:.1f}MB")
        logging.info(f"=== EDF Viewer Application Exiting with code {exit_code} ===")
        
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        sys.exit(1)