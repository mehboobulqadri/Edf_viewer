"""
Enhanced auto-move functionality with gaze-aware scrolling.

Extends the existing auto-move system to pause on fixations, resume after
annotations, and provide intelligent scrolling behavior for gaze-based review.

This module integrates with the main EDF viewer's auto-move functionality
while adding gaze-aware features for improved clinical workflow.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

logger = logging.getLogger(__name__)


class ScrollState(Enum):
    """Auto-scroll states."""
    STOPPED = "stopped"
    SCROLLING = "scrolling"
    PAUSED_FOR_FIXATION = "paused_fixation"
    PAUSED_FOR_ANNOTATION = "paused_annotation"
    WAITING_RESUME = "waiting_resume"
    COMPLETED = "completed"


class PauseReason(Enum):
    """Reasons for pausing auto-scroll."""
    FIXATION_DETECTED = "fixation_detected"
    ANNOTATION_CREATION = "annotation_creation"
    USER_INTERACTION = "user_interaction"
    ERROR_OCCURRED = "error_occurred"
    MANUAL_PAUSE = "manual_pause"


@dataclass
class ScrollConfiguration:
    """Configuration for gaze-enhanced auto-scroll."""
    base_scroll_speed: float = 2.5  # Seconds per time window
    fast_scroll_speed: float = 1.0  # Fast scroll speed
    slow_scroll_speed: float = 4.0  # Slow scroll speed
    
    # Pause behavior
    pause_on_fixation: bool = True
    fixation_pause_threshold: float = 0.5  # Minimum fixation duration to pause
    auto_resume_delay: float = 2.0  # Seconds to wait before auto-resume
    annotation_pause_duration: float = 1.0  # Extra pause after annotation
    
    # Progress tracking
    overlap_percentage: float = 10.0  # Percentage overlap between windows
    end_buffer_seconds: float = 5.0  # Buffer before end of data
    
    # Advanced features
    adaptive_speed: bool = True  # Adapt speed based on EEG complexity
    smart_pause_logic: bool = True  # Intelligent pause decisions
    progress_feedback: bool = True  # Provide progress updates


@dataclass
class ScrollProgress:
    """Progress tracking for auto-scroll."""
    current_time: float = 0.0
    total_duration: float = 0.0
    windows_completed: int = 0
    total_windows: int = 0
    annotations_created: int = 0
    scroll_speed: float = 2.5
    estimated_completion: float = 0.0  # Seconds remaining


class ScrollBehavior:
    """
    Configurable scrolling behaviors for different scenarios.
    
    Manages different scrolling patterns based on EEG content,
    user behavior, and annotation requirements.
    """
    
    def __init__(self):
        """Initialize scroll behavior manager."""
        self.behaviors = {
            'normal': {'speed': 2.5, 'sensitivity': 0.5},
            'detailed': {'speed': 4.0, 'sensitivity': 0.3},
            'quick': {'speed': 1.5, 'sensitivity': 0.7},
            'annotation_heavy': {'speed': 3.0, 'sensitivity': 0.4}
        }
        
        self.current_behavior = 'normal'
        self.adaptive_enabled = True
        
        logger.debug("ScrollBehavior initialized")
    
    def get_scroll_speed(self, context: Dict[str, Any] = None) -> float:
        """
        Get appropriate scroll speed based on context.
        
        Args:
            context: Current EEG and annotation context
            
        Returns:
            Scroll speed in seconds per window
        """
        base_speed = self.behaviors[self.current_behavior]['speed']
        
        if not self.adaptive_enabled or not context:
            return base_speed
        
        # Adjust speed based on EEG complexity
        complexity_factor = context.get('eeg_complexity', 1.0)
        annotation_density = context.get('annotation_density', 0.0)
        
        # Slow down for complex EEG or high annotation areas
        adjustment = 1.0 + (complexity_factor - 1.0) * 0.5 + annotation_density * 0.3
        
        adjusted_speed = base_speed * adjustment
        return max(1.0, min(6.0, adjusted_speed))  # Clamp between 1-6 seconds
    
    def should_pause_for_fixation(self, fixation_data: Dict[str, Any]) -> bool:
        """
        Determine if scrolling should pause for a fixation.
        
        Args:
            fixation_data: Information about the detected fixation
            
        Returns:
            True if scrolling should pause
        """
        duration = fixation_data.get('duration', 0.0)
        confidence = fixation_data.get('confidence', 0.0)
        stability = fixation_data.get('stability', 0.0)
        
        # Minimum thresholds for pause
        min_duration = 0.5
        min_confidence = 0.6
        min_stability = 0.5
        
        # Get behavior sensitivity
        sensitivity = self.behaviors[self.current_behavior]['sensitivity']
        
        # Adjust thresholds based on sensitivity
        adjusted_duration = min_duration * (1.1 - sensitivity)
        adjusted_confidence = min_confidence * (1.1 - sensitivity)
        
        should_pause = (duration >= adjusted_duration and
                       confidence >= adjusted_confidence and
                       stability >= min_stability)
        
        logger.debug(f"Pause decision: {should_pause} (duration={duration:.2f}s, "
                    f"confidence={confidence:.2f}, stability={stability:.2f})")
        
        return should_pause
    
    def set_behavior(self, behavior_name: str):
        """
        Set current scrolling behavior.
        
        Args:
            behavior_name: Name of behavior to use
        """
        if behavior_name in self.behaviors:
            self.current_behavior = behavior_name
            logger.info(f"Scroll behavior set to: {behavior_name}")
        else:
            logger.warning(f"Unknown behavior: {behavior_name}")


class PauseLogic:
    """
    Smart pause decision logic based on gaze patterns and EEG context.
    
    Implements intelligent decisions about when to pause, resume,
    and adjust scrolling based on multiple factors.
    """
    
    def __init__(self):
        """Initialize pause logic."""
        self.pause_history = []
        self.max_history_size = 50
        
        # Timing thresholds
        self.min_pause_duration = 1.0  # Minimum pause time
        self.max_pause_duration = 30.0  # Maximum automatic pause
        self.rapid_pause_threshold = 5.0  # Detect rapid pausing pattern
        
        logger.debug("PauseLogic initialized")
    
    def should_pause(self, fixation_data: Dict[str, Any], 
                    context: Dict[str, Any] = None) -> tuple[bool, PauseReason]:
        """
        Determine if scrolling should pause and why.
        
        Args:
            fixation_data: Current fixation information
            context: Additional context (EEG, user behavior)
            
        Returns:
            Tuple of (should_pause, reason)
        """
        current_time = time.time()
        
        # Check for rapid pausing pattern
        if self._is_rapid_pausing(current_time):
            logger.debug("Pause rejected - rapid pausing pattern detected")
            return False, PauseReason.USER_INTERACTION
        
        # Basic fixation quality check
        if not self._is_quality_fixation(fixation_data):
            return False, PauseReason.FIXATION_DETECTED
        
        # Context-aware decision
        if context:
            eeg_interest = context.get('eeg_interest_score', 0.5)
            if eeg_interest > 0.7:
                # High-interest EEG area - more likely to pause
                return True, PauseReason.FIXATION_DETECTED
            elif eeg_interest < 0.3:
                # Low-interest area - less likely to pause
                if fixation_data.get('duration', 0) < 1.0:
                    return False, PauseReason.FIXATION_DETECTED
        
        # Default decision based on fixation quality
        return True, PauseReason.FIXATION_DETECTED
    
    def calculate_pause_duration(self, fixation_data: Dict[str, Any],
                                reason: PauseReason) -> float:
        """
        Calculate appropriate pause duration.
        
        Args:
            fixation_data: Fixation information
            reason: Reason for pausing
            
        Returns:
            Pause duration in seconds
        """
        base_duration = 2.0
        
        if reason == PauseReason.FIXATION_DETECTED:
            # Base on fixation characteristics
            stability = fixation_data.get('stability', 0.5)
            confidence = fixation_data.get('confidence', 0.5)
            
            duration_factor = (stability + confidence) / 2.0
            base_duration = 1.0 + duration_factor * 2.0
            
        elif reason == PauseReason.ANNOTATION_CREATION:
            base_duration = 3.0  # Longer pause for annotation creation
        
        return max(self.min_pause_duration, 
                  min(self.max_pause_duration, base_duration))
    
    def _is_quality_fixation(self, fixation_data: Dict[str, Any]) -> bool:
        """Check if fixation meets quality thresholds."""
        duration = fixation_data.get('duration', 0.0)
        confidence = fixation_data.get('confidence', 0.0)
        stability = fixation_data.get('stability', 0.0)
        
        return (duration >= 0.3 and confidence >= 0.5 and stability >= 0.4)
    
    def _is_rapid_pausing(self, current_time: float) -> bool:
        """Check for rapid pausing pattern that might indicate issues."""
        # Clean old history
        self.pause_history = [t for t in self.pause_history 
                             if current_time - t < self.rapid_pause_threshold]
        
        # Add current pause
        self.pause_history.append(current_time)
        
        # Check for rapid pattern (>3 pauses in 5 seconds)
        return len(self.pause_history) > 3


class ProgressTracker:
    """
    Tracks progress through EDF data during auto-scroll review.
    
    Provides completion estimates, statistics, and progress feedback.
    """
    
    def __init__(self):
        """Initialize progress tracker."""
        self.start_time = None
        self.total_duration = 0.0
        self.window_duration = 10.0  # Default window size
        self.overlap_percentage = 10.0
        
        self.progress = ScrollProgress()
        self.session_stats = {
            'scroll_start_time': None,
            'total_pauses': 0,
            'total_pause_duration': 0.0,
            'annotations_created': 0,
            'windows_reviewed': 0
        }
        
        logger.debug("ProgressTracker initialized")
    
    def start_session(self, total_duration: float, window_duration: float):
        """
        Start a new scroll session.
        
        Args:
            total_duration: Total EDF data duration
            window_duration: Duration of each scroll window
        """
        self.start_time = time.time()
        self.total_duration = total_duration
        self.window_duration = window_duration
        
        # Calculate total windows
        effective_window = window_duration * (1 - self.overlap_percentage / 100)
        import math
        self.progress.total_windows = int(math.ceil(total_duration / effective_window))
        self.progress.total_duration = total_duration
        
        self.session_stats['scroll_start_time'] = self.start_time
        
        logger.info(f"Scroll session started: {total_duration:.1f}s data, "
                   f"{self.progress.total_windows} windows")
    
    def update_progress(self, current_time: float):
        """
        Update progress tracking.
        
        Args:
            current_time: Current position in EDF data
        """
        self.progress.current_time = current_time
        
        # Calculate windows completed
        effective_window = self.window_duration * (1 - self.overlap_percentage / 100)
        self.progress.windows_completed = int(current_time / effective_window)
        
        # Calculate completion percentage
        completion_percentage = current_time / self.total_duration if self.total_duration > 0 else 0
        
        # Estimate remaining time
        if self.start_time and completion_percentage > 0.1:  # After 10% completion
            elapsed_real_time = time.time() - self.start_time
            estimated_total_time = elapsed_real_time / completion_percentage
            self.progress.estimated_completion = estimated_total_time - elapsed_real_time
        
        self.session_stats['windows_reviewed'] = self.progress.windows_completed
    
    def add_pause(self, duration: float):
        """
        Record a pause in the session.
        
        Args:
            duration: Duration of the pause
        """
        self.session_stats['total_pauses'] += 1
        self.session_stats['total_pause_duration'] += duration
    
    def add_annotation(self):
        """Record an annotation creation."""
        self.progress.annotations_created += 1
        self.session_stats['annotations_created'] += 1
    
    def get_progress_report(self) -> Dict[str, Any]:
        """
        Get current progress report.
        
        Returns:
            Progress report dictionary
        """
        completion_percentage = (self.progress.current_time / self.progress.total_duration 
                               if self.progress.total_duration > 0 else 0) * 100
        
        return {
            'completion_percentage': completion_percentage,
            'current_time': self.progress.current_time,
            'total_duration': self.progress.total_duration,
            'windows_completed': self.progress.windows_completed,
            'total_windows': self.progress.total_windows,
            'annotations_created': self.progress.annotations_created,
            'estimated_completion_seconds': self.progress.estimated_completion,
            'session_stats': self.session_stats.copy()
        }
    
    def is_complete(self) -> bool:
        """Check if scroll session is complete."""
        return (self.progress.current_time >= 
                self.total_duration - self.window_duration / 2)


class GazeEnhancedAutoMove(QObject):
    """
    Enhanced auto-move controller with gaze-aware features.
    
    Coordinates with existing auto-move functionality while adding
    intelligent pause/resume behavior based on gaze patterns.
    """
    
    # Signals for communication with main application
    scroll_paused = pyqtSignal(str)  # Pause reason
    scroll_resumed = pyqtSignal()
    progress_updated = pyqtSignal(dict)  # Progress report
    annotation_opportunity = pyqtSignal(dict)  # Annotation suggestion
    session_completed = pyqtSignal(dict)  # Final statistics
    
    def __init__(self, main_window):
        """
        Initialize enhanced auto-move controller.
        
        Args:
            main_window: Reference to main EDF viewer window
        """
        super().__init__()
        
        self.main_window = main_window
        self.original_auto_move = None  # Reference to original auto-move
        
        # Components
        self.config = ScrollConfiguration()
        self.behavior = ScrollBehavior()
        self.pause_logic = PauseLogic()
        self.progress_tracker = ProgressTracker()
        
        # State management
        self.current_state = ScrollState.STOPPED
        self.pause_start_time = None
        self.resume_timer = QTimer()
        self.resume_timer.timeout.connect(self._auto_resume)
        self.resume_timer.setSingleShot(True)
        
        # Progress update timer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self._update_progress)
        self.progress_timer.start(1000)  # Update every second
        
        logger.info("GazeEnhancedAutoMove initialized")
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure enhanced auto-move settings.
        
        Args:
            config: Configuration dictionary
        """
        # Update configuration
        for key, value in config.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Update behavior if specified
        if 'scroll_behavior' in config:
            self.behavior.set_behavior(config['scroll_behavior'])
        
        logger.info("Enhanced auto-move configured")
    
    def connect_to_original_auto_move(self, auto_move_function: Callable):
        """
        Connect to the original auto-move functionality.
        
        Args:
            auto_move_function: Original auto-move function from main window
        """
        self.original_auto_move = auto_move_function
        logger.debug("Connected to original auto-move function")
    
    def start_enhanced_scroll(self, total_duration: float, window_duration: float):
        """
        Start enhanced auto-scroll session.
        
        Args:
            total_duration: Total data duration
            window_duration: Duration per window
        """
        if self.current_state != ScrollState.STOPPED:
            logger.warning("Cannot start scroll - already active")
            return False
        
        # Initialize session
        self.progress_tracker.start_session(total_duration, window_duration)
        self.current_state = ScrollState.SCROLLING
        
        # Start scrolling
        success = self._start_scrolling()
        
        if success:
            logger.info("Enhanced auto-scroll session started")
            self.progress_updated.emit(self.progress_tracker.get_progress_report())
            return True
        else:
            self.current_state = ScrollState.STOPPED
            return False
    
    def handle_fixation_detected(self, fixation_data: Dict[str, Any],
                                context: Dict[str, Any] = None):
        """
        Handle fixation detection during auto-scroll.
        
        Args:
            fixation_data: Information about detected fixation
            context: Additional context information
        """
        if self.current_state != ScrollState.SCROLLING:
            return
        
        # Check if we should pause
        if not self.config.pause_on_fixation:
            return
        
        should_pause, reason = self.pause_logic.should_pause(fixation_data, context)
        
        if should_pause and self.behavior.should_pause_for_fixation(fixation_data):
            self._pause_scrolling(reason, fixation_data)
    
    def handle_annotation_created(self, annotation_data: Dict[str, Any]):
        """
        Handle annotation creation during auto-scroll.
        
        Args:
            annotation_data: Information about created annotation
        """
        self.progress_tracker.add_annotation()
        
        # Extend pause for annotation processing
        if self.current_state == ScrollState.PAUSED_FOR_FIXATION:
            self.current_state = ScrollState.PAUSED_FOR_ANNOTATION
            
            # Extend resume timer
            additional_pause = self.config.annotation_pause_duration
            current_remaining = self.resume_timer.remainingTime()
            new_timeout = max(additional_pause * 1000, current_remaining + 500)
            
            self.resume_timer.start(int(new_timeout))
            
            logger.debug("Extended pause for annotation creation")
    
    def manual_resume(self):
        """Manually resume scrolling."""
        if self.current_state in [ScrollState.PAUSED_FOR_FIXATION, 
                                 ScrollState.PAUSED_FOR_ANNOTATION,
                                 ScrollState.WAITING_RESUME]:
            self._resume_scrolling()
    
    def manual_pause(self):
        """Manually pause scrolling."""
        if self.current_state == ScrollState.SCROLLING:
            self._pause_scrolling(PauseReason.MANUAL_PAUSE)
    
    def stop_enhanced_scroll(self):
        """Stop enhanced auto-scroll session."""
        if self.current_state == ScrollState.STOPPED:
            return
        
        # Stop timers
        self.resume_timer.stop()
        
        # Stop original auto-move if active
        if self.original_auto_move and hasattr(self.main_window, 'auto_move_active'):
            if self.main_window.auto_move_active:
                self.original_auto_move()  # Toggle off
        
        self.current_state = ScrollState.STOPPED
        
        # Emit completion statistics
        final_stats = self.progress_tracker.get_progress_report()
        self.session_completed.emit(final_stats)
        
        logger.info("Enhanced auto-scroll session stopped")
    
    def _start_scrolling(self) -> bool:
        """Start the actual scrolling process."""
        try:
            if self.original_auto_move:
                # Start original auto-move if not already active
                if hasattr(self.main_window, 'auto_move_active'):
                    if not self.main_window.auto_move_active:
                        self.original_auto_move()  # Toggle on
                        return True
                else:
                    # Fallback: call auto-move function
                    self.original_auto_move()
                    return True
            else:
                logger.error("No original auto-move function connected")
                return False
                
        except Exception as e:
            logger.error(f"Error starting scrolling: {e}")
            return False
    
    def _pause_scrolling(self, reason: PauseReason, 
                        fixation_data: Dict[str, Any] = None):
        """
        Pause scrolling with specified reason.
        
        Args:
            reason: Reason for pausing
            fixation_data: Fixation data if applicable
        """
        if self.current_state != ScrollState.SCROLLING:
            return
        
        # Pause original auto-move
        if (self.original_auto_move and hasattr(self.main_window, 'auto_move_active') 
            and self.main_window.auto_move_active):
            self.original_auto_move()  # Toggle off
        
        # Update state
        if reason == PauseReason.FIXATION_DETECTED:
            self.current_state = ScrollState.PAUSED_FOR_FIXATION
        elif reason == PauseReason.ANNOTATION_CREATION:
            self.current_state = ScrollState.PAUSED_FOR_ANNOTATION
        else:
            self.current_state = ScrollState.WAITING_RESUME
        
        self.pause_start_time = time.time()
        
        # Calculate pause duration
        if fixation_data:
            pause_duration = self.pause_logic.calculate_pause_duration(fixation_data, reason)
        else:
            pause_duration = self.config.auto_resume_delay
        
        # Start resume timer
        self.resume_timer.start(int(pause_duration * 1000))
        
        # Track pause
        self.progress_tracker.add_pause(pause_duration)
        
        # Emit signal
        self.scroll_paused.emit(reason.value)
        
        logger.debug(f"Scrolling paused: {reason.value}, resume in {pause_duration:.1f}s")
    
    def _auto_resume(self):
        """Automatically resume scrolling after pause timeout."""
        if self.current_state in [ScrollState.PAUSED_FOR_FIXATION,
                                 ScrollState.PAUSED_FOR_ANNOTATION,
                                 ScrollState.WAITING_RESUME]:
            self._resume_scrolling()
    
    def _resume_scrolling(self):
        """Resume scrolling from paused state."""
        try:
            # Restart original auto-move
            if (self.original_auto_move and hasattr(self.main_window, 'auto_move_active') 
                and not self.main_window.auto_move_active):
                self.original_auto_move()  # Toggle on
            
            self.current_state = ScrollState.SCROLLING
            self.pause_start_time = None
            
            # Emit signal
            self.scroll_resumed.emit()
            
            logger.debug("Scrolling resumed")
            
        except Exception as e:
            logger.error(f"Error resuming scrolling: {e}")
            self.current_state = ScrollState.STOPPED
    
    def _update_progress(self):
        """Update progress tracking."""
        if self.current_state == ScrollState.STOPPED:
            return
        
        # Get current position from main window
        if hasattr(self.main_window, 'view_start_time'):
            current_time = self.main_window.view_start_time
            self.progress_tracker.update_progress(current_time)
            
            # Check for completion
            if self.progress_tracker.is_complete():
                self.current_state = ScrollState.COMPLETED
                self.stop_enhanced_scroll()
                return
            
            # Emit progress update
            if self.config.progress_feedback:
                progress_report = self.progress_tracker.get_progress_report()
                self.progress_updated.emit(progress_report)
    
    def get_current_state(self) -> ScrollState:
        """Get current scroll state."""
        return self.current_state
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get enhanced auto-move statistics.
        
        Returns:
            Statistics dictionary
        """
        progress_report = self.progress_tracker.get_progress_report()
        
        return {
            'current_state': self.current_state.value,
            'configuration': {
                'base_speed': self.config.base_scroll_speed,
                'pause_on_fixation': self.config.pause_on_fixation,
                'auto_resume_delay': self.config.auto_resume_delay,
                'current_behavior': self.behavior.current_behavior
            },
            'progress': progress_report,
            'pause_start_time': self.pause_start_time
        }