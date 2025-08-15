"""
Validation and Error Handling Utilities
Centralized validation and error handling for the EDF Viewer application.
"""

import logging
from pathlib import Path
from typing import Any, Tuple, Optional
from PyQt6.QtWidgets import QMessageBox

class ValidationUtils:
    """Centralized validation utilities to reduce code duplication"""
    
    @staticmethod
    def validate_raw_data(raw_data, context="operation") -> bool:
        """Centralized raw data validation"""
        if not raw_data:
            logging.debug(f"{context}: No raw data available")
            return False
            
        if not hasattr(raw_data, 'info') or not raw_data.info:
            logging.error(f"{context}: Raw data missing info structure")
            return False
            
        if not hasattr(raw_data, 'ch_names') or not raw_data.ch_names:
            logging.error(f"{context}: Raw data missing channel names")
            return False
            
        if 'sfreq' not in raw_data.info:
            logging.error(f"{context}: Raw data missing sampling frequency")
            return False
            
        return True
    
    @staticmethod
    def validate_ui_component(obj, component_name: str, context="operation") -> bool:
        """Centralized UI component validation"""
        if not hasattr(obj, component_name):
            logging.error(f"{context}: Missing {component_name}")
            return False
            
        component = getattr(obj, component_name)
        if not component:
            logging.error(f"{context}: {component_name} not initialized")
            return False
            
        return True
    
    @staticmethod
    def validate_numeric_range(value: Any, min_val: float, max_val: float, 
                             name: str, context="operation") -> Tuple[bool, Optional[float]]:
        """Validate numeric values are within acceptable ranges"""
        try:
            value = float(value)
            if not (min_val <= value <= max_val):
                logging.error(f"{context}: {name} value {value} outside range [{min_val}, {max_val}]")
                return False, None
            return True, value
        except (ValueError, TypeError) as e:
            logging.error(f"{context}: Invalid {name} value: {e}")
            return False, None
    
    @staticmethod
    def validate_file_path(file_path: str, supported_extensions: list = None) -> Tuple[bool, Optional[Path]]:
        """Validate file path exists and has correct extension"""
        try:
            if not file_path or not isinstance(file_path, str):
                logging.error("Invalid file path: empty or not string")
                return False, None
            
            path = Path(file_path)
            
            if not path.exists():
                logging.error(f"File does not exist: {file_path}")
                return False, None
            
            if not path.is_file():
                logging.error(f"Path is not a file: {file_path}")
                return False, None
            
            if supported_extensions and path.suffix.lower() not in supported_extensions:
                logging.error(f"Unsupported file format: {path.suffix}")
                return False, None
            
            return True, path
            
        except Exception as e:
            logging.error(f"File path validation error: {e}")
            return False, None
    
    @staticmethod
    def validate_channel_selection(channel_indices: list, max_channels: int) -> bool:
        """Validate channel selection indices"""
        if not channel_indices:
            logging.error("No channels selected")
            return False
        
        if not isinstance(channel_indices, list):
            logging.error("Channel indices must be a list")
            return False
        
        for idx in channel_indices:
            if not isinstance(idx, int) or idx < 0 or idx >= max_channels:
                logging.error(f"Invalid channel index: {idx}")
                return False
        
        return True

class ErrorHandlingUtils:
    """Centralized error handling utilities"""
    
    @staticmethod
    def safe_execute(func, context="operation", default_return=None, *args, **kwargs):
        """Safely execute function with comprehensive error handling"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {context}: {e}", exc_info=True)
            return default_return
    
    @staticmethod
    def show_user_error(parent, title: str, message: str, error_type="warning"):
        """Centralized user error message display"""
        try:
            if error_type == "critical":
                QMessageBox.critical(parent, title, message)
            elif error_type == "information":
                QMessageBox.information(parent, title, message)
            else:
                QMessageBox.warning(parent, title, message)
        except Exception as e:
            logging.error(f"Failed to show user error message: {e}")
    
    @staticmethod
    def log_performance_warning(operation: str, duration: float, threshold: float = 1.0):
        """Log performance warnings for slow operations"""
        if duration > threshold:
            logging.warning(f"Performance warning: {operation} took {duration:.2f}s (threshold: {threshold:.2f}s)")
    
    @staticmethod
    def handle_memory_error(context: str, available_memory: float, required_memory: float):
        """Handle memory-related errors"""
        logging.error(
            f"Memory error in {context}: "
            f"Required {required_memory:.1f}MB, Available {available_memory:.1f}MB"
        )
        return "Insufficient memory available for this operation"
    
    @staticmethod
    def create_error_context(operation: str, **kwargs) -> str:
        """Create detailed error context for logging"""
        context_parts = [operation]
        for key, value in kwargs.items():
            context_parts.append(f"{key}={value}")
        return " | ".join(context_parts)

class DataValidator:
    """Specialized data validation utilities"""
    
    @staticmethod
    def validate_edf_compatibility(raw_data) -> Tuple[bool, str]:
        """Validate EDF data compatibility"""
        try:
            if not ValidationUtils.validate_raw_data(raw_data, "EDF compatibility check"):
                return False, "Invalid raw data structure"
            
            # Check sampling frequency
            sfreq = raw_data.info['sfreq']
            if sfreq <= 0:
                return False, f"Invalid sampling frequency: {sfreq}"
            
            # Check channel count
            n_channels = len(raw_data.ch_names)
            if n_channels == 0:
                return False, "No channels found in EDF file"
            
            # Check data duration
            n_samples = raw_data.n_times
            duration = n_samples / sfreq
            if duration <= 0:
                return False, f"Invalid data duration: {duration}s"
            
            # Log compatibility info
            logging.info(
                f"EDF compatibility check passed: "
                f"{n_channels} channels, {sfreq}Hz, {duration:.1f}s duration"
            )
            
            return True, "EDF data is compatible"
            
        except Exception as e:
            error_msg = f"EDF compatibility validation failed: {e}"
            logging.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def validate_view_parameters(view_start: float, view_duration: float, 
                                max_duration: float) -> Tuple[bool, str]:
        """Validate view parameters"""
        if view_start < 0:
            return False, "View start time cannot be negative"
        
        if view_duration <= 0:
            return False, "View duration must be positive"
        
        if view_start + view_duration > max_duration:
            return False, f"View extends beyond data duration ({max_duration:.1f}s)"
        
        return True, "View parameters are valid"

# Enhanced logging configuration with multiple handlers
def setup_logging():
    """Configure comprehensive logging with file and console handlers"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers to prevent duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler for detailed logs
    file_handler = logging.FileHandler('edf_viewer_errors.log', mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # Performance log for benchmarking
    perf_handler = logging.FileHandler('edf_viewer_performance.log', mode='a')
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(simple_formatter)
    perf_handler.addFilter(lambda record: 'performance' in record.getMessage().lower())
    logger.addHandler(perf_handler)
    
    logging.info("Enhanced logging system initialized")