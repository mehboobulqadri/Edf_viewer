"""
Core interface to Tobii Spark eye tracking hardware.
Handles connection, data streaming, and basic gaze data processing.

This module provides the primary interface for connecting to and receiving
data from Tobii eye tracking devices, with robust error handling and 
PyQt6 signal integration for thread-safe communication.
"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# Optional Tobii dependency - graceful fallback if not available
try:
    import tobii_research as tr
    TOBII_AVAILABLE = True
except ImportError:
    TOBII_AVAILABLE = False
    tr = None

logger = logging.getLogger(__name__)


@dataclass
class GazePoint:
    """Data structure for gaze point information."""
    x: float  # Normalized coordinates (0-1)
    y: float  # Normalized coordinates (0-1)
    timestamp: float  # System timestamp
    validity_left: bool  # Left eye validity
    validity_right: bool  # Right eye validity
    confidence: float  # Overall confidence (0-1)


class GazeDataCallback:
    """Callback system for processing gaze data."""
    
    def __init__(self, callback_func: Callable[[GazePoint], None]):
        """
        Initialize callback with processing function.
        
        Args:
            callback_func: Function to call with each gaze point
        """
        self.callback_func = callback_func
    
    def __call__(self, gaze_data):
        """Process incoming gaze data from Tobii SDK."""
        if not gaze_data:
            return
        
        try:
            # Extract gaze data from Tobii format
            left_eye = gaze_data.get('left_gaze_point_on_display_area')
            right_eye = gaze_data.get('right_gaze_point_on_display_area')
            left_valid = gaze_data.get('left_gaze_point_validity', False)
            right_valid = gaze_data.get('right_gaze_point_validity', False)
            
            # Calculate average position if both eyes are valid
            if left_valid and right_valid and left_eye and right_eye:
                x = (left_eye[0] + right_eye[0]) / 2
                y = (left_eye[1] + right_eye[1]) / 2
                confidence = 1.0
            elif left_valid and left_eye:
                x, y = left_eye[0], left_eye[1]
                confidence = 0.7
            elif right_valid and right_eye:
                x, y = right_eye[0], right_eye[1]
                confidence = 0.7
            else:
                # No valid gaze data
                return
            
            # Create gaze point and call callback
            gaze_point = GazePoint(
                x=x,
                y=y,
                timestamp=time.time(),
                validity_left=left_valid,
                validity_right=right_valid,
                confidence=confidence
            )
            
            self.callback_func(gaze_point)
            
        except Exception as e:
            logger.error(f"Error processing gaze data: {e}")


class GazeTracker(QObject):
    """
    Primary hardware interface for Tobii eye tracking devices.
    
    Provides connection management, data streaming, and status monitoring
    with PyQt6 signal integration for thread-safe UI communication.
    """
    
    # PyQt6 signals for thread-safe communication
    connection_status_changed = pyqtSignal(bool)  # Connected/disconnected
    gaze_data_received = pyqtSignal(object)  # New gaze data
    error_occurred = pyqtSignal(str)  # Error message
    device_found = pyqtSignal(str)  # Device name
    
    def __init__(self):
        """Initialize gaze tracker."""
        super().__init__()
        
        self.device = None
        self.is_connected = False
        self.is_streaming = False
        self.callback = None
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self._check_connection)
        
        # Configuration parameters
        self.config = {
            'sampling_rate': 30,  # Hz
            'retry_attempts': 3,
            'retry_delay': 1.0,  # seconds
            'connection_timeout': 5.0,  # seconds
        }
        
        logger.info("GazeTracker initialized")
    
    def set_gaze_callback(self, callback_func: Callable[[GazePoint], None]):
        """
        Set callback function for gaze data processing.
        
        Args:
            callback_func: Function to call with each gaze point
        """
        self.callback = GazeDataCallback(callback_func)
        logger.info("Gaze callback set")
    
    def discover_devices(self) -> list:
        """
        Discover available eye tracking devices using multiple detection methods.
        
        Returns:
            List of discovered device information
        """
        devices = []
        
        # Method 1: Tobii Research SDK
        if TOBII_AVAILABLE:
            try:
                tobii_devices = tr.find_all_eyetrackers()
                for device in tobii_devices:
                    info = {
                        'type': 'tobii',
                        'address': device.address,
                        'device_name': device.device_name,
                        'model': device.model,
                        'serial_number': device.serial_number,
                        'firmware_version': device.firmware_version
                    }
                    devices.append(info)
                    logger.info(f"Found Tobii device: {info['device_name']} ({info['model']})")
                    self.device_found.emit(info['device_name'])
            except Exception as e:
                logger.warning(f"Tobii detection failed: {e}")
        
        # Method 2: USB device detection for common eye trackers
        try:
            import subprocess
            import re
            
            # Get USB device list on Windows
            result = subprocess.run(['wmic', 'path', 'win32_pnpentity', 'get', 'name'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                usb_devices = result.stdout.lower()
                
                # Check for known eye tracker manufacturers
                eye_tracker_patterns = [
                    (r'tobii', 'Tobii Eye Tracker'),
                    (r'eyetech', 'EyeTech Digital Systems'),
                    (r'gazepoint', 'GazePoint Eye Tracker'),
                    (r'sr research', 'SR Research EyeLink'),
                    (r'smart eye', 'Smart Eye Tracker'),
                    (r'pupil labs', 'Pupil Labs Eye Tracker'),
                    (r'mirametrix', 'Mirametrix Eye Tracker'),
                    (r'sensomotoric', 'SensoMotoric Instruments'),
                ]
                
                for pattern, device_name in eye_tracker_patterns:
                    if re.search(pattern, usb_devices):
                        info = {
                            'type': 'usb_detected',
                            'address': 'USB',
                            'device_name': device_name,
                            'model': 'USB Connected',
                            'serial_number': 'Unknown',
                            'firmware_version': 'Unknown'
                        }
                        devices.append(info)
                        logger.info(f"Found USB eye tracker: {device_name}")
                        self.device_found.emit(device_name)
                        
        except Exception as e:
            logger.warning(f"USB detection failed: {e}")
        
        # Method 3: Check for running eye tracker software
        try:
            import psutil
            
            eye_tracker_processes = [
                ('tobii', 'Tobii Eye Tracker Service'),
                ('eyetech', 'EyeTech TM5'),
                ('gazepoint', 'GazePoint GP3'),
                ('eyelink', 'SR Research EyeLink'),
                ('smarteye', 'Smart Eye Pro'),
                ('pupil', 'Pupil Capture'),
            ]
            
            running_processes = [p.name().lower() for p in psutil.process_iter()]
            
            for process_name, device_name in eye_tracker_processes:
                if any(process_name in proc for proc in running_processes):
                    info = {
                        'type': 'software_detected',
                        'address': 'Software',
                        'device_name': device_name,
                        'model': 'Software Running',
                        'serial_number': 'Unknown',
                        'firmware_version': 'Unknown'
                    }
                    devices.append(info)
                    logger.info(f"Found eye tracker software: {device_name}")
                    self.device_found.emit(device_name)
                    
        except Exception as e:
            logger.warning(f"Process detection failed: {e}")
        
        if not devices:
            logger.info("No eye tracking devices found")
            self.error_occurred.emit("No eye tracking devices found. Check hardware connection and drivers.")
        
        return devices
    
    def connect_device(self, device_address: Optional[str] = None) -> bool:
        """
        Connect to eye tracking device.
        
        Args:
            device_address: Specific device address, or None for auto-discovery
            
        Returns:
            True if connection successful, False otherwise
        """
        if not TOBII_AVAILABLE:
            self.error_occurred.emit("Tobii Research SDK not available")
            return False
        
        try:
            if device_address:
                # Connect to specific device
                self.device = tr.EyeTracker(device_address)
            else:
                # Auto-discovery - connect to first available device
                devices = tr.find_all_eyetrackers()
                if not devices:
                    self.error_occurred.emit("No eye tracking devices found")
                    return False
                
                self.device = devices[0]
            
            # Test connection
            device_info = {
                'name': self.device.device_name,
                'model': self.device.model,
                'serial': self.device.serial_number
            }
            
            self.is_connected = True
            self.connection_status_changed.emit(True)
            
            # Start connection monitoring
            self.connection_timer.start(5000)  # Check every 5 seconds
            
            logger.info(f"Connected to device: {device_info['name']}")
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.error_occurred.emit(f"Connection failed: {str(e)}")
            self.is_connected = False
            self.connection_status_changed.emit(False)
            return False
    
    def disconnect_device(self):
        """Disconnect from eye tracking device."""
        try:
            if self.is_streaming:
                self.stop_streaming()
            
            self.connection_timer.stop()
            self.device = None
            self.is_connected = False
            self.connection_status_changed.emit(False)
            
            logger.info("Device disconnected")
            
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            self.error_occurred.emit(f"Disconnection error: {str(e)}")
    
    def start_streaming(self) -> bool:
        """
        Start gaze data streaming.
        
        Returns:
            True if streaming started successfully, False otherwise
        """
        if not self.is_connected or not self.device:
            self.error_occurred.emit("Device not connected")
            return False
        
        if not self.callback:
            self.error_occurred.emit("No callback function set")
            return False
        
        try:
            # Subscribe to gaze data
            self.device.subscribe_to(tr.EYETRACKER_GAZE_DATA, self.callback)
            self.is_streaming = True
            
            logger.info("Gaze data streaming started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            self.error_occurred.emit(f"Streaming failed: {str(e)}")
            return False
    
    def stop_streaming(self):
        """Stop gaze data streaming."""
        try:
            if self.device and self.is_streaming:
                self.device.unsubscribe_from(tr.EYETRACKER_GAZE_DATA, self.callback)
                self.is_streaming = False
                logger.info("Gaze data streaming stopped")
                
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
            self.error_occurred.emit(f"Streaming stop error: {str(e)}")
    
    def _check_connection(self):
        """Periodically check device connection status."""
        if not self.device:
            return
        
        try:
            # Try to get device info to test connection
            _ = self.device.device_name
            
            if not self.is_connected:
                self.is_connected = True
                self.connection_status_changed.emit(True)
                logger.info("Device connection restored")
                
        except Exception as e:
            if self.is_connected:
                self.is_connected = False
                self.connection_status_changed.emit(False)
                self.error_occurred.emit("Device connection lost")
                logger.warning("Device connection lost")
    
    def get_device_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current device information.
        
        Returns:
            Device information dictionary or None if not connected
        """
        if not self.device or not self.is_connected:
            return None
        
        try:
            return {
                'device_name': self.device.device_name,
                'model': self.device.model,
                'serial_number': self.device.serial_number,
                'firmware_version': self.device.firmware_version,
                'address': self.device.address,
                'is_connected': self.is_connected,
                'is_streaming': self.is_streaming
            }
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return None
    
    def update_config(self, config_updates: Dict[str, Any]):
        """
        Update configuration parameters.
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        self.config.update(config_updates)
        logger.info(f"Configuration updated: {config_updates}")


# Mock implementation for testing when Tobii SDK is not available
class MockGazeTracker(GazeTracker):
    """Mock implementation for testing without hardware."""
    
    def __init__(self):
        super().__init__()
        self.mock_timer = QTimer()
        self.mock_timer.timeout.connect(self._generate_mock_data)
        
    def connect_device(self, device_address: Optional[str] = None) -> bool:
        """Mock connection always succeeds."""
        self.is_connected = True
        self.connection_status_changed.emit(True)
        self.device_found.emit("Mock Eye Tracker")
        logger.info("Mock device connected")
        return True
    
    def start_streaming(self) -> bool:
        """Start mock data generation."""
        if not self.callback:
            return False
        
        self.is_streaming = True
        self.mock_timer.start(33)  # ~30 FPS
        logger.info("Mock streaming started")
        return True
    
    def stop_streaming(self):
        """Stop mock data generation."""
        self.mock_timer.stop()
        self.is_streaming = False
        logger.info("Mock streaming stopped")
    
    def _generate_mock_data(self):
        """Generate mock gaze data for testing."""
        import random
        
        if self.callback and self.callback.callback_func:
            # Generate random gaze point
            gaze_point = GazePoint(
                x=random.uniform(0.2, 0.8),
                y=random.uniform(0.2, 0.8),
                timestamp=time.time(),
                validity_left=True,
                validity_right=True,
                confidence=random.uniform(0.8, 1.0)
            )
            
            try:
                self.callback.callback_func(gaze_point)
            except Exception as e:
                logger.error(f"Error in mock data callback: {e}")