"""
Coordinate mapping system for gaze tracking.

Maps gaze coordinates between different coordinate systems:
Tobii normalized (0-1) → Screen pixels → Widget coordinates → EDF time/channel

This module handles the complex transformation chain required to convert
raw gaze coordinates from the eye tracker into meaningful EDF data coordinates.
"""

import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, QRect
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QScreen

logger = logging.getLogger(__name__)


@dataclass
class CalibrationData:
    """Calibration offset data for improving gaze accuracy."""
    offset_x: float = 0.0  # X offset in pixels
    offset_y: float = 0.0  # Y offset in pixels
    scale_x: float = 1.0   # X scale factor
    scale_y: float = 1.0   # Y scale factor
    rotation: float = 0.0  # Rotation in degrees
    timestamp: float = 0.0 # Calibration timestamp
    
    def is_valid(self) -> bool:
        """Check if calibration data is valid."""
        return (abs(self.offset_x) < 1000 and 
                abs(self.offset_y) < 1000 and
                0.5 <= self.scale_x <= 2.0 and
                0.5 <= self.scale_y <= 2.0)


@dataclass
class CoordinateBounds:
    """Boundary information for coordinate validation."""
    screen_width: int
    screen_height: int
    widget_x: int
    widget_y: int
    widget_width: int
    widget_height: int
    
    def contains_screen_point(self, x: int, y: int) -> bool:
        """Check if screen coordinates are within bounds."""
        return 0 <= x < self.screen_width and 0 <= y < self.screen_height
    
    def contains_widget_point(self, x: int, y: int) -> bool:
        """Check if widget coordinates are within bounds."""
        return (self.widget_x <= x < self.widget_x + self.widget_width and
                self.widget_y <= y < self.widget_y + self.widget_height)


@dataclass
class EDFCoordinates:
    """EDF-specific coordinate information."""
    time_seconds: float      # Time in seconds from start of recording
    channel_index: int       # Channel index (-1 if invalid)
    channel_name: str        # Channel name (empty if invalid)
    is_valid: bool          # Whether coordinates are valid
    widget_x: int           # Widget X coordinate
    widget_y: int           # Widget Y coordinate


class CoordinateMapper(QObject):
    """
    Core coordinate mapping functionality.
    
    Handles the multi-stage coordinate transformation from eye tracker
    normalized coordinates to EDF time and channel coordinates.
    """
    
    def __init__(self):
        """Initialize coordinate mapper."""
        super().__init__()
        
        self.calibration_data = CalibrationData()
        self.bounds = None
        self.widget = None
        self.channel_names = []
        self.current_view_start = 0.0  # Current view start time in seconds
        self.current_view_duration = 10.0  # Current view duration in seconds
        self.visible_channels = 10  # Number of visible channels
        self.channel_offset = 0  # Offset for scrolled channels
        
        logger.info("CoordinateMapper initialized")
    
    def set_target_widget(self, widget: QWidget):
        """
        Set the target widget for coordinate mapping.
        
        Args:
            widget: The EDF plot widget to map coordinates to
        """
        self.widget = widget
        self._update_bounds()
        logger.info(f"Target widget set: {widget.__class__.__name__}")
    
    def set_calibration_data(self, calibration: CalibrationData):
        """
        Set calibration data for improved accuracy.
        
        Args:
            calibration: Calibration offset data
        """
        if calibration.is_valid():
            self.calibration_data = calibration
            logger.info("Calibration data updated")
        else:
            logger.warning("Invalid calibration data rejected")
    
    def set_edf_context(self, 
                       channel_names: list,
                       view_start: float,
                       view_duration: float,
                       visible_channels: int,
                       channel_offset: int = 0):
        """
        Set EDF viewing context for coordinate mapping.
        
        Args:
            channel_names: List of all channel names
            view_start: Current view start time in seconds
            view_duration: Current view duration in seconds
            visible_channels: Number of visible channels
            channel_offset: Offset for scrolled channels
        """
        self.channel_names = channel_names
        self.current_view_start = view_start
        self.current_view_duration = view_duration
        self.visible_channels = visible_channels
        self.channel_offset = channel_offset
        
        logger.debug(f"EDF context updated: {len(channel_names)} channels, "
                    f"view {view_start:.1f}-{view_start + view_duration:.1f}s")
    
    def _update_bounds(self):
        """Update coordinate bounds based on current widget."""
        if not self.widget:
            return
        
        # Get screen information
        app = QApplication.instance()
        if not app:
            return
        
        screen = app.primaryScreen()
        screen_geometry = screen.geometry()
        
        # Get widget geometry
        widget_geometry = self.widget.geometry()
        widget_global_pos = self.widget.mapToGlobal(widget_geometry.topLeft())
        
        self.bounds = CoordinateBounds(
            screen_width=screen_geometry.width(),
            screen_height=screen_geometry.height(),
            widget_x=widget_global_pos.x(),
            widget_y=widget_global_pos.y(),
            widget_width=widget_geometry.width(),
            widget_height=widget_geometry.height()
        )
        
        logger.debug(f"Bounds updated: screen {self.bounds.screen_width}x{self.bounds.screen_height}, "
                    f"widget {self.bounds.widget_width}x{self.bounds.widget_height}")
    
    def map_gaze_to_screen(self, gaze_x: float, gaze_y: float) -> Tuple[int, int]:
        """
        Convert normalized gaze coordinates to screen pixels.
        
        Args:
            gaze_x: Normalized X coordinate (0-1)
            gaze_y: Normalized Y coordinate (0-1)
            
        Returns:
            Tuple of (screen_x, screen_y) in pixels
        """
        if not self.bounds:
            self._update_bounds()
        
        if not self.bounds:
            return (0, 0)
        
        # Convert normalized coordinates to screen pixels
        screen_x = int(gaze_x * self.bounds.screen_width)
        screen_y = int(gaze_y * self.bounds.screen_height)
        
        # Apply calibration offsets
        screen_x += int(self.calibration_data.offset_x)
        screen_y += int(self.calibration_data.offset_y)
        
        # Apply scale factors
        screen_x = int(screen_x * self.calibration_data.scale_x)
        screen_y = int(screen_y * self.calibration_data.scale_y)
        
        # Clamp to screen bounds
        screen_x = max(0, min(screen_x, self.bounds.screen_width - 1))
        screen_y = max(0, min(screen_y, self.bounds.screen_height - 1))
        
        return (screen_x, screen_y)
    
    def map_screen_to_widget(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        Convert screen coordinates to widget-local coordinates.
        
        Args:
            screen_x: Screen X coordinate in pixels
            screen_y: Screen Y coordinate in pixels
            
        Returns:
            Tuple of (widget_x, widget_y) relative to widget
        """
        if not self.bounds:
            return (0, 0)
        
        # Convert screen coordinates to widget-local coordinates
        widget_x = screen_x - self.bounds.widget_x
        widget_y = screen_y - self.bounds.widget_y
        
        return (widget_x, widget_y)
    
    def map_widget_to_edf(self, widget_x: int, widget_y: int) -> EDFCoordinates:
        """
        Convert widget coordinates to EDF time and channel coordinates.
        
        Args:
            widget_x: Widget X coordinate
            widget_y: Widget Y coordinate
            
        Returns:
            EDFCoordinates object with time and channel information
        """
        if not self.bounds or not self.widget:
            return EDFCoordinates(0.0, -1, "", False, widget_x, widget_y)
        
        # Check if coordinates are within widget bounds
        if not (0 <= widget_x < self.bounds.widget_width and
                0 <= widget_y < self.bounds.widget_height):
            return EDFCoordinates(0.0, -1, "", False, widget_x, widget_y)
        
        # Calculate time from X coordinate
        time_ratio = widget_x / self.bounds.widget_width
        time_seconds = self.current_view_start + (time_ratio * self.current_view_duration)
        
        # Calculate channel from Y coordinate
        channel_ratio = widget_y / self.bounds.widget_height
        channel_float = channel_ratio * self.visible_channels
        channel_index = int(channel_float) + self.channel_offset
        
        # Validate channel index
        if (channel_index < 0 or 
            channel_index >= len(self.channel_names) or
            channel_index >= len(self.channel_names)):
            return EDFCoordinates(time_seconds, -1, "", False, widget_x, widget_y)
        
        channel_name = self.channel_names[channel_index]
        
        return EDFCoordinates(
            time_seconds=time_seconds,
            channel_index=channel_index,
            channel_name=channel_name,
            is_valid=True,
            widget_x=widget_x,
            widget_y=widget_y
        )
    
    def map_gaze_to_edf(self, gaze_x: float, gaze_y: float) -> EDFCoordinates:
        """
        Complete transformation from normalized gaze to EDF coordinates.
        
        Args:
            gaze_x: Normalized X coordinate (0-1)
            gaze_y: Normalized Y coordinate (0-1)
            
        Returns:
            EDFCoordinates object with time and channel information
        """
        # Step 1: Gaze to screen coordinates
        screen_x, screen_y = self.map_gaze_to_screen(gaze_x, gaze_y)
        
        # Step 2: Screen to widget coordinates
        widget_x, widget_y = self.map_screen_to_widget(screen_x, screen_y)
        
        # Step 3: Widget to EDF coordinates
        edf_coords = self.map_widget_to_edf(widget_x, widget_y)
        
        logger.debug(f"Gaze ({gaze_x:.3f}, {gaze_y:.3f}) → "
                    f"Screen ({screen_x}, {screen_y}) → "
                    f"Widget ({widget_x}, {widget_y}) → "
                    f"EDF (t={edf_coords.time_seconds:.2f}s, ch={edf_coords.channel_name})")
        
        return edf_coords
    
    def is_gaze_in_widget(self, gaze_x: float, gaze_y: float) -> bool:
        """
        Check if gaze coordinates are within the target widget.
        
        Args:
            gaze_x: Normalized X coordinate (0-1)
            gaze_y: Normalized Y coordinate (0-1)
            
        Returns:
            True if gaze is within widget bounds
        """
        screen_x, screen_y = self.map_gaze_to_screen(gaze_x, gaze_y)
        widget_x, widget_y = self.map_screen_to_widget(screen_x, screen_y)
        
        if not self.bounds:
            return False
        
        return (0 <= widget_x < self.bounds.widget_width and
                0 <= widget_y < self.bounds.widget_height)
    
    def get_channel_y_range(self, channel_index: int) -> Tuple[int, int]:
        """
        Get Y coordinate range for a specific channel.
        
        Args:
            channel_index: Channel index
            
        Returns:
            Tuple of (y_start, y_end) in widget coordinates
        """
        if not self.bounds or channel_index < self.channel_offset:
            return (0, 0)
        
        visible_index = channel_index - self.channel_offset
        if visible_index >= self.visible_channels:
            return (0, 0)
        
        channel_height = self.bounds.widget_height / self.visible_channels
        y_start = int(visible_index * channel_height)
        y_end = int((visible_index + 1) * channel_height)
        
        return (y_start, y_end)
    
    def get_time_x_position(self, time_seconds: float) -> int:
        """
        Get X coordinate for a specific time.
        
        Args:
            time_seconds: Time in seconds
            
        Returns:
            X coordinate in widget coordinates
        """
        if not self.bounds:
            return 0
        
        if (time_seconds < self.current_view_start or 
            time_seconds > self.current_view_start + self.current_view_duration):
            return -1  # Time not in current view
        
        time_ratio = ((time_seconds - self.current_view_start) / 
                     self.current_view_duration)
        return int(time_ratio * self.bounds.widget_width)
    
    def validate_coordinates(self, edf_coords: EDFCoordinates) -> Dict[str, Any]:
        """
        Validate EDF coordinates and provide diagnostic information.
        
        Args:
            edf_coords: EDF coordinates to validate
            
        Returns:
            Dictionary with validation results and diagnostics
        """
        validation = {
            'is_valid': edf_coords.is_valid,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        # Check time bounds
        if edf_coords.time_seconds < 0:
            validation['errors'].append("Negative time coordinate")
        elif edf_coords.time_seconds < self.current_view_start:
            validation['warnings'].append("Time before current view")
        elif edf_coords.time_seconds > self.current_view_start + self.current_view_duration:
            validation['warnings'].append("Time after current view")
        
        # Check channel bounds
        if edf_coords.channel_index < 0:
            validation['errors'].append("Invalid channel index")
        elif edf_coords.channel_index >= len(self.channel_names):
            validation['errors'].append("Channel index out of range")
        
        # Add diagnostic information
        validation['info'] = {
            'time_in_view': (self.current_view_start <= edf_coords.time_seconds <= 
                           self.current_view_start + self.current_view_duration),
            'channel_visible': (self.channel_offset <= edf_coords.channel_index < 
                              self.channel_offset + self.visible_channels),
            'widget_bounds': self.bounds.__dict__ if self.bounds else None,
            'calibration_applied': self.calibration_data.is_valid()
        }
        
        validation['is_valid'] = len(validation['errors']) == 0
        
        return validation