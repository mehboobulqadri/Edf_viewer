"""
Real-time Gaze Processing Pipeline.

Integrates gaze data acquisition, coordinate mapping, fixation detection,
and EDF annotation generation into a cohesive processing system.

This module handles the complete data flow from raw gaze coordinates
to meaningful EDF annotations with robust error handling and performance monitoring.
"""

import time
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from .gaze_tracker import GazeTracker, GazePoint
from .coordinate_mapper import CoordinateMapper, EDFCoordinates
from .fixation_detector import FixationDetector, FixationPoint, FixationConfig

logger = logging.getLogger(__name__)


@dataclass
class GazeEvent:
    """Represents a processed gaze event with EDF context."""
    gaze_point: GazePoint
    edf_coordinates: EDFCoordinates
    fixation: Optional[FixationPoint]
    timestamp: float
    processing_latency: float  # Time from gaze to processing completion


@dataclass
class ProcessingStats:
    """Statistics for gaze processing pipeline performance."""
    total_gaze_points: int = 0
    valid_gaze_points: int = 0
    fixations_detected: int = 0
    annotations_created: int = 0
    average_latency_ms: float = 0.0
    peak_latency_ms: float = 0.0
    processing_rate_hz: float = 0.0
    error_count: int = 0
    last_update_time: float = 0.0


class GazeProcessor(QObject):
    """
    Main gaze processing pipeline that orchestrates all gaze tracking components.
    
    Handles the complete workflow:
    1. Receive gaze data from eye tracker
    2. Map coordinates to EDF space
    3. Detect fixations
    4. Generate annotation events
    5. Provide real-time feedback
    """
    
    # PyQt signals for communication with UI
    gaze_event_processed = pyqtSignal(object)  # GazeEvent
    fixation_detected = pyqtSignal(object)  # FixationPoint with EDF context
    annotation_triggered = pyqtSignal(object)  # Annotation data
    processing_error = pyqtSignal(str)  # Error message
    statistics_updated = pyqtSignal(object)  # ProcessingStats
    
    def __init__(self):
        """Initialize gaze processor."""
        super().__init__()
        
        # Component instances
        self.gaze_tracker = None
        self.coordinate_mapper = CoordinateMapper()
        self.fixation_detector = None
        
        # Processing state
        self.is_active = False
        self.processing_config = {}
        self.stats = ProcessingStats()
        self.latency_buffer = []  # For average latency calculation
        
        # Timers
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_statistics)
        
        # Event callbacks
        self.annotation_callbacks = []
        self.feedback_callbacks = []
        
        logger.info("GazeProcessor initialized")
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure the processing pipeline.
        
        Args:
            config: Configuration dictionary from GazeModeSetupDialog
        """
        self.processing_config = config
        
        # Configure fixation detection
        fixation_config = FixationConfig(
            velocity_threshold=config.get('gaze_detection', {}).get('spatial_accuracy', 50),
            duration_threshold=config.get('gaze_detection', {}).get('fixation_duration', 1.0),
            confidence_threshold=config.get('gaze_detection', {}).get('confidence_threshold', 0.7),
            noise_reduction=config.get('gaze_detection', {}).get('enable_smoothing', True)
        )
        
        self.fixation_detector = FixationDetector(fixation_config)
        
        # Configure coordinate mapper with EDF context
        display_config = config.get('display', {})
        self.coordinate_mapper.set_edf_context(
            channel_names=[],  # Will be set when EDF is loaded
            view_start=0.0,
            view_duration=display_config.get('time_scale', 10.0),
            visible_channels=display_config.get('channel_count', 10),
            channel_offset=0
        )
        
        logger.info(f"Gaze processor configured: fixation_duration={fixation_config.duration_threshold}s")
    
    def set_gaze_tracker(self, tracker: GazeTracker):
        """
        Set the gaze tracker instance.
        
        Args:
            tracker: Configured gaze tracker
        """
        self.gaze_tracker = tracker
        
        # Set up gaze data callback
        self.gaze_tracker.set_gaze_callback(self._process_gaze_point)
        
        logger.info("Gaze tracker set and callback configured")
    
    def set_edf_context(self, channel_names: List[str], view_start: float, 
                       view_duration: float, visible_channels: int, channel_offset: int = 0):
        """
        Update EDF viewing context for coordinate mapping.
        
        Args:
            channel_names: List of channel names
            view_start: Current view start time
            view_duration: Current view duration
            visible_channels: Number of visible channels
            channel_offset: Channel scroll offset
        """
        self.coordinate_mapper.set_edf_context(
            channel_names, view_start, view_duration, visible_channels, channel_offset
        )
        
        logger.debug(f"EDF context updated: {len(channel_names)} channels, "
                    f"view {view_start:.1f}-{view_start + view_duration:.1f}s")
    
    def set_target_widget(self, widget):
        """
        Set the target widget for coordinate mapping.
        
        Args:
            widget: The EDF plot widget
        """
        self.coordinate_mapper.set_target_widget(widget)
        logger.debug("Target widget set for coordinate mapping")
    
    def start_processing(self) -> bool:
        """
        Start the gaze processing pipeline.
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self.gaze_tracker:
            self.processing_error.emit("No gaze tracker configured")
            return False
        
        if not self.fixation_detector:
            self.processing_error.emit("No fixation detector configured")
            return False
        
        try:
            # Start gaze data streaming
            if not self.gaze_tracker.start_streaming():
                self.processing_error.emit("Failed to start gaze data streaming")
                return False
            
            # Reset statistics
            self.stats = ProcessingStats()
            self.stats.last_update_time = time.time()
            self.latency_buffer = []
            
            # Start statistics timer
            self.stats_timer.start(1000)  # Update every second
            
            self.is_active = True
            logger.info("Gaze processing pipeline started")
            return True
            
        except Exception as e:
            error_msg = f"Failed to start processing: {str(e)}"
            self.processing_error.emit(error_msg)
            logger.error(error_msg)
            return False
    
    def stop_processing(self):
        """Stop the gaze processing pipeline."""
        try:
            self.is_active = False
            
            # Stop timers
            self.stats_timer.stop()
            
            # Stop gaze data streaming
            if self.gaze_tracker:
                self.gaze_tracker.stop_streaming()
            
            # Reset detectors
            if self.fixation_detector:
                self.fixation_detector.reset()
            
            logger.info("Gaze processing pipeline stopped")
            
        except Exception as e:
            logger.error(f"Error stopping processing: {e}")
    
    def _process_gaze_point(self, gaze_point: GazePoint):
        """
        Process a single gaze point through the complete pipeline.
        
        Args:
            gaze_point: Raw gaze point from eye tracker
        """
        if not self.is_active:
            return
        
        start_time = time.time()
        
        try:
            self.stats.total_gaze_points += 1
            
            # Step 1: Map gaze coordinates to EDF space
            edf_coords = self.coordinate_mapper.map_gaze_to_edf(gaze_point.x, gaze_point.y)
            
            # Check if gaze is within valid EDF area
            if not edf_coords.is_valid:
                # Still count as processed but skip further processing
                logger.debug(f"Skipping invalid coordinates: {edf_coords.time_seconds}, {edf_coords.channel_name}")
                return  # Skip invalid coordinates
            
            self.stats.valid_gaze_points += 1
            
            # Step 2: Process through fixation detector
            fixation = None
            if self.fixation_detector:
                fixation = self.fixation_detector.process_gaze_point(gaze_point)
                
                if fixation:
                    self.stats.fixations_detected += 1
                    self._handle_fixation_detected(fixation, edf_coords)
            
            # Step 3: Create gaze event
            processing_latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            gaze_event = GazeEvent(
                gaze_point=gaze_point,
                edf_coordinates=edf_coords,
                fixation=fixation,
                timestamp=time.time(),
                processing_latency=processing_latency
            )
            
            # Step 4: Emit event for UI updates
            self.gaze_event_processed.emit(gaze_event)
            
            # Update latency statistics
            self._update_latency_stats(processing_latency)
            
            # Step 5: Check for annotation triggers
            self._check_annotation_triggers(gaze_event)
            
        except Exception as e:
            self.stats.error_count += 1
            error_msg = f"Error processing gaze point: {str(e)}"
            logger.error(error_msg)
            self.processing_error.emit(error_msg)
    
    def _handle_fixation_detected(self, fixation: FixationPoint, edf_coords: EDFCoordinates):
        """
        Handle a newly detected fixation.
        
        Args:
            fixation: Detected fixation
            edf_coords: EDF coordinates for the fixation center
        """
        try:
            # Map fixation center to EDF coordinates
            fixation_edf_coords = self.coordinate_mapper.map_gaze_to_edf(fixation.x, fixation.y)
            
            # Create enriched fixation data
            fixation_data = {
                'fixation': fixation,
                'edf_coordinates': fixation_edf_coords,
                'channel_name': fixation_edf_coords.channel_name,
                'time_seconds': fixation_edf_coords.time_seconds,
                'duration': fixation.duration,
                'confidence': fixation.confidence
            }
            
            # Emit fixation detected signal
            self.fixation_detected.emit(fixation_data)
            
            logger.debug(f"Fixation detected at channel {fixation_edf_coords.channel_name}, "
                        f"time {fixation_edf_coords.time_seconds:.2f}s, "
                        f"duration {fixation.duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error handling fixation: {e}")
    
    def _check_annotation_triggers(self, gaze_event: GazeEvent):
        """
        Check if annotation should be triggered based on gaze event.
        
        Args:
            gaze_event: Processed gaze event
        """
        try:
            # Get trigger configuration
            trigger_config = self.processing_config.get('annotations', {})
            trigger_mode = trigger_config.get('trigger_mode', 'Fixation Only')
            
            annotation_data = None
            
            if trigger_mode == 'Fixation Only' and gaze_event.fixation:
                # Trigger annotation on fixation
                annotation_data = self._create_annotation_data(gaze_event)
                
            elif trigger_mode == 'Fixation + Blink':
                # Enhanced trigger logic would go here
                # For now, same as fixation only
                if gaze_event.fixation:
                    annotation_data = self._create_annotation_data(gaze_event)
            
            if annotation_data:
                self.stats.annotations_created += 1
                self.annotation_triggered.emit(annotation_data)
                
                # Call registered callbacks
                for callback in self.annotation_callbacks:
                    try:
                        callback(annotation_data)
                    except Exception as e:
                        logger.error(f"Error in annotation callback: {e}")
                        
        except Exception as e:
            logger.error(f"Error checking annotation triggers: {e}")
    
    def _create_annotation_data(self, gaze_event: GazeEvent) -> Dict[str, Any]:
        """
        Create annotation data from gaze event.
        
        Args:
            gaze_event: Gaze event to create annotation from
            
        Returns:
            Annotation data dictionary
        """
        annotation_config = self.processing_config.get('annotations', {})
        
        # Calculate annotation timing
        if gaze_event.fixation:
            start_time = gaze_event.edf_coordinates.time_seconds - gaze_event.fixation.duration / 2
            duration = gaze_event.fixation.duration
        else:
            start_time = gaze_event.edf_coordinates.time_seconds
            duration = annotation_config.get('default_duration', 1.0)
        
        # Generate description
        if annotation_config.get('auto_description', True):
            description = self._generate_auto_description(gaze_event)
        else:
            description = annotation_config.get('default_category', 'Gaze Annotation')
        
        return {
            'start_time': start_time,
            'duration': duration,
            'description': description,
            'channel': gaze_event.edf_coordinates.channel_name,
            'confidence': gaze_event.gaze_point.confidence,
            'fixation_duration': gaze_event.fixation.duration if gaze_event.fixation else 0.0,
            'gaze_coordinates': (gaze_event.gaze_point.x, gaze_event.gaze_point.y),
            'edf_coordinates': gaze_event.edf_coordinates,
            'timestamp': gaze_event.timestamp,
            'processing_latency': gaze_event.processing_latency
        }
    
    def _generate_auto_description(self, gaze_event: GazeEvent) -> str:
        """
        Generate automatic description for annotation.
        
        Args:
            gaze_event: Gaze event to describe
            
        Returns:
            Auto-generated description
        """
        base_category = self.processing_config.get('annotations', {}).get('default_category', 'Event')
        
        if gaze_event.fixation:
            duration_desc = "brief" if gaze_event.fixation.duration < 1.0 else "sustained"
            confidence_desc = "high" if gaze_event.fixation.confidence > 0.8 else "moderate"
            return f"{base_category} - {duration_desc} fixation ({confidence_desc} confidence)"
        else:
            return f"{base_category} - gaze point"
    
    def _update_latency_stats(self, latency: float):
        """
        Update latency statistics.
        
        Args:
            latency: Processing latency in milliseconds
        """
        self.latency_buffer.append(latency)
        
        # Keep only last 100 measurements
        if len(self.latency_buffer) > 100:
            self.latency_buffer.pop(0)
        
        # Update peak latency
        if latency > self.stats.peak_latency_ms:
            self.stats.peak_latency_ms = latency
        
        # Update average latency
        self.stats.average_latency_ms = sum(self.latency_buffer) / len(self.latency_buffer)
    
    def _update_statistics(self):
        """Update processing statistics (called by timer)."""
        if not self.is_active:
            return
        
        current_time = time.time()
        time_diff = current_time - self.stats.last_update_time
        
        if time_diff > 0:
            # Calculate processing rate
            points_processed = self.stats.total_gaze_points
            self.stats.processing_rate_hz = points_processed / (current_time - self.stats.last_update_time + 1e-6)
        
        self.stats.last_update_time = current_time
        
        # Emit updated statistics
        self.statistics_updated.emit(self.stats)
    
    def add_annotation_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Add callback for annotation events.
        
        Args:
            callback: Function to call when annotation is triggered
        """
        self.annotation_callbacks.append(callback)
    
    def add_feedback_callback(self, callback: Callable[[GazeEvent], None]):
        """
        Add callback for gaze feedback events.
        
        Args:
            callback: Function to call for each gaze event
        """
        self.feedback_callbacks.append(callback)
    
    def get_statistics(self) -> ProcessingStats:
        """
        Get current processing statistics.
        
        Returns:
            Current statistics
        """
        return self.stats
    
    def get_recent_fixations(self, duration: float = 10.0) -> List[FixationPoint]:
        """
        Get fixations detected in the last N seconds.
        
        Args:
            duration: Time window in seconds
            
        Returns:
            List of recent fixations
        """
        if self.fixation_detector:
            return self.fixation_detector.get_recent_fixations(duration)
        return []
    
    def update_processing_config(self, config: Dict[str, Any]):
        """
        Update processing configuration without stopping.
        
        Args:
            config: New configuration dictionary
        """
        self.processing_config.update(config)
        
        # Update fixation detector configuration if needed
        if self.fixation_detector and 'gaze_detection' in config:
            gaze_config = config['gaze_detection']
            new_fixation_config = FixationConfig(
                velocity_threshold=gaze_config.get('spatial_accuracy', 50),
                duration_threshold=gaze_config.get('fixation_duration', 1.0),
                confidence_threshold=gaze_config.get('confidence_threshold', 0.7),
                noise_reduction=gaze_config.get('enable_smoothing', True)
            )
            self.fixation_detector.update_config(new_fixation_config)
        
        logger.info("Processing configuration updated")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            self.stop_processing()
            
            # Clear callbacks
            self.annotation_callbacks.clear()
            self.feedback_callbacks.clear()
            
            # Clean up components
            if self.fixation_detector:
                self.fixation_detector.clear_old_fixations(0)  # Clear all
            
            logger.info("GazeProcessor cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")