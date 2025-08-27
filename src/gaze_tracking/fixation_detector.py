"""
Fixation Detection Algorithm for gaze tracking.

Implements multiple fixation detection algorithms including:
- I-VT (Velocity-Threshold) algorithm
- I-DT (Dispersion-Threshold) algorithm  
- I-MST (Minimum Spanning Tree) algorithm

Provides real-time fixation detection with configurable parameters
for clinical EEG review applications.
"""

import time
import math
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

from .gaze_tracker import GazePoint

logger = logging.getLogger(__name__)


class FixationAlgorithm(Enum):
    """Supported fixation detection algorithms."""
    I_VT = "I-VT"  # Velocity-Threshold
    I_DT = "I-DT"  # Dispersion-Threshold
    I_MST = "I-MST"  # Minimum Spanning Tree


@dataclass
class FixationPoint:
    """Represents a detected fixation."""
    start_time: float
    end_time: float
    x: float  # Average x coordinate (0-1)
    y: float  # Average y coordinate (0-1)
    duration: float  # Duration in seconds
    confidence: float  # Confidence score (0-1)
    gaze_points: List[GazePoint] = field(default_factory=list)
    dispersion: float = 0.0  # Spatial dispersion
    stability: float = 0.0  # Temporal stability
    
    @property
    def is_valid(self) -> bool:
        """Check if fixation meets minimum requirements."""
        return (self.duration > 0.1 and 
                self.confidence > 0.5 and
                len(self.gaze_points) >= 3)


@dataclass
class FixationConfig:
    """Configuration parameters for fixation detection."""
    algorithm: FixationAlgorithm = FixationAlgorithm.I_VT
    
    # I-VT parameters
    velocity_threshold: float = 30.0  # pixels/second
    
    # I-DT parameters
    dispersion_threshold: float = 50.0  # pixels
    duration_threshold: float = 0.1  # seconds
    
    # I-MST parameters
    mst_threshold: float = 25.0  # pixels
    
    # General parameters
    min_fixation_duration: float = 0.1  # seconds
    max_fixation_duration: float = 5.0  # seconds
    confidence_threshold: float = 0.7
    smoothing_window: int = 3
    noise_reduction: bool = True
    adaptive_thresholds: bool = False


class GazeDataBuffer:
    """
    Circular buffer for managing incoming gaze data with efficient
    access patterns for fixation detection algorithms.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize gaze data buffer.
        
        Args:
            max_size: Maximum number of gaze points to store
        """
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.timestamps = deque(maxlen=max_size)
        self._total_added = 0
        
    def add_point(self, gaze_point: GazePoint):
        """
        Add a new gaze point to the buffer.
        
        Args:
            gaze_point: New gaze point to add
        """
        self.buffer.append(gaze_point)
        self.timestamps.append(gaze_point.timestamp)
        self._total_added += 1
        
    def get_recent_points(self, duration: float) -> List[GazePoint]:
        """
        Get gaze points from the last N seconds.
        
        Args:
            duration: Time window in seconds
            
        Returns:
            List of gaze points within the time window
        """
        if not self.buffer:
            return []
        
        current_time = self.buffer[-1].timestamp
        cutoff_time = current_time - duration
        
        recent_points = []
        for point in reversed(self.buffer):
            if point.timestamp >= cutoff_time:
                recent_points.append(point)
            else:
                break
        
        return list(reversed(recent_points))
    
    def get_points_range(self, start_idx: int, end_idx: int) -> List[GazePoint]:
        """
        Get gaze points in a specific index range.
        
        Args:
            start_idx: Start index (negative indices supported)
            end_idx: End index (negative indices supported)
            
        Returns:
            List of gaze points in the range
        """
        if not self.buffer:
            return []
        
        # Convert negative indices
        if start_idx < 0:
            start_idx = len(self.buffer) + start_idx
        if end_idx < 0:
            end_idx = len(self.buffer) + end_idx
            
        # Clamp to valid range
        start_idx = max(0, min(start_idx, len(self.buffer) - 1))
        end_idx = max(0, min(end_idx, len(self.buffer)))
        
        return list(self.buffer)[start_idx:end_idx]
    
    def clear(self):
        """Clear all data from buffer."""
        self.buffer.clear()
        self.timestamps.clear()
        self._total_added = 0
    
    @property
    def size(self) -> int:
        """Get current buffer size."""
        return len(self.buffer)
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is at maximum capacity."""
        return len(self.buffer) >= self.max_size


class FixationDetector:
    """
    Real-time fixation detection with multiple algorithm support.
    
    Processes incoming gaze data and detects fixations using
    configurable algorithms and parameters.
    """
    
    def __init__(self, config: Optional[FixationConfig] = None):
        """
        Initialize fixation detector.
        
        Args:
            config: Fixation detection configuration
        """
        self.config = config or FixationConfig()
        self.buffer = GazeDataBuffer()
        self.current_fixation_candidates = []
        self.completed_fixations = []
        self.last_processing_time = 0.0
        
        # Statistics
        self.stats = {
            'total_points_processed': 0,
            'fixations_detected': 0,
            'average_fixation_duration': 0.0,
            'processing_time_ms': 0.0
        }
        
        logger.info(f"FixationDetector initialized with {self.config.algorithm.value} algorithm")
    
    def process_gaze_point(self, gaze_point: GazePoint) -> Optional[FixationPoint]:
        """
        Process a new gaze point and potentially return a completed fixation.
        
        Args:
            gaze_point: New gaze point to process
            
        Returns:
            Completed fixation if detected, None otherwise
        """
        start_time = time.time()
        
        # Add to buffer
        self.buffer.add_point(gaze_point)
        self.stats['total_points_processed'] += 1
        
        # Apply smoothing if enabled
        if self.config.noise_reduction:
            smoothed_point = self._smooth_gaze_point(gaze_point)
        else:
            smoothed_point = gaze_point
        
        # Detect fixations based on algorithm
        fixation = None
        if self.config.algorithm == FixationAlgorithm.I_VT:
            fixation = self._detect_fixation_ivt(smoothed_point)
        elif self.config.algorithm == FixationAlgorithm.I_DT:
            fixation = self._detect_fixation_idt(smoothed_point)
        elif self.config.algorithm == FixationAlgorithm.I_MST:
            fixation = self._detect_fixation_imst(smoothed_point)
        
        # Update statistics
        processing_time = (time.time() - start_time) * 1000
        self.stats['processing_time_ms'] = processing_time
        self.last_processing_time = time.time()
        
        if fixation and fixation.is_valid:
            self.completed_fixations.append(fixation)
            self.stats['fixations_detected'] += 1
            
            # Update average duration
            total_duration = sum(f.duration for f in self.completed_fixations)
            self.stats['average_fixation_duration'] = total_duration / len(self.completed_fixations)
            
            logger.debug(f"Fixation detected: duration={fixation.duration:.2f}s, "
                        f"position=({fixation.x:.3f}, {fixation.y:.3f})")
            
            return fixation
        
        return None
    
    def _smooth_gaze_point(self, gaze_point: GazePoint) -> GazePoint:
        """
        Apply smoothing to reduce noise in gaze data.
        
        Args:
            gaze_point: Raw gaze point
            
        Returns:
            Smoothed gaze point
        """
        if self.buffer.size < self.config.smoothing_window:
            return gaze_point
        
        # Get recent points for smoothing
        recent_points = self.buffer.get_points_range(-self.config.smoothing_window, -1)
        recent_points.append(gaze_point)
        
        # Apply moving average
        avg_x = sum(p.x for p in recent_points) / len(recent_points)
        avg_y = sum(p.y for p in recent_points) / len(recent_points)
        avg_confidence = sum(p.confidence for p in recent_points) / len(recent_points)
        
        return GazePoint(
            x=avg_x,
            y=avg_y,
            timestamp=gaze_point.timestamp,
            validity_left=gaze_point.validity_left,
            validity_right=gaze_point.validity_right,
            confidence=avg_confidence
        )
    
    def _detect_fixation_ivt(self, gaze_point: GazePoint) -> Optional[FixationPoint]:
        """
        I-VT (Velocity-Threshold) fixation detection.
        
        Args:
            gaze_point: Current gaze point
            
        Returns:
            Detected fixation if found
        """
        if self.buffer.size < 2:
            return None
        
        # Calculate velocity from last two points
        prev_point = self.buffer.get_points_range(-2, -1)[0]
        
        # Convert to pixel coordinates (assuming 1920x1080 screen)
        screen_width, screen_height = 1920, 1080
        
        dx = (gaze_point.x - prev_point.x) * screen_width
        dy = (gaze_point.y - prev_point.y) * screen_height
        dt = gaze_point.timestamp - prev_point.timestamp
        
        if dt <= 0:
            return None
        
        velocity = math.sqrt(dx*dx + dy*dy) / dt
        
        # Check if velocity is below threshold (potential fixation)
        if velocity < self.config.velocity_threshold:
            # Add to current fixation candidate
            if not self.current_fixation_candidates:
                self.current_fixation_candidates = [prev_point, gaze_point]
            else:
                self.current_fixation_candidates.append(gaze_point)
        else:
            # High velocity - end current fixation if it exists
            if len(self.current_fixation_candidates) >= 3:
                fixation = self._create_fixation_from_points(self.current_fixation_candidates)
                self.current_fixation_candidates = []
                return fixation
            else:
                self.current_fixation_candidates = []
        
        return None
    
    def _detect_fixation_idt(self, gaze_point: GazePoint) -> Optional[FixationPoint]:
        """
        I-DT (Dispersion-Threshold) fixation detection.
        
        Args:
            gaze_point: Current gaze point
            
        Returns:
            Detected fixation if found
        """
        # Get points within duration threshold
        window_points = self.buffer.get_recent_points(self.config.duration_threshold)
        
        if len(window_points) < 3:
            return None
        
        # Calculate dispersion
        dispersion = self._calculate_dispersion(window_points)
        
        # Convert threshold to normalized coordinates (assuming 1920x1080 screen)
        screen_width, screen_height = 1920, 1080
        norm_threshold = self.config.dispersion_threshold / min(screen_width, screen_height)
        
        if dispersion < norm_threshold:
            # Low dispersion - potential fixation
            duration = window_points[-1].timestamp - window_points[0].timestamp
            if duration >= self.config.min_fixation_duration:
                return self._create_fixation_from_points(window_points)
        
        return None
    
    def _detect_fixation_imst(self, gaze_point: GazePoint) -> Optional[FixationPoint]:
        """
        I-MST (Minimum Spanning Tree) fixation detection.
        
        Args:
            gaze_point: Current gaze point
            
        Returns:
            Detected fixation if found
        """
        # Simplified MST implementation for real-time processing
        # Use sliding window approach
        window_size = 10  # Number of recent points to consider
        recent_points = self.buffer.get_points_range(-window_size, -1)
        recent_points.append(gaze_point)
        
        if len(recent_points) < 5:
            return None
        
        # Calculate MST cost (simplified as average pairwise distance)
        total_distance = 0.0
        count = 0
        
        for i in range(len(recent_points)):
            for j in range(i + 1, len(recent_points)):
                dist = self._euclidean_distance(recent_points[i], recent_points[j])
                total_distance += dist
                count += 1
        
        if count == 0:
            return None
        
        avg_distance = total_distance / count
        
        # Convert threshold to normalized coordinates
        screen_width, screen_height = 1920, 1080
        norm_threshold = self.config.mst_threshold / min(screen_width, screen_height)
        
        if avg_distance < norm_threshold:
            duration = recent_points[-1].timestamp - recent_points[0].timestamp
            if duration >= self.config.min_fixation_duration:
                return self._create_fixation_from_points(recent_points)
        
        return None
    
    def _calculate_dispersion(self, points: List[GazePoint]) -> float:
        """
        Calculate spatial dispersion of gaze points.
        
        Args:
            points: List of gaze points
            
        Returns:
            Dispersion value (normalized coordinates)
        """
        if len(points) < 2:
            return 0.0
        
        # Find bounding box
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)
        
        # Return diagonal of bounding box
        return math.sqrt((max_x - min_x)**2 + (max_y - min_y)**2)
    
    def _euclidean_distance(self, p1: GazePoint, p2: GazePoint) -> float:
        """
        Calculate Euclidean distance between two gaze points.
        
        Args:
            p1: First gaze point
            p2: Second gaze point
            
        Returns:
            Distance in normalized coordinates
        """
        return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    
    def _create_fixation_from_points(self, points: List[GazePoint]) -> FixationPoint:
        """
        Create a fixation point from a list of gaze points.
        
        Args:
            points: List of gaze points that form the fixation
            
        Returns:
            FixationPoint object
        """
        if not points:
            raise ValueError("Cannot create fixation from empty point list")
        
        # Calculate average position
        avg_x = sum(p.x for p in points) / len(points)
        avg_y = sum(p.y for p in points) / len(points)
        
        # Calculate confidence (weighted by individual point confidence)
        total_confidence = sum(p.confidence for p in points)
        avg_confidence = total_confidence / len(points)
        
        # Calculate duration
        duration = points[-1].timestamp - points[0].timestamp
        
        # Calculate dispersion and stability
        dispersion = self._calculate_dispersion(points)
        stability = self._calculate_stability(points)
        
        return FixationPoint(
            start_time=points[0].timestamp,
            end_time=points[-1].timestamp,
            x=avg_x,
            y=avg_y,
            duration=duration,
            confidence=avg_confidence,
            gaze_points=points.copy(),
            dispersion=dispersion,
            stability=stability
        )
    
    def _calculate_stability(self, points: List[GazePoint]) -> float:
        """
        Calculate temporal stability of fixation.
        
        Args:
            points: List of gaze points
            
        Returns:
            Stability score (0-1, higher is more stable)
        """
        if len(points) < 3:
            return 0.0
        
        # Calculate variance in position over time
        avg_x = sum(p.x for p in points) / len(points)
        avg_y = sum(p.y for p in points) / len(points)
        
        variance = sum((p.x - avg_x)**2 + (p.y - avg_y)**2 for p in points) / len(points)
        
        # Convert variance to stability score (inverse relationship)
        stability = 1.0 / (1.0 + variance * 1000)  # Scale factor for normalization
        
        return min(1.0, max(0.0, stability))
    
    def get_recent_fixations(self, duration: float) -> List[FixationPoint]:
        """
        Get fixations detected in the last N seconds.
        
        Args:
            duration: Time window in seconds
            
        Returns:
            List of recent fixations
        """
        current_time = time.time()
        cutoff_time = current_time - duration
        
        return [f for f in self.completed_fixations if f.end_time >= cutoff_time]
    
    def clear_old_fixations(self, max_age: float = 300.0):
        """
        Remove fixations older than max_age seconds to prevent memory buildup.
        
        Args:
            max_age: Maximum age in seconds
        """
        current_time = time.time()
        cutoff_time = current_time - max_age
        
        self.completed_fixations = [f for f in self.completed_fixations if f.end_time >= cutoff_time]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detection statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = self.stats.copy()
        stats.update({
            'buffer_size': self.buffer.size,
            'total_fixations': len(self.completed_fixations),
            'current_candidates': len(self.current_fixation_candidates),
            'algorithm': self.config.algorithm.value,
            'last_processing_time': self.last_processing_time
        })
        
        return stats
    
    def update_config(self, config: FixationConfig):
        """
        Update fixation detection configuration.
        
        Args:
            config: New configuration
        """
        self.config = config
        logger.info(f"Configuration updated to {config.algorithm.value} algorithm")
    
    def reset(self):
        """Reset detector state."""
        self.buffer.clear()
        self.current_fixation_candidates = []
        self.completed_fixations = []
        self.stats = {
            'total_points_processed': 0,
            'fixations_detected': 0,
            'average_fixation_duration': 0.0,
            'processing_time_ms': 0.0
        }
        logger.info("FixationDetector reset")