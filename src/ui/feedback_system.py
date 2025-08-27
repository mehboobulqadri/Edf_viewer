"""
Real-time feedback system for gaze tracking.

Provides audio and visual feedback during gaze annotation sessions,
including sound cues, visual indicators, and user guidance.

This module handles all feedback mechanisms to help users understand
the current state of gaze tracking and annotation creation.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame

# Optional multimedia imports - fallback if not available
try:
    from PyQt6.QtMultimedia import QSoundEffect, QAudioOutput, QMediaPlayer
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of feedback events."""
    GAZE_DETECTED = "gaze_detected"
    FIXATION_STARTED = "fixation_started"
    FIXATION_PROGRESS = "fixation_progress"
    FIXATION_COMPLETED = "fixation_completed"
    ANNOTATION_CREATED = "annotation_created"
    ERROR_OCCURRED = "error_occurred"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


@dataclass
class FeedbackEvent:
    """Represents a feedback event."""
    event_type: FeedbackType
    message: str
    data: Dict[str, Any]
    timestamp: float
    priority: int = 1  # 1=low, 2=medium, 3=high


class AudioFeedback:
    """
    Audio feedback system using Qt's multimedia capabilities.
    
    Provides sound cues for various gaze tracking events with
    configurable volume and sound selection.
    """
    
    def __init__(self):
        """Initialize audio feedback system."""
        self.enabled = False
        self.volume = 0.5
        self.sound_effects = {}
        self.audio_output = None
        self.media_player = None
        
        # Check if multimedia is available
        if not MULTIMEDIA_AVAILABLE:
            logger.info("Audio feedback disabled - PyQt6.QtMultimedia not available")
            return
        
        # Try to initialize audio components
        try:
            # Create audio output
            self.audio_output = QAudioOutput()
            self.audio_output.setVolume(self.volume)
            
            # Create media player for longer sounds
            self.media_player = QMediaPlayer()
            self.media_player.setAudioOutput(self.audio_output)
            
            self.enabled = True
            logger.info("Audio feedback system initialized")
            
        except Exception as e:
            logger.warning(f"Audio feedback not available: {e}")
            self.enabled = False
    
    def set_volume(self, volume: float):
        """
        Set audio volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        if self.audio_output:
            self.audio_output.setVolume(self.volume)
    
    def play_feedback(self, event_type: FeedbackType, data: Dict[str, Any] = None):
        """
        Play audio feedback for an event.
        
        Args:
            event_type: Type of feedback event
            data: Additional event data
        """
        if not self.enabled or self.volume == 0:
            return
        
        try:
            # Generate simple tones for different events
            # In a full implementation, these would be actual sound files
            if event_type == FeedbackType.FIXATION_STARTED:
                self._play_tone(440, 0.1)  # A4 note, 100ms
            elif event_type == FeedbackType.FIXATION_COMPLETED:
                self._play_tone(880, 0.2)  # A5 note, 200ms
            elif event_type == FeedbackType.ANNOTATION_CREATED:
                self._play_tone(660, 0.3)  # E5 note, 300ms
            elif event_type == FeedbackType.ERROR_OCCURRED:
                self._play_tone(220, 0.5)  # A3 note, 500ms
            
            logger.debug(f"Audio feedback played for {event_type.value}")
            
        except Exception as e:
            logger.error(f"Error playing audio feedback: {e}")
    
    def _play_tone(self, frequency: float, duration: float):
        """
        Play a simple tone (placeholder implementation).
        
        Args:
            frequency: Tone frequency in Hz
            duration: Tone duration in seconds
        """
        # This is a placeholder - in a real implementation, you would
        # generate actual audio data or use sound files
        logger.debug(f"Playing tone: {frequency}Hz for {duration}s")


class VisualFeedbackPanel(QWidget):
    """
    Visual feedback panel showing gaze tracking status and progress.
    
    Displays real-time information about gaze tracking state,
    fixation progress, and system status.
    """
    
    def __init__(self):
        """Initialize visual feedback panel."""
        super().__init__()
        
        self.setFixedHeight(100)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI';
                border: 1px solid #555555;
            }
            QLabel {
                font-size: 12px;
                padding: 2px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        
        self._setup_ui()
        self._reset_state()
        
        logger.debug("VisualFeedbackPanel initialized")
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Status row
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.confidence_label = QLabel("Confidence: --")
        status_layout.addWidget(self.confidence_label)
        
        layout.addLayout(status_layout)
        
        # Progress row
        progress_layout = QHBoxLayout()
        
        progress_layout.addWidget(QLabel("Fixation Progress:"))
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.time_label = QLabel("0.0s")
        progress_layout.addWidget(self.time_label)
        
        layout.addLayout(progress_layout)
        
        # Statistics row
        stats_layout = QHBoxLayout()
        
        self.fixations_label = QLabel("Fixations: 0")
        stats_layout.addWidget(self.fixations_label)
        
        self.annotations_label = QLabel("Annotations: 0")
        stats_layout.addWidget(self.annotations_label)
        
        stats_layout.addStretch()
        
        self.fps_label = QLabel("FPS: --")
        stats_layout.addWidget(self.fps_label)
        
        layout.addLayout(stats_layout)
    
    def _reset_state(self):
        """Reset panel to initial state."""
        self.fixation_count = 0
        self.annotation_count = 0
        self.current_confidence = 0.0
        self.current_fps = 0.0
        self.fixation_start_time = None
        self.target_fixation_duration = 1.0
    
    def update_status(self, status: str, color: str = "#ffffff"):
        """
        Update status display.
        
        Args:
            status: Status message
            color: Text color
        """
        self.status_label.setText(f"Status: {status}")
        self.status_label.setStyleSheet(f"font-weight: bold; color: {color};")
    
    def update_confidence(self, confidence: float):
        """
        Update gaze confidence display.
        
        Args:
            confidence: Confidence value (0-1)
        """
        self.current_confidence = confidence
        confidence_percent = int(confidence * 100)
        
        # Color based on confidence level
        if confidence > 0.8:
            color = "#4CAF50"  # Green
        elif confidence > 0.5:
            color = "#FFC107"  # Yellow
        else:
            color = "#F44336"  # Red
        
        self.confidence_label.setText(f"Confidence: {confidence_percent}%")
        self.confidence_label.setStyleSheet(f"color: {color};")
    
    def start_fixation_progress(self, duration: float):
        """
        Start fixation progress tracking.
        
        Args:
            duration: Target fixation duration in seconds
        """
        self.fixation_start_time = time.time()
        self.target_fixation_duration = duration
        self.progress_bar.setValue(0)
        self.update_status("Tracking Fixation", "#FFC107")
    
    def update_fixation_progress(self, elapsed_time: float):
        """
        Update fixation progress.
        
        Args:
            elapsed_time: Time elapsed since fixation start
        """
        if self.fixation_start_time:
            progress = min(100, int((elapsed_time / self.target_fixation_duration) * 100))
            self.progress_bar.setValue(progress)
            self.time_label.setText(f"{elapsed_time:.1f}s")
    
    def complete_fixation(self):
        """Mark fixation as completed."""
        self.fixation_count += 1
        self.fixations_label.setText(f"Fixations: {self.fixation_count}")
        self.progress_bar.setValue(100)
        self.update_status("Fixation Complete", "#4CAF50")
        
        # Reset after brief delay
        QTimer.singleShot(1000, self._reset_fixation_display)
    
    def cancel_fixation(self):
        """Cancel current fixation."""
        self._reset_fixation_display()
        self.update_status("Fixation Cancelled", "#F44336")
    
    def add_annotation(self):
        """Record new annotation."""
        self.annotation_count += 1
        self.annotations_label.setText(f"Annotations: {self.annotation_count}")
        self.update_status("Annotation Created", "#4CAF50")
    
    def update_fps(self, fps: float):
        """
        Update FPS display.
        
        Args:
            fps: Current frames per second
        """
        self.current_fps = fps
        self.fps_label.setText(f"FPS: {fps:.1f}")
    
    def _reset_fixation_display(self):
        """Reset fixation progress display."""
        self.progress_bar.setValue(0)
        self.time_label.setText("0.0s")
        self.fixation_start_time = None
        self.update_status("Ready", "#ffffff")
    
    def reset_statistics(self):
        """Reset all statistics."""
        self._reset_state()
        self.fixations_label.setText("Fixations: 0")
        self.annotations_label.setText("Annotations: 0")
        self.fps_label.setText("FPS: --")
        self.confidence_label.setText("Confidence: --")
        self._reset_fixation_display()


class FeedbackSystem(QObject):
    """
    Comprehensive feedback system coordinator.
    
    Manages audio and visual feedback, processes feedback events,
    and provides unified interface for user feedback during gaze tracking.
    """
    
    # Signals for feedback events
    feedback_event_processed = pyqtSignal(object)  # FeedbackEvent
    status_changed = pyqtSignal(str, str)  # status, color
    
    def __init__(self):
        """Initialize feedback system."""
        super().__init__()
        
        # Components
        self.audio_feedback = AudioFeedback()
        self.visual_panel = VisualFeedbackPanel()
        
        # Configuration
        self.config = {
            'audio_enabled': True,
            'visual_enabled': True,
            'audio_volume': 0.5,
            'feedback_priority_threshold': 1
        }
        
        # Event tracking
        self.event_history = []
        self.max_history_size = 100
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'audio_events_played': 0,
            'visual_updates': 0,
            'last_update_time': time.time()
        }
        
        logger.info("FeedbackSystem initialized")
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure feedback system.
        
        Args:
            config: Configuration dictionary
        """
        self.config.update(config)
        
        # Apply configuration
        if 'audio_volume' in config:
            self.audio_feedback.set_volume(config['audio_volume'])
        
        logger.info("Feedback system configured")
    
    def process_event(self, event_type: FeedbackType, message: str = "", 
                     data: Dict[str, Any] = None, priority: int = 1):
        """
        Process a feedback event.
        
        Args:
            event_type: Type of feedback event
            message: Event message
            data: Additional event data
            priority: Event priority (1=low, 2=medium, 3=high)
        """
        if data is None:
            data = {}
        
        # Create feedback event
        event = FeedbackEvent(
            event_type=event_type,
            message=message,
            data=data,
            timestamp=time.time(),
            priority=priority
        )
        
        # Check priority threshold
        if priority < self.config.get('feedback_priority_threshold', 1):
            return
        
        try:
            # Process audio feedback
            if self.config.get('audio_enabled', True):
                self.audio_feedback.play_feedback(event_type, data)
                self.stats['audio_events_played'] += 1
            
            # Process visual feedback
            if self.config.get('visual_enabled', True):
                self._process_visual_feedback(event)
                self.stats['visual_updates'] += 1
            
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
            
            self.stats['events_processed'] += 1
            
            # Emit signal
            self.feedback_event_processed.emit(event)
            
            logger.debug(f"Processed feedback event: {event_type.value}")
            
        except Exception as e:
            logger.error(f"Error processing feedback event: {e}")
    
    def _process_visual_feedback(self, event: FeedbackEvent):
        """
        Process visual feedback for an event.
        
        Args:
            event: Feedback event to process
        """
        event_type = event.event_type
        data = event.data
        
        if event_type == FeedbackType.GAZE_DETECTED:
            confidence = data.get('confidence', 1.0)
            self.visual_panel.update_confidence(confidence)
            
        elif event_type == FeedbackType.FIXATION_STARTED:
            duration = data.get('duration', 1.0)
            self.visual_panel.start_fixation_progress(duration)
            
        elif event_type == FeedbackType.FIXATION_PROGRESS:
            elapsed = data.get('elapsed_time', 0.0)
            self.visual_panel.update_fixation_progress(elapsed)
            
        elif event_type == FeedbackType.FIXATION_COMPLETED:
            self.visual_panel.complete_fixation()
            
        elif event_type == FeedbackType.ANNOTATION_CREATED:
            self.visual_panel.add_annotation()
            
        elif event_type == FeedbackType.ERROR_OCCURRED:
            self.visual_panel.update_status("Error: " + event.message, "#F44336")
            
        elif event_type == FeedbackType.SESSION_STARTED:
            self.visual_panel.update_status("Session Active", "#4CAF50")
            self.visual_panel.reset_statistics()
            
        elif event_type == FeedbackType.SESSION_ENDED:
            self.visual_panel.update_status("Session Ended", "#FFC107")
    
    def update_gaze_data(self, confidence: float, fps: float = None):
        """
        Update real-time gaze data display.
        
        Args:
            confidence: Current gaze confidence
            fps: Current processing FPS
        """
        self.visual_panel.update_confidence(confidence)
        
        if fps is not None:
            self.visual_panel.update_fps(fps)
        
        # Generate gaze detected event (low priority)
        self.process_event(
            FeedbackType.GAZE_DETECTED,
            data={'confidence': confidence, 'fps': fps},
            priority=1
        )
    
    def start_session(self):
        """Start feedback session."""
        self.process_event(
            FeedbackType.SESSION_STARTED,
            "Gaze tracking session started",
            priority=2
        )
        
        # Reset statistics
        self.stats['events_processed'] = 0
        self.stats['audio_events_played'] = 0
        self.stats['visual_updates'] = 0
        self.stats['last_update_time'] = time.time()
    
    def end_session(self):
        """End feedback session."""
        self.process_event(
            FeedbackType.SESSION_ENDED,
            "Gaze tracking session ended",
            priority=2
        )
    
    def report_error(self, error_message: str):
        """
        Report an error through the feedback system.
        
        Args:
            error_message: Error message to display
        """
        self.process_event(
            FeedbackType.ERROR_OCCURRED,
            error_message,
            priority=3
        )
    
    def get_visual_panel(self) -> VisualFeedbackPanel:
        """
        Get the visual feedback panel widget.
        
        Returns:
            Visual feedback panel widget
        """
        return self.visual_panel
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get feedback system statistics.
        
        Returns:
            Statistics dictionary
        """
        current_time = time.time()
        session_duration = current_time - self.stats['last_update_time']
        
        return {
            'events_processed': self.stats['events_processed'],
            'audio_events_played': self.stats['audio_events_played'],
            'visual_updates': self.stats['visual_updates'],
            'session_duration': session_duration,
            'events_per_second': self.stats['events_processed'] / (session_duration + 1e-6),
            'audio_enabled': self.config.get('audio_enabled', True),
            'visual_enabled': self.config.get('visual_enabled', True),
            'event_history_size': len(self.event_history)
        }
    
    def get_recent_events(self, count: int = 10) -> List[FeedbackEvent]:
        """
        Get recent feedback events.
        
        Args:
            count: Number of recent events to return
            
        Returns:
            List of recent feedback events
        """
        return self.event_history[-count:] if self.event_history else []
    
    def cleanup(self):
        """Clean up feedback system resources."""
        try:
            # Clean up audio
            if (hasattr(self.audio_feedback, 'media_player') and 
                self.audio_feedback.media_player is not None):
                self.audio_feedback.media_player.stop()
            
            # Clear event history
            self.event_history.clear()
            
            logger.info("Feedback system cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during feedback cleanup: {e}")