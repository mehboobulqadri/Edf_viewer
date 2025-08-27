"""
Gaze mode setup dialog for configuring gaze annotation mode.

This dialog allows users to configure various parameters for gaze-based
annotation including display settings, gaze detection parameters, and
visual feedback options.
"""

import logging
from typing import Dict, Any, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QLabel, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QCheckBox, QSlider, QMessageBox, QProgressBar,
    QGridLayout, QFormLayout, QTextEdit
)
from PyQt6.QtGui import QFont

try:
    from ..gaze_tracking.gaze_tracker import GazeTracker, MockGazeTracker
except ImportError:
    # Handle case when running from different directory
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from gaze_tracking.gaze_tracker import GazeTracker, MockGazeTracker

logger = logging.getLogger(__name__)


class GazeModeSetupDialog(QDialog):
    """
    Comprehensive setup dialog for gaze annotation mode.
    
    Provides configuration for display settings, gaze detection parameters,
    auto-scroll configuration, annotation settings, and visual feedback.
    """
    
    def __init__(self, parent=None):
        """Initialize gaze mode setup dialog."""
        super().__init__(parent)
        
        self.setWindowTitle("Gaze Annotation Mode Setup")
        self.setModal(True)
        self.resize(600, 700)
        
        # Configuration storage
        self.config = self._get_default_config()
        self.test_tracker = None
        
        # Initialize UI
        self._setup_ui()
        self._load_default_values()
        
        logger.info("GazeModeSetupDialog initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self._create_display_tab()
        self._create_gaze_detection_tab()
        self._create_auto_scroll_tab()
        self._create_annotation_tab()
        self._create_feedback_tab()
        self._create_hardware_tab()
        
        layout.addWidget(self.tab_widget)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Test connection button
        self.test_button = QPushButton("Test Eye Tracker")
        self.test_button.clicked.connect(self._test_eye_tracker)
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        # Standard dialog buttons
        self.ok_button = QPushButton("Start Gaze Mode")
        self.cancel_button = QPushButton("Cancel")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Status bar
        self.status_label = QLabel("Ready to configure gaze mode")
        layout.addWidget(self.status_label)
    
    def _create_display_tab(self):
        """Create display settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # EDF Display Settings
        display_group = QGroupBox("EDF Display Settings")
        display_layout = QFormLayout()
        
        # Time scale
        self.time_scale_combo = QComboBox()
        self.time_scale_combo.addItems(["5s", "10s", "15s", "20s", "30s", "1m"])
        self.time_scale_combo.setCurrentText("10s")
        display_layout.addRow("Time Scale:", self.time_scale_combo)
        
        # Channel count
        self.channel_count_combo = QComboBox()
        self.channel_count_combo.addItems(["5", "8", "10", "12", "15", "20", "All"])
        self.channel_count_combo.setCurrentText("10")
        display_layout.addRow("Visible Channels:", self.channel_count_combo)
        
        # Sensitivity
        self.sensitivity_spin = QDoubleSpinBox()
        self.sensitivity_spin.setRange(1.0, 1000.0)
        self.sensitivity_spin.setValue(50.0)
        self.sensitivity_spin.setSuffix(" µV")
        display_layout.addRow("Sensitivity:", self.sensitivity_spin)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Zoom and Navigation
        nav_group = QGroupBox("Navigation Settings")
        nav_layout = QFormLayout()
        
        # Auto-fit to content
        self.auto_fit_check = QCheckBox("Auto-fit sensitivity to content")
        nav_layout.addRow(self.auto_fit_check)
        
        # Channel scrolling
        self.allow_scrolling_check = QCheckBox("Allow channel scrolling during review")
        self.allow_scrolling_check.setChecked(True)
        nav_layout.addRow(self.allow_scrolling_check)
        
        nav_group.setLayout(nav_layout)
        layout.addWidget(nav_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Display Settings")
    
    def _create_gaze_detection_tab(self):
        """Create gaze detection parameters tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Fixation Detection
        fixation_group = QGroupBox("Fixation Detection")
        fixation_layout = QFormLayout()
        
        # Fixation duration
        self.fixation_duration_spin = QDoubleSpinBox()
        self.fixation_duration_spin.setRange(0.1, 5.0)
        self.fixation_duration_spin.setValue(1.0)
        self.fixation_duration_spin.setSingleStep(0.1)
        self.fixation_duration_spin.setSuffix(" seconds")
        fixation_layout.addRow("Fixation Duration:", self.fixation_duration_spin)
        
        # Spatial accuracy
        self.spatial_accuracy_spin = QSpinBox()
        self.spatial_accuracy_spin.setRange(10, 200)
        self.spatial_accuracy_spin.setValue(50)
        self.spatial_accuracy_spin.setSuffix(" pixels")
        fixation_layout.addRow("Spatial Accuracy:", self.spatial_accuracy_spin)
        
        # Confidence threshold
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.1, 1.0)
        self.confidence_spin.setValue(0.7)
        self.confidence_spin.setSingleStep(0.1)
        fixation_layout.addRow("Confidence Threshold:", self.confidence_spin)
        
        fixation_group.setLayout(fixation_layout)
        layout.addWidget(fixation_group)
        
        # Advanced Settings
        advanced_group = QGroupBox("Advanced Detection")
        advanced_layout = QFormLayout()
        
        # Smoothing
        self.smoothing_check = QCheckBox("Enable gaze smoothing")
        self.smoothing_check.setChecked(True)
        advanced_layout.addRow(self.smoothing_check)
        
        # Outlier removal
        self.outlier_removal_check = QCheckBox("Remove gaze outliers")
        self.outlier_removal_check.setChecked(True)
        advanced_layout.addRow(self.outlier_removal_check)
        
        # Edge detection
        self.edge_detection_check = QCheckBox("Detect edge fixations")
        advanced_layout.addRow(self.edge_detection_check)
        
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Gaze Detection")
    
    def _create_auto_scroll_tab(self):
        """Create auto-scroll configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Auto-scroll Settings
        scroll_group = QGroupBox("Auto-Scroll Configuration")
        scroll_layout = QFormLayout()
        
        # Enable auto-scroll
        self.auto_scroll_check = QCheckBox("Enable auto-scroll during review")
        self.auto_scroll_check.setChecked(True)
        scroll_layout.addRow(self.auto_scroll_check)
        
        # Scroll speed
        self.scroll_speed_spin = QDoubleSpinBox()
        self.scroll_speed_spin.setRange(0.5, 10.0)
        self.scroll_speed_spin.setValue(2.0)
        self.scroll_speed_spin.setSingleStep(0.5)
        self.scroll_speed_spin.setSuffix(" seconds per window")
        scroll_layout.addRow("Scroll Speed:", self.scroll_speed_spin)
        
        # Pause on fixation
        self.pause_on_fixation_check = QCheckBox("Pause on fixation")
        self.pause_on_fixation_check.setChecked(True)
        scroll_layout.addRow(self.pause_on_fixation_check)
        
        # Pause duration
        self.pause_duration_spin = QDoubleSpinBox()
        self.pause_duration_spin.setRange(0.5, 10.0)
        self.pause_duration_spin.setValue(3.0)
        self.pause_duration_spin.setSingleStep(0.5)
        self.pause_duration_spin.setSuffix(" seconds")
        scroll_layout.addRow("Pause Duration:", self.pause_duration_spin)
        
        scroll_group.setLayout(scroll_layout)
        layout.addWidget(scroll_group)
        
        # Review Behavior
        behavior_group = QGroupBox("Review Behavior")
        behavior_layout = QFormLayout()
        
        # Loop at end
        self.loop_review_check = QCheckBox("Loop review at end of recording")
        behavior_layout.addRow(self.loop_review_check)
        
        # Skip already annotated
        self.skip_annotated_check = QCheckBox("Skip already annotated regions")
        behavior_layout.addRow(self.skip_annotated_check)
        
        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Auto-Scroll")
    
    def _create_annotation_tab(self):
        """Create annotation settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Default Annotation Settings
        annotation_group = QGroupBox("Default Annotation Settings")
        annotation_layout = QFormLayout()
        
        # Default category
        self.default_category_combo = QComboBox()
        self.default_category_combo.addItems([
            "Abnormality", "Spike", "Sharp Wave", "Slow Wave",
            "Artifact", "Sleep Spindle", "K-Complex", "Custom"
        ])
        annotation_layout.addRow("Default Category:", self.default_category_combo)
        
        # Default duration
        self.default_duration_spin = QDoubleSpinBox()
        self.default_duration_spin.setRange(0.1, 10.0)
        self.default_duration_spin.setValue(1.0)
        self.default_duration_spin.setSingleStep(0.1)
        self.default_duration_spin.setSuffix(" seconds")
        annotation_layout.addRow("Default Duration:", self.default_duration_spin)
        
        # Auto-description
        self.auto_description_check = QCheckBox("Generate automatic descriptions")
        self.auto_description_check.setChecked(True)
        annotation_layout.addRow(self.auto_description_check)
        
        annotation_group.setLayout(annotation_layout)
        layout.addWidget(annotation_group)
        
        # Trigger Settings
        trigger_group = QGroupBox("Annotation Triggers")
        trigger_layout = QFormLayout()
        
        # Trigger mode
        self.trigger_mode_combo = QComboBox()
        self.trigger_mode_combo.addItems([
            "Fixation Only", "Fixation + Blink", "Manual Confirm"
        ])
        self.trigger_mode_combo.setCurrentText("Fixation Only")
        trigger_layout.addRow("Trigger Mode:", self.trigger_mode_combo)
        
        # Multi-channel detection
        self.multi_channel_check = QCheckBox("Enable multi-channel annotations")
        trigger_layout.addRow(self.multi_channel_check)
        
        trigger_group.setLayout(trigger_layout)
        layout.addWidget(trigger_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Annotations")
    
    def _create_feedback_tab(self):
        """Create visual feedback settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Visual Feedback
        feedback_group = QGroupBox("Visual Feedback")
        feedback_layout = QFormLayout()
        
        # Show gaze cursor
        self.show_cursor_check = QCheckBox("Show gaze cursor")
        self.show_cursor_check.setChecked(True)
        feedback_layout.addRow(self.show_cursor_check)
        
        # Show fixation progress
        self.show_progress_check = QCheckBox("Show fixation progress")
        self.show_progress_check.setChecked(True)
        feedback_layout.addRow(self.show_progress_check)
        
        # Show annotation previews
        self.show_preview_check = QCheckBox("Show annotation previews")
        self.show_preview_check.setChecked(True)
        feedback_layout.addRow(self.show_preview_check)
        
        # Cursor size
        self.cursor_size_spin = QSpinBox()
        self.cursor_size_spin.setRange(5, 50)
        self.cursor_size_spin.setValue(15)
        self.cursor_size_spin.setSuffix(" pixels")
        feedback_layout.addRow("Cursor Size:", self.cursor_size_spin)
        
        feedback_group.setLayout(feedback_layout)
        layout.addWidget(feedback_group)
        
        # Audio Feedback
        audio_group = QGroupBox("Audio Feedback")
        audio_layout = QFormLayout()
        
        # Enable audio
        self.audio_feedback_check = QCheckBox("Enable audio feedback")
        audio_layout.addRow(self.audio_feedback_check)
        
        # Audio volume
        self.audio_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.audio_volume_slider.setRange(0, 100)
        self.audio_volume_slider.setValue(50)
        audio_layout.addRow("Audio Volume:", self.audio_volume_slider)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Feedback")
    
    def _create_hardware_tab(self):
        """Create hardware testing and configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Hardware Status
        status_group = QGroupBox("Hardware Status")
        status_layout = QGridLayout()
        
        # Connection status
        status_layout.addWidget(QLabel("Connection:"), 0, 0)
        self.connection_status_label = QLabel("Not tested")
        status_layout.addWidget(self.connection_status_label, 0, 1)
        
        # Device info
        status_layout.addWidget(QLabel("Device:"), 1, 0)
        self.device_info_label = QLabel("Unknown")
        status_layout.addWidget(self.device_info_label, 1, 1)
        
        # Test progress
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        status_layout.addWidget(self.test_progress, 2, 0, 1, 2)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Test Options
        test_group = QGroupBox("Testing Options")
        test_layout = QFormLayout()
        
        # Use mock data
        self.use_mock_check = QCheckBox("Use mock data for testing")
        test_layout.addRow(self.use_mock_check)
        
        # Test duration
        self.test_duration_spin = QSpinBox()
        self.test_duration_spin.setRange(5, 60)
        self.test_duration_spin.setValue(10)
        self.test_duration_spin.setSuffix(" seconds")
        test_layout.addRow("Test Duration:", self.test_duration_spin)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        # Test Results
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout()
        
        self.test_results = QTextEdit()
        self.test_results.setMaximumHeight(150)
        self.test_results.setReadOnly(True)
        results_layout.addWidget(self.test_results)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        layout.addStretch()
        self.tab_widget.addTab(tab, "Hardware Test")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            'display': {
                'time_scale': 10.0,
                'channel_count': 10,
                'sensitivity': 50.0,
                'auto_fit': False,
                'allow_scrolling': True
            },
            'gaze_detection': {
                'fixation_duration': 1.0,
                'spatial_accuracy': 50,
                'confidence_threshold': 0.7,
                'enable_smoothing': True,
                'remove_outliers': True,
                'edge_detection': False
            },
            'auto_scroll': {
                'enabled': True,
                'speed': 2.0,
                'pause_on_fixation': True,
                'pause_duration': 3.0,
                'loop_review': False,
                'skip_annotated': False
            },
            'annotations': {
                'default_category': 'Abnormality',
                'default_duration': 1.0,
                'auto_description': True,
                'trigger_mode': 'Fixation Only',
                'multi_channel': False
            },
            'feedback': {
                'show_cursor': True,
                'show_progress': True,
                'show_preview': True,
                'cursor_size': 15,
                'audio_feedback': False,
                'audio_volume': 50
            },
            'hardware': {
                'use_mock': False,
                'test_duration': 10
            }
        }
    
    def _load_default_values(self):
        """Load default values into UI controls."""
        # This method will be expanded to load from the config dictionary
        pass
    
    def _test_eye_tracker(self):
        """Test eye tracker connection and functionality."""
        self.test_button.setEnabled(False)
        self.test_progress.setVisible(True)
        self.test_progress.setValue(0)
        
        try:
            # Choose tracker type based on mock setting
            if self.use_mock_check.isChecked():
                self.test_tracker = MockGazeTracker()
                self.connection_status_label.setText("Mock connection")
                self.device_info_label.setText("Mock Eye Tracker")
            else:
                self.test_tracker = GazeTracker()
                
                # Try to discover and connect to devices
                devices = self.test_tracker.discover_devices()
                if not devices:
                    self.connection_status_label.setText("No devices found")
                    self.device_info_label.setText("None")
                    self._show_test_message("No eye tracking devices found. Enable mock mode for testing.")
                    return
                
                # Connect to first device
                if self.test_tracker.connect_device():
                    device_info = self.test_tracker.get_device_info()
                    if device_info:
                        self.connection_status_label.setText("Connected")
                        self.device_info_label.setText(f"{device_info['device_name']} ({device_info['model']})")
                    else:
                        self.connection_status_label.setText("Connected (info unavailable)")
                        self.device_info_label.setText("Unknown device")
                else:
                    self.connection_status_label.setText("Connection failed")
                    self.device_info_label.setText("None")
                    self._show_test_message("Failed to connect to eye tracker. Check hardware connection.")
                    return
            
            self.test_progress.setValue(50)
            self._show_test_message("Eye tracker connection successful! Ready for gaze annotation mode.")
            self.test_progress.setValue(100)
            
        except Exception as e:
            self.connection_status_label.setText("Error")
            self.device_info_label.setText("Test failed")
            self._show_test_message(f"Eye tracker test failed: {str(e)}")
            logger.error(f"Eye tracker test error: {e}")
        
        finally:
            self.test_button.setEnabled(True)
            if self.test_tracker:
                self.test_tracker.disconnect_device()
                self.test_tracker = None
    
    def _show_test_message(self, message: str):
        """Show test result message."""
        self.test_results.append(f"[{self._get_timestamp()}] {message}")
        self.status_label.setText(message)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for logging."""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current configuration from dialog controls.
        
        Returns:
            Configuration dictionary
        """
        config = self._get_default_config()
        
        # Update config with current UI values
        # Display settings
        time_scale_text = self.time_scale_combo.currentText()
        if time_scale_text.endswith('m'):
            config['display']['time_scale'] = float(time_scale_text[:-1]) * 60
        else:
            config['display']['time_scale'] = float(time_scale_text[:-1])
        
        channel_count_text = self.channel_count_combo.currentText()
        if channel_count_text == "All":
            config['display']['channel_count'] = -1
        else:
            config['display']['channel_count'] = int(channel_count_text)
        
        config['display']['sensitivity'] = self.sensitivity_spin.value()
        config['display']['auto_fit'] = self.auto_fit_check.isChecked()
        config['display']['allow_scrolling'] = self.allow_scrolling_check.isChecked()
        
        # Gaze detection settings
        config['gaze_detection']['fixation_duration'] = self.fixation_duration_spin.value()
        config['gaze_detection']['spatial_accuracy'] = self.spatial_accuracy_spin.value()
        config['gaze_detection']['confidence_threshold'] = self.confidence_spin.value()
        config['gaze_detection']['enable_smoothing'] = self.smoothing_check.isChecked()
        config['gaze_detection']['remove_outliers'] = self.outlier_removal_check.isChecked()
        config['gaze_detection']['edge_detection'] = self.edge_detection_check.isChecked()
        
        # Auto-scroll settings
        config['auto_scroll']['enabled'] = self.auto_scroll_check.isChecked()
        config['auto_scroll']['speed'] = self.scroll_speed_spin.value()
        config['auto_scroll']['pause_on_fixation'] = self.pause_on_fixation_check.isChecked()
        config['auto_scroll']['pause_duration'] = self.pause_duration_spin.value()
        config['auto_scroll']['loop_review'] = self.loop_review_check.isChecked()
        config['auto_scroll']['skip_annotated'] = self.skip_annotated_check.isChecked()
        
        # Annotation settings
        config['annotations']['default_category'] = self.default_category_combo.currentText()
        config['annotations']['default_duration'] = self.default_duration_spin.value()
        config['annotations']['auto_description'] = self.auto_description_check.isChecked()
        config['annotations']['trigger_mode'] = self.trigger_mode_combo.currentText()
        config['annotations']['multi_channel'] = self.multi_channel_check.isChecked()
        
        # Feedback settings
        config['feedback']['show_cursor'] = self.show_cursor_check.isChecked()
        config['feedback']['show_progress'] = self.show_progress_check.isChecked()
        config['feedback']['show_preview'] = self.show_preview_check.isChecked()
        config['feedback']['cursor_size'] = self.cursor_size_spin.value()
        config['feedback']['audio_feedback'] = self.audio_feedback_check.isChecked()
        config['feedback']['audio_volume'] = self.audio_volume_slider.value()
        
        # Hardware settings
        config['hardware']['use_mock'] = self.use_mock_check.isChecked()
        config['hardware']['test_duration'] = self.test_duration_spin.value()
        
        return config
    
    def accept(self):
        """Accept dialog and validate configuration."""
        config = self.get_configuration()
        
        # Basic validation
        if config['gaze_detection']['fixation_duration'] < 0.1:
            QMessageBox.warning(self, "Invalid Configuration", 
                              "Fixation duration must be at least 0.1 seconds.")
            return
        
        if config['display']['time_scale'] < 1.0:
            QMessageBox.warning(self, "Invalid Configuration",
                              "Time scale must be at least 1 second.")
            return
        
        logger.info("Gaze mode configuration accepted")
        super().accept()
    
    def reject(self):
        """Cancel dialog."""
        logger.info("Gaze mode setup cancelled")
        super().reject()