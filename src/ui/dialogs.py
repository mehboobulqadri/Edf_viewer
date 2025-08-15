"""
Dialog Classes for EDF Viewer
All dialog windows including channel selection, color settings, screenshots, annotations, etc.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QDoubleValidator, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSlider, QCheckBox, QRadioButton,
    QListWidget, QListWidgetItem, QTextEdit, QDoubleSpinBox, QSpinBox,
    QColorDialog, QFileDialog, QMessageBox, QGroupBox, QSplitter,
    QButtonGroup, QTabWidget, QWidget, QProgressDialog
)

from ui.components import ModernButton, ModernGroupBox, ModernLabel, theme_manager
from utils.validation import ValidationUtils, ErrorHandlingUtils
from config import Annotation

class ChannelSelectionDialog(QDialog):
    """Dialog for selecting and reordering channels"""
    
    def __init__(self, raw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Selection")
        self.resize(600, 800)
        self.raw = raw
        self.selected_channels = parent.channel_indices if hasattr(parent, 'channel_indices') else list(range(len(raw.ch_names)))
        self.setup_ui()
        self.populate_channels()
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
        
    def setup_ui(self):
        """Setup the dialog UI"""
        main_layout = QVBoxLayout(self)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Available channels group
        available_group = ModernGroupBox("Available Channels")
        available_layout = QVBoxLayout()
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        available_layout.addWidget(self.available_list)
        available_group.setLayout(available_layout)
        
        # Selected channels group
        selected_group = ModernGroupBox("Selected Channels (Drag to reorder)")
        selected_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.selected_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        selected_layout.addWidget(self.selected_list)
        selected_group.setLayout(selected_layout)
        
        splitter.addWidget(available_group)
        splitter.addWidget(selected_group)
        splitter.setSizes([300, 500])
        
        # Buttons
        button_layout = QHBoxLayout()
        self.add_all_button = ModernButton("Add All")
        self.add_button = ModernButton("→ Add")
        self.remove_button = ModernButton("← Remove")
        self.remove_all_button = ModernButton("Remove All")
        self.ok_button = ModernButton("OK")
        self.cancel_button = ModernButton("Cancel")
        
        button_layout.addWidget(self.add_all_button)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.remove_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # Connect signals
        self.add_all_button.clicked.connect(self.add_all_channels)
        self.add_button.clicked.connect(self.add_channels)
        self.remove_button.clicked.connect(self.remove_channels)
        self.remove_all_button.clicked.connect(self.remove_all_channels)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        main_layout.addWidget(splitter)
        main_layout.addLayout(button_layout)
    
    def populate_channels(self):
        """Populate channel lists"""
        selected_set = set(self.selected_channels)
        
        for i, ch_name in enumerate(self.raw.ch_names):
            item = QListWidgetItem(ch_name)
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            if i in selected_set:
                self.selected_list.addItem(item)
            else:
                self.available_list.addItem(item)
    
    def add_all_channels(self):
        """Add all available channels to selected"""
        while self.available_list.count() > 0:
            self.selected_list.addItem(self.available_list.takeItem(0))
    
    def add_channels(self):
        """Add selected available channels"""
        for item in self.available_list.selectedItems():
            row = self.available_list.row(item)
            self.selected_list.addItem(self.available_list.takeItem(row))
    
    def remove_channels(self):
        """Remove selected channels"""
        for item in self.selected_list.selectedItems():
            row = self.selected_list.row(item)
            self.available_list.addItem(self.selected_list.takeItem(row))
    
    def remove_all_channels(self):
        """Remove all selected channels"""
        while self.selected_list.count() > 0:
            self.available_list.addItem(self.selected_list.takeItem(0))
    
    def get_selected_channels(self) -> List[int]:
        """Get list of selected channel indices"""
        return [
            self.selected_list.item(i).data(Qt.ItemDataRole.UserRole) 
            for i in range(self.selected_list.count())
        ]
    
    def accept(self):
        """Accept dialog if valid selection"""
        if self.selected_list.count() == 0:
            ErrorHandlingUtils.show_user_error(
                self, "Invalid Selection", 
                "You must select at least one channel."
            )
            return
        super().accept()
    
    def apply_theme(self, theme: dict):
        """Apply theme to dialog"""
        colors = theme['colors']
        self.setStyleSheet(f"""
            QDialog {{
                background: {colors['primary_bg']};
                color: {colors['primary_text']};
            }}
            
            QListWidget {{
                background: {colors['secondary_bg']};
                color: {colors['primary_text']};
                border: 1px solid {colors['separator_color']};
                border-radius: 4px;
                selection-background-color: {colors['accent_color']};
            }}
        """)

class ChannelColorDialog(QDialog):
    """Dialog for setting channel colors"""
    
    def __init__(self, raw, channel_colors: Dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Channel Colors")
        self.resize(400, 600)
        self.raw = raw
        self.channel_colors = channel_colors.copy()
        self.setup_ui()
        self.populate_colors()
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Instructions
        instruction_label = ModernLabel("Double-click a channel to change its color.")
        layout.addWidget(instruction_label)
        
        # Color list
        self.color_list = QListWidget()
        self.color_list.setAlternatingRowColors(True)
        self.color_list.itemDoubleClicked.connect(self.change_color)
        layout.addWidget(self.color_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.reset_button = ModernButton("Reset to Default")
        self.ok_button = ModernButton("OK")
        self.cancel_button = ModernButton("Cancel")
        
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # Connect signals
        self.reset_button.clicked.connect(self.reset_colors)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        layout.addLayout(button_layout)
    
    def populate_colors(self):
        """Populate color list"""
        default_color = theme_manager.get_color('primary_text')
        
        for ch_name in self.raw.ch_names:
            color = self.channel_colors.get(ch_name, default_color)
            item = QListWidgetItem(ch_name)
            item.setForeground(QColor(color))
            self.color_list.addItem(item)
    
    def change_color(self, item: QListWidgetItem):
        """Change color for selected channel"""
        ch_name = item.text()
        current_color = self.channel_colors.get(ch_name, '#e0e6ed')
        
        color = QColorDialog.getColor(
            QColor(current_color), 
            self, 
            f"Select Color for {ch_name}"
        )
        
        if color.isValid():
            self.channel_colors[ch_name] = color.name()
            item.setForeground(color)
    
    def reset_colors(self):
        """Reset all colors to default"""
        default_color = theme_manager.get_color('primary_text')
        
        for i in range(self.color_list.count()):
            item = self.color_list.item(i)
            ch_name = item.text()
            self.channel_colors[ch_name] = default_color
            item.setForeground(QColor(default_color))
    
    def get_channel_colors(self) -> Dict[str, str]:
        """Get the channel colors dictionary"""
        return self.channel_colors
    
    def apply_theme(self, theme: dict):
        """Apply theme to dialog"""
        colors = theme['colors']
        self.setStyleSheet(f"""
            QDialog {{
                background: {colors['primary_bg']};
                color: {colors['primary_text']};
            }}
            
            QListWidget {{
                background: {colors['secondary_bg']};
                color: {colors['primary_text']};
                border: 1px solid {colors['separator_color']};
                border-radius: 4px;
                selection-background-color: {colors['accent_color']};
            }}
        """)

class ScreenshotDialog(QDialog):
    """Advanced screenshot dialog with multiple options"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Screenshot Options")
        self.resize(500, 700)
        self.setup_ui()
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
    
    def setup_ui(self):
        """Setup the dialog UI"""
        main_layout = QVBoxLayout(self)
        
        # Create tabs for different settings
        tab_widget = QTabWidget()
        
        # File settings tab
        file_tab = self.create_file_settings_tab()
        tab_widget.addTab(file_tab, "File Settings")
        
        # Size and resolution tab
        size_tab = self.create_size_settings_tab()
        tab_widget.addTab(size_tab, "Size & Resolution")
        
        # Appearance tab
        appearance_tab = self.create_appearance_settings_tab()
        tab_widget.addTab(appearance_tab, "Grid & Appearance")
        
        # Transform tab
        transform_tab = self.create_transform_settings_tab()
        tab_widget.addTab(transform_tab, "Transforms")
        
        main_layout.addWidget(tab_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.preview_button = ModernButton("Preview")
        self.ok_button = ModernButton("Save Screenshot")
        self.cancel_button = ModernButton("Cancel")
        
        button_layout.addStretch()
        button_layout.addWidget(self.preview_button)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # Connect signals
        self.preview_button.clicked.connect(self.preview_screenshot)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        main_layout.addLayout(button_layout)
    
    def create_file_settings_tab(self) -> QWidget:
        """Create file settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        file_group = ModernGroupBox("File Settings")
        file_layout = QFormLayout()
        
        # Filename
        self.filename_input = QLineEdit("eeg_screenshot")
        file_layout.addRow("Filename:", self.filename_input)
        
        # Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "PDF", "SVG"])
        file_layout.addRow("Format:", self.format_combo)
        
        # Quality (for JPEG)
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(95)
        self.quality_label = QLabel("95%")
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"{v}%")
        )
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_label)
        file_layout.addRow("Quality (JPEG):", quality_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        layout.addStretch()
        
        return widget
    
    def create_size_settings_tab(self) -> QWidget:
        """Create size settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        size_group = ModernGroupBox("Size & Resolution")
        size_layout = QFormLayout()
        
        # Size presets
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "Current View", "1920x1080 (HD)", "2560x1440 (QHD)", 
            "3840x2160 (4K)", "Custom"
        ])
        size_layout.addRow("Size:", self.size_combo)
        
        # Custom size
        custom_layout = QHBoxLayout()
        self.width_input = QLineEdit("1920")
        self.width_input.setValidator(QDoubleValidator(100, 10000, 0))
        self.height_input = QLineEdit("1080")
        self.height_input.setValidator(QDoubleValidator(100, 10000, 0))
        custom_layout.addWidget(QLabel("Width:"))
        custom_layout.addWidget(self.width_input)
        custom_layout.addWidget(QLabel("Height:"))
        custom_layout.addWidget(self.height_input)
        size_layout.addRow("Custom Size:", custom_layout)
        
        # DPI
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["72", "150", "300", "600"])
        self.dpi_combo.setCurrentText("150")
        size_layout.addRow("DPI:", self.dpi_combo)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        layout.addStretch()
        
        return widget
    
    def create_appearance_settings_tab(self) -> QWidget:
        """Create appearance settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        appearance_group = ModernGroupBox("Grid & Appearance")
        appearance_layout = QVBoxLayout()
        
        # Grid settings
        self.show_grid = QCheckBox("Show Grid")
        self.show_grid.setChecked(True)
        appearance_layout.addWidget(self.show_grid)
        
        grid_layout = QFormLayout()
        
        # Grid style
        self.grid_style = QComboBox()
        self.grid_style.addItems(["Solid", "Dashed", "Dotted"])
        grid_layout.addRow("Grid Style:", self.grid_style)
        
        # Grid color
        self.grid_color_button = ModernButton("Choose Color")
        self.grid_color = QColor(128, 128, 128, 100)
        self.grid_color_button.clicked.connect(self.choose_grid_color)
        grid_layout.addRow("Grid Color:", self.grid_color_button)
        
        # Time grid
        self.time_grid_input = QLineEdit("1.0")
        self.time_grid_input.setValidator(QDoubleValidator(0.1, 60.0, 1))
        grid_layout.addRow("Time Grid (s):", self.time_grid_input)
        
        # Amplitude grid
        self.amp_grid_input = QLineEdit("50")
        self.amp_grid_input.setValidator(QDoubleValidator(1.0, 1000.0, 1))
        grid_layout.addRow("Amplitude Grid (µV):", self.amp_grid_input)
        
        appearance_layout.addLayout(grid_layout)
        
        # Other appearance options
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
        layout.addWidget(appearance_group)
        layout.addStretch()
        
        return widget
    
    def create_transform_settings_tab(self) -> QWidget:
        """Create transform settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        transform_group = ModernGroupBox("Transforms")
        transform_layout = QVBoxLayout()
        
        # Filter options
        filter_group = QGroupBox("Filters")
        filter_layout = QVBoxLayout()
        
        self.apply_highpass = QCheckBox("High-pass Filter")
        filter_layout.addWidget(self.apply_highpass)
        
        self.highpass_freq = QDoubleSpinBox()
        self.highpass_freq.setRange(0.1, 100.0)
        self.highpass_freq.setValue(0.5)
        self.highpass_freq.setSuffix(" Hz")
        filter_layout.addWidget(self.highpass_freq)
        
        self.apply_lowpass = QCheckBox("Low-pass Filter")
        filter_layout.addWidget(self.apply_lowpass)
        
        self.lowpass_freq = QDoubleSpinBox()
        self.lowpass_freq.setRange(1.0, 500.0)
        self.lowpass_freq.setValue(40.0)
        self.lowpass_freq.setSuffix(" Hz")
        filter_layout.addWidget(self.lowpass_freq)
        
        filter_group.setLayout(filter_layout)
        transform_layout.addWidget(filter_group)
        
        # Scaling options
        scale_group = QGroupBox("Scaling")
        scale_layout = QVBoxLayout()
        
        self.auto_scale = QCheckBox("Auto Scale")
        self.auto_scale.setChecked(True)
        scale_layout.addWidget(self.auto_scale)
        
        self.scale_factor = QDoubleSpinBox()
        self.scale_factor.setRange(0.1, 10.0)
        self.scale_factor.setValue(1.0)
        self.scale_factor.setSuffix("x")
        scale_layout.addWidget(self.scale_factor)
        
        scale_group.setLayout(scale_layout)
        transform_layout.addWidget(scale_group)
        
        transform_group.setLayout(transform_layout)
        layout.addWidget(transform_group)
        layout.addStretch()
        
        return widget
    
    def choose_grid_color(self):
        """Choose grid color"""
        color = QColorDialog.getColor(self.grid_color, self, "Select Grid Color")
        if color.isValid():
            self.grid_color = color
            self.grid_color_button.setStyleSheet(
                f"background-color: {color.name()}"
            )
    
    def preview_screenshot(self):
        """Preview screenshot settings"""
        # Implementation would show a preview of the screenshot
        ErrorHandlingUtils.show_user_error(
            self, "Preview", 
            "Screenshot preview functionality would be implemented here.",
            "information"
        )
    
    def get_screenshot_settings(self) -> Dict[str, Any]:
        """Get all screenshot settings"""
        return {
            'filename': self.filename_input.text(),
            'format': self.format_combo.currentText(),
            'quality': self.quality_slider.value(),
            'size_preset': self.size_combo.currentText(),
            'custom_width': float(self.width_input.text()) if self.width_input.text() else 1920,
            'custom_height': float(self.height_input.text()) if self.height_input.text() else 1080,
            'dpi': int(self.dpi_combo.currentText()),
            'show_grid': self.show_grid.isChecked(),
            'grid_style': self.grid_style.currentText(),
            'grid_color': self.grid_color.name(),
            'time_grid': float(self.time_grid_input.text()) if self.time_grid_input.text() else 1.0,
            'amp_grid': float(self.amp_grid_input.text()) if self.amp_grid_input.text() else 50.0,
            'show_labels': self.show_labels.isChecked(),
            'show_time_axis': self.show_time_axis.isChecked(),
            'show_annotations': self.show_annotations.isChecked(),
            'apply_highpass': self.apply_highpass.isChecked(),
            'highpass_freq': self.highpass_freq.value(),
            'apply_lowpass': self.apply_lowpass.isChecked(),
            'lowpass_freq': self.lowpass_freq.value(),
            'auto_scale': self.auto_scale.isChecked(),
            'scale_factor': self.scale_factor.value()
        }
    
    def apply_theme(self, theme: dict):
        """Apply theme to dialog"""
        colors = theme['colors']
        self.setStyleSheet(f"""
            QDialog {{
                background: {colors['primary_bg']};
                color: {colors['primary_text']};
            }}
            
            QTabWidget::pane {{
                border: 1px solid {colors['separator_color']};
                background: {colors['primary_bg']};
            }}
            
            QTabBar::tab {{
                background: {colors['secondary_bg']};
                color: {colors['secondary_text']};
                border: 1px solid {colors['separator_color']};
                padding: 8px 16px;
                margin-right: 2px;
            }}
            
            QTabBar::tab:selected {{
                background: {colors['accent_color']};
                color: white;
            }}
        """)

class AnnotationDialog(QDialog):
    """Dialog for creating/editing annotations"""
    
    def __init__(self, annotation: Optional[Annotation] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Annotation" if annotation else "New Annotation")
        self.resize(400, 300)
        self.annotation = annotation
        self.setup_ui()
        
        if annotation:
            self.load_annotation(annotation)
        
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Form layout for annotation fields
        form_layout = QFormLayout()
        
        # Description
        self.description_input = QLineEdit()
        form_layout.addRow("Description:", self.description_input)
        
        # Start time
        self.start_time_input = QDoubleSpinBox()
        self.start_time_input.setRange(0, 999999)
        self.start_time_input.setDecimals(3)
        self.start_time_input.setSuffix(" s")
        form_layout.addRow("Start Time:", self.start_time_input)
        
        # Duration
        self.duration_input = QDoubleSpinBox()
        self.duration_input.setRange(0.001, 999999)
        self.duration_input.setDecimals(3)
        self.duration_input.setSuffix(" s")
        form_layout.addRow("Duration:", self.duration_input)
        
        # Color
        color_layout = QHBoxLayout()
        self.color_button = ModernButton("Choose Color")
        self.color = QColor("#ff0000")
        self.color_button.clicked.connect(self.choose_color)
        self.update_color_button()
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        form_layout.addRow("Color:", color_layout)
        
        # Channel (optional)
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Optional - leave empty for all channels")
        form_layout.addRow("Channel:", self.channel_input)
        
        layout.addLayout(form_layout)
        
        # Notes
        notes_group = ModernGroupBox("Notes")
        notes_layout = QVBoxLayout()
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        notes_layout.addWidget(self.notes_input)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = ModernButton("OK")
        self.cancel_button = ModernButton("Cancel")
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # Connect signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        layout.addLayout(button_layout)
    
    def load_annotation(self, annotation: Annotation):
        """Load annotation data into form"""
        self.description_input.setText(annotation.description)
        self.start_time_input.setValue(annotation.start_time)
        self.duration_input.setValue(annotation.duration)
        self.color = QColor(annotation.color)
        self.update_color_button()
        
        if annotation.channel:
            self.channel_input.setText(annotation.channel)
        
        self.notes_input.setPlainText(annotation.notes)
    
    def choose_color(self):
        """Choose annotation color"""
        color = QColorDialog.getColor(self.color, self, "Select Annotation Color")
        if color.isValid():
            self.color = color
            self.update_color_button()
    
    def update_color_button(self):
        """Update color button appearance"""
        self.color_button.setStyleSheet(
            f"background-color: {self.color.name()}; color: white;"
        )
    
    def get_annotation(self) -> Annotation:
        """Get annotation from form data"""
        return Annotation(
            start_time=self.start_time_input.value(),
            duration=self.duration_input.value(),
            description=self.description_input.text(),
            color=self.color.name(),
            timestamp=datetime.now().isoformat(),
            channel=self.channel_input.text() if self.channel_input.text() else None,
            notes=self.notes_input.toPlainText()
        )
    
    def accept(self):
        """Accept dialog if valid input"""
        if not self.description_input.text().strip():
            ErrorHandlingUtils.show_user_error(
                self, "Invalid Input", 
                "Description cannot be empty."
            )
            return
        
        if self.duration_input.value() <= 0:
            ErrorHandlingUtils.show_user_error(
                self, "Invalid Input", 
                "Duration must be greater than 0."
            )
            return
        
        super().accept()
    
    def apply_theme(self, theme: dict):
        """Apply theme to dialog"""
        colors = theme['colors']
        self.setStyleSheet(f"""
            QDialog {{
                background: {colors['primary_bg']};
                color: {colors['primary_text']};
            }}
            
            QLineEdit, QDoubleSpinBox, QTextEdit {{
                background: {colors['secondary_bg']};
                color: {colors['primary_text']};
                border: 1px solid {colors['separator_color']};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QLineEdit:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
                border: 1px solid {colors['accent_color']};
            }}
        """)

class HighlightSectionDialog(QDialog):
    """Dialog for highlighting EEG sections"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Highlight Section")
        self.resize(350, 250)
        self.setup_ui()
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Start time
        self.start_time_input = QDoubleSpinBox()
        self.start_time_input.setRange(0, 999999)
        self.start_time_input.setDecimals(3)
        self.start_time_input.setSuffix(" s")
        form_layout.addRow("Start Time:", self.start_time_input)
        
        # End time
        self.end_time_input = QDoubleSpinBox()
        self.end_time_input.setRange(0, 999999)
        self.end_time_input.setDecimals(3)
        self.end_time_input.setSuffix(" s")
        form_layout.addRow("End Time:", self.end_time_input)
        
        # Color
        color_layout = QHBoxLayout()
        self.color_button = ModernButton("Choose Color")
        self.color = QColor("#ffff00")  # Yellow default
        self.color_button.clicked.connect(self.choose_color)
        self.update_color_button()
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        form_layout.addRow("Highlight Color:", color_layout)
        
        # Opacity
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(50)
        self.opacity_label = QLabel("50%")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        form_layout.addRow("Opacity:", opacity_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = ModernButton("OK")
        self.cancel_button = ModernButton("Cancel")
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        # Connect signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        layout.addLayout(button_layout)
    
    def choose_color(self):
        """Choose highlight color"""
        color = QColorDialog.getColor(self.color, self, "Select Highlight Color")
        if color.isValid():
            self.color = color
            self.update_color_button()
    
    def update_color_button(self):
        """Update color button appearance"""
        self.color_button.setStyleSheet(
            f"background-color: {self.color.name()}; color: white;"
        )
    
    def get_highlight_settings(self) -> Dict[str, Any]:
        """Get highlight settings"""
        return {
            'start_time': self.start_time_input.value(),
            'end_time': self.end_time_input.value(),
            'color': self.color,
            'opacity': self.opacity_slider.value() / 100.0
        }
    
    def accept(self):
        """Accept dialog if valid input"""
        start_time = self.start_time_input.value()
        end_time = self.end_time_input.value()
        
        if end_time <= start_time:
            ErrorHandlingUtils.show_user_error(
                self, "Invalid Input", 
                "End time must be greater than start time."
            )
            return
        
        super().accept()
    
    def apply_theme(self, theme: dict):
        """Apply theme to dialog"""
        colors = theme['colors']
        self.setStyleSheet(f"""
            QDialog {{
                background: {colors['primary_bg']};
                color: {colors['primary_text']};
            }}
            
            QDoubleSpinBox {{
                background: {colors['secondary_bg']};
                color: {colors['primary_text']};
                border: 1px solid {colors['separator_color']};
                border-radius: 4px;
                padding: 4px;
            }}
        """)

# Export all dialog classes
__all__ = [
    'ChannelSelectionDialog', 'ChannelColorDialog', 'ScreenshotDialog',
    'AnnotationDialog', 'HighlightSectionDialog'
]